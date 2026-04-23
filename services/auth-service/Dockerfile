FROM python:3.12-slim

WORKDIR /code

COPY services/auth-service/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY libs /code/libs
COPY services/auth-service/app /code/app

ENV PYTHONPATH=/code

RUN adduser --disabled-password --gecos '' appuser

COPY services/auth-service/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh && mkdir -p /data && chown appuser:appuser /data

USER root
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
