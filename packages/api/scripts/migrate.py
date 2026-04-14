"""Thin wrapper around Alembic CLI that eliminates the need for alembic.ini.

Usage:
    python -m scripts.migrate upgrade head
    python -m scripts.migrate revision --autogenerate -m "add foo column"
    python -m scripts.migrate downgrade -1
    python -m scripts.migrate history
"""

from pathlib import Path

from alembic.config import CommandLine, Config

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    cli = CommandLine()
    options = cli.parser.parse_args()

    cfg = Config()
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    # sqlalchemy.url is set dynamically in env.py from app settings

    cli.run_cmd(cfg, options)


if __name__ == "__main__":
    main()
