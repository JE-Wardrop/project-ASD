import os

from openai import OpenAI


def _truncate_words(text: str, limit: int = 45) -> str:
    words = " ".join(text.split()).split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit]) + " ..."


class AIRunner:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.implementation_model = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
        self.review_model = os.getenv("OLLAMA_REVIEW_MODEL", "llama3.1:8b")
        # Used when the review model cannot run (e.g. llama3.1:8b out of memory),
        # same rule as multi-agent-server/agents/reviewer_agent.py.
        self.review_fallback_model = os.getenv("OLLAMA_REVIEW_FALLBACK_MODEL", self.implementation_model)
        self.client = OpenAI(base_url=self.base_url, api_key="ollama", timeout=180.0)

    def call(self, system_prompt: str, user_prompt: str, *, review: bool = False, max_tokens: int = 180) -> tuple[str | None, str | None]:
        if not review:
            return self._call(self.implementation_model, system_prompt, user_prompt, max_tokens)

        output, err = self._call(self.review_model, system_prompt, user_prompt, max_tokens)
        if err is None or self.review_fallback_model == self.review_model:
            return output, err

        output, fallback_err = self._call(self.review_fallback_model, system_prompt, user_prompt, max_tokens)
        if fallback_err:
            return None, f"{err}; fallback also failed: {fallback_err}"
        return f"[reviewed by {self.review_fallback_model}: {self.review_model} unavailable] {output}", None

    def _call(self, model_name: str, system_prompt: str, user_prompt: str, max_tokens: int) -> tuple[str | None, str | None]:
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                return "No response generated.", None
            return _truncate_words(content), None
        except Exception as exc:
            return None, f"Model call failed ({model_name}): {exc}"