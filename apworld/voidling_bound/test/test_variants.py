from unittest.mock import patch

from BaseClasses import LocationProgressType
from Fill import distribute_items_restrictive

from . import VoidlingBoundTestBase
from .. import Locations, Variants, VoidlingBoundWorld
from ..Genes import SPECIES_REGIONS
from ..Variants import Variant

# The real variant list comes from the game (data/variants.json), so these tests use their own.
TEST_VARIANTS = [
    Variant(847001, "Variant: Kwipeck", "Kwipeck", "DA_Evolution_PK01_Base"),
    Variant(847002, "Variant: Qwebek Kwipeck", "Kwipeck", "DA_Evolution_PK01_Qwebek"),
    Variant(847003, "Variant: Ember Morfang", "Morfang", "DA_Evolution_UB01_Ember"),
]


class VariantTestBase(VoidlingBoundTestBase):
    def setUp(self) -> None:
        table = {variant.name: Locations.LocationData(variant.code, SPECIES_REGIONS.get(variant.species, Locations.AULIS))
                 for variant in TEST_VARIANTS}
        for patcher in (
            patch.object(Locations, "VARIANTS", TEST_VARIANTS),
            patch.dict(Locations.location_table, table),
            patch.dict(VoidlingBoundWorld.location_name_to_id, {v.name: v.code for v in TEST_VARIANTS}),
            patch.dict(Variants.VARIANTS_BY_NAME, {variant.name: variant for variant in TEST_VARIANTS}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        super().setUp()

    def variant_locations(self) -> dict:
        return {loc.name: loc for loc in self.multiworld.get_locations(self.player)
                if loc.name in Variants.VARIANTS_BY_NAME}


class TestVariantsByDefault(VariantTestBase):
    def test_variants_are_on_by_default(self) -> None:
        self.assertEqual(set(self.variant_locations()), {variant.name for variant in TEST_VARIANTS})

    def test_variants_follow_their_species_planet(self) -> None:
        self.assertTrue(self.can_reach_location("Variant: Qwebek Kwipeck"))
        self.assertFalse(self.can_reach_location("Variant: Ember Morfang"))
        self.collect_by_name(["Planet Access: Solum", "Planet Access: Aulis"])
        self.assertTrue(self.can_reach_location("Variant: Ember Morfang"))

    def test_variants_only_hold_filler(self) -> None:
        distribute_items_restrictive(self.multiworld)
        for location in self.variant_locations().values():
            self.assertEqual(location.progress_type, LocationProgressType.EXCLUDED, location.name)
            self.assertFalse(location.item.advancement or location.item.useful, f"{location.name}: {location.item}")


class TestVariantsOff(VariantTestBase):
    options = {"collection_checks": "off"}

    def test_no_variant_locations(self) -> None:
        self.assertEqual(self.variant_locations(), {})


class TestGenesOnlyHasNoVariants(VariantTestBase):
    options = {"collection_checks": "genes"}

    def test_no_variant_locations(self) -> None:
        self.assertEqual(self.variant_locations(), {})


class TestBothCollections(VariantTestBase):
    options = {"collection_checks": "both"}

    def test_variants_and_genes(self) -> None:
        from ..Genes import GENES
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertEqual(set(self.variant_locations()), {variant.name for variant in TEST_VARIANTS})
        self.assertTrue(all(gene.name in names for gene in GENES))
