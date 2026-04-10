FROM python:3.12-slim

WORKDIR /code

COPY ./services/agent-service/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./libs /code/libs
COPY ./services/agent-service/app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
