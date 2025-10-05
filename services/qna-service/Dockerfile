FROM python:3.12-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

# sentence-transformers requires torch, which is a large dependency.
# This will increase the build time for this service.
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
