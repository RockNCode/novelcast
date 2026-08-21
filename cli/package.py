import os
import typer
from typing import Optional
from rich.console import Console
from novelcast.core.packager import AudiobookPackager

console = Console()

def package_audiobook(
    chapters_dir: str = typer.Argument("output/chapters", help="Directory containing stitched chapter MP3 files"),
    output_m4b: str = typer.Option("output/Master_Audiobook.m4b", "--output", "-o", help="Path for the output master M4B audiobook"),
    title: str = typer.Option("NovelCast Audiobook", "--title", "-t", help="Book title"),
    author: str = typer.Option("Author", "--author", "-a", help="Author name"),
    cover: Optional[str] = typer.Option(None, "--cover", "-c", help="Path to cover art image (jpg/png)"),
    bitrate: str = typer.Option("128k", "--bitrate", "-b", help="AAC Audio Bitrate")
):
    """
    Package all stitched chapter audio files into a single master M4B audiobook with chapter markers & cover art.
    """
    if not os.path.exists(chapters_dir):
        console.print(f"[bold red]Error: Chapters directory '{chapters_dir}' does not exist.[/bold red]")
        raise typer.Exit(code=1)

    mp3_files = sorted([f for f in os.listdir(chapters_dir) if f.endswith(('.mp3', '.m4a', '.wav'))])
    if not mp3_files:
        console.print(f"[bold red]Error: No audio files found in '{chapters_dir}'[/bold red]")
        raise typer.Exit(code=1)

    console.print(f"[bold yellow]📦 Packaging Master Audiobook:[/bold yellow] [cyan]{title}[/cyan]")
    console.print(f"  • Author: [green]{author}[/green]")
    console.print(f"  • Chapters: {len(mp3_files)} files in [dim]{chapters_dir}[/dim]")
    if cover and os.path.exists(cover):
        console.print(f"  • Cover Art: [magenta]{cover}[/magenta]")

    chapter_entries = []
    for f in mp3_files:
        base_name = os.path.splitext(f)[0]
        # Format human-friendly chapter title
        clean_title = base_name.replace("_", " ").title()
        chapter_entries.append({
            "title": clean_title,
            "audio_path": os.path.join(chapters_dir, f)
        })

    packager = AudiobookPackager(bitrate=bitrate)
    success = packager.package_m4b(
        chapter_files=chapter_entries,
        output_m4b_path=output_m4b,
        book_title=title,
        author=author,
        cover_image_path=cover
    )

    if success and os.path.exists(output_m4b):
        size_mb = os.path.getsize(output_m4b) / (1024 * 1024)
        total_sec = packager.get_audio_duration_seconds(output_m4b)
        hours = int(total_sec // 3600)
        mins = int((total_sec % 3600) // 60)
        secs = total_sec % 60

        console.print(f"\n[bold green]🎉 MASTER M4B AUDIOBOOK CREATED SUCCESSFULLY![/bold green]")
        console.print(f"  • File: [cyan]{output_m4b}[/cyan]")
        console.print(f"  • Duration: [yellow]{hours}h {mins}m {secs:.1f}s[/yellow]")
        console.print(f"  • Size: [magenta]{size_mb:.2f} MB[/magenta]")
    else:
        console.print(f"[bold red]✗ Failed to package audiobook.[/bold red]")
