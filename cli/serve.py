import typer
from rich.console import Console

console = Console()

def serve_api(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development")
):
    """
    Start the NovelCast Studio REST API server for Web and Desktop GUIs.
    """
    try:
        import uvicorn
        console.print(f"[bold green]🚀 Starting NovelCast Studio API on http://{host}:{port}[/bold green]")
        uvicorn.run("novelcast.server.app:app", host=host, port=port, reload=reload)
    except ImportError:
        console.print("[bold red]Error: uvicorn is required to run the server. Install it with: pip install 'novelcast[server]'[/bold red]")
        raise typer.Exit(code=1)
