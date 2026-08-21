import os
import typer
from typing import Optional
from rich.console import Console
from novelcast.cli.parse import parse_book
from novelcast.cli.generate import generate_script
from novelcast.cli.stitch import stitch_script
from novelcast.cli.package import package_audiobook

console = Console()

def run_pipeline(
    book_path: str = typer.Argument(..., help="Path to input EPUB or TXT file"),
    title: str = typer.Option("NovelCast Audiobook", "--title", "-t", help="Book title"),
    author: str = typer.Option("Author", "--author", "-a", help="Author name"),
    engine_name: str = typer.Option("omnivoice", "--engine", "-e", help="TTS Engine (omnivoice, cosyvoice, kokoro, elevenlabs)"),
    remote_url: Optional[str] = typer.Option("http://192.168.0.180:9880/synthesize", "--remote", "-r", help="Remote GPU server URL"),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of concurrent generation workers"),
    cover: Optional[str] = typer.Option(None, "--cover", "-c", help="Path to cover art image (jpg/png)"),
    output_m4b: str = typer.Option("output/Master_Audiobook.m4b", "--output", "-o", help="Path for the output master M4B audiobook"),
    cache_dir: str = typer.Option("cache_omnivoice", "--cache", help="Directory for chunk audio cache"),
    voice_config: str = typer.Option("voice_config.json", "--voice-config", "-v", help="Path to voice config JSON")
):
    """
    ⚡ Run the full end-to-end NovelCast pipeline from eBook to Master M4B Audiobook in a single command.
    """
    console.print("\n[bold magenta]=======================================================[/bold magenta]")
    console.print(f"[bold cyan]🚀 NovelCast End-to-End Audiobook Production[/bold cyan]: [bold yellow]{title}[/bold yellow]")
    console.print("[bold magenta]=======================================================[/bold magenta]\n")

    # Step 1: Parse
    scripts_dir = "data/scripts"
    console.print("[bold yellow]Step 1/4: Parsing eBook...[/bold yellow]")
    parse_book(book_path=book_path, output_dir=scripts_dir, book_name=title)

    # Step 2: Generate
    console.print("\n[bold yellow]Step 2/4: Synthesizing Audio Chunks...[/bold yellow]")
    generate_script(
        target=scripts_dir,
        engine_name=engine_name,
        remote_url=remote_url,
        workers=workers,
        cache_dir=cache_dir,
        voice_config=voice_config
    )

    # Step 3: Stitch
    chapters_dir = "output/chapters"
    console.print("\n[bold yellow]Step 3/4: Stitching Chapters...[/bold yellow]")
    stitch_script(
        target=scripts_dir,
        output_dir=chapters_dir,
        cache_dir=cache_dir
    )

    # Step 4: Package
    console.print("\n[bold yellow]Step 4/4: Packaging Master M4B Audiobook...[/bold yellow]")
    package_audiobook(
        chapters_dir=chapters_dir,
        output_m4b=output_m4b,
        title=title,
        author=author,
        cover=cover
    )

    console.print(f"\n[bold green]🎉 FULL PIPELINE COMPLETED SUCCESSFULLY![/bold green]")
    console.print(f"Master Audiobook available at: [cyan]{output_m4b}[/cyan]\n")
