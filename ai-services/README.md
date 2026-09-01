# AI-Mode Service

Lop bao dung chung quanh Ollama cho ca nhom 44.

    Frontend -> Backend/API -> ai-service (8090) -> Ollama (11434) -> LLM

## Contract

    POST /ai/generate
    { "prompt": "...", "model": "qwen2.5:1.5b" }   # model khong bat buoc

    -> 200  { "response": "...", "model": "..." }
    -> 400  { "error": "prompt is required" }
    -> 503  { "error": "AI model is not available", "detail": "..." }

    GET /health
    -> 200  { "status": "ok", "ollama": "up", "models": [...] }
    -> 503  { "status": "degraded", "ollama": "down" }

## Chay local

    pip install -r requirements.txt
    PORT=8090 python app.py

Can Ollama dang chay tren may va da co model:

    ollama pull qwen2.5:1.5b

## Bien moi truong

| Bien       | Mac dinh                 | Y nghia                     |
|------------|--------------------------|-----------------------------|
| OLLAMA_BASE_URL | http://localhost:11434/v1 | Dia chi Ollama (endpoint /v1) |
| LLM_MODEL  | qwen2.5:1.5b             | Model mac dinh cho ca nhom  |
| AI_TIMEOUT | 120                      | Giay cho mot cau tra loi    |
| PORT       | 8000                     | Cong lang nghe              |
