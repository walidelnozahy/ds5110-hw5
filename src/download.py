"""Part 1: download the raw file once. Never overwrite it."""
import sys
from pathlib import Path
from urllib.request import urlretrieve

# Copy the link to AmesHousing.txt from the JSE article page (De Cock, 2011).
# Record the same URL and today's date in README.md.
DATA_URL = "https://jse.amstat.org/v19n3/decock/AmesHousing.txt"


def main(dest: str) -> None:
    path = Path(dest)
    if path.exists():
        print(f"{path} exists; raw data is never overwritten.")
        return
    if not DATA_URL:
        sys.exit("Set DATA_URL in src/download.py first.")
    path.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(DATA_URL, path)
    print(f"Downloaded {path}")


if __name__ == "__main__":
    main(sys.argv[1])
