from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path


def ensure_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def append_if_missing(path: Path, marker: str, block: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + block.strip() + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap new module context files for Project YK."
    )
    parser.add_argument("module_path", help="Module folder path, e.g. SalesOps")
    parser.add_argument(
        "--purpose",
        default="TODO: describe module purpose",
        help="Short purpose text for module registry",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    module_rel = Path(args.module_path).as_posix().strip("/")
    module_name = Path(module_rel).name
    module_dir = repo_root / module_rel

    ensure_file(
        module_dir / "AGENT_MEMORY.md",
        f"# {module_name} Agent Memory\n\n- Purpose: {args.purpose}\n- Add current standards here.\n",
    )
    ensure_file(
        module_dir / "DECISION_LOG.md",
        f"# {module_name} Decision Log\n\n## {date.today().isoformat()}\n- Initialized module log.\n",
    )

    registry = repo_root / "ProjectYK_System" / "MODULE_REGISTRY.md"
    row_marker = f"| {module_name} |"
    row = (
        f"| {module_name} | {args.purpose} | `{module_rel}/` | "
        f"`{module_rel}/AGENT_MEMORY.md` | `{module_rel}/DECISION_LOG.md` | `-` |"
    )
    append_if_missing(registry, row_marker, row)

    master_log = repo_root / "ProjectYK_System" / "CHANGELOG_MASTER.md"
    log_marker = f"- Registered new module: `{module_name}`"
    log_block = (
        f"## {date.today().isoformat()} (module bootstrap)\n"
        f"- Registered new module: `{module_name}`\n"
        f"- Module path: `{module_rel}/`\n"
        f"- Created: `AGENT_MEMORY.md`, `DECISION_LOG.md`"
    )
    append_if_missing(master_log, log_marker, log_block)

    print(f"Done. Module ready at: {module_dir}")


if __name__ == "__main__":
    main()
