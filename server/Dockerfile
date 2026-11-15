FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    NOVA_ACT_SKIP_PLAYWRIGHT_INSTALL=1 \
    NOVA_ACT_BROWSER_ARGS="--no-sandbox --disable-dev-shm-usage --disable-gpu"

WORKDIR /srv

COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
 && pip install --no-cache-dir -r requirements.txt \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

COPY app ./app

RUN useradd --create-home --uid 10001 mcp && chmod -R a+rX /ms-playwright
USER mcp

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
