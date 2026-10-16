"""Turns the mod's gene dump into the apworld's gene list.

Usage: python tools/import_genes.py %APPDATA%/Voidlingpelago/genes.txt

genes.txt (written by the mod's F5 gene dump) has one tab separated line per gene:
    asset path, gene class, gene name, species code, species name, collectible
Genes the game reports as not collectible (UGeneDataAsset:IsCollectible) are skipped, they would be impossible
checks. An empty collectible field (the dump couldn't tell) counts as collectible.

Genes already in apworld/voidling_bound/data/genes.json keep their ID and location name, new genes get the next
free IDs. IDs are part of the network protocol, so genes are never removed or renumbered here: a gene that is
missing from the dump (e.g. a demo dump after a full game dump) stays in the list.
"""
import json
import sys
from pathlib import Path

GENES_JSON = Path(__file__).parent.parent / "apworld" / "voidling_bound" / "data" / "genes.json"
FIRST_ID = 845001

# Gene class -> type, the folder in the asset path is the fallback.
CLASS_TYPES = {
    "ColorGeneDataAsset": "Color", "EyeGeneDataAsset": "Eye", "PatternGeneDataAsset": "Pattern",
    "SizeGeneDataAsset": "Size", "ElementGeneDataAsset": "Element", "PerkGeneDataAsset": "Perk",
    "AbilityVariantGeneDataAsset": "Ability Variant", "CosmeticModuleDataAsset": "Module",
}
FOLDER_TYPES = {
    "colors": "Color", "color": "Color", "eyes": "Eye", "eye": "Eye", "patterns": "Pattern", "pattern": "Pattern",
    "sizes": "Size", "size": "Size", "elements": "Element", "element": "Element", "perks": "Perk", "perk": "Perk",
    "abilityvariants": "Ability Variant", "abilities": "Ability Variant", "modules": "Module",
}


def gene_type(path: str, gene_class: str) -> str:
    if gene_class in CLASS_TYPES:
        return CLASS_TYPES[gene_class]
    parts = path.split("/")
    if "Genes" in parts and parts.index("Genes") + 1 < len(parts):
        folder = parts[parts.index("Genes") + 1].lower().replace(" ", "")
        if folder in FOLDER_TYPES:
            return FOLDER_TYPES[folder]
    return "Other"


def parse_dump(text: str) -> list:
    genes = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 5:
            raise ValueError(f"Expected 5 tab separated fields: {line!r}")
        path, gene_class, gene_name, species_code, species_name = (field.strip() for field in fields[:5])
        if len(fields) > 5 and fields[5].strip().lower() == "false":
            continue
        asset = path.rsplit(".", 1)[-1]
        genes.append({
            "asset": asset,
            "path": path,
            "type": gene_type(path, gene_class),
            "gene_name": gene_name or asset,
            "species": species_name or species_code or "Unknown",
        })
    return genes


# Curly quotes, and the replacement character UE4SS leaves where the game's text had one.
TEXT_FIXES = {"�": "'", "’": "'", "‘": "'", "“": '"', "”": '"'}


def clean_text(text: str) -> str:
    for bad, good in TEXT_FIXES.items():
        text = text.replace(bad, good)
    return text


def location_name(gene: dict) -> str:
    return clean_text(f"{gene['species']} {gene['type']} Gene: {gene['gene_name']}")


def merge(existing: list, dumped: list) -> tuple:
    by_asset = {entry["asset"]: entry for entry in existing}
    used_names = {entry["name"] for entry in existing}
    next_id = max([entry["id"] for entry in existing], default=FIRST_ID - 1) + 1
    added = []
    for gene in sorted(dumped, key=lambda g: g["path"]):
        if gene["asset"] in by_asset:
            continue
        name = location_name(gene)
        if name in used_names:  # two genes with the same display name, e.g. variants of one color
            suffix = 2
            while f"{name} ({suffix})" in used_names:
                suffix += 1
            name = f"{name} ({suffix})"
        entry = {"id": next_id, "name": name, "species": gene["species"], "type": gene["type"],
                 "asset": gene["asset"], "path": gene["path"]}
        next_id += 1
        used_names.add(name)
        by_asset[gene["asset"]] = entry
        added.append(entry)
    return sorted(by_asset.values(), key=lambda e: e["id"]), added


def main(dump_path: str, genes_json: Path = GENES_JSON) -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # gene names aren't all ASCII, the Windows console is
    dumped = parse_dump(Path(dump_path).read_text(encoding="utf-8"))
    existing = json.loads(genes_json.read_text(encoding="utf-8")) if genes_json.exists() else []
    merged, added = merge(existing, dumped)
    genes_json.write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(dumped)} genes in the dump, {len(added)} new, {len(merged)} in {genes_json}")
    for entry in added:
        print(f"  {entry['id']}  {entry['name']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
