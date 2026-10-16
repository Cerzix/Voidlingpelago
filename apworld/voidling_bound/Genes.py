# worlds/voidling_bound/Genes.py
# Every gene the player unlocks is a location. The gene list comes from the game: the mod's F5 gene dump
# writes genes.txt, and tools/import_genes.py turns it into data/genes.json with stable IDs.
import json
import pkgutil
from typing import Dict, List, NamedTuple

# Region names, same as in Locations.py (which imports this module, so they can't be imported from there).
VIREO, SOLUM, AULIS = "Vireo", "Solum", "Aulis"


class Gene(NamedTuple):
    code: int
    name: str  # location name, e.g. "Kwipeck Eye Gene: Starry"
    species: str
    type: str
    asset: str  # the game's asset name, e.g. "DA_Gene_Eye_RL01_00", how the mod reports it


# Size and Element genes exist, but the game marks all of them as not collectible, so they never become locations.
GENE_TYPES = ["Color", "Eye", "Pattern", "Perk", "Ability Variant", "Module", "Size", "Element"]

# The first planet whose missions reward eggs of the species (Voidling Bound wiki, mission rewards).
# Genes are unlocked by hatching, so a species' genes are in logic once its eggs can drop.
# Species that aren't listed go to Aulis, which is always safe. That includes Packuran (LB01), the ninth species,
# which the wiki doesn't name.
SPECIES_REGIONS: Dict[str, str] = {
    "Kwipeck": VIREO, "Kerapin": VIREO, "Gilick": VIREO, "Gwigoon": VIREO,
    "Nimiod": SOLUM, "Anami": SOLUM, "Ur-Sek": SOLUM,
    "Morfang": AULIS,
}


def gene_region(gene: Gene) -> str:
    return SPECIES_REGIONS.get(gene.species, AULIS)


def load_genes() -> List[Gene]:
    raw = pkgutil.get_data(__package__, "data/genes.json")
    if not raw:
        return []
    return [Gene(entry["id"], entry["name"], entry["species"], entry["type"], entry["asset"])
            for entry in json.loads(raw.decode("utf-8"))]


GENES: List[Gene] = load_genes()
GENES_BY_NAME: Dict[str, Gene] = {gene.name: gene for gene in GENES}
GENES_BY_ASSET: Dict[str, Gene] = {gene.asset: gene for gene in GENES}
