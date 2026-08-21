README


https://github.com/Georges034302/asd-labs/blob/main/AI_Agent_Configuration_Guide.md

Instructions for start up
Windows:


Linux:


Runtime checks for Ollama:
Windows:
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" --version
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
& "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" ps
curl.exe http://127.0.0.1:11434


Linux:
ollama serve
ollama --version
ollama list
ollama ps
curl http://127.0.0.1:11434


ollama run qwen2.5:0.5b

ollama pull deepseek-r1:8b
ollama run deepseek-r1:8b

Model API checks:
curl http://localhost:11434
curl http://localhost:11434/api/tags



