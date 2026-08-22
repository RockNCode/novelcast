import typer
from rich.console import Console
from novelcast.cli.init import init_project
from novelcast.cli.parse import parse_book
from novelcast.cli.voices import app as voices_app
from novelcast.cli.generate import generate_script
from novelcast.cli.stitch import stitch_script
from novelcast.cli.package import package_audiobook
from novelcast.cli.run import run_pipeline
from novelcast.cli.serve import serve_api
from novelcast.cli.dub import dub_audiobook

console = Console()

app = typer.Typer(
    name="novelcast",
    help="NovelCast: Multi-Voice AI Audiobook Studio for Light Novels and Fiction",
    add_completion=False,
    no_args_is_help=True
)

# Register subcommands
app.command("init", help="Initialize a new NovelCast audiobook project workspace")(init_project)
app.command("parse", help="Extract and segment eBook dialogue and narration into chapter scripts")(parse_book)
app.add_typer(voices_app, name="voices")
app.command("generate", help="Synthesize speech audio chunks with multi-worker GPU acceleration and caching")(generate_script)
app.command("stitch", help="Stitch audio chunks into continuous chapter tracks with smart pause timing")(stitch_script)
app.command("package", help="Package stitched chapters into a master M4B audiobook with chapters and cover art")(package_audiobook)
app.command("run", help="Run the complete end-to-end pipeline in a single command")(run_pipeline)
app.command("dub", help="Translate and dub an existing audiobook while cloning original voices and tone")(dub_audiobook)
app.command("serve", help="Start the NovelCast Studio REST API for Web/Desktop GUIs")(serve_api)

@app.callback()
def main_callback():
    """
    NovelCast CLI: Multi-Voice AI Audiobook Studio.
    """
    pass

if __name__ == "__main__":
    app()
