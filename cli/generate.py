import os
import json
import typer
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from novelcast.core.schema import ChapterScript
from novelcast.core.voice_bank import VoiceBank
from novelcast.engines import get_engine

console = Console()

def generate_script(
    target: str = typer.Argument(..., help="Path to script JSON file or directory containing scripts"),
    engine_name: str = typer.Option("omnivoice", "--engine", "-e", help="TTS Engine (omnivoice, cosyvoice, kokoro, elevenlabs)"),
    remote_url: Optional[str] = typer.Option(None, "--remote", "-r", help="Remote GPU server URL. If omitted, runs local OmniVoice model."),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of concurrent generation workers"),
    cache_dir: str = typer.Option("cache_omnivoice", "--cache", "-c", help="Directory for chunk audio cache"),
    voice_config: str = typer.Option("voice_config.json", "--voice-config", "-v", help="Path to voice config JSON")
):
    """
    Batch synthesize audio chunks for one or more chapter scripts with SHA-256 caching.
    """
    vb = VoiceBank(config_path=voice_config)
    engine = get_engine(engine_name, remote_url=remote_url, cache_dir=cache_dir, workers=workers)

    # Collect scripts to process
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

    console.print(f"[bold yellow]⚡ Batch TTS Generation Engine:[/bold yellow] [green]{engine_name}[/green] ({workers} workers)")
    if remote_url:
        console.print(f"  • Remote GPU Endpoint: [cyan]{remote_url}[/cyan]")
    console.print(f"  • Found {len(scripts)} chapter script(s) to process\n")

    for s_path in scripts:
        with open(s_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            script = ChapterScript(**data)

        console.print(f"[bold cyan]▶ Processing:[/bold cyan] {script.title} ({len(script.segments)} segments)")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task_id = progress.add_task(f"[yellow]{script.chapter_id}[/yellow]", total=len(script.segments))

            def on_progress(current, total, seg, was_cached, success=True):
                status_icon = "⚡ cached" if was_cached else ("✓ gen" if success else "✗ fail")
                progress.update(
                    task_id,
                    completed=current,
                    description=f"[yellow]{seg.speaker}[/yellow] ({current}/{total}) [{status_icon}]"
                )

            engine.batch_synthesize(script, vb, progress_callback=on_progress)

        console.print(f"[green]✓ Completed chapter synthesis:[/green] {script.chapter_id}\n")

    console.print("[bold green]🎉 All requested chapters synthesized successfully![/bold green]")
