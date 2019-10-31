import sys
import click
import json

from pathlib import Path;
from src.state import State;

@click.group(name="blog")
def cli() -> None:
    """Build management script for static blog site"""

@cli.command(name="init")
def init_cmd() -> None:
    path = Path("state.json")
    if path.exists():
        click.echo("state.json already exists, blog already initialized")
        sys.exit(1)

    state = State([])
    path.write_text(json.dumps(state.to_json()))




def main() -> None:
    cli()
