import os
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable
from novelcast.engines.base import BaseTTSEngine
from novelcast.core.schema import Segment, ChapterScript
from novelcast.core.voice_bank import VoiceBank

class Qwen3TTSEngine(BaseTTSEngine):
    """
    Qwen3-TTS Engine supporting high-fidelity zero-shot voice cloning,
    natural language style prompts, and multi-worker GPU acceleration.
    """

    def __init__(
        self,
        remote_url: Optional[str] = "http://192.168.0.180:9881/synthesize",
        model_name_or_path: str = "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        cache_dir: str = "cache_qwen3",
        workers: int = 4
    ):
        super().__init__(name="qwen3", cache_dir=cache_dir)
        self.remote_url = remote_url
        self.model_name_or_path = model_name_or_path
        self.workers = workers
        self._local_model = None
        self._processor = None
        self._device = None

    def _init_local_model(self):
        """Lazy loader for local in-process Qwen3-TTS model on CUDA/MPS/CPU."""
        if self._local_model is None:
            try:
                import torch
                try:
                    from qwen_tts import Qwen3TTSModel
                    self._local_model = Qwen3TTSModel.from_pretrained(self.model_name_or_path)
                except ImportError:
                    from transformers import AutoModelForCausalLM, AutoProcessor
                    self._processor = AutoProcessor.from_pretrained(self.model_name_or_path)
                    device = "cuda" if torch.cuda.is_available() else ("mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")
                    self._local_model = AutoModelForCausalLM.from_pretrained(
                        self.model_name_or_path,
                        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                        device_map="auto" if device == "cuda" else None
                    )
                    self._device = device
            except ImportError:
                raise ImportError(
                    "Local Qwen3-TTS requires PyTorch and qwen-tts / transformers.\n"
                    "Install with: pip install -U qwen-tts torch torchaudio\n"
                    "Or connect to a remote GPU server with: --remote http://<ip>:9881/synthesize"
                )

    def _synthesize_local(self, segment: Segment, ref_audio: str, instruct: str, speed: float, output_path: str) -> bool:
        """Runs in-process local Qwen3-TTS generation."""
        self._init_local_model()
        import torch
        import soundfile as sf

        try:
            # If using high-level qwen_tts package
            if hasattr(self._local_model, "generate"):
                gen_kwargs = {
                    "text": segment.text.strip(),
                    "ref_audio": ref_audio,
                    "language": "Spanish",
                    "speed": float(speed)
                }
                if instruct:
                    gen_kwargs["instruct"] = instruct

                wav, sr = self._local_model.generate(**gen_kwargs)
                temp_wav = os.path.join(self.cache_dir, f"temp_{segment.audio_hash or 'chunk'}.wav")
                sf.write(temp_wav, wav, sr)

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
        return False

    def _synthesize_remote(self, segment: Segment, ref_audio: str, instruct: str, speed: float, output_path: str) -> bool:
        """Sends HTTP request to remote Qwen3-TTS server."""
        try:
            with open(ref_audio, "rb") as f:
                files = {"ref_audio": (os.path.basename(ref_audio), f, "audio/wav")}
                data = {
                    "text": segment.text.strip(),
                    "language": "Spanish",
                    "speed": str(speed)
                }
                if instruct:
                    data["instruct"] = instruct

                resp = requests.post(self.remote_url, data=data, files=files, timeout=360)

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

        instruct = segment.instruct or char_info.instruct or ""
        speed = segment.speed if segment.speed != 1.0 else char_info.speed

        if self.remote_url:
            return self._synthesize_remote(segment, ref_audio, instruct, speed, output_path)
        else:
            return self._synthesize_local(segment, ref_audio, instruct, speed, output_path)

    def batch_synthesize(
        self,
        script: ChapterScript,
        voice_bank: VoiceBank,
        language: str = "es",
        progress_callback: Optional[Callable[[int, int, Segment, bool, bool], None]] = None
    ) -> List[str]:
        """Concurrent multi-worker batch synthesis for Qwen3-TTS."""
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

        max_workers = self.workers if self.remote_url else min(self.workers, 2)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(worker, t): t for t in tasks}
            for future in as_completed(future_to_task):
                idx, seg, cache_file, success = future.result()
                if success and os.path.exists(cache_file):
                    audio_files[idx] = cache_file
                if progress_callback:
                    progress_callback(idx + 1, total, seg, False, success)

        return audio_files
