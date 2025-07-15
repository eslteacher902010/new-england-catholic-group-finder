FROM python:3.12.6 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN python -m venv .venv
COPY requirements.txt ./
RUN .venv/bin/pip install -r requirements.txt

FROM python:3.12.6-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY . .

CMD [".venv/bin/gunicorn", "main:app", "--bind", "0.0.0.0:8080"]
