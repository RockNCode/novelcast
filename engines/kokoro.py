import os
from typing import Optional
from novelcast.engines.base import BaseTTSEngine
from novelcast.core.schema import Segment
from novelcast.core.voice_bank import VoiceBank

class KokoroEngine(BaseTTSEngine):
    """
    Kokoro-82M lightweight local CPU/GPU TTS Engine.
    """

    def __init__(self, cache_dir: str = "cache_kokoro"):
        super().__init__(name="kokoro", cache_dir=cache_dir)
        self._pipeline = None

    def _init_pipeline(self):
        if self._pipeline is None:
            try:
                from kokoro import KPipeline
                self._pipeline = KPipeline(lang_code='e') # Spanish / English
            except ImportError:
                pass

    def synthesize_chunk(self, segment: Segment, voice_bank: VoiceBank, output_path: str) -> bool:
        self._init_pipeline()
        if self._pipeline is None:
            return False
        # Local Kokoro synthesis logic
        try:
            generator = self._pipeline(segment.text, voice='em_alex', speed=segment.speed)
            import soundfile as sf
            for _, _, audio in generator:
                sf.write(output_path, audio, 24000)
                return True
        except Exception:
            return False
        return False
