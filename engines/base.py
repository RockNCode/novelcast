import os
import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from novelcast.core.schema import Segment, ChapterScript
from novelcast.core.voice_bank import VoiceBank

class BaseTTSEngine(ABC):
    """Abstract base class for all NovelCast TTS synthesis backends."""

    def __init__(self, name: str, cache_dir: str = "cache"):
        self.name = name
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cache_path(self, segment: Segment, language: str = "es") -> str:
        """Returns the cached audio filepath for a given segment."""
        spk_clean = segment.speaker.lower().replace(" ", "_")
        chunk_hash = segment.compute_hash(language=language)
        return os.path.join(self.cache_dir, f"{spk_clean}_{chunk_hash}.mp3")

    def is_cached(self, segment: Segment, language: str = "es") -> bool:
        cache_file = self.get_cache_path(segment, language=language)
        return os.path.exists(cache_file) and os.path.getsize(cache_file) > 1000

    @abstractmethod
    def synthesize_chunk(self, segment: Segment, voice_bank: VoiceBank, output_path: str) -> bool:
        """Synthesize a single audio segment to output_path."""
        pass

    def batch_synthesize(
        self,
        script: ChapterScript,
        voice_bank: VoiceBank,
        language: str = "es",
        progress_callback: Optional[Callable[[int, int, Segment, bool], None]] = None
    ) -> List[str]:
        """
        Synthesizes all segments in a script with caching and progress reporting.
        Returns list of generated/cached audio filepaths in order.
        """
        audio_files = []
        total = len(script.segments)

        for idx, seg in enumerate(script.segments):
            cache_file = self.get_cache_path(seg, language=language)
            was_cached = self.is_cached(seg, language=language)

            if not was_cached:
                success = self.synthesize_chunk(seg, voice_bank, cache_file)
                if not success:
                    # Retry once
                    success = self.synthesize_chunk(seg, voice_bank, cache_file)
            else:
                success = True

            if progress_callback:
                progress_callback(idx + 1, total, seg, was_cached)

            if success and os.path.exists(cache_file):
                audio_files.append(cache_file)
            else:
                audio_files.append(None)

        return audio_files
