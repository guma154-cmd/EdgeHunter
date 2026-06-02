import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.edgehunter.ops.environment_check import run_environment_check

def main():
    res = run_environment_check(base_path=str(Path(__file__).parent.parent))
    print(res)

if __name__ == "__main__":
    main()
