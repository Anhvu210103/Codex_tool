FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Ho_Chi_Minh

WORKDIR /app

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY . .

RUN useradd --system --uid 10001 mailnotes \
    && mkdir -p /app/.local \
    && chown -R mailnotes:mailnotes /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       poppler-utils \
    && rm -rf /var/lib/apt/lists/*

USER mailnotes

EXPOSE 8080

# Thay bằng entry point web thực tế của dự án.
CMD ["python", "-m", "mailnotes.web"]
