import sys
import click
import json
import subprocess
import functools
import socketserver
import http.server
from datetime import datetime
from pathlib import Path
import subprocess

from src.state import State, Post
import src.generate as generate

state_path = Path("state.json")


@click.group(name="blog")
def cli() -> None:
    """Build management script for static blog site"""


@cli.command(name="init")
@click.option("--force", is_flag=True, default=False)
def init_cmd(force: bool) -> None:
    if state_path.exists() and not force:
        click.echo("state.json already exists, blog already initialized")
        sys.exit(1)

    state = State(
        [Post(0, "test_post", datetime.now())]
    )
    state_path.write_text(json.dumps(state.to_json()))


@cli.command(name="build")
@click.option("--debug", is_flag=True, default=False)
def build_cmd(debug: bool) -> None:
    if not state_path.exists():
        click.echo("Could not find state.json, please run blog init first")
        sys.exit(1)

    state = State.from_json(json.loads(state_path.read_text()))
    if not state:
        click.echo("state.json is not valid")
        sys.exit(1)

    output_dir = Path("ignore") / "build"
    source_dir = Path("design")
    generate.build(source_dir, state, output_dir, debug=debug)


@cli.command("preview")
@click.option("--port", default=8000, type=int, help="Port to use")
@click.option("--bind", default="", help="Address to bind on (default: all interfaces)")
@click.option(
    "--watch", is_flag=True, default=False, help="Auto rebuild on source changes"
)
def preview_cmd(port: int, bind: str, watch: bool) -> None:
    """Run a local webserver on build output"""
    output_dir = Path("ignore/build")
    if not output_dir.is_dir():
        click.echo("No output to serve. Please run `pxl build` first.", err=True)
        sys.exit(1)

    click.launch(f"http://localhost:{port}")

    if watch:
        subprocess.run(["scripts/watch.sh"])

    # Start the default Python HTTP server.
    #
    # We want to specify that the `build` directory is used for serving
    # the responses. The TCPServer class expects a `handler_class` to
    # initialize, so we can't construct in a `SimpleHTTPRequestHandler`
    # instance and pass it the `directory` argument directly. Instead
    # we need to partially apply the constructor with the `directory`
    # keyword argument and pass that as the handler_class.
    #
    # This feels more complicated than it should be.
    server_address = (bind, port)
    socketserver.TCPServer.allow_reuse_address = True
    handler_class = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(output_dir)
    )
    with socketserver.TCPServer(server_address, handler_class) as httpd:  # type: ignore
        click.echo(f"Serving {output_dir} at port {port}", err=True)
        httpd.serve_forever()


def main() -> None:
    cli()
