import os
import json
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from novelcast.core.schema import ChapterScript
from novelcast.core.voice_bank import VoiceBank
from novelcast.core.llm_manager import LLMConfigManager
from novelcast.core.ai_director import AIDirector

console = Console()

def direct_script(
    script_path: str = typer.Argument(..., help="Path to chapter script JSON file (e.g. data/scripts/vol2_02_capitulo_2.json)"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM Provider ID (ollama, lmstudio, deepseek, openai, groq, openrouter, custom)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model override (e.g. qwen2.5:7b, deepseek-chat, gpt-4o-mini)"),
    batch_size: int = typer.Option(25, "--batch-size", "-b", help="Number of dialogue lines to process per LLM context window"),
    config: str = typer.Option("voice_config.json", "--config", "-c", help="Path to voice_config.json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Optional custom output JSON path (defaults to overwriting script_path)")
):
    """
    Direct and auto-fix dialogue speakers, emotional tone prompts, and audio tokens in a chapter script using an LLM.
    """
    if not os.path.exists(script_path):
        console.print(f"[bold red]Error: Script file '{script_path}' not found.[/bold red]")
        raise typer.Exit(code=1)

    with open(script_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    script = ChapterScript(**data)

    vb = VoiceBank(config_path=config)
    mgr = LLMConfigManager()

    active_provider = provider or mgr.config.active_provider
    prov_cfg = mgr.get_provider(active_provider)
    active_model = model or mgr.config.active_model or prov_cfg.default_model

    console.print(f"[bold magenta]🎬 NovelCast AI Script Director[/bold magenta]")
    console.print(f"📖 [cyan]Chapter:[/cyan] {script.title} ({len(script.segments)} segments)")
    console.print(f"🤖 [yellow]LLM Provider:[/yellow] {prov_cfg.name} | [green]Model:[/green] {active_model}")
    console.print(f"🎙️ [dim]Voice Bank Characters:[/dim] {len(vb.config.characters)} profiles registered\n")

    director = AIDirector(config_manager=mgr)
    director.set_provider(active_provider, model_override=active_model)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Directing chapter dialogue...", total=len(script.segments))

        def on_batch(b_num, total_b, fixed_cnt, msg):
            progress.update(task, completed=min(b_num * batch_size, len(script.segments)), description=f"[cyan]{msg}[/cyan]")

        updated_script, diffs = director.direct_chapter_script(
            script=script,
            vb=vb,
            batch_size=batch_size,
            progress_callback=on_batch
        )

    # Save output
    out_path = output or script_path
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(updated_script.dict(), f, indent=2, ensure_ascii=False)

    console.print(f"\n[bold green]✓ AI Direction Complete![/bold green] Saved to: [dim]{out_path}[/dim]")
    console.print(f"[bold yellow]Total Lines Corrected:[/bold yellow] [cyan]{len(diffs)}[/cyan] out of {len(script.segments)}\n")

    if diffs:
        table = Table(title="AI Director Changes Diff Sample", show_header=True, header_style="bold magenta")
        table.add_column("Line #", style="dim", width=8)
        table.add_column("Original Speaker", style="red", width=18)
        table.add_column("AI Corrected Speaker", style="green", width=20)
        table.add_column("Delivery Instruct & Audio Token", style="yellow")
        table.add_column("Explanation / Reasoning", style="white")

        for d in diffs[:12]:
            inst_str = d.get("new_instruct") or "-"
            table.add_row(
                str(d["id"]),
                d["old_speaker"],
                f"✓ {d['new_speaker']}",
                inst_str,
                d.get("explanation", "-")
            )

        console.print(table)
        if len(diffs) > 12:
            console.print(f"[dim]... and {len(diffs) - 12} more corrected lines.[/dim]")
