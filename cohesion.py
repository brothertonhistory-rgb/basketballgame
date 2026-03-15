import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Cohesion System v1.0
# System 4 of the Design Bible
#
# Cohesion measures two things that are related but distinct:
#
#   LAYER 1 -- ROSTER CONTINUITY SCORE (0-100)
#     How much of last year's minute production is returning.
#     A team returning 85% of its minutes has built-in familiarity.
#     A team with 7 new freshmen starts from scratch.
#     This feeds directly into the game engine as a team modifier.
#
#   LAYER 2 -- VETERAN COMBO BONDS
#     Specific partnerships between players who have logged
#     substantial minutes together over multiple seasons.
#     These are worth more than general cohesion because the
#     two players have developed specific reads and habits together.
#
#     QUALIFYING REQUIREMENTS:
#       Both players average 20+ minutes per game
#       Both have been on the roster together 2+ seasons
#       They form a recognized combo type
#
#     COMBO TYPES:
#       backcourt_duo    -- two guards (PG/SG)
#       post_duo         -- two bigs (PF/C)
#       big_small        -- one big + one perimeter player
#       starting_unit    -- all five starters together (rare, powerful)
#
#     BOND STRENGTH (0-100):
#       Year 2 together: 35-45  (foundation building)
#       Year 3 together: 60-75  (genuine partnership)
#       Year 4 together: 80-95  (senior leadership, peak cohesion)
#
# GAME ENGINE EFFECTS:
#   Continuity score feeds:
#     - Turnover rate modifier
#     - Shot selection quality modifier
#     - Late-game composure modifier
#
#   Combo bonds add on top:
#     backcourt_duo:  turnover reduction, defensive switching
#     post_duo:       rebounding bonus, help defense
#     big_small:      ball movement quality, two-man game
#     starting_unit:  all of the above at reduced strength
#                     + late-game composure bonus
#
# COACHING CHANGE SURVIVAL:
#   When a coaching change happens (future feature), call
#   apply_coaching_change_penalty() to reduce bonds.
#   Bonds survive at 60% -- players still know each other,
#   they just have to relearn the system reads.
#
# SEASON FLOW:
#   1. allocate_minutes() in roster_minutes.py -- called at season start
#   2. update_cohesion() -- called after lifecycle (roster turnover)
#   3. get_cohesion_modifiers() -- called by game_engine.py each game
# -----------------------------------------


# Minutes threshold for combo bond qualification
COMBO_MINUTES_THRESHOLD = 20.0

# Seasons together threshold for combo bond qualification
COMBO_SEASONS_THRESHOLD = 2

# Coaching change survival rate
COACHING_CHANGE_SURVIVAL = 0.60

# Combo type definitions -- positional requirements
COMBO_DEFINITIONS = {
    "backcourt_duo":  {"positions": [{"PG", "SG"}, {"PG", "SG"}],     "min_players": 2},
    "post_duo":       {"positions": [{"PF", "C"},  {"PF", "C"}],       "min_players": 2},
    "big_small":      {"positions": [{"PG","SG","SF"}, {"PF","C"}],    "min_players": 2},
    "starting_unit":  {"positions": None,                               "min_players": 5},
}

# Game engine modifier ranges by cohesion level
# These are the bounds -- actual value scales with cohesion score
COHESION_MODIFIERS = {
    # continuity_score -> modifier range
    "turnover_rate_mod":    {"very_high": -0.03, "high": -0.015, "low": +0.02, "very_low": +0.04},
    "shot_quality_mod":     {"very_high": +0.02, "high": +0.01,  "low": -0.01, "very_low": -0.02},
    "late_game_comp_mod":   {"very_high": +0.08, "high": +0.04,  "low": -0.03, "very_low": -0.06},
}

# Combo bond game engine bonuses (added on top of continuity modifiers)
COMBO_BOND_BONUSES = {
    "backcourt_duo": {
        "turnover_rate_mod": -0.01,
        "defensive_switch_mod": +0.05,
    },
    "post_duo": {
        "rebounding_mod": +0.03,
        "help_defense_mod": +0.02,
    },
    "big_small": {
        "shot_quality_mod": +0.01,
        "ball_movement_mod": +0.03,
    },
    "starting_unit": {
        "turnover_rate_mod": -0.01,
        "rebounding_mod": +0.01,
        "late_game_comp_mod": +0.04,
    },
}


# -----------------------------------------
# MAIN COHESION UPDATE
# Called after roster turnover each season
# -----------------------------------------

def update_cohesion(program, previous_minutes=None):
    """
    Updates both cohesion layers after roster turnover.

    program          -- full program dict (post-lifecycle)
    previous_minutes -- dict of {player_name: avg_minutes} from LAST season.
                        Used to calculate continuity score.
                        None on first season -- cohesion starts at baseline.

    Stores on program:
      program["cohesion_score"]  -- 0-100
      program["combo_bonds"]     -- list of active bond dicts
      program["cohesion_tier"]   -- "very_high"/"high"/"average"/"low"/"very_low"
    """

    # --- LAYER 1: ROSTER CONTINUITY SCORE ---
    continuity = _calculate_continuity(program, previous_minutes)

    # --- LAYER 2: VETERAN COMBO BONDS ---
    bonds = _find_combo_bonds(program)

    # Store on program
    program["cohesion_score"] = continuity
    program["combo_bonds"]    = bonds
    program["cohesion_tier"]  = _score_to_tier(continuity)

    return program


def _calculate_continuity(program, previous_minutes):
    """
    Calculates roster continuity score (0-100).

    Formula:
      For each returning player, check if they were in the previous
      rotation (20+ min). Their returning minutes as a fraction of
      total previous minutes = continuity fraction.

      continuity_score = continuity_fraction * 100, adjusted for
      roster size and system continuity.

    First season: no previous minutes, returns baseline 50.
    """
    if not previous_minutes:
        return 50   # baseline -- no history yet

    current_roster  = program.get("roster", [])
    current_names   = {p["name"] for p in current_roster}
    current_minutes = program.get("minutes_allocation", {})

    # Total minutes from last season (only 20+ min players matter)
    prev_rotation_minutes = {
        name: mins for name, mins in previous_minutes.items()
        if mins >= COMBO_MINUTES_THRESHOLD
    }
    total_prev_minutes = sum(prev_rotation_minutes.values())

    if total_prev_minutes == 0:
        return 50

    # How many of last year's rotation minutes are returning
    returning_minutes = sum(
        mins for name, mins in prev_rotation_minutes.items()
        if name in current_names
    )

    continuity_fraction = returning_minutes / total_prev_minutes
    continuity_score    = round(continuity_fraction * 100)

    # Clamp and return
    return max(0, min(100, continuity_score))


def _find_combo_bonds(program):
    """
    Scans the roster for qualifying veteran combo bonds.

    Requirements:
      - Both players average 20+ minutes (from minutes_allocation)
      - Both have been on the roster 2+ seasons (years_on_roster field)
        If years_on_roster not tracked yet, uses year class as proxy:
        Sophomore = 1 season, Junior = 2, Senior = 3+
      - Positional combo type matches

    Returns list of bond dicts:
      {
        "type":     combo type string,
        "players":  [name1, name2] or [n1,n2,n3,n4,n5] for unit,
        "strength": 0-100,
        "seasons":  seasons together,
      }
    """
    roster     = program.get("roster", [])
    allocation = program.get("minutes_allocation", {})

    # Filter to qualifying players: 20+ minutes, 2+ seasons
    qualified = []
    for player in roster:
        mins    = allocation.get(player["name"], 0)
        seasons = _estimate_seasons_together(player)
        if mins >= COMBO_MINUTES_THRESHOLD and seasons >= COMBO_SEASONS_THRESHOLD:
            qualified.append(player)

    bonds = []

    # Check backcourt duos
    guards = [p for p in qualified if p.get("position") in ("PG", "SG")]
    bonds.extend(_find_pair_bonds(guards, "backcourt_duo", allocation))

    # Check post duos
    bigs = [p for p in qualified if p.get("position") in ("PF", "C")]
    bonds.extend(_find_pair_bonds(bigs, "post_duo", allocation))

    # Check big/small combos
    perimeter = [p for p in qualified if p.get("position") in ("PG", "SG", "SF")]
    interior  = [p for p in qualified if p.get("position") in ("PF", "C")]
    bonds.extend(_find_bigsmall_bonds(perimeter, interior, allocation))

    # Check starting unit (all five starters with 2+ seasons together)
    starters = [p for p in qualified
                if allocation.get(p["name"], 0) >= 28]   # 28+ min = starter
    if len(starters) >= 5:
        unit_bond = _find_unit_bond(starters[:5], allocation)
        if unit_bond:
            bonds.append(unit_bond)

    return bonds


def _find_pair_bonds(players, combo_type, allocation):
    """Finds all qualifying pairs within a positional group."""
    bonds = []
    n = len(players)
    for i in range(n):
        for j in range(i + 1, n):
            p1 = players[i]
            p2 = players[j]
            seasons  = min(
                _estimate_seasons_together(p1),
                _estimate_seasons_together(p2)
            )
            if seasons < COMBO_SEASONS_THRESHOLD:
                continue
            strength = _calculate_bond_strength(
                seasons,
                allocation.get(p1["name"], 0),
                allocation.get(p2["name"], 0)
            )
            bonds.append({
                "type":     combo_type,
                "players":  [p1["name"], p2["name"]],
                "strength": strength,
                "seasons":  seasons,
            })
    return bonds


def _find_bigsmall_bonds(perimeter, interior, allocation):
    """Finds qualifying big/small combo bonds."""
    bonds = []
    for small in perimeter:
        for big in interior:
            seasons = min(
                _estimate_seasons_together(small),
                _estimate_seasons_together(big)
            )
            if seasons < COMBO_SEASONS_THRESHOLD:
                continue
            strength = _calculate_bond_strength(
                seasons,
                allocation.get(small["name"], 0),
                allocation.get(big["name"], 0)
            )
            bonds.append({
                "type":     "big_small",
                "players":  [small["name"], big["name"]],
                "strength": strength,
                "seasons":  seasons,
            })
    return bonds


def _find_unit_bond(starters, allocation):
    """Checks if all five starters qualify for a starting unit bond."""
    if len(starters) < 5:
        return None
    min_seasons = min(_estimate_seasons_together(p) for p in starters[:5])
    if min_seasons < COMBO_SEASONS_THRESHOLD:
        return None
    avg_minutes = sum(allocation.get(p["name"], 0) for p in starters[:5]) / 5
    strength    = _calculate_bond_strength(min_seasons, avg_minutes, avg_minutes)
    return {
        "type":     "starting_unit",
        "players":  [p["name"] for p in starters[:5]],
        "strength": strength,
        "seasons":  min_seasons,
    }


def _estimate_seasons_together(player):
    """
    Estimates how many seasons a player has been on the roster.
    Uses year class as proxy until years_on_roster is explicitly tracked.
    Freshman = 0 (just arrived), Sophomore = 1, Junior = 2, Senior = 3
    """
    year_map = {"Freshman": 0, "Sophomore": 1, "Junior": 2, "Senior": 3}
    return year_map.get(player.get("year", "Freshman"), 0)


def _calculate_bond_strength(seasons, minutes1, minutes2):
    """
    Calculates bond strength (0-100) based on seasons together
    and average minutes played.

    Seasons together is the primary driver:
      2 seasons: base 35-45
      3 seasons: base 60-75
      4 seasons: base 80-95

    Minutes shared adds a small bonus -- heavier usage = stronger bond.
    """
    # Base strength by seasons
    if seasons >= 4:
        base = random.randint(80, 95)
    elif seasons >= 3:
        base = random.randint(60, 75)
    else:
        base = random.randint(35, 45)

    # Minutes bonus -- heavier usage players build bonds faster
    avg_minutes = (minutes1 + minutes2) / 2
    if avg_minutes >= 32:
        base = min(100, base + 5)
    elif avg_minutes >= 25:
        base = min(100, base + 3)

    return base


def _score_to_tier(score):
    """Converts 0-100 cohesion score to tier label."""
    if score >= 80: return "very_high"
    if score >= 60: return "high"
    if score >= 40: return "average"
    if score >= 20: return "low"
    return "very_low"


# -----------------------------------------
# GAME ENGINE INTERFACE
# -----------------------------------------

def get_cohesion_modifiers(program):
    """
    Returns all cohesion modifiers for this program's current game.
    Called by game_engine.py for each game.

    Returns a dict of modifier keys and values:
      turnover_rate_mod     -- additive to base turnover rate
      shot_quality_mod      -- additive to base shot quality
      late_game_comp_mod    -- multiplier on late-game composure
      rebounding_mod        -- additive to rebounding chance
      help_defense_mod      -- additive to help defense
      defensive_switch_mod  -- not yet used by engine, hook for future
      ball_movement_mod     -- not yet used by engine, hook for future
    """
    cohesion_score = program.get("cohesion_score", 50)
    tier           = program.get("cohesion_tier", "average")
    combo_bonds    = program.get("combo_bonds", [])

    # Base modifiers from continuity score
    mods = {
        "turnover_rate_mod":    _get_base_modifier("turnover_rate_mod",   tier),
        "shot_quality_mod":     _get_base_modifier("shot_quality_mod",    tier),
        "late_game_comp_mod":   _get_base_modifier("late_game_comp_mod",  tier),
        "rebounding_mod":       0.0,
        "help_defense_mod":     0.0,
        "defensive_switch_mod": 0.0,
        "ball_movement_mod":    0.0,
    }

    # Add combo bond bonuses -- scaled by bond strength
    for bond in combo_bonds:
        bond_type  = bond.get("type", "")
        strength   = bond.get("strength", 50) / 100.0   # 0.0-1.0
        bonuses    = COMBO_BOND_BONUSES.get(bond_type, {})

        for key, value in bonuses.items():
            if key in mods:
                mods[key] += value * strength

    return mods


def _get_base_modifier(mod_key, tier):
    """Returns the base modifier value for a cohesion tier."""
    tier_values = COHESION_MODIFIERS.get(mod_key, {})
    if tier == "very_high":
        return tier_values.get("very_high", 0.0)
    elif tier == "high":
        return tier_values.get("high", 0.0)
    elif tier == "low":
        return tier_values.get("low", 0.0)
    elif tier == "very_low":
        return tier_values.get("very_low", 0.0)
    return 0.0   # average = no modifier


# -----------------------------------------
# COACHING CHANGE HANDLER
# -----------------------------------------

def apply_coaching_change_penalty(program):
    """
    Called when a coaching change occurs (future feature).
    Reduces all combo bond strengths by COACHING_CHANGE_SURVIVAL rate.
    Continuity score drops significantly -- system is new even if
    players aren't.

    Players still know each other physically, but they're relearning
    reads, habits, and system-specific chemistry.
    """
    bonds = program.get("combo_bonds", [])
    for bond in bonds:
        bond["strength"] = round(bond["strength"] * COACHING_CHANGE_SURVIVAL)

    # Continuity score also takes a hit from the system change
    current = program.get("cohesion_score", 50)
    program["cohesion_score"] = max(20, round(current * 0.70))
    program["cohesion_tier"]  = _score_to_tier(program["cohesion_score"])

    return program


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_cohesion_report(program):
    """Prints a readable cohesion report for a program."""
    name   = program.get("name", "Unknown")
    score  = program.get("cohesion_score", 50)
    tier   = program.get("cohesion_tier", "average")
    bonds  = program.get("combo_bonds", [])
    mods   = get_cohesion_modifiers(program)

    print("")
    print("=== " + name + " -- Cohesion Report ===")
    print("  Continuity score: " + str(score) + "/100  (" + tier + ")")
    print("  Active combo bonds: " + str(len(bonds)))

    if bonds:
        print("")
        print("  Veteran partnerships:")
        for bond in bonds:
            players_str = " + ".join(bond["players"])
            print("    " + bond["type"].replace("_", " ").ljust(18) +
                  "  strength: " + str(bond["strength"]) + "/100" +
                  "  (" + str(bond["seasons"]) + " seasons)" +
                  "  " + players_str[:50])

    print("")
    print("  Game engine modifiers:")
    for key, val in mods.items():
        if val != 0.0:
            sign = "+" if val > 0 else ""
            print("    " + key.ljust(25) + sign + str(round(val, 4)))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from roster_minutes import allocate_minutes

    print("Loading programs and allocating minutes...")
    all_programs = build_all_d1_programs()
    for program in all_programs:
        allocate_minutes(program)

    print("Running cohesion update for all programs...")
    # First season -- no previous minutes, baseline cohesion
    for program in all_programs:
        update_cohesion(program, previous_minutes=None)

    print("Done.")
    print("")

    # Show cohesion for a sample of programs
    test_programs = ["Kentucky", "Gonzaga", "Drake", "Wagner"]
    for name in test_programs:
        prog = next((p for p in all_programs if p["name"] == name), None)
        if prog:
            print_cohesion_report(prog)

    print("")
    print("=" * 65)
    print("  COHESION DISTRIBUTION -- all 326 programs")
    print("=" * 65)
    tier_counts = {"very_high": 0, "high": 0, "average": 0,
                   "low": 0, "very_low": 0}
    for p in all_programs:
        tier = p.get("cohesion_tier", "average")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    for tier, count in tier_counts.items():
        bar = "█" * count
        print("  " + tier.ljust(12) + str(count).rjust(4) + "  " + bar[:50])

    print("")
    print("  Note: All programs start at baseline 50 (average).")
    print("  Cohesion diverges after season 1 when returning minutes are known.")

    print("")
    print("=" * 65)
    print("  SIMULATING COHESION AFTER 3 SEASONS")
    print("  Showing how continuity builds over time")
    print("=" * 65)

    # Simulate 3 years of roster turnover to show cohesion evolution
    from player import create_player
    import copy

    # Build a test program with a stable roster
    test_prog = next(p for p in all_programs if p["name"] == "Kentucky")

    for year_num in range(1, 4):
        prev_minutes = copy.copy(test_prog.get("minutes_allocation", {}))
        allocate_minutes(test_prog)
        update_cohesion(test_prog, previous_minutes=prev_minutes)

        score = test_prog.get("cohesion_score", 50)
        tier  = test_prog.get("cohesion_tier", "average")
        bonds = test_prog.get("combo_bonds", [])
        print("  After year " + str(year_num) + ": " +
              "cohesion " + str(score) + " (" + tier + ")" +
              "  combo bonds: " + str(len(bonds)))
