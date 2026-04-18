FROM python:3.12-slim

WORKDIR /code

COPY services/finops-monitor/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt

COPY libs /code/libs
COPY services/finops-monitor/app /code/app

EXPOSE 8021

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8021"]
