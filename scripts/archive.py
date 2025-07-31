from pathlib import Path

from rad import Reader

if __name__ == "__main__":
    print("Create archive for the latest")
    Reader.from_rad().create_archive(Path(__file__).parent.parent / "archive.json")

    print("Create archive for the static schemas")
    Reader.from_rad(manifest_type="static").create_archive(Path(__file__).parent.parent / "static_archive.json")
