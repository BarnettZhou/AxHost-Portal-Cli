"""入口点"""

import asyncio
import sys

from .main import main

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(1)
