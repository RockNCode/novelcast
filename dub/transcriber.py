import os
import json
import subprocess
from typing import List, Dict, Optional, Tuple

class AudioTranscriber:
    """
    Handles audio transcription, speech segmentation, chapter extraction,
    and voice actor reference clip harvesting.
    """

    def __init__(self, model_size: str = "base", device: str = "auto"):
        self.model_size = model_size
        self.device = device
        self._model = None

    def extract_m4b_metadata(self, m4b_path: str) -> Tuple[List[Dict], Optional[str]]:
        """
        Extracts chapter markers and embedded cover art from an M4B/MP3 file.
        Returns: (chapters_list, cover_art_path_or_None)
        """
        if not os.path.exists(m4b_path):
            raise FileNotFoundError(f"Audiobook not found: {m4b_path}")

        # 1. Extract chapter timestamps via ffprobe
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_chapters", m4b_path
        ]
        chapters = []
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            for ch in data.get("chapters", []):
                start_sec = float(ch.get("start_time", 0))
                end_sec = float(ch.get("end_time", 0))
                tags = ch.get("tags", {})
                title = tags.get("title", f"Chapter {len(chapters) + 1}")
                chapters.append({
                    "id": len(chapters) + 1,
                    "title": title,
                    "start": start_sec,
                    "end": end_sec
                })
        except Exception:
            pass

        # 2. Extract embedded cover art if present
        cover_path = None
        cover_temp = os.path.splitext(m4b_path)[0] + "_extracted_cover.jpg"
        cover_cmd = [
            "ffmpeg", "-y", "-i", m4b_path,
            "-an", "-vcodec", "copy", cover_temp
        ]
        try:
            res = subprocess.run(cover_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and os.path.exists(cover_temp) and os.path.getsize(cover_temp) > 1000:
                cover_path = cover_temp
        except Exception:
            pass

        return chapters, cover_path

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> List[Dict]:
        """
        Transcribes audio into timestamped segments using faster-whisper or openai-whisper.
        Falls back gracefully if not installed.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        segments_data = []

        # Try faster-whisper first
        try:
            from faster_whisper import WhisperModel
            if self._model is None:
                device = "cuda" if self.device == "cuda" else ("cpu" if self.device == "cpu" else "auto")
                compute_type = "float16" if device == "cuda" else "int8"
                self._model = WhisperModel(self.model_size, device=device, compute_type=compute_type)

            segments, info = self._model.transcribe(audio_path, language=language, beam_size=5)
            for seg in segments:
                segments_data.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                    "speaker": "Narrator"
                })
            return segments_data
        except ImportError:
            pass

        # Try standard openai-whisper
        try:
            import whisper
            if self._model is None:
                self._model = whisper.load_model(self.model_size)
            result = self._model.transcribe(audio_path, language=language)
            for seg in result.get("segments", []):
                segments_data.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip(),
                    "speaker": "Narrator"
                })
            return segments_data
        except ImportError:
            raise ImportError(
                "Whisper is required for audio dubbing transcription.\n"
                "Install with: pip install faster-whisper\n"
                "Or: pip install openai-whisper"
            )

    def extract_voice_samples(
        self,
        audio_path: str,
        segments: List[Dict],
        output_dir: str,
        min_duration_sec: float = 4.0,
        max_duration_sec: float = 12.0
    ) -> Dict[str, str]:
        """
        Extracts clean reference audio clips for each identified character/narrator.
        Returns a dict of: {speaker_name: reference_wav_path}
        """
        os.makedirs(output_dir, exist_ok=True)
        speaker_samples = {}
        speaker_segments = {}

        for seg in segments:
            spk = seg.get("speaker", "Narrator")
            dur = seg["end"] - seg["start"]
            if spk not in speaker_segments:
                speaker_segments[spk] = []
            speaker_segments[spk].append((dur, seg["start"], seg["end"]))

        for spk, seg_list in speaker_segments.items():
            # Pick a clean segment between min and max duration
            candidates = [s for s in seg_list if min_duration_sec <= s[0] <= max_duration_sec]
            if not candidates:
                candidates = sorted(seg_list, key=lambda x: x[0], reverse=True)

            if candidates:
                best_dur, start_s, end_s = candidates[0]
                safe_name = spk.lower().replace(" ", "_")
                sample_path = os.path.join(output_dir, f"{safe_name}.wav")

                # Cut using ffmpeg
                cmd = [
                    "ffmpeg", "-y", "-ss", str(start_s), "-to", str(end_s),
                    "-i", audio_path,
                    "-ac", "1", "-ar", "24000", sample_path
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if os.path.exists(sample_path) and os.path.getsize(sample_path) > 1000:
                    speaker_samples[spk] = sample_path

        return speaker_samples
