import os
import requests
from typing import Optional
from novelcast.engines.base import BaseTTSEngine
from novelcast.core.schema import Segment
from novelcast.core.voice_bank import VoiceBank

class ElevenLabsEngine(BaseTTSEngine):
    """
    ElevenLabs Cloud API TTS Engine.
    """

    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "cache_elevenlabs"):
        super().__init__(name="elevenlabs", cache_dir=cache_dir)
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")

    def synthesize_chunk(self, segment: Segment, voice_bank: VoiceBank, output_path: str) -> bool:
        if not self.api_key:
            return False

        char_info = voice_bank.get_character(segment.speaker)
        voice_id = getattr(char_info, "voice_id", None) or "21m00Tcm4TlvDq8ikWAM" # Rachel default

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": segment.text.strip(),
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.45,
                "similarity_boost": 0.80
            }
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return True
            return False
        except Exception:
            return False
