FROM python:3.12-slim
WORKDIR /code

COPY ./services/user-profile-service/requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./libs /code/libs
COPY ./services/user-profile-service/app /code/app
COPY ./services/user-profile-service/alembic.ini /code/alembic.ini
COPY ./services/user-profile-service/alembic /code/alembic

RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
