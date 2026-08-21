import os
import requests
from typing import Optional
from novelcast.engines.base import BaseTTSEngine
from novelcast.core.schema import Segment
from novelcast.core.voice_bank import VoiceBank

class CosyVoiceEngine(BaseTTSEngine):
    """
    CosyVoice & CosyVoice3 TTS Engine for high-fidelity zero-shot voice cloning.
    """

    def __init__(
        self,
        remote_url: Optional[str] = "http://192.168.0.180:9880/synthesize_cosyvoice",
        cache_dir: str = "cache_cosyvoice"
    ):
        super().__init__(name="cosyvoice", cache_dir=cache_dir)
        self.remote_url = remote_url

    def synthesize_chunk(self, segment: Segment, voice_bank: VoiceBank, output_path: str) -> bool:
        if not self.remote_url:
            return False

        char_info = voice_bank.get_character(segment.speaker)
        ref_audio = char_info.reference_audio or os.path.join(voice_bank.voice_bank_dir, f"{segment.speaker.lower()}.wav")

        payload = {
            "speaker": segment.speaker,
            "text": segment.text.strip(),
            "instruct": segment.instruct or "",
            "speed": segment.speed,
            "prompt_text": "Texto de referencia en español para clonación de voz.",
            "ref_audio_path": ref_audio if os.path.exists(ref_audio) else ""
        }

        try:
            resp = requests.post(self.remote_url, json=payload, timeout=60)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return True
            return False
        except Exception:
            return False
