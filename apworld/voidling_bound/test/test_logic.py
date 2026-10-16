from . import VoidlingBoundTestBase


class TestCampaignGoal(VoidlingBoundTestBase):
    def test_sectors_are_gated(self) -> None:
        self.assertFalse(self.can_reach_location("W02: Crater Survival"))
        self.collect_by_name("Planet Access: Sector 2 (W02)")
        self.assertTrue(self.can_reach_location("W02: Crater Survival"))
        self.assertFalse(self.can_reach_location("W03: Oasis Survival"))

    def test_goal_needs_all_sectors(self) -> None:
        self.collect_by_name(["Planet Access: Sector 2 (W02)", "Planet Access: Sector 3 (W03)"])
        self.assertBeatable(False)
        self.collect_by_name("Planet Access: Sector 4 (W04)")
        self.assertBeatable(True)


class TestAbyssGoal(VoidlingBoundTestBase):
    options = {"goal": "abyss_depth", "abyss_goal_depth": 23, "abyss_check_interval": 5}

    def test_goal_needs_abyss_access(self) -> None:
        self.collect_by_name(["Planet Access: Sector 2 (W02)", "Planet Access: Sector 3 (W03)",
                              "Planet Access: Sector 4 (W04)"])
        self.assertBeatable(False)
        self.collect_by_name("Abyss Access")
        self.assertBeatable(True)

    def test_goal_depth_has_a_check(self) -> None:
        depths = [loc.name for loc in self.multiworld.get_locations(self.player) if loc.name.startswith("Abyss:")]
        self.assertEqual(sorted(depths, key=lambda n: int(n.split()[-1])),
                         [f"Abyss: Reach Depth {d}" for d in (5, 10, 15, 20, 23)])


class TestMinimalLocations(VoidlingBoundTestBase):
    options = {"bonus_objectives": False, "wrangler_rank_checks": 0, "abyss_goal_depth": 5,
               "abyss_check_interval": 10}
