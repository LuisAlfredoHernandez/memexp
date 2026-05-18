FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE = 1
ENV PYTHONUNBUFFERED = 1

WORKDIR /code

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY ./app /code/app

CMD ["fastapi", "dev", "app/main.py", "--host", "0.0.0.0", "--port", "80"]
