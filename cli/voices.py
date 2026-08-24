import os
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from novelcast.core.voice_bank import VoiceBank
from novelcast.core.schema import CharacterVoice, Segment
from novelcast.engines import get_engine

console = Console()
app = typer.Typer(help="Manage and test character voice profiles and audio samples.")

@app.command("list")
def list_voices(
    config: str = typer.Option("voice_config.json", "--config", "-c", help="Path to voice_config.json")
):
    """List all configured character voices and reference audio files."""
    vb = VoiceBank(config_path=config)
    chars = vb.list_characters()

    table = Table(title="NovelCast Voice Bank", show_header=True, header_style="bold magenta")
    table.add_column("Character", style="cyan", width=16)
    table.add_column("Gender", style="green", width=10)
    table.add_column("Speed / Scale", style="yellow", width=14)
    table.add_column("Instruct Prompt", style="white")
    table.add_column("Ref Audio", style="dim", width=22)

    for name, char in chars.items():
        ref = char.reference_audio or "-"
        inst = char.instruct or "(Narrator Default)"
        sp_sc = f"{char.speed}x / {char.guidance_scale}"
        table.add_row(name, char.gender or "-", sp_sc, inst, ref)

    console.print(table)

@app.command("test")
def test_voice(
    speaker: str = typer.Argument(..., help="Character name to test"),
    text: str = typer.Option("Hola, esto es una prueba de voz con NovelCast.", "--text", "-t", help="Text to speak"),
    engine_name: str = typer.Option("omnivoice", "--engine", "-e", help="TTS Engine (omnivoice, cosyvoice, kokoro, elevenlabs)"),
    remote_url: Optional[str] = typer.Option(None, "--remote", "-r", help="Remote GPU server URL. If omitted, runs local model."),
    output: str = typer.Option("output/voice_test.mp3", "--output", "-o", help="Output audio file path"),
    config: str = typer.Option("voice_config.json", "--config", "-c", help="Path to voice_config.json")
):
    """Synthesize a quick test audio clip for a character voice."""
    vb = VoiceBank(config_path=config)
    char = vb.get_character(speaker)
    engine = get_engine(engine_name, remote_url=remote_url, cache_dir="cache_test")

    seg = Segment(
        id=1,
        speaker=speaker,
        text=text,
        instruct=char.instruct,
        speed=char.speed,
        guidance_scale=char.guidance_scale
    )

    console.print(f"[bold yellow]🎙️ Testing voice for:[/bold yellow] [cyan]{speaker}[/cyan] with engine [green]{engine_name}[/green]...")
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    success = engine.synthesize_chunk(seg, vb, output)

    if success and os.path.exists(output):
        console.print(f"[bold green]✓ Voice sample generated successfully:[/bold green] {output}")
    else:
        console.print(f"[bold red]✗ Failed to generate voice sample for {speaker}[/bold red]")

@app.command("add")
def add_voice(
    name: str = typer.Argument(..., help="Character name"),
    instruct: Optional[str] = typer.Option(None, "--instruct", "-i", help="Instruct prompt (e.g. 'female, young adult, high pitch')"),
    ref_audio: Optional[str] = typer.Option(None, "--ref", "-r", help="Path to reference audio file"),
    gender: str = typer.Option("unspecified", "--gender", "-g", help="Gender"),
    speed: float = typer.Option(1.0, "--speed", "-s", help="Speaking speed multiplier"),
    config: str = typer.Option("voice_config.json", "--config", "-c", help="Path to voice_config.json")
):
    """Add or update a character voice profile."""
    vb = VoiceBank(config_path=config)
    voice = CharacterVoice(
        gender=gender,
        instruct=instruct,
        reference_audio=ref_audio,
        speed=speed
    )
    vb.add_character(name, voice)
    console.print(f"[bold green]✓ Saved character voice profile for:[/bold green] [cyan]{name}[/cyan]")

@app.command("remove")
def remove_voice(
    name: str = typer.Argument(..., help="Character name to remove"),
    config: str = typer.Option("voice_config.json", "--config", "-c", help="Path to voice_config.json")
):
    """Remove a character voice profile from voice_config.json."""
    vb = VoiceBank(config_path=config)
    if name in vb.config.characters:
        del vb.config.characters[name]
        vb.save()
        console.print(f"[bold green]✓ Removed character voice profile:[/bold green] [cyan]{name}[/cyan]")
    else:
        console.print(f"[bold red]✗ Character '{name}' not found in voice config.[/bold red]")

@app.command("ingest")
def ingest_voice(
    audio_path: str = typer.Argument(..., help="Path to reference audio file (.wav, .mp3, .flac)"),
    speaker_name: str = typer.Option(None, "--name", "-n", help="Character / Speaker name (default derived from filename)"),
    category: str = typer.Option("custom", "--category", "-cat", help="Target subfolder in voice_bank/ (e.g. custom, all_voices)"),
    gender: str = typer.Option("unspecified", "--gender", "-g", help="Gender (male, female, kid, neutral)"),
    instruct: Optional[str] = typer.Option(None, "--instruct", "-i", help="Instruct delivery prompt"),
    config: str = typer.Option("voice_config.json", "--config", "-c", help="Path to voice_config.json")
):
    """Copy an audio file into the Voice Bank and register its character profile."""
    if not os.path.exists(audio_path):
        console.print(f"[bold red]Error: File '{audio_path}' not found.[/bold red]")
        raise typer.Exit(code=1)

    import shutil
    base_file = os.path.basename(audio_path)
    target_dir = os.path.join("voice_bank", category) if category != "root" else "voice_bank"
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, base_file)

    shutil.copy2(audio_path, target_path)
    rel_path = os.path.relpath(target_path, "voice_bank")
    
    char_key = speaker_name or os.path.splitext(base_file)[0].replace("_", " ").title()
    vb = VoiceBank(config_path=config)
    vb.config.characters[char_key] = CharacterVoice(
        gender=gender,
        instruct=instruct,
        reference_audio=f"voice_bank/{rel_path}",
        description=f"Ingested audio sample: {base_file}"
    )
    vb.save()
    console.print(f"[bold green]✓ Ingested and registered voice sample:[/bold green] [cyan]{char_key}[/cyan] -> [dim]{target_path}[/dim]")
