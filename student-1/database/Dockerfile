FROM python:3.11-slim

WORKDIR /student-1/database

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements

COPY cm_CRUD.py .
COPY init_db.py .

RUN python init_db.py

EXPOSE 5002

CMD ["python", "app.py"]