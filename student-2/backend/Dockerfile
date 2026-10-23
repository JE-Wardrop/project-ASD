FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Build context is student-2/backend (prompts/ lives inside it), so the same
# image builds in docker-compose and in Azure (scripts/clouddeployment/deploy-azure.sh).
COPY . .

EXPOSE 5001

CMD ["python", "app.py"]
