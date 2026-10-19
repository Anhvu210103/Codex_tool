FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MAILNOTES_DATA_DIR=/data \
    MAILNOTES_INBOX_DIR=/inbox \
    MAILNOTES_PUBLIC_URL=http://localhost:8080

WORKDIR /app
COPY requirements-web.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements-web.txt \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /data /inbox \
    && chown app:app /data /inbox

COPY --chown=app:app config.json ./
COPY --chown=app:app examples ./examples
COPY --chown=app:app chrome-extension ./chrome-extension
COPY --chown=app:app mailnotes ./mailnotes

USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3))['app']=='mailnotes'"]
CMD ["python", "-m", "mailnotes.web", "--host", "0.0.0.0", "--port", "8080"]
