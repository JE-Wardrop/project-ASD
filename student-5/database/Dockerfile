FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

ENV DB_PATH=/data/transactions.db

ENV PORT=8000

EXPOSE 8000
CMD ["python", "app.py"]