import jinja2
import shutil
from pathlib import Path

from src.state import State, Post

def build(
        state: State,
        output_dir: Path
) -> None:

    print(Path.cwd())
    clear_directory(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Copy public files from design
    shutil.copytree(Path("design/public"), output_dir / "public")

    # Render posts
    posts_dir = output_dir / "posts"
    posts_dir.mkdir(exist_ok=True)

    for post in state.posts:
        template = load_template(post.path)
        with open(posts_dir / (post.title + ".html"), "w") as f:
            template.stream(post=post).dump(f)


def load_template(template_file: Path) -> jinja2.Template:
    """Load a jinja template from a file.

    There isn't a method in the standard API that does this, so
    we roll it ourselves."""

    env = jinja2.Environment(loader=jinja2.FileSystemLoader("design/pages/"))
    return env.get_template(str(template_file))

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

