# worlds/voidling_bound/Variants.py
# Every Voidling variant the player unlocks is a location. Variants are the game's evolutions (UEvolutionDataAsset,
# about 30 per species), which the game unlocks like genes when a variant is hatched or evolved. The list comes
# from the game: the developer tools' F5 dump writes variants.txt, and tools/import_variants.py turns it into
# data/variants.json with stable IDs.
import json
import pkgutil
from typing import Dict, List, NamedTuple


class Variant(NamedTuple):
    code: int
    name: str  # location name, e.g. "Variant: Qwebek Kwipeck"
    species: str
    asset: str  # the game's asset name, e.g. "DA_Evolution_RL01_Base", how the mod reports it


def load_variants() -> List[Variant]:
    raw = pkgutil.get_data(__package__, "data/variants.json")
    if not raw:
        return []
    return [Variant(entry["id"], entry["name"], entry["species"], entry["asset"])
            for entry in json.loads(raw.decode("utf-8"))]


VARIANTS: List[Variant] = load_variants()
VARIANTS_BY_NAME: Dict[str, Variant] = {variant.name: variant for variant in VARIANTS}
VARIANTS_BY_ASSET: Dict[str, Variant] = {variant.asset: variant for variant in VARIANTS}
