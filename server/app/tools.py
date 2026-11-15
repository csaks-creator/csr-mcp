from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.nova_service import ACT_TIMEOUT_SECONDS, nova_session
from app.security import verify_token

router = APIRouter(tags=["nova"], dependencies=[Depends(verify_token)])


class SearchResult(BaseModel):
    title: str
    url: str | None = None
    snippet: str | None = None


class SearchResults(BaseModel):
    results: list[SearchResult]


class SearchRequest(BaseModel):
    url: str = Field(description="Absolute http(s) URL of the website to search")
    query: str = Field(min_length=1, max_length=300, description="Text to search for")
    max_results: int = Field(default=5, ge=1, le=10)


class ExtractRequest(BaseModel):
    url: str = Field(description="Absolute http(s) URL of the page")
    instruction: str = Field(min_length=1, max_length=1000, description="What to read or extract from the page")
    json_schema: dict[str, Any] | None = Field(
        default=None, description="Optional JSON Schema for structured output; plain text is returned if omitted"
    )
    max_steps: int = Field(default=10, ge=1, le=30)


class ExtractResponse(BaseModel):
    data: Any


class FillFormRequest(BaseModel):
    url: str = Field(description="Absolute http(s) URL of the page containing the form")
    fields: dict[str, str] = Field(
        min_length=1, max_length=25, description="Map of visible field label to the value to enter"
    )
    submit: bool = Field(default=False, description="Submit the form after filling it in")
    max_steps: int = Field(default=15, ge=1, le=30)


class FillFormResponse(BaseModel):
    submitted: bool
    report: str | None


@router.post(
    "/search",
    operation_id="search_website",
    summary="Search a website",
    description="Open a website in a browser, use its search box and return the top results.",
)
def search_website(req: SearchRequest) -> SearchResults:
    with nova_session(req.url) as nova:
        nova.act(
            f"Search for {req.query!r} using the site's search box and press enter to submit.",
            max_steps=10,
            timeout=ACT_TIMEOUT_SECONDS,
        )
        res = nova.act_get(
            f"Return the top {req.max_results} search results on the page.",
            schema=SearchResults.model_json_schema(),
            max_steps=5,
            timeout=ACT_TIMEOUT_SECONDS,
        )
    if not res.matches_schema:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not read search results from the page")
    results = SearchResults.model_validate(res.parsed_response)
    return SearchResults(results=results.results[: req.max_results])


@router.post(
    "/extract",
    operation_id="extract_page_data",
    summary="Extract data from a web page",
    description="Open a page in a browser and extract information, optionally as JSON matching a schema.",
)
def extract_page_data(req: ExtractRequest) -> ExtractResponse:
    with nova_session(req.url) as nova:
        if req.json_schema:
            res = nova.act_get(
                req.instruction, schema=req.json_schema, max_steps=req.max_steps, timeout=ACT_TIMEOUT_SECONDS
            )
            if not res.matches_schema:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Page data did not match json_schema")
            return ExtractResponse(data=res.parsed_response)
        res = nova.act_get(req.instruction, max_steps=req.max_steps, timeout=ACT_TIMEOUT_SECONDS)
        return ExtractResponse(data=res.response)


@router.post(
    "/fill_form",
    operation_id="fill_form",
    summary="Fill in a web form",
    description=(
        "Open a page, fill in form fields by label and optionally submit. "
        "Do not pass passwords or payment details: they would appear in screenshots and logs."
    ),
)
def fill_form(req: FillFormRequest) -> FillFormResponse:
    lines = "\n".join(f"- {label}: {value}" for label, value in req.fields.items())
    ending = "Then submit the form." if req.submit else "Do not submit the form."
    with nova_session(req.url) as nova:
        res = nova.act_get(
            f"Fill in the form on this page with these values (field label: value):\n{lines}\n"
            f"{ending} Finally, briefly report which fields you filled in.",
            max_steps=req.max_steps,
            timeout=ACT_TIMEOUT_SECONDS,
        )
    return FillFormResponse(submitted=req.submit, report=res.response)
