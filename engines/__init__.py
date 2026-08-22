from novelcast.engines.base import BaseTTSEngine
from novelcast.engines.omnivoice import OmniVoiceEngine
from novelcast.engines.cosyvoice import CosyVoiceEngine
from novelcast.engines.kokoro import KokoroEngine
from novelcast.engines.elevenlabs import ElevenLabsEngine
from novelcast.engines.qwen3 import Qwen3TTSEngine

def get_engine(name: str = "omnivoice", **kwargs) -> BaseTTSEngine:
    name = name.lower().strip()
    if name == "omnivoice":
        return OmniVoiceEngine(**kwargs)
    elif name in ["qwen3", "qwen3-tts", "qwen"]:
        return Qwen3TTSEngine(**kwargs)
    elif name in ["cosyvoice", "cosyvoice3"]:
        return CosyVoiceEngine(**kwargs)
    elif name == "kokoro":
        return KokoroEngine(**kwargs)
    elif name == "elevenlabs":
        return ElevenLabsEngine(**kwargs)
    else:
        raise ValueError(f"Unknown TTS engine '{name}'. Supported: omnivoice, qwen3, cosyvoice, kokoro, elevenlabs")

__all__ = [
    "BaseTTSEngine",
    "OmniVoiceEngine",
    "Qwen3TTSEngine",
    "CosyVoiceEngine",
    "KokoroEngine",
    "ElevenLabsEngine",
    "get_engine"
]
