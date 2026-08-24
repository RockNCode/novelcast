import os
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable
from novelcast.engines.base import BaseTTSEngine
from novelcast.core.schema import Segment, ChapterScript
from novelcast.core.voice_bank import VoiceBank
from novelcast.core.director import sanitize_instruct

class OmniVoiceEngine(BaseTTSEngine):
    """
    OmniVoice TTS Engine supporting both local GPU inference (Windows/Linux)
    and remote Dual-GPU FastAPI server.
    """

    def __init__(
        self,
        remote_url: Optional[str] = None,
        model_name_or_path: str = "k2-fsa/OmniVoice",
        cache_dir: str = "cache_omnivoice",
        workers: int = 4
    ):
        super().__init__(name="omnivoice", cache_dir=cache_dir)
        self.remote_url = remote_url
        self.model_name_or_path = model_name_or_path
        self.workers = workers
        self._local_model = None
        self._device = None

    def _init_local_model(self):
        """Lazy loader for local in-process OmniVoice model on CUDA/MPS/CPU."""
        if self._local_model is None:
            try:
                import torch
                try:
                    from omnivoice import OmniVoice
                except ImportError:
                    from omnivoice.models.omnivoice import OmniVoice
            except ImportError:
                raise ImportError(
                    "Local OmniVoice inference requires PyTorch and the omnivoice package.\n"
                    "Install with: pip install torch torchaudio omnivoice\n"
                    "Or connect to a remote GPU server with: --remote http://<ip>:<port>/synthesize"
                )

            if torch.cuda.is_available():
                self._device = "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self._device = "mps"
            else:
                self._device = "cpu"

            self._local_model = OmniVoice.from_pretrained(self.model_name_or_path, device=self._device)

    def _synthesize_local(self, segment: Segment, ref_audio: str, instruct: str, guidance: float, speed: float, output_path: str) -> bool:
        """Runs in-process local OmniVoice generation."""
        self._init_local_model()
        import torch
        import torchaudio

        gen_kwargs = {
            "text": segment.text.strip(),
            "ref_audio": ref_audio,
            "language": "Spanish",
            "speed": float(speed),
            "guidance_scale": float(guidance)
        }
        if instruct:
            gen_kwargs["instruct"] = instruct

        try:
            with torch.no_grad():
                wav = self._local_model.generate(**gen_kwargs)

            temp_wav = os.path.join(self.cache_dir, f"temp_{segment.audio_hash or 'chunk'}.wav")
            sample_rate = getattr(self._local_model, "sample_rate", 24000)

            if hasattr(wav, "cpu"):
                wav = wav.cpu()
            if hasattr(wav, "ndim") and wav.ndim == 1:
                wav = wav.unsqueeze(0)

            torchaudio.save(temp_wav, wav, sample_rate)

            # Convert to standard MP3
            subprocess.run([
                "ffmpeg", "-y", "-i", temp_wav,
                "-acodec", "libmp3lame", "-b:a", "192k", "-ar", "44100",
                output_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            if os.path.exists(temp_wav):
                try: os.remove(temp_wav)
                except Exception: pass

            return os.path.exists(output_path) and os.path.getsize(output_path) > 500
        except Exception:
            return False

    def _synthesize_remote(self, segment: Segment, ref_audio: str, instruct: str, guidance: float, speed: float, output_path: str) -> bool:
        """Sends HTTP request to remote OmniVoice server."""
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

    def synthesize_chunk(self, segment: Segment, voice_bank: VoiceBank, output_path: str) -> bool:
        char_info = voice_bank.get_character(segment.speaker)
        ref_audio = char_info.reference_audio or os.path.join(voice_bank.voice_bank_dir, f"{segment.speaker.lower()}.wav")
        if not os.path.exists(ref_audio):
            ref_audio = os.path.join(voice_bank.voice_bank_dir, "narrador.wav")

        if not os.path.exists(ref_audio):
            return False

        raw_instruct = segment.instruct or char_info.instruct or ""
        instruct = sanitize_instruct(raw_instruct) or ""
        guidance = segment.guidance_scale if segment.guidance_scale != 2.8 else char_info.guidance_scale
        speed = segment.speed if segment.speed != 1.0 else char_info.speed

        if self.remote_url:
            return self._synthesize_remote(segment, ref_audio, instruct, guidance, speed, output_path)
        else:
            return self._synthesize_local(segment, ref_audio, instruct, guidance, speed, output_path)

    def batch_synthesize(
        self,
        script: ChapterScript,
        voice_bank: VoiceBank,
        language: str = "es",
        progress_callback: Optional[Callable[[int, int, Segment, bool, bool], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
        is_paused: Optional[Callable[[], bool]] = None
    ) -> List[str]:
        """Concurrent multi-worker batch synthesis for OmniVoice with active pause and cancellation."""
        import time
        total = len(script.segments)
        audio_files = [None] * total
        tasks = []

        # First pass: check cached items
        for idx, seg in enumerate(script.segments):
            if is_cancelled and is_cancelled():
                return audio_files

            cache_file = self.get_cache_path(seg, language=language)
            if self.is_cached(seg, language=language):
                audio_files[idx] = cache_file
                if progress_callback:
                    progress_callback(idx + 1, total, seg, True, True)
            else:
                tasks.append((idx, seg, cache_file))

        if not tasks or (is_cancelled and is_cancelled()):
            return audio_files

        # Second pass: synthesize missing chunks concurrently with active pause/cancel checking
        def worker(idx_seg_cache):
            i, s, path = idx_seg_cache
            if is_cancelled and is_cancelled():
                return i, s, path, False
            while is_paused and is_paused():
                time.sleep(0.25)
                if is_cancelled and is_cancelled():
                    return i, s, path, False

            if is_cancelled and is_cancelled():
                return i, s, path, False

            success = self.synthesize_chunk(s, voice_bank, path)
            return i, s, path, success

        max_workers = self.workers if self.remote_url else min(self.workers, 2)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {}
            for t in tasks:
                if is_cancelled and is_cancelled():
                    break
                future = executor.submit(worker, t)
                future_to_task[future] = t

            for future in as_completed(future_to_task):
                if is_cancelled and is_cancelled():
                    for f in future_to_task:
                        f.cancel()
                    break

                try:
                    idx, seg, cache_file, success = future.result()
                    if success and os.path.exists(cache_file):
                        audio_files[idx] = cache_file
                    if progress_callback and not (is_cancelled and is_cancelled()):
                        progress_callback(idx + 1, total, seg, False, success)
                except Exception:
                    pass

        return audio_files
