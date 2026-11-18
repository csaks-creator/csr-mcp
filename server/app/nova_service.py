import os
import tempfile
import threading
from contextlib import contextmanager
from typing import Iterator

from fastapi import HTTPException, status
from nova_act import (
    ActAgentError,
    ActRateLimitExceededError,
    ActStateGuardrailError,
    NovaAct,
    NovaActError,
)
from nova_act.types.errors import AuthError

from app.security import state_guardrail, validate_url

_slots = threading.BoundedSemaphore(int(os.environ.get("MAX_CONCURRENT_SESSIONS", "2")))
ACT_TIMEOUT_SECONDS = int(os.environ.get("ACT_TIMEOUT_SECONDS", "180"))


@contextmanager
def nova_session(url: str) -> Iterator[NovaAct]:
    """Open a headless Nova Act browser session on a validated URL, limited by MAX_CONCURRENT_SESSIONS."""
    validate_url(url)
    logs_dir = os.environ.get("NOVA_LOGS_DIR", os.path.join(tempfile.gettempdir(), "nova_act_logs"))
    os.makedirs(logs_dir, exist_ok=True)  # NovaAct raises InvalidPath if it is missing
    if not _slots.acquire(blocking=False):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "All browser sessions are busy; retry shortly")
    try:
        with NovaAct(
            starting_page=url,
            headless=os.environ.get("NOVA_HEADLESS", "1") == "1",
            tty=False,
            state_guardrail=state_guardrail,
            logs_directory=logs_dir,
        ) as nova:
            yield nova
    except HTTPException:
        raise
    except ActStateGuardrailError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Navigation blocked: {e}")
    except ActRateLimitExceededError:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Nova Act rate limit exceeded")
    except ActAgentError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Nova Act could not complete the task: {e}")
    except AuthError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Nova Act authentication failed; check NOVA_ACT_API_KEY")
    except NovaActError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Nova Act error: {e}")
    finally:
        _slots.release()
