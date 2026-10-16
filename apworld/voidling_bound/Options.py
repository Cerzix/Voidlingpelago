# worlds/voidling_bound/Options.py
from dataclasses import dataclass

from Options import Choice, DeathLink, OptionSet, PerGameCommonOptions, Range, Toggle


class Goal(Choice):
    """
    What you need to do to finish your game.
    Campaign: beat the final campaign mission, End to the Unknown.
    Abyss Depth: reach the configured depth in the Abyss (requires Abyss Access).
    """
    display_name = "Goal"
    option_campaign = 0
    option_abyss_depth = 1
    default = 0


class AbyssGoalDepth(Range):
    """Abyss depth you have to reach when the goal is Abyss Depth. Also caps how many Abyss depth checks exist."""
    display_name = "Abyss Goal Depth"
    range_start = 5
    range_end = 50
    default = 20


class AbyssCheckInterval(Range):
    """Every this many Abyss depths, reaching a new record depth sends a check."""
    display_name = "Abyss Check Interval"
    range_start = 1
    range_end = 10
    default = 5


class BonusObjectives(Toggle):
    """Adds a check per mission for collecting all golden eggs, and another for collecting all bonus mutagens."""
    display_name = "Bonus Objectives"
    default = 1


class WranglerRankChecks(Range):
    """Number of Wrangler rank-ups that send a check (rank 2 up to rank N+1). 0 disables them."""
    display_name = "Wrangler Rank Checks"
    range_start = 0
    range_end = 20
    default = 10


class GeneChecks(Toggle):
    """
    Every gene you unlock (by hatching, breeding or evolving) sends a check. That adds up to 1,042 checks.
    Gene checks only ever hold filler, never progression or useful items: many genes come from random hatches,
    so a hard-to-get gene never blocks or holds back anyone's game.
    """
    display_name = "Gene Checks"
    default = 0


class GeneTypes(OptionSet):
    """
    Which kinds of genes send checks when Gene Checks is on. Modules are the cosmetic body parts (rare, superior,
    exotic and mutated). Size and Element genes can't be collected in the game, so they add no checks.
    """
    display_name = "Gene Types"
    valid_keys = {"Color", "Eye", "Pattern", "Perk", "Ability Variant", "Module", "Size", "Element"}
    default = frozenset(valid_keys)


@dataclass
class VoidlingBoundOptions(PerGameCommonOptions):
    goal: Goal
    abyss_goal_depth: AbyssGoalDepth
    abyss_check_interval: AbyssCheckInterval
    bonus_objectives: BonusObjectives
    wrangler_rank_checks: WranglerRankChecks
    gene_checks: GeneChecks
    gene_types: GeneTypes
    death_link: DeathLink
