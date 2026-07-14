from pathlib import Path

import config


PATTERNS = [
    config.DATA_DIR / "*.csv",
    config.RESULTS_DIR / "*.csv",
    config.RESULTS_DIR / "*.json",
    config.PLOTS_DIR / "*.png",
]


def main():
    removed = 0
    for pattern in PATTERNS:
        for path in Path(pattern.parent).glob(pattern.name):
            path.unlink()
            removed += 1
    print(f"Removed {removed} generated files.")


if __name__ == "__main__":
    main()
