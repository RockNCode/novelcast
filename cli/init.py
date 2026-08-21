import os
import shutil
import typer
from rich.console import Console

console = Console()

def init_project(
    project_dir: str = typer.Argument(".", help="Directory to initialize the NovelCast project in"),
    name: str = typer.Option("My Audiobook", "--name", "-n", help="Name of the audiobook project")
):
    """
    Initialize a new NovelCast workspace with directory structure and example configs.
    """
    base = os.path.abspath(project_dir)
    os.makedirs(os.path.join(base, "data", "scripts"), exist_ok=True)
    os.makedirs(os.path.join(base, "voice_bank"), exist_ok=True)
    os.makedirs(os.path.join(base, "output", "chapters"), exist_ok=True)
    os.makedirs(os.path.join(base, "cache_omnivoice"), exist_ok=True)

    config_src = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "configs")
    
    project_yaml = os.path.join(base, "project.yaml")
    if not os.path.exists(project_yaml):
        src_yaml = os.path.join(config_src, "project.example.yaml")
        if os.path.exists(src_yaml):
            shutil.copy(src_yaml, project_yaml)
        else:
            with open(project_yaml, "w") as f:
                f.write(f'project_name: "{name}"\nlanguage: "es"\n')

    voice_cfg = os.path.join(base, "voice_config.json")
    if not os.path.exists(voice_cfg):
        src_voice = os.path.join(config_src, "voice_config.example.json")
        if os.path.exists(src_voice):
            shutil.copy(src_voice, voice_cfg)

    console.print(f"[bold green]✨ Initialized NovelCast project at:[/bold green] {base}")
    console.print("  • Created [cyan]data/scripts/[/cyan], [cyan]voice_bank/[/cyan], [cyan]output/[/cyan], [cyan]cache_omnivoice/[/cyan]")
    console.print("  • Created [yellow]project.yaml[/yellow] and [yellow]voice_config.json[/yellow]")
