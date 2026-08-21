import os
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable
from novelcast.engines.base import BaseTTSEngine
from novelcast.core.schema import Segment, ChapterScript
from novelcast.core.voice_bank import VoiceBank

class OmniVoiceEngine(BaseTTSEngine):
    """
    OmniVoice TTS Engine supporting both local inference and remote Dual-GPU FastAPI server.
    """

    def __init__(
        self,
        remote_url: Optional[str] = "http://192.168.0.180:9880/synthesize",
        cache_dir: str = "cache_omnivoice",
        workers: int = 4
    ):
        super().__init__(name="omnivoice", cache_dir=cache_dir)
        self.remote_url = remote_url
        self.workers = workers

    def synthesize_chunk(self, segment: Segment, voice_bank: VoiceBank, output_path: str) -> bool:
        if not self.remote_url:
            raise NotImplementedError("Local OmniVoice inference requires PyTorch and GPU weights configured. Provide a remote_url.")

        char_info = voice_bank.get_character(segment.speaker)
        ref_audio = char_info.reference_audio or os.path.join(voice_bank.voice_bank_dir, f"{segment.speaker.lower()}.wav")
        if not os.path.exists(ref_audio):
            ref_audio = os.path.join(voice_bank.voice_bank_dir, "narrador.wav")

        if not os.path.exists(ref_audio):
            return False

        instruct = segment.instruct or char_info.instruct or ""
        guidance = segment.guidance_scale if segment.guidance_scale != 2.8 else char_info.guidance_scale
        speed = segment.speed if segment.speed != 1.0 else char_info.speed

        try:
            with open(ref_audio, "rb") as f:
                files = {"ref_audio": (os.path.basename(ref_audio), f, "audio/wav")}
                data = {
                    "text": segment.text.strip(),
                    "language": "Spanish",
                    "guidance_scale": str(guidance),
                    "speed": str(speed)
                }
                if instruct:
                    data["instruct"] = instruct

                resp = requests.post(self.remote_url, data=data, files=files, timeout=120)

            if resp.status_code == 200:
                temp_wav = os.path.join(self.cache_dir, f"temp_{segment.audio_hash or 'chunk'}.wav")
                with open(temp_wav, "wb") as f_out:
                    f_out.write(resp.content)

                # Convert to high-quality MP3
                subprocess.run([
                    "ffmpeg", "-y", "-i", temp_wav,
                    "-acodec", "libmp3lame", "-b:a", "192k", "-ar", "44100",
                    output_path
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

                if os.path.exists(temp_wav):
                    try: os.remove(temp_wav)
                    except Exception: pass

                return os.path.exists(output_path) and os.path.getsize(output_path) > 500
            else:
                return False
        except Exception:
            return False

    def batch_synthesize(
        self,
        script: ChapterScript,
        voice_bank: VoiceBank,
        language: str = "es",
        progress_callback: Optional[Callable[[int, int, Segment, bool, bool], None]] = None
    ) -> List[str]:
        """Concurrent multi-worker batch synthesis for OmniVoice."""
        total = len(script.segments)
        audio_files = [None] * total
        tasks = []

        # First pass: check cached items
        for idx, seg in enumerate(script.segments):
            cache_file = self.get_cache_path(seg, language=language)
            if self.is_cached(seg, language=language):
                audio_files[idx] = cache_file
                if progress_callback:
                    progress_callback(idx + 1, total, seg, True, True)
            else:
                tasks.append((idx, seg, cache_file))

        if not tasks:
            return audio_files

        # Second pass: synthesize missing chunks concurrently
        def worker(idx_seg_cache):
            i, s, path = idx_seg_cache
            success = self.synthesize_chunk(s, voice_bank, path)
            return i, s, path, success

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_task = {executor.submit(worker, t): t for t in tasks}
            for future in as_completed(future_to_task):
                idx, seg, cache_file, success = future.result()
                if success and os.path.exists(cache_file):
                    audio_files[idx] = cache_file
                if progress_callback:
                    progress_callback(idx + 1, total, seg, False, success)

        return audio_files
