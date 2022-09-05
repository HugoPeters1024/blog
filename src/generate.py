import jinja2
import shutil
import click
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Callable, List, Any, Optional
from pygments.formatters import HtmlFormatter  # type: ignore
import pygments.lexers  # type: ignore

from src.state import State, Post, PreparedPost, PreparedState

def include_file(filename: str):
    with open(filename, "r") as f:
        return f.readlines()


def build(
    source_dir: Path, locked_state: State, output_dir: Path, debug: bool = False
) -> None:

    if debug:
        print("DEBUG ENABLED!")

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

    # Prepare state
    state = prepareState(locked_state, output_dir)

    # Setup jinja2 context
    env = jinja2.Environment(loader=jinja2.FileSystemLoader("design/"))
    env.globals["DEBUG"] = debug
    env.globals["highlight"] = highlight
    env.globals["refPostString"] = lambda post_id: refPostString(state, post_id)
    env.globals["include_file"] = include_file

    load_template: Callable[
        [Path], jinja2.Template
    ] = lambda template_file: env.get_template(str(template_file).replace('\\', '/'))

    # Render index
    template = load_template(Path("index.html"))
    with open(output_dir / "index.html", "w") as f:
        template.stream(state=state).dump(f)

    # Render posts index
    posts_dir = output_dir / "posts"
    template = load_template(Path("posts") / "index.html")
    with open(posts_dir / "index.html", "w") as f:
        template.stream(state=state).dump(f)

    for post in state.posts:
        post_path = posts_dir / str(post.number)

        # load template
        template = load_template(Path("posts") / str(post.number) / "index.html")
        render = template.render(post=post)

        # overwrite template with rendered version
        with open(post_path / "index.html", "w", encoding="utf-8") as f:
            f.write(render)


def prepareState(state: State, root: Path) -> PreparedState:
    posts_dir = root / "posts"
    prepared_posts = []
    for post in state.posts:
        post_path = posts_dir / str(post.number)

        modifiedAt = lastModified(post_path)

        # load the abstract
        abstract = "abstract not available"
        abstract_path = post_path / "abstract.html"
        if abstract_path.exists():
            with open(abstract_path, "r") as f:
                abstract = f.read()
        prepared_posts.append(
            PreparedPost(
                post.number,
                post.title,
                post.postedAt,
                post.languages,
                post.favicon,
                modifiedAt,
                abstract,
            )
        )

    return PreparedState(prepared_posts)


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


def highlight(lang: str, code: str, source: Optional[str] = None) -> str:
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
    res = str(pygments.highlight(code, lex, formatter))
    # Assuming tag ends with the 6 characters of '</div>'
    if source:
        res = (
            res[:-7]
            + f'<a class="source" href="{source}" target="_blank">full source</a></pre></div>'
        )
    return res

def lastModified(path: Path) -> datetime:
    latest = 0
    for entry in path.glob("*"):
        if not entry.is_dir():
            mtime = int(entry.stat().st_mtime)
            latest = max(latest, mtime)

    return datetime.fromtimestamp(latest)


def refPostString(state: PreparedState, post_id: int) -> str:
    for post in state.posts:
        if post.number == post_id:
            res_post = post
            break
    else:
        raise Exception(f"Post {post_id} does not exist but is referenced")
    return f'<a href="/posts/{post_id}">{res_post.title}</a>'
