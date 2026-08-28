import os
import json
import time
import requests
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

DEFAULT_PRESETS = {
    "ollama": {
        "name": "Ollama (Local)",
        "type": "local",
        "api_base": "http://localhost:11434/v1",
        "api_key": "",
        "default_model": "qwen2.5:7b",
        "models": ["qwen2.5:7b", "qwen2.5:14b", "llama3.1:8b", "mistral:latest", "gemma2:9b"],
        "description": "Fast local private inference with Ollama on Mac/Linux/Windows."
    },
    "lmstudio": {
        "name": "LM Studio (Local)",
        "type": "local",
        "api_base": "http://localhost:1234/v1",
        "api_key": "",
        "default_model": "local-model",
        "models": ["local-model"],
        "description": "Local OpenAI-compatible server running in LM Studio."
    },
    "vllm": {
        "name": "vLLM / llama.cpp (Local)",
        "type": "local",
        "api_base": "http://localhost:8000/v1",
        "api_key": "",
        "default_model": "default",
        "models": ["default"],
        "description": "High-throughput local vLLM, llama.cpp, or Aphrodite server."
    },
    "deepseek": {
        "name": "DeepSeek API",
        "type": "cloud",
        "api_base": "https://api.deepseek.com/v1",
        "api_key": "",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "description": "Ultra-affordable, state-of-the-art literary reasoning and Spanish comprehension."
    },
    "openai": {
        "name": "OpenAI",
        "type": "cloud",
        "api_base": "https://api.openai.com/v1",
        "api_key": "",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
        "description": "OpenAI flagship models for nuanced dialogue direction."
    },
    "groq": {
        "name": "Groq Cloud",
        "type": "cloud",
        "api_base": "https://api.groq.com/openai/v1",
        "api_key": "",
        "default_model": "llama-3.3-70b-versatile",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "description": "Ultra-fast LPU inference (500+ tokens/sec)."
    },
    "gemini": {
        "name": "Google Gemini",
        "type": "cloud",
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key": "",
        "default_model": "gemini-2.5-flash",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "description": "Google's Gemini models with massive context window and lightning-fast dialogue reasoning."
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "cloud",
        "api_base": "https://openrouter.ai/api/v1",
        "api_key": "",
        "default_model": "deepseek/deepseek-chat",
        "models": ["deepseek/deepseek-chat", "meta-llama/llama-3.3-70b-instruct", "anthropic/claude-3.5-haiku", "google/gemini-2.0-flash-exp:free"],
        "description": "Unified gateway to every major open-source and commercial LLM."
    },
    "custom": {
        "name": "Custom OpenAI-Compatible API",
        "type": "custom",
        "api_base": "http://localhost:8080/v1",
        "api_key": "",
        "default_model": "custom-model",
        "models": ["custom-model"],
        "description": "Any self-hosted or proxy endpoint supporting the OpenAI /chat/completions API."
    }
}

class LLMProviderConfig(BaseModel):
    name: str
    type: str = "local" # local, cloud, custom
    api_base: str
    api_key: str = ""
    default_model: str
    models: List[str] = Field(default_factory=list)
    description: str = ""
    temperature: float = 0.2
    timeout_seconds: int = 45

class LLMGlobalConfig(BaseModel):
    active_provider: str = "ollama"
    active_model: str = "qwen2.5:7b"
    providers: Dict[str, LLMProviderConfig] = Field(default_factory=dict)

class LLMConfigManager:
    """
    Manages loading, saving, testing, and querying LLM providers and credentials.
    """

    def __init__(self, config_path: str = "llm_config.json"):
        self.config_path = config_path
        self.config = self._load()

    def _load(self) -> LLMGlobalConfig:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cfg = LLMGlobalConfig(**data)
                    # Auto-inject any missing presets (e.g. newly added Gemini)
                    updated = False
                    for key, p in DEFAULT_PRESETS.items():
                        if key not in cfg.providers:
                            cfg.providers[key] = LLMProviderConfig(**p)
                            updated = True
                    if updated:
                        self._save_raw(cfg)
                    return cfg
            except Exception as e:
                print(f"[LLMConfigManager] Warning loading {self.config_path}: {e}. Creating default.")
        
        # Build initial default from presets
        providers = {}
        for key, p in DEFAULT_PRESETS.items():
            providers[key] = LLMProviderConfig(**p)
        
        cfg = LLMGlobalConfig(
            active_provider="ollama",
            active_model="qwen2.5:7b",
            providers=providers
        )
        self._save_raw(cfg)
        return cfg

    def _save_raw(self, cfg: LLMGlobalConfig):
        os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg.dict(), f, indent=2, ensure_ascii=False)

    def save(self):
        self._save_raw(self.config)

    def get_provider(self, provider_id: Optional[str] = None) -> LLMProviderConfig:
        p_id = provider_id or self.config.active_provider
        if p_id not in self.config.providers:
            if "ollama" in self.config.providers:
                return self.config.providers["ollama"]
            # Fallback
            return list(self.config.providers.values())[0]
        return self.config.providers[p_id]

    def set_active(self, provider_id: str, model: Optional[str] = None):
        if provider_id in self.config.providers:
            self.config.active_provider = provider_id
            if model:
                self.config.active_model = model
            else:
                self.config.active_model = self.config.providers[provider_id].default_model
            self.save()

    def update_provider(
        self,
        provider_id: str,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        models: Optional[List[str]] = None,
        temperature: Optional[float] = None
    ):
        if provider_id not in self.config.providers:
            if provider_id in DEFAULT_PRESETS:
                self.config.providers[provider_id] = LLMProviderConfig(**DEFAULT_PRESETS[provider_id])
            else:
                self.config.providers[provider_id] = LLMProviderConfig(
                    name=provider_id.title(),
                    api_base=api_base or "http://localhost:8080/v1",
                    default_model=default_model or "default"
                )

        prov = self.config.providers[provider_id]
        if api_base is not None: prov.api_base = api_base.rstrip("/")
        if api_key is not None: prov.api_key = api_key
        if default_model is not None: prov.default_model = default_model
        if models is not None: prov.models = models
        if temperature is not None: prov.temperature = temperature
        self.save()

    def test_connection(self, provider_id: str, model_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Tests whether the specified LLM provider endpoint is reachable and responsive.
        """
        prov = self.get_provider(provider_id)
        model = model_override or prov.default_model
        endpoint = f"{prov.api_base.rstrip('/')}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if prov.api_key:
            headers["Authorization"] = f"Bearer {prov.api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a test assistant. Answer with 1 word: OK"},
                {"role": "user", "content": "ping"}
            ],
            "max_tokens": 10,
            "temperature": 0.0
        }

        start_t = time.time()
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=12)
            latency_ms = round((time.time() - start_t) * 1000, 1)

            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                return {
                    "success": True,
                    "provider": provider_id,
                    "model": model,
                    "latency_ms": latency_ms,
                    "reply": reply,
                    "message": f"✓ Connected successfully ({latency_ms}ms)"
                }
            else:
                return {
                    "success": False,
                    "provider": provider_id,
                    "model": model,
                    "status_code": resp.status_code,
                    "latency_ms": latency_ms,
                    "error": resp.text[:200],
                    "message": f"Server returned error code {resp.status_code}: {resp.text[:120]}"
                }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "provider": provider_id,
                "model": model,
                "message": f"Connection refused at {prov.api_base}. Is your local LLM (Ollama/LM Studio/vLLM) running?"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "provider": provider_id,
                "model": model,
                "message": f"Connection timed out (12s) to {prov.api_base}."
            }
        except Exception as e:
            return {
                "success": False,
                "provider": provider_id,
                "model": model,
                "message": f"Connection test failed: {str(e)}"
            }
