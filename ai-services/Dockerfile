# AI-Mode service (dung chung)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Trong compose, Ollama la mot container ten "ollama"
ENV OLLAMA_BASE_URL=http://ollama:11434/v1
ENV LLM_MODEL=qwen2.5:1.5b
ENV PORT=8000

EXPOSE 8000

CMD ["python", "app.py"]
