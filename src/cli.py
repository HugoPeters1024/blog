import sys
import click
import json

from pathlib import Path;

@click.group(name="blog")
def cli() -> None:
    """Build management script for static blog site"""

@cli.command(name="init")
def init_cmd() -> None:
    state = Path("lock.json")
    if state.exists():
        click.echo("lock.json already exists, blog already initialized")
        sys.exit(1)


    

def main() -> None:
    cli()
