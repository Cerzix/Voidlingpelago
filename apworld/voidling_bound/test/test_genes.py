from unittest.mock import patch

from BaseClasses import LocationProgressType
from Fill import distribute_items_restrictive

from . import VoidlingBoundTestBase
from .. import Genes, Locations, VoidlingBoundWorld
from ..Genes import Gene, gene_region

# The real gene list comes from the game (data/genes.json), so these tests use their own.
TEST_GENES = [
    Gene(845001, "Kwipeck Eye Gene: Starry", "Kwipeck", "Eye", "DA_Gene_Eye_RL01_00"),
    Gene(845002, "Kwipeck Perk Gene: Thick Skin", "Kwipeck", "Perk", "DA_Gene_Perk_RL01_01"),
    Gene(845003, "Morfang Color Gene: Ember", "Morfang", "Color", "DA_Gene_Color_RL08_00"),
    Gene(845004, "RL09 Size Gene: Huge", "RL09", "Size", "DA_Gene_Size_RL09_00"),
]


class GeneTestBase(VoidlingBoundTestBase):
    options = {"collection_checks": "genes"}

    def setUp(self) -> None:
        table = {gene.name: Locations.LocationData(gene.code, gene_region(gene)) for gene in TEST_GENES}
        for patcher in (
            patch.object(Locations, "GENES", TEST_GENES),
            patch.dict(Locations.location_table, table),
            patch.dict(VoidlingBoundWorld.location_name_to_id, {gene.name: gene.code for gene in TEST_GENES}),
            patch.dict(Genes.GENES_BY_NAME, {gene.name: gene for gene in TEST_GENES}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        super().setUp()

    def gene_locations(self) -> dict:
        return {loc.name: loc for loc in self.multiworld.get_locations(self.player) if loc.name in Genes.GENES_BY_NAME}


class TestGenesDefault(GeneTestBase):
    def test_every_gene_is_a_location(self) -> None:
        self.assertEqual(set(self.gene_locations()), {gene.name for gene in TEST_GENES})

    def test_genes_follow_their_species_planet(self) -> None:
        self.assertTrue(self.can_reach_location("Kwipeck Eye Gene: Starry"))
        self.assertFalse(self.can_reach_location("Morfang Color Gene: Ember"))
        self.assertFalse(self.can_reach_location("RL09 Size Gene: Huge"), "unknown species count as Aulis")
        self.collect_by_name(["Planet Access: Solum", "Planet Access: Aulis"])
        self.assertTrue(self.can_reach_location("Morfang Color Gene: Ember"))
        self.assertTrue(self.can_reach_location("RL09 Size Gene: Huge"))

    def test_genes_only_hold_filler(self) -> None:
        distribute_items_restrictive(self.multiworld)
        for location in self.gene_locations().values():
            self.assertEqual(location.progress_type, LocationProgressType.EXCLUDED, location.name)
            self.assertFalse(location.item.advancement or location.item.useful, f"{location.name}: {location.item}")


class TestGeneTypes(GeneTestBase):
    options = {"collection_checks": "genes", "gene_types": ["Eye", "Color"]}

    def test_only_selected_types(self) -> None:
        self.assertEqual(set(self.gene_locations()), {"Kwipeck Eye Gene: Starry", "Morfang Color Gene: Ember"})


class TestGenesOffByDefault(GeneTestBase):
    options = {}

    def test_no_gene_locations(self) -> None:
        self.assertEqual(self.gene_locations(), {})
