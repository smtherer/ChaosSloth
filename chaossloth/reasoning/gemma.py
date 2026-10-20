import requests
from typing import Dict

class LocalGemmaReasoner:
    def __init__(self, endpoint: str = "http://localhost:11434/api/generate", model: str = "gemma2:2b"):
        self.endpoint = endpoint
        self.model = model

    def analyze_concurrency_hazard(self, code_snippet: str, variable_name: str) -> Dict[str, str]:
        prompt = (
            f"You are an expert formal concurrency engineer. In 2 concise sentences, "
            f"diagnose the race hazard on `{variable_name}` and explain why an atomic critical section is required:\n\n"
            f"{code_snippet}\n\nDiagnosis:"
        )
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 120}
            }
            res = requests.post(self.endpoint, json=payload, timeout=30.0)
            if res.status_code == 200:
                raw_text = res.json().get("response", "").strip()
                if raw_text:
                    return {"diagnosis": raw_text}
        except Exception:
            pass

        return {
            "diagnosis": f"Interleaving collision exposed on `{variable_name}`. Unsynchronized mutation across event loop yield points."
        }
