import jinja2
import shutil
import click
from pathlib import Path
from typing import Callable

from src.state import State, Post

def build(
        source_dir: Path,
        state: State,
        output_dir: Path,
        debug: bool = False,
) -> None:
    if not Path.cwd() == Path.home() / "repos" / "blog":
        click.echo("Running from bad location")
        exit(1)

    clear_directory(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)


    # Copy public files from design
    shutil.copytree(source_dir / "public", output_dir / "public")

    # Setup jinja2 context
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("design/pages/"))
    env.globals["DEBUG"] = debug

    load_template : Callable[[Path], jinja2.Template] = lambda template_file: env.get_template(str(template_file))

    # Render index
    template = load_template("index.html")
    with open(output_dir / "index.html", "w") as f:
        template.stream(state=state).dump(f)

    # Render posts
    posts_dir = output_dir / "posts"
    posts_dir.mkdir(exist_ok=True)

    for post in state.posts:
        template = load_template(post.path)
        with open(posts_dir / (post.title + ".html"), "w") as f:
            template.stream(post=post).dump(f)


def clear_directory(dir_path: Path) -> None:
    """Remove all directory contents, except for the directory itself.

    This is useful so the inode number for the directory doesn't get removed
    and HTTP servers and the like keep on working."""

    if not dir_path.exists():
        return

    assert dir_path.is_dir()

    for entry in dir_path.iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()

