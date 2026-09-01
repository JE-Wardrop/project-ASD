FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DB_URL=http://student5-db:8000
ENV ACCOUNTS_URL=http://student2-backend:8000
ENV NOTIFICATIONS_URL=http://student3-backend:8000

ENV BACKEND_URL=http://localhost:8205

ENV PORT=8000
EXPOSE 8000

CMD ["python", "app.py"]