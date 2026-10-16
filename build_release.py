"""Builds the release files into dist/:
    voidling_bound.apworld  - apworld/voidling_bound, with the manifest Archipelago expects in packaged apworlds
    Voidlingpelago.zip      - the UE4SS mod, to unzip into the game's ue4ss/Mods/ folder
    Voidling Bound.yaml     - player options template
"""
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
WORLD = ROOT / "apworld" / "voidling_bound"
MOD = ROOT / "mod" / "Voidlingpelago"
DIST = ROOT / "dist"
CONTAINER_VERSION = 7  # worlds.Files.container_version of Archipelago 0.6.x


def zip_folder(zf: zipfile.ZipFile, folder: Path, skip=lambda path: False) -> None:
    for path in sorted(folder.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts or skip(path):
            continue
        zf.write(path, Path(folder.name) / path.relative_to(folder))


def build_apworld() -> Path:
    manifest = json.loads((WORLD / "archipelago.json").read_text(encoding="utf-8"))
    manifest.update({"version": CONTAINER_VERSION, "compatible_version": CONTAINER_VERSION})
    output = DIST / "voidling_bound.apworld"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zip_folder(zf, WORLD, skip=lambda path: path.name == "archipelago.json")
        zf.writestr("voidling_bound/archipelago.json", json.dumps(manifest, indent=4))
    return output


def build_mod() -> Path:
    output = DIST / "Voidlingpelago.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zip_folder(zf, MOD)
    return output


def main() -> None:
    DIST.mkdir(exist_ok=True)
    template = Path(shutil.copy(ROOT / "apworld" / "Voidling Bound.yaml", DIST))
    for output in (build_apworld(), build_mod(), template):
        print(f"Built {output}")


if __name__ == "__main__":
    main()
