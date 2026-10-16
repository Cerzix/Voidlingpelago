from . import VoidlingBoundTestBase
from ..Locations import MISSIONS


class TestCampaignGoal(VoidlingBoundTestBase):
    def test_planets_are_gated(self) -> None:
        self.assertTrue(self.can_reach_location("Centennial Bloom"))
        self.assertFalse(self.can_reach_location("Search and Rescue"))
        self.collect_by_name("Planet Access: Solum")
        self.assertTrue(self.can_reach_location("Search and Rescue"))
        self.assertFalse(self.can_reach_location("Storm Breaker"))

    def test_goal_needs_aulis(self) -> None:
        self.collect_by_name("Planet Access: Solum")
        self.assertBeatable(False)
        self.collect_by_name("Planet Access: Aulis")
        self.assertBeatable(True)

    def test_void_strike_needs_abyss_access(self) -> None:
        self.collect_by_name(["Planet Access: Solum", "Planet Access: Aulis"])
        self.assertFalse(self.can_reach_location("Operation: Void Strike"))
        self.collect_by_name("Abyss Access")
        self.assertTrue(self.can_reach_location("Operation: Void Strike"))


class TestAbyssGoal(VoidlingBoundTestBase):
    options = {"goal": "abyss_depth", "abyss_goal_depth": 23, "abyss_check_interval": 5}

    def test_goal_needs_abyss_access(self) -> None:
        self.collect_by_name(["Planet Access: Solum", "Planet Access: Aulis"])
        self.assertBeatable(False)
        self.collect_by_name("Abyss Access")
        self.assertBeatable(True)

    def test_goal_depth_has_a_check(self) -> None:
        depths = [loc.name for loc in self.multiworld.get_locations(self.player) if loc.name.startswith("Abyss:")]
        self.assertEqual(sorted(depths, key=lambda n: int(n.split()[-1])),
                         [f"Abyss: Reach Depth {d}" for d in (5, 10, 15, 20, 23)])


class TestBonusObjectives(VoidlingBoundTestBase):
    def test_only_missions_with_collectibles_have_bonus_checks(self) -> None:
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        for mission in MISSIONS:
            self.assertEqual(f"{mission.name} - All Golden Eggs" in names, mission.golden_eggs > 0, mission.name)
        self.assertEqual(sum(1 for name in names if name.endswith("All Golden Eggs")), 9)


class TestMinimalLocations(VoidlingBoundTestBase):
    options = {"bonus_objectives": False, "wrangler_rank_checks": 0, "abyss_goal_depth": 5,
               "abyss_check_interval": 10}


class TestAllGenes(VoidlingBoundTestBase):
    """The real gene list: over a thousand filler-only locations must still fill."""
    options = {"gene_checks": True}

    def test_every_collectible_gene_is_a_location(self) -> None:
        from ..Genes import GENES
        names = {loc.name for loc in self.multiworld.get_locations(self.player)}
        self.assertTrue(GENES)
        self.assertTrue(all(gene.name in names for gene in GENES))
