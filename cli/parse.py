import os
import json
import zipfile
import typer
from rich.console import Console
from novelcast.core.parser import BookParser
from novelcast.core.director import Director

console = Console()

def parse_book(
    book_path: str = typer.Argument(..., help="Path to input EPUB or TXT file"),
    output_dir: str = typer.Option("data/scripts", "--output-dir", "-o", help="Directory to save generated JSON scripts"),
    book_name: str = typer.Option("NovelCast Audiobook", "--name", "-n", help="Name of the book")
):
    """
    Parse an EPUB file into structured chapter scripts with dialogue attribution.
    """
    if not os.path.exists(book_path):
        console.print(f"[bold red]Error: Book file '{book_path}' does not exist.[/bold red]")
        raise typer.Exit(code=1)

    os.makedirs(output_dir, exist_ok=True)
    parser = BookParser()

    console.print(f"[bold yellow]📖 Parsing eBook:[/bold yellow] [cyan]{book_path}[/cyan]...")

    chapters_meta = parser.parse_epub_chapters(book_path)
    total_chapters = len(chapters_meta)
    total_segments = 0
    total_dialogues = 0

    with zipfile.ZipFile(book_path, 'r') as z:
        for cinfo in chapters_meta:
            chap_id = cinfo["id"]
            chap_title = cinfo["title"]
            files = cinfo["files"]

            html_contents = []
            for fpath in files:
                if fpath in z.namelist():
                    html_contents.append(z.read(fpath).decode('utf-8', errors='ignore'))

            script = parser.parse_html_to_script(html_contents, chapter_id=chap_id, title=chap_title, book_name=book_name)

            out_path = os.path.join(output_dir, f"{chap_id}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)

            segs = len(script.segments)
            dials = script.dialogue_count
            total_segments += segs
            total_dialogues += dials

            console.print(f"  [green]✓[/green] [bold]{chap_id}.json[/bold]: {segs} segments ({dials} dialogues, {script.total_characters:,} chars)")

    console.print(f"\n[bold green]🎉 Parsing Complete![/bold green] Generated {total_chapters} chapters ({total_segments} total segments, {total_dialogues} dialogues) in [cyan]{output_dir}[/cyan]")
