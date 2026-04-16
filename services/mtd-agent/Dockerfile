FROM python:3.12-slim

WORKDIR /code

COPY ./services/mtd-agent/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./libs /code/libs
COPY ./services/mtd-agent/app /code/app

ENV PYTHONPATH=/code

EXPOSE 8022

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8022"]
