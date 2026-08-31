FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app.py ./app.py
COPY ./services ./services
# COPY prompts/service ./prompts/service
# COPY prompts/lab4 ./prompts/lab4

EXPOSE 5001

CMD ["python", "app.py"]