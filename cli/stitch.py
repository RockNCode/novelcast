import os
import json
import typer
from rich.console import Console
from novelcast.core.schema import ChapterScript
from novelcast.core.stitcher import AudioStitcher
from novelcast.engines import get_engine

console = Console()

def stitch_script(
    target: str = typer.Argument(..., help="Path to script JSON file or directory containing scripts"),
    output_dir: str = typer.Option("output/chapters", "--output-dir", "-o", help="Directory to save stitched chapter audio"),
    cache_dir: str = typer.Option("cache_omnivoice", "--cache", "-c", help="Directory for chunk audio cache"),
    normalize_lufs: float = typer.Option(-16.0, "--normalize", "-n", help="Target loudness in dBFS/LUFS")
):
    """
    Stitch generated audio chunks into seamless chapter audio files with natural conversational timing.
    """
    os.makedirs(output_dir, exist_ok=True)
    stitcher = AudioStitcher()
    engine = get_engine("omnivoice", cache_dir=cache_dir)

    scripts = []
    if os.path.isfile(target):
        scripts.append(target)
    elif os.path.isdir(target):
        for fname in sorted(os.listdir(target)):
            if fname.endswith(".json"):
                scripts.append(os.path.join(target, fname))

    if not scripts:
        console.print(f"[bold red]Error: No script JSON files found at '{target}'[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold yellow]🎧 Stitching Audio for {len(scripts)} Chapter(s)...[/bold yellow]\n")

    for s_path in scripts:
        with open(s_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            script = ChapterScript(**data)

        audio_files = []
        for seg in script.segments:
            cpath = engine.get_cache_path(seg)
            audio_files.append(cpath if os.path.exists(cpath) else None)

        out_audio = os.path.join(output_dir, f"{script.chapter_id}.mp3")
        console.print(f"  • Stitching [cyan]{script.chapter_id}[/cyan] ({len(audio_files)} chunks) -> [yellow]{out_audio}[/yellow]...")
        success = stitcher.stitch_chapter(script, audio_files, out_audio, normalize_db=normalize_lufs)

        if success and os.path.exists(out_audio):
            size_mb = os.path.getsize(out_audio) / (1024 * 1024)
            console.print(f"    [green]✓ Successfully stitched ({size_mb:.2f} MB)[/green]")
        else:
            console.print(f"    [red]✗ Failed to stitch {script.chapter_id}[/red]")

    console.print("\n[bold green]🎉 Chapter stitching complete![/bold green]")
