FROM python:3.12-slim

WORKDIR /app

COPY services/regulatory-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY libs /app/libs
COPY services/regulatory-service/app /app/app

ENV PYTHONPATH=/app

EXPOSE 8025

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8025"]
