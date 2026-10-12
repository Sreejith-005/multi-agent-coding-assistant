"""CLI:  python main.py "Build a calculator web app ..." """
import argparse
from pathlib import Path

from .agent import run_stream
from .agent.tools import zip_project


def main():
    ap = argparse.ArgumentParser(description="Multi-agent coding assistant")
    ap.add_argument("prompt", help="What to build")
    ap.add_argument("--model", default=None, help="Groq model id (default: $GROQ_MODEL)")
    args = ap.parse_args()

    project_dir = None
    for node, update in run_stream(args.prompt, args.model):
        print(f"[{node}] {update.get('status', '')}")
        project_dir = update.get("project_dir", project_dir)

    if project_dir:
        zip_path = Path(project_dir).with_suffix(".zip")
        zip_path.write_bytes(zip_project(project_dir))
        print(f"\nProject: {project_dir}\nZip:     {zip_path}")


if __name__ == "__main__":
    main()
