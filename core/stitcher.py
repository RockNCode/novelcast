import os
from typing import List, Optional, Callable
from pydub import AudioSegment
from novelcast.core.schema import ChapterScript, PauseSettings, Segment

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
        normalize_db: Optional[float] = -16.0,
        progress_callback: Optional[Callable[[int, int, Segment], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> bool:
        chunks: List[AudioSegment] = []
        last_speaker = None
        target_sample_rate = 24000
        target_channels = 1
        target_sample_width = 2
        total_segs = len(script.segments)

        for idx, (seg, apath) in enumerate(zip(script.segments, audio_files)):
            if is_cancelled and is_cancelled():
                return False

            if not apath or not os.path.exists(apath) or os.path.getsize(apath) < 100:
                if progress_callback:
                    progress_callback(idx + 1, total_segs, seg)
                continue

            try:
                chunk_audio = AudioSegment.from_file(apath)
                # Standardize format for fast raw data concatenation
                if chunk_audio.frame_rate != target_sample_rate or chunk_audio.channels != target_channels or chunk_audio.sample_width != target_sample_width:
                    chunk_audio = chunk_audio.set_frame_rate(target_sample_rate).set_channels(target_channels).set_sample_width(target_sample_width)
            except Exception:
                if progress_callback:
                    progress_callback(idx + 1, total_segs, seg)
                continue

            # Calculate pause before this chunk (or after previous)
            if last_speaker is not None:
                if seg.pause_after_ms:
                    pause_ms = seg.pause_after_ms
                elif seg.speaker == last_speaker:
                    pause_ms = self.pauses.same_speaker_ms
                else:
                    pause_ms = self.pauses.speaker_change_ms

                silent_chunk = AudioSegment.silent(duration=pause_ms, frame_rate=target_sample_rate)
                if silent_chunk.channels != target_channels or silent_chunk.sample_width != target_sample_width:
                    silent_chunk = silent_chunk.set_channels(target_channels).set_sample_width(target_sample_width)
                chunks.append(silent_chunk)

            chunks.append(chunk_audio)
            last_speaker = seg.speaker

            if progress_callback:
                progress_callback(idx + 1, total_segs, seg)

        if not chunks or (is_cancelled and is_cancelled()):
            return False

        # Fast O(N) concatenation
        raw_combined = b"".join(c.raw_data for c in chunks)
        combined = chunks[0]._spawn(raw_combined)

        if normalize_db is not None and combined.dBFS != float("-inf"):
            change_in_gain = normalize_db - combined.dBFS
            combined = combined.apply_gain(change_in_gain)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        ext = os.path.splitext(output_path)[1].lower().replace('.', '')
        combined.export(output_path, format=ext or 'mp3', bitrate='128k')
        return True
