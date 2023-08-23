from python:3.8-alpine

WORKDIR /app
COPY . .

RUN apk add --no-cache --virtual .build-deps gcc musl-dev && pip install --no-cache-dir -r requirements.txt && apk del .build-deps

ENV PYTHONUNBUFFERED=0

CMD ["python", "-u", "main.py"]
