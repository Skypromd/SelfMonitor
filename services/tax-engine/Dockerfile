FROM python:3.12-slim

WORKDIR /code

COPY ./services/tax-engine/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./libs /code/libs
COPY ./services/tax-engine/app /code/app

RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
