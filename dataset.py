"""Versioned build-time bundles; no raw archive or request-time downloads."""

import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from urllib.error import HTTPError
from urllib.request import urlopen
import zipfile

# Runtime-only search_service.py consumes snapshots; it does not build them.
INPUTS = (
    "dataset-source.json",
    "core.py",
    "catalog.py",
    "character_catalog.py",
    "build.py",
    "build_portraits.py",
    "dataset.py",
    "portraits.source.json",
    "requirements.txt",
    "search_queries.py",
    "translation_alignment.py",
)
RELEASES = "https://github.com/gamerinl10n/Arknights_Index/releases/download"


def fingerprint(root=Path(".")):
    digest = hashlib.sha256()
    for name in INPUTS:
        digest.update(name.encode() + b"\0" + (root / name).read_bytes() + b"\0")
    return digest.hexdigest()[:24]


def bundle_paths(root):
    return [
        root / "generated/search.sqlite.gz",
        root / "characters.json",
        root / "characters.source.json",
        *sorted((root / "generated/portraits").glob("*")),
    ]


def pack(root=Path("."), output=Path("generated/dataset.zip")):
    manifest = {"fingerprint": fingerprint(root), "files": {}}
    paths = bundle_paths(root)
    if len(paths) < 4:
        raise ValueError("Incomplete dataset")
    for path in paths:
        manifest["files"][path.relative_to(root).as_posix()] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(root).as_posix())
        archive.writestr("manifest.json", json.dumps(manifest))


def restore(archive_path, root=Path(".")):
    """Validate the entire bundle before replacing any generated output."""
    with (
        zipfile.ZipFile(archive_path) as archive,
        tempfile.TemporaryDirectory() as folder,
    ):
        if (
            len(archive.infolist()) > 2000
            or sum(info.file_size for info in archive.infolist()) > 220 * 1024**2
        ):
            raise ValueError("Dataset bundle too large")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest["fingerprint"] != fingerprint(root):
            raise ValueError("Dataset fingerprint mismatch")
        names = manifest["files"]
        required = {
            "generated/search.sqlite.gz",
            "characters.json",
            "characters.source.json",
            "generated/portraits/index.json",
        }
        if not required.issubset(names) or set(archive.namelist()) != set(names) | {
            "manifest.json"
        }:
            raise ValueError("Incomplete dataset manifest")
        for name, digest in names.items():
            path = Path(name)
            if name not in required and (
                path.parent.as_posix() != "generated/portraits"
                or path.suffix != ".webp"
            ):
                raise ValueError("Unexpected bundle path")
            if archive.getinfo(name).file_size > 200 * 1024**2:
                raise ValueError("Dataset member too large")
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError("Dataset checksum mismatch")
            temporary = Path(folder) / name
            temporary.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(content)
        for name in names:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(folder) / name, destination)


def reuse(root=Path(".")):
    tag = "dataset-" + fingerprint(root)
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / "dataset.zip"
        try:
            with (
                urlopen(f"{RELEASES}/{tag}/dataset.zip", timeout=60) as response,
                archive.open("wb") as output,
            ):
                shutil.copyfileobj(response, output)
        except HTTPError as error:
            if error.code == 404:
                print(f"Dataset {tag} not published yet; building from pinned source")
                return False
            raise
        restore(archive, root)
    print(f"Reused verified dataset: {tag}")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "pack":
        pack()
    else:
        print(fingerprint())
