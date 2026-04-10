FROM python:3.12-slim

WORKDIR /code

COPY ./services/documents-service/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./libs /code/libs
COPY ./services/documents-service/app /code/app
COPY ./services/documents-service/alembic.ini /code/alembic.ini
COPY ./services/documents-service/alembic /code/alembic

RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
