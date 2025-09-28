"""Entry point for running ReTileUp as a module."""

import sys
from typing import Any


def main() -> Any:
    """Main entry point for python -m retileup."""
    try:
        from .cli.main import app
        return app()
    except ImportError as e:
        print(f"Error importing ReTileUp CLI: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()