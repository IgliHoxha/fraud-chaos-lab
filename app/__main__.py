"""Enable ``python -m app`` to reach the CLI."""

import sys

from app.cli import main

if __name__ == "__main__":
    sys.exit(main())
