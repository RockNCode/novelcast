import os
import json
import subprocess
from typing import Optional, Callable, List, Tuple
from rich.console import Console

from novelcast.dub.transcriber import AudioTranscriber
from novelcast.dub.translator import ScriptTranslator
from novelcast.core.schema import ChapterScript
from novelcast.core.voice_bank import VoiceBank
from novelcast.core.stitcher import AudioStitcher
from novelcast.core.packager import AudiobookPackager
from novelcast.engines import get_engine

console = Console()

class DubbingPipeline:
    """
    Complete Cross-Lingual Audiobook Dubbing & Translation Pipeline.
    Supports chapter-by-chapter translation, voice actor harvesting,
    and master M4B packaging.
    """

    def __init__(
        self,
        project_dir: str = "workspace_dub",
        whisper_model: str = "base",
        llm_api_base: Optional[str] = None,
        llm_api_key: Optional[str] = None
    ):
        self.project_dir = project_dir
        self.transcriber = AudioTranscriber(model_size=whisper_model)
        self.translator = ScriptTranslator(api_base=llm_api_base, api_key=llm_api_key)

    def run(
        self,
        input_audio: str,
        from_lang: str = "en",
        to_lang: str = "es",
        engine_name: str = "omnivoice",
        remote_url: Optional[str] = None,
        output_m4b: Optional[str] = None,
        workers: int = 4,
        sample_seconds: int = 60,
        ref_voice: Optional[str] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> str:
        """
        Executes end-to-end voice-cloned audiobook translation.
        """
        if not os.path.exists(input_audio):
            raise FileNotFoundError(f"Input audio file not found: {input_audio}")

        os.makedirs(self.project_dir, exist_ok=True)
        raw_chapters_dir = os.path.join(self.project_dir, "raw_chapters")
        scripts_dir = os.path.join(self.project_dir, "scripts")
        voice_bank_dir = os.path.join(self.project_dir, "voice_bank")
        cache_dir = os.path.join(self.project_dir, f"cache_{engine_name}")
        chapters_audio_dir = os.path.join(self.project_dir, "chapters_audio")
        
        for d in [raw_chapters_dir, scripts_dir, voice_bank_dir, cache_dir, chapters_audio_dir]:
            os.makedirs(d, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(input_audio))[0]
        if not output_m4b:
            output_m4b = os.path.join("output", f"{base_name}_{to_lang}.m4b")
        os.makedirs(os.path.dirname(output_m4b) or "output", exist_ok=True)

        console.print(f"[bold cyan]▶ Step 1/5: Extracting Chapter Metadata & Embedded Cover Art...[/bold cyan]")
        chapters_meta, cover_path = self.transcriber.extract_m4b_metadata(input_audio)
        console.print(f"  • Extracted {len(chapters_meta)} chapter marker(s)")
        if cover_path:
            console.print(f"  • Found embedded cover art: {cover_path}")

        # If no chapters found in metadata, treat whole file as Chapter 1
        if not chapters_meta:
            chapters_meta = [{
                "id": 1,
                "title": "Chapter 1",
                "start": 0.0,
                "end": None
            }]

        console.print(f"\n[bold cyan]▶ Step 2/5: Extracting Voice Actor Reference Samples...[/bold cyan]")
        if ref_voice and os.path.exists(ref_voice):
            console.print(f"  • Using specified clean reference voice: [green]{ref_voice}[/green]")
            for target_name in ["narrator.wav", "narrador.wav"]:
                target_path = os.path.join(voice_bank_dir, target_name)
                cmd = ["ffmpeg", "-y", "-i", ref_voice, "-ac", "1", "-ar", "24000", target_path]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        else:
            # Skip Audible/intro fanfare: find first substantial story chapter (> 60s)
            sample_start = 60.0
            for ch in chapters_meta:
                if ch.get("start") is not None and ch.get("end") is not None:
                    if (ch["end"] - ch["start"]) > 120.0:
                        sample_start = ch["start"] + 10.0
                        break

            console.print(f"  • Sampling clean speech at {sample_start:.1f}s (skipping intro music)...")
            sample_clip = os.path.join(self.project_dir, "clean_voice_sample.m4a")
            cmd = ["ffmpeg", "-y", "-ss", str(sample_start), "-t", str(sample_seconds or 60), "-i", input_audio, "-vn", "-c:a", "copy", sample_clip]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            sample_segments = self.transcriber.transcribe(sample_clip, language=from_lang)
            voice_samples = self.transcriber.extract_voice_samples(
                sample_clip, sample_segments, voice_bank_dir
            )
            for spk, path in voice_samples.items():
                console.print(f"  • Harvested clean voice actor reference for [green]{spk}[/green]: {path}")
                fallback_narrador = os.path.join(voice_bank_dir, "narrador.wav")
                if not os.path.exists(fallback_narrador) and os.path.exists(path):
                    import shutil
                    shutil.copyfile(path, fallback_narrador)

        voice_bank = VoiceBank(config_path=os.path.join(self.project_dir, "voice_config.json"), voice_bank_dir=voice_bank_dir)
        voice_bank.auto_discover_voices()
        engine = get_engine(engine_name, remote_url=remote_url, cache_dir=cache_dir, workers=workers)
        stitcher = AudioStitcher()

        stitched_chapters_for_packaging: List[Tuple[str, str]] = []

        console.print(f"\n[bold cyan]▶ Step 3/5: Processing & Translating {len(chapters_meta)} Chapters...[/bold cyan]")
        for ch_idx, ch in enumerate(chapters_meta):
            ch_num = ch_idx + 1
            ch_title = ch.get("title", f"Chapter {ch_num}")
            ch_id = f"chapter_{ch_num:03d}"
            
            ch_audio_out = os.path.join(chapters_audio_dir, f"{ch_id}.mp3")
            script_file = os.path.join(scripts_dir, f"{ch_id}.json")

            if os.path.exists(ch_audio_out) and os.path.getsize(ch_audio_out) > 5000:
                console.print(f"  • [green]Chapter {ch_num}/{len(chapters_meta)} already completed[/green]: {ch_title}")
                stitched_chapters_for_packaging.append((ch_title, ch_audio_out))
                continue

            console.print(f"\n  [bold yellow]── Chapter {ch_num}/{len(chapters_meta)}: {ch_title} ──[/bold yellow]")

            # 1. Demux chapter audio chunk
            raw_ch_audio = os.path.join(raw_chapters_dir, f"{ch_id}.m4a")
            if not os.path.exists(raw_ch_audio):
                cmd = ["ffmpeg", "-y", "-ss", str(ch["start"])]
                if ch["end"] is not None:
                    cmd += ["-to", str(ch["end"])]
                cmd += ["-i", input_audio, "-vn", "-c:a", "copy", raw_ch_audio]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

            # 2. Transcribe chapter
            if not os.path.exists(script_file):
                console.print(f"    • Transcribing speech with Whisper...")
                ch_segments = self.transcriber.transcribe(raw_ch_audio, language=from_lang)
                console.print(f"    • Translating {len(ch_segments)} lines ({from_lang.upper()} -> {to_lang.upper()})...")
                chapter_script = self.translator.build_chapter_script(
                    chapter_title=ch_title,
                    chapter_id=ch_id,
                    segments=ch_segments,
                    from_lang=from_lang,
                    to_lang=to_lang
                )
                with open(script_file, "w", encoding="utf-8") as f:
                    json.dump(chapter_script.model_dump(), f, indent=2, ensure_ascii=False)
            else:
                with open(script_file, "r", encoding="utf-8") as f:
                    chapter_script = ChapterScript(**json.load(f))

            # 3. Synthesize chapter
            console.print(f"    • Synthesizing {len(chapter_script.segments)} lines with {engine_name.upper()}...")
            audio_chunks = engine.batch_synthesize(chapter_script, voice_bank, language=to_lang)

            # 4. Stitch chapter
            console.print(f"    • Stitching chapter audio...")
            success = stitcher.stitch_chapter(
                script=chapter_script,
                audio_files=audio_chunks,
                output_path=ch_audio_out
            )
            if success and os.path.exists(ch_audio_out):
                stitched_chapters_for_packaging.append((ch_title, ch_audio_out))

        # 5. Package master M4B
        console.print(f"\n[bold cyan]▶ Step 5/5: Packaging Master M4B Audiobook with Chapters & Cover...[/bold cyan]")
        packager = AudiobookPackager()
        final_m4b = packager.package_m4b(
            chapters_audio=stitched_chapters_for_packaging,
            output_m4b_path=output_m4b,
            title=f"{base_name} (Doblado al Español)",
            author="NovelCast Dub Studio",
            cover_image_path=cover_path
        )

        console.print(f"\n[bold green]✓ Master Dubbed Audiobook Created Successfully: {final_m4b}[/bold green]\n")
        return final_m4b
