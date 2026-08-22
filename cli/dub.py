import os
import typer
from typing import Optional
from rich.console import Console
from novelcast.dub.pipeline import DubbingPipeline

console = Console()

def dub_audiobook(
    audiobook_file: str = typer.Argument(..., help="Path to input audio file or M4B audiobook (e.g. book.m4b, book.mp3)"),
    from_lang: str = typer.Option("en", "--from-lang", "-f", help="Source language code (e.g. en, ja, es)"),
    to_lang: str = typer.Option("es", "--to-lang", "-t", help="Target translation language code (e.g. es, en, fr)"),
    engine: str = typer.Option("omnivoice", "--engine", "-e", help="TTS synthesis engine (omnivoice, qwen3, cosyvoice, kokoro)"),
    remote: Optional[str] = typer.Option(None, "--remote", "-r", help="Remote GPU server URL (e.g. http://192.168.0.180:9880/synthesize)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Path to output translated M4B audiobook"),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of parallel GPU worker threads"),
    sample_seconds: int = typer.Option(60, "--sample-seconds", "-s", help="Seconds of audio to sample for initial voice harvesting (0 for entire file)"),
    ref_voice: Optional[str] = typer.Option(None, "--ref-voice", help="Path to custom clean reference audio WAV/MP3 to override voice clone"),
    whisper_model: str = typer.Option("base", "--whisper-model", help="Whisper ASR model size (tiny, base, small, medium, large-v3)"),
    llm_api_base: Optional[str] = typer.Option(None, "--llm-base", help="OpenAI/Ollama API base URL for translation (e.g. http://localhost:11434/v1)"),
    llm_api_key: Optional[str] = typer.Option(None, "--llm-key", help="API key for translation LLM")
):
    """
    Dub and translate an existing audiobook while cloning and preserving the original voice actors and tone.
    """
    if not os.path.exists(audiobook_file):
        console.print(f"[bold red]Error:[/bold red] Input audio file '{audiobook_file}' not found.")
        raise typer.Exit(1)

    console.print(f"\n[bold green]NovelCast Dub: Voice-Preserving Cross-Lingual Studio[/bold green]")
    console.print(f"  • Source Audiobook: {audiobook_file} ({from_lang.upper()})")
    console.print(f"  • Target Language: {to_lang.upper()}")
    console.print(f"  • Synthesis Engine: {engine.upper()} (remote={remote or 'Local'})\n")

    pipeline = DubbingPipeline(
        project_dir="workspace_dub",
        whisper_model=whisper_model,
        llm_api_base=llm_api_base,
        llm_api_key=llm_api_key
    )

    result_m4b = pipeline.run(
        input_audio=audiobook_file,
        from_lang=from_lang,
        to_lang=to_lang,
        engine_name=engine,
        remote_url=remote,
        output_m4b=output,
        workers=workers,
        sample_seconds=sample_seconds,
        ref_voice=ref_voice
    )

    console.print(f"[bold green]Dubbing complete! Output:[/bold green] {result_m4b}")
