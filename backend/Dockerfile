FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

RUN useradd --create-home api
USER api

EXPOSE 8080
# Хостинг (Render, Railway, Fly) сам задаёт порт в PORT; локально — 8080
ENV PORT=8080
# IP посетителя берётся из X-Forwarded-For по числу доверенных прокси справа (TRUSTED_PROXY_HOPS, см. app/deps.py).
# Заголовки прокси uvicorn не разбирает: request.client остаётся адресом соединения, подделать его нельзя
ENV TRUSTED_PROXY_HOPS=0
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=2)"
# Сначала миграции схемы (python -m app.migrate), затем API
CMD ["sh", "-c", "python -m app.migrate && exec uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\" --no-proxy-headers"]
