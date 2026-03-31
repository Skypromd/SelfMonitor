FROM python:3.12-slim

WORKDIR /code

COPY ./services/transactions-service/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./libs /code/libs
COPY ./services/transactions-service/app /code/app
COPY ./services/transactions-service/alembic.ini /code/alembic.ini
COPY ./services/transactions-service/alembic /code/alembic

RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
