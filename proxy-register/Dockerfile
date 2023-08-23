from python:3.8

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt 

ENV PYTHONUNBUFFERED=0

CMD ["python", "-u", "main.py"]
