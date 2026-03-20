"""CLI interface for Purple Team GPT."""

import typer
from rich.console import Console

app = typer.Typer(name="purple-team")
console = Console()


@app.command()
def version() -> None:
    """Show version information."""
    from purple_team_gpt import __version__, __app_name__
    console.print(f"{__app_name__} v{__version__}")


@app.command()
def config() -> None:
    """Show current configuration."""
    from purple_team_gpt.config import get_settings
    settings = get_settings()
    console.print(settings.model_dump_json(indent=2))


@app.command()
def run(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
) -> None:
    """Run the API server."""
    import uvicorn
    console.print(f"[green]Starting Purple Team GPT server on {host}:{port}[/green]")
    uvicorn.run(
        "purple_team_gpt.backend.main:app",
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()