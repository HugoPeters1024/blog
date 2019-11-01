import jinja2
import shutil
import click
import pygments
from pygments.formatters import HtmlFormatter
import pygments.lexers
from pathlib import Path
from typing import Callable

from src.state import State, Post


def build(
    source_dir: Path, state: State, output_dir: Path, debug: bool = False
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
    env.globals["highlight"] = highlight

    load_template: Callable[
        [Path], jinja2.Template
    ] = lambda template_file: env.get_template(str(template_file))

    # Render index
    template = load_template(Path("index.html"))
    with open(output_dir / "index.html", "w") as f:
        template.stream(state=state).dump(f)

    # Render posts
    posts_output = output_dir / "posts"
    posts_output.mkdir(exist_ok=True)

    for post in state.posts:
        template = load_template(Path("posts") / str(post.number) / "index.html")
        post_path = posts_output / str(post.number)
        post_path.mkdir(exist_ok=True)
        with open(post_path /  "index.html", "w") as f:
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

def highlight(lang: str, code: str) -> str:
    formatter = HtmlFormatter()

    # Remove all common whitespace
    lines = code.split('\n')
    while all([str(x)[0].isspace() for x in lines if len(x) > 0]) and not \
            all([len(x) == 0 for x in lines]):
        for i in range(len(lines)):
            if len(lines[i]) > 0:
                lines[i] = lines[i][1:]
    code = "\n".join(lines) 
    lex = pygments.lexers.get_lexer_by_name(lang)
    return pygments.highlight(code, lex, formatter)
