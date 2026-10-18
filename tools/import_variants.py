"""Turns the developer tools' variant dump into the apworld's variant list.

Usage: python tools/import_variants.py %APPDATA%/Voidlingpelago/variants.txt

variants.txt (written by F5 in the developer tools, next to genes.txt) has one tab separated line per variant:
    asset path, evolution name, creature name, species code, species name, rarity, cost

The location is named after the creature name the game shows ("Variant: Qwebek Kwipeck"), or the species and
evolution name when the game didn't give one. Variants already in apworld/voidling_bound/data/variants.json keep
their ID and name, new ones get the next free IDs, and none are ever removed or renumbered (IDs are part of the
network protocol).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from import_genes import clean_text  # noqa: E402

VARIANTS_JSON = Path(__file__).parent.parent / "apworld" / "voidling_bound" / "data" / "variants.json"
FIRST_ID = 847001


def parse_dump(text: str) -> list:
    variants = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        fields = (line.split("\t") + [""] * 7)[:7]
        path, evolution_name, creature_name, species_code, species_name, rarity, cost = (f.strip() for f in fields)
        asset = path.rsplit(".", 1)[-1]
        species = species_name or species_code or "Unknown"
        display = creature_name or f"{evolution_name or asset} {species}".strip()
        variants.append({"asset": asset, "path": path, "species": species, "display": clean_text(display)})
    return variants


def merge(existing: list, dumped: list) -> tuple:
    by_asset = {entry["asset"]: entry for entry in existing}
    used_names = {entry["name"] for entry in existing}
    next_id = max([entry["id"] for entry in existing], default=FIRST_ID - 1) + 1
    added = []
    for variant in sorted(dumped, key=lambda v: v["path"]):
        if variant["asset"] in by_asset:
            continue
        name = f"Variant: {variant['display']}"
        if name in used_names:
            suffix = 2
            while f"{name} ({suffix})" in used_names:
                suffix += 1
            name = f"{name} ({suffix})"
        entry = {"id": next_id, "name": name, "species": variant["species"], "asset": variant["asset"],
                 "path": variant["path"]}
        next_id += 1
        used_names.add(name)
        by_asset[variant["asset"]] = entry
        added.append(entry)
    return sorted(by_asset.values(), key=lambda e: e["id"]), added


def main(dump_path: str, variants_json: Path = VARIANTS_JSON) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dumped = parse_dump(Path(dump_path).read_text(encoding="utf-8"))
    existing = json.loads(variants_json.read_text(encoding="utf-8")) if variants_json.exists() else []
    merged, added = merge(existing, dumped)
    variants_json.write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(dumped)} variants in the dump, {len(added)} new, {len(merged)} in {variants_json}")
    for entry in added:
        print(f"  {entry['id']}  {entry['name']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
