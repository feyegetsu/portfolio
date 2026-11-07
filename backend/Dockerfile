FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home api
USER api

EXPOSE 8080
# Хостинг (Render, Railway, Fly) сам задаёт порт в PORT; локально — 8080
ENV PORT=8080
# За nginx укажите его адрес в FORWARDED_ALLOW_IPS: тогда лимиты считаются по реальному IP посетителя
ENV FORWARDED_ALLOW_IPS=127.0.0.1
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health', timeout=2)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips \"$FORWARDED_ALLOW_IPS\""]
