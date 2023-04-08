FROM python:3.10-alpine

RUN apk add --no-cache bash

WORKDIR /app
COPY . .

ENTRYPOINT ["bash", "run.sh"]
