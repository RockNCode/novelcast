import os
from typing import List, Optional
from pydub import AudioSegment
from novelcast.core.schema import ChapterScript, PauseSettings

class AudioStitcher:
    """
    Stitches individual segment audio files into continuous chapter tracks
    with natural conversational pause timing and loudness consistency.
    """

    def __init__(self, pause_settings: Optional[PauseSettings] = None):
        self.pauses = pause_settings or PauseSettings()

    def stitch_chapter(
        self,
        script: ChapterScript,
        audio_files: List[Optional[str]],
        output_path: str,
        normalize_db: Optional[float] = -16.0
    ) -> bool:
        combined = AudioSegment.empty()
        last_speaker = None
        stitched_count = 0

        for idx, (seg, apath) in enumerate(zip(script.segments, audio_files)):
            if not apath or not os.path.exists(apath) or os.path.getsize(apath) < 100:
                continue

            try:
                chunk_audio = AudioSegment.from_file(apath)
            except Exception:
                continue

            # Calculate pause before this chunk (or after previous)
            if last_speaker is not None:
                if seg.pause_after_ms:
                    pause_ms = seg.pause_after_ms
                elif seg.speaker == last_speaker:
                    pause_ms = self.pauses.same_speaker_ms
                else:
                    pause_ms = self.pauses.speaker_change_ms

                combined += AudioSegment.silent(duration=pause_ms)

            combined += chunk_audio
            last_speaker = seg.speaker
            stitched_count += 1

        if len(combined) == 0:
            return False

        if normalize_db is not None:
            change_in_gain = normalize_db - combined.dBFS
            combined = combined.apply_gain(change_in_gain)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        ext = os.path.splitext(output_path)[1].lower().replace('.', '')
        combined.export(output_path, format=ext or 'mp3', bitrate='128k')
        return True
