import jinja2
import shutil
import click
from pygments.formatters import HtmlFormatter  # type: ignore
import pygments.lexers  # type: ignore
from pathlib import Path
from typing import Callable, List, Any

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
    for entry in source_dir.iterdir():
        if entry.is_dir():
            if entry.name == "templates":
                continue
            shutil.copytree(entry, output_dir / entry.name)
        else:
            shutil.copy(entry, output_dir)

    # Setup jinja2 context
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("design/"))
    env.globals["DEBUG"] = debug
    env.globals["highlight"] = highlight

    load_template: Callable[
        [Path], jinja2.Template
    ] = lambda template_file: env.get_template(str(template_file))


    # Render index
    template = load_template("index.html")
    with open(output_dir / "index.html", "w") as f:
        template.stream(state=state).dump(f)

    # Render posts index
    posts_dir = output_dir / "posts"

    # Render posts index
    template = load_template(Path("posts") / "index.html")
    with open(posts_dir / "index.html", "w") as f:
        template.stream(state=state).dump(f)

    for post in state.posts:
        # Copy all files
        post_path = posts_dir / str(post.number)

        # load template
        template = load_template(Path("posts") / str(post.number) / "index.html")

        # overwrite template with rendered version
        with open(post_path / "index.html", "w") as f:
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

    # special all() function that return false for empty sets
    alln: Callable[[List[Any]], bool] = lambda l: all(l) and len(l) > 0

    # Remove all shared whitespace
    lines = code.split("\n")
    while alln([str(x)[0].isspace() for x in lines if len(x) > 0]):
        for i in range(len(lines)):
            if len(lines[i]) > 0:
                lines[i] = lines[i][1:]
    code = "\n".join(lines)
    lex = pygments.lexers.get_lexer_by_name(lang)
    return str(pygments.highlight(code, lex, formatter))
