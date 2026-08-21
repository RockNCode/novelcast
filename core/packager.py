import os
import subprocess
from typing import List, Dict, Optional, Any

class AudiobookPackager:
    """
    Packages stitched audio chapters into a single master M4B/MP3 audiobook
    with AAC 128k, embedded chapter markers, and high-resolution cover art.
    """

    def __init__(self, bitrate: str = "128k", sample_rate: int = 44100):
        self.bitrate = bitrate
        self.sample_rate = sample_rate

    def get_audio_duration_seconds(self, filepath: str) -> float:
        """Retrieves exact audio duration using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            filepath
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            return 0.0

    def generate_metadata_file(
        self,
        chapters: List[Dict[str, Any]], # [{"title": "...", "duration": 123.4}, ...]
        book_title: str,
        author: str = "Unknown Author",
        artist: str = "NovelCast Multi-Voice Cast",
        output_meta_path: str = "ffmetadata.txt"
    ) -> str:
        lines = [";FFMETADATA1"]
        lines.append(f"title={book_title}")
        lines.append(f"artist={author}")
        lines.append(f"album_artist={artist}")
        lines.append(f"album={book_title}")
        lines.append("genre=Audiobook")
        lines.append("date=2026")
        lines.append("")

        current_ms = 0
        for chap in chapters:
            duration_ms = int(chap["duration"] * 1000)
            end_ms = current_ms + duration_ms
            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={current_ms}")
            lines.append(f"END={end_ms}")
            lines.append(f"title={chap['title']}")
            lines.append("")
            current_ms = end_ms

        with open(output_meta_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_meta_path

    def package_m4b(
        self,
        chapter_files: List[Dict[str, str]], # [{"title": "...", "audio_path": "..."}, ...]
        output_m4b_path: str,
        book_title: str = "NovelCast Audiobook",
        author: str = "Author",
        cover_image_path: Optional[str] = None
    ) -> bool:
        if not chapter_files:
            return False

        temp_dir = os.path.dirname(os.path.abspath(output_m4b_path))
        os.makedirs(temp_dir, exist_ok=True)
        concat_list_path = os.path.join(temp_dir, "temp_concat_list.txt")
        combined_aac_path = os.path.join(temp_dir, "temp_combined.aac")
        meta_path = os.path.join(temp_dir, "temp_ffmetadata.txt")

        # 1. Compute chapter durations and write concat list
        chap_meta_list = []
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for c in chapter_files:
                dur = self.get_audio_duration_seconds(c["audio_path"])
                chap_meta_list.append({"title": c["title"], "duration": dur})
                f.write(f"file '{os.path.abspath(c['audio_path'])}'\n")

        # 2. Write FFmetadata file
        self.generate_metadata_file(chap_meta_list, book_title=book_title, author=author, output_meta_path=meta_path)

        # 3. Concatenate and transcode to AAC stream
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_path,
            "-c:a", "aac", "-b:a", self.bitrate,
            "-ar", str(self.sample_rate),
            combined_aac_path
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # 4. Merge AAC audio stream, metadata, and optional cover image into M4B
        if cover_image_path and os.path.exists(cover_image_path):
            final_cmd = [
                "ffmpeg", "-y",
                "-i", combined_aac_path,
                "-i", meta_path,
                "-i", cover_image_path,
                "-map", "0:a",
                "-map", "2:v",
                "-map_metadata", "1",
                "-c:a", "copy",
                "-c:v", "mjpeg",
                "-disposition:v", "attached_pic",
                output_m4b_path
            ]
        else:
            final_cmd = [
                "ffmpeg", "-y",
                "-i", combined_aac_path,
                "-i", meta_path,
                "-map", "0:a",
                "-map_metadata", "1",
                "-c:a", "copy",
                output_m4b_path
            ]

        subprocess.run(final_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Clean up temporary files
        for tmp in [concat_list_path, combined_aac_path, meta_path]:
            if os.path.exists(tmp):
                try: os.remove(tmp)
                except Exception: pass

        return os.path.exists(output_m4b_path) and os.path.getsize(output_m4b_path) > 1000
