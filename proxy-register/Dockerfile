from python:3.8-alpine

WORKDIR /app
COPY . .

RUN apk add --no-cache gcc python3-dev musl-dev linux-headers

RUN pip install -r requirements.txt

ENV PYTHONUNBUFFERED=0

CMD ["python", "-u", "main.py"]
