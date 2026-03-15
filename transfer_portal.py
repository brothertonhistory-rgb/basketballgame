# -----------------------------------------
# COLLEGE HOOPS SIM -- Transfer Portal v1.0
#
# Phase 1: Entry filter only.
# Destination matching is STUBBED -- players who enter the portal
# are removed from their roster and exit the world.
# Phase 2 (destination matching) built separately after validation.
#
# PIPELINE POSITION:
#   After season ends and conference/NCAA tournaments resolve.
#   Before recruiting cycle runs.
#   Portal players leave before HS recruits arrive.
#
# ERA TOGGLE:
#   TRANSFER_RULES_ERA = "modern"
#     Players are immediately eligible at new school.
#   TRANSFER_RULES_ERA = "classic"
#     Players must sit out one year. Tracked via portal_sit_year on
#     the player dict. Game engine reads this to suppress their stats.
#
# ENTRY FILTER DESIGN:
#   Each player is evaluated against a set of triggers.
#   Each trigger fires independently -- no stacking.
#   A player enters the portal if ANY trigger fires.
#   This prevents compounding probabilities from making transfers
#   near-certain for players with multiple risk factors.
#
#   Triggers:
#     1. Minutes crash     -- dropped 30%+ from last season. Feeds playing_time_hunger.
#     2. Pure bench        -- never started, low minutes all year. Feeds playing_time_hunger.
#     3. Small fish        -- starter quality player at floor_conf program. Feeds prestige_ambition.
#     4. Top recruit stuck -- high-talent player at non-elite program. Feeds prestige_ambition.
#     5. Role player up    -- wants bigger stage, willing to accept bench. Feeds role_acceptance.
#     6. Pure volatility   -- leaves for no specific reason. Feeds volatility.
#
#   Freshmen get a patience discount -- they're less likely to bolt after
#   one season. Seniors never enter the portal (they're graduating).
#
# GEOGRAPHY:
#   State -> region lookup for destination scoring (Phase 2).
#   Distance tier between player home_state and any school:
#     same_state, same_region, adjacent_region, far
#   This file is the single source of truth for geography.
#
# PORTAL STATE ON PLAYER DICT:
#   portal_status:  "none" | "entered" | "committed" | "undrafted"
#   portal_year:    season year they entered the portal
#   portal_from:    program name they left
#   portal_sit_year: True/False (classic era only)
#   previous_school: program name (for cohesion penalty tracking)
# -----------------------------------------

import random
from player import ensure_player_personality

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

# Era toggle -- change this one constant to switch rule sets
# "modern"  = immediate eligibility
# "classic" = sit out one year
TRANSFER_RULES_ERA = "modern"

# Minimum minutes per game to qualify as a meaningful contributor
# Below this = bench player for portal trigger purposes
BENCH_MINUTES_THRESHOLD   = 12.0
STARTER_MINUTES_THRESHOLD = 28.0

# Minutes drop threshold for "minutes crash" trigger
# A player who loses this fraction of their minutes is at risk
MINUTES_CRASH_THRESHOLD = 0.30   # 30% drop

# Player quality threshold for "small fish" trigger
# Average primary attribute above this = starter-quality player
STARTER_QUALITY_THRESHOLD = 600

# True talent proxy: if a player's primary attributes average this or above
# at a non-elite program, they may be looking up
HIGH_TALENT_THRESHOLD = 650

# Prestige thresholds for trigger evaluation
ELITE_PROGRAM_THRESHOLD    = 79   # strong+ programs
FLOOR_CONF_MAX_PRESTIGE    = 25   # floor_conf programs roughly

# Freshman patience discount -- multiplied against trigger probability
# Freshmen are less likely to leave after just one season
FRESHMAN_PATIENCE = 0.40

# Sophomore patience discount
SOPHOMORE_PATIENCE = 0.70


# -----------------------------------------
# GEOGRAPHY
# -----------------------------------------

# State -> region mapping
# Used for destination scoring in Phase 2
STATE_REGIONS = {
    # Southeast
    "AL": "Southeast", "AR": "Southeast", "FL": "Southeast",
    "GA": "Southeast", "KY": "Southeast", "LA": "Southeast",
    "MS": "Southeast", "SC": "Southeast", "TN": "Southeast",
    "NC": "Southeast", "VA": "Southeast",
    # Midwest
    "IL": "Midwest", "IN": "Midwest", "IA": "Midwest",
    "KS": "Midwest", "MI": "Midwest", "MN": "Midwest",
    "MO": "Midwest", "NE": "Midwest", "ND": "Midwest",
    "OH": "Midwest", "SD": "Midwest", "WI": "Midwest",
    # Northeast
    "CT": "Northeast", "DC": "Northeast", "DE": "Northeast",
    "MA": "Northeast", "MD": "Northeast", "ME": "Northeast",
    "NH": "Northeast", "NJ": "Northeast", "NY": "Northeast",
    "PA": "Northeast", "RI": "Northeast", "VT": "Northeast",
    "WV": "Northeast",
    # Southwest
    "AZ": "Southwest", "CO": "Southwest", "NM": "Southwest",
    "OK": "Southwest", "TX": "Southwest", "UT": "Southwest",
    # West
    "AK": "West", "CA": "West", "HI": "West", "ID": "West",
    "MT": "West", "NV": "West", "OR": "West", "WA": "West",
    "WY": "West",
}

# Regions that border each other -- used for "adjacent_region" tier
ADJACENT_REGIONS = {
    "Southeast": {"Midwest", "Southwest", "Northeast"},
    "Midwest":   {"Southeast", "Southwest", "Northeast", "West"},
    "Northeast": {"Southeast", "Midwest"},
    "Southwest": {"Southeast", "Midwest", "West"},
    "West":      {"Midwest", "Southwest"},
}


def get_distance_tier(player_home_state, school_state):
    """
    Returns distance tier between a player's home state and a school's state.
    Used in Phase 2 destination scoring.

    Returns one of: "same_state", "same_region", "adjacent_region", "far"
    """
    if player_home_state == school_state:
        return "same_state"

    player_region = STATE_REGIONS.get(player_home_state)
    school_region = STATE_REGIONS.get(school_state)

    if player_region is None or school_region is None:
        return "far"

    if player_region == school_region:
        return "same_region"

    if school_region in ADJACENT_REGIONS.get(player_region, set()):
        return "adjacent_region"

    return "far"


# -----------------------------------------
# PLAYER QUALITY HELPERS
# -----------------------------------------

def _get_primary_quality(player):
    """
    Returns average primary attribute value for a player's position.
    Used to assess whether a player is starter quality.
    """
    from recruiting import POSITION_ARCHETYPES
    pos      = player.get("position", "SF")
    arch     = POSITION_ARCHETYPES.get(pos, {})
    primary  = arch.get("primary", [])
    if not primary:
        return 500
    return sum(player.get(a, 400) for a in primary) / len(primary)


def _get_last_season_minutes(player, program):
    """
    Returns the player's average minutes per game from the allocation system.
    Falls back to 0 if not found.
    """
    allocation = program.get("minutes_allocation", {})
    return allocation.get(player["name"], 0.0)


def _get_previous_minutes(player):
    """
    Returns minutes from the season before last, stored on the player dict.
    Set during portal processing each year so next year can compare.
    Returns None if no history.
    """
    return player.get("portal_prev_minutes", None)


# -----------------------------------------
# ENTRY TRIGGER EVALUATIONS
# -----------------------------------------

def _trigger_minutes_crash(player, current_minutes, prev_minutes, patience_mult):
    """
    Trigger 1: Minutes crash.
    Fired when a player loses 30%+ of their minutes vs last season.
    Probability scales with playing_time_hunger and size of the drop.
    """
    if prev_minutes is None or prev_minutes < BENCH_MINUTES_THRESHOLD:
        return False   # Was already a bench player -- different trigger handles this

    drop_fraction = (prev_minutes - current_minutes) / max(1, prev_minutes)
    if drop_fraction < MINUTES_CRASH_THRESHOLD:
        return False

    hunger      = player.get("playing_time_hunger", 10)
    drop_excess = max(0, drop_fraction - MINUTES_CRASH_THRESHOLD)

    # Base 20% at minimum drop, scales up with how much they lost
    base_prob = 0.20 + (drop_excess * 0.60)
    # Hunger multiplier: at max hunger (20) doubles it; at min (1) cuts to 10%
    hunger_mult = 0.10 + (hunger / 20.0) * 0.90

    prob = base_prob * hunger_mult * patience_mult
    return random.random() < prob


def _trigger_pure_bench(player, current_minutes, patience_mult):
    """
    Trigger 2: Pure bench.
    Fired for players averaging under BENCH_MINUTES_THRESHOLD all year.
    Scales heavily with playing_time_hunger.
    """
    if current_minutes >= BENCH_MINUTES_THRESHOLD:
        return False

    hunger = player.get("playing_time_hunger", 10)
    # High hunger benchwarmers are volatile -- low hunger guys accept their role
    base_prob   = 0.08 + ((current_minutes / BENCH_MINUTES_THRESHOLD) * -0.04)
    hunger_mult = 0.05 + (hunger / 20.0) * 0.70

    prob = base_prob * hunger_mult * patience_mult
    return random.random() < prob


def _trigger_small_fish(player, program, current_minutes, patience_mult):
    """
    Trigger 3: Small fish in a small pond.
    A starter-quality player at a floor_conf or low-prestige program
    who has the ambition to seek a bigger stage.
    Does NOT require role_acceptance -- this player wants to start somewhere better.
    """
    prestige = program.get("prestige_current", 50)
    if prestige >= ELITE_PROGRAM_THRESHOLD:
        return False   # Already at a quality program

    quality = _get_primary_quality(player)
    if quality < STARTER_QUALITY_THRESHOLD:
        return False   # Not good enough to attract interest

    if current_minutes < STARTER_MINUTES_THRESHOLD:
        return False   # Not even starting here

    ambition    = player.get("prestige_ambition", 10)
    quality_gap = max(0, quality - STARTER_QUALITY_THRESHOLD)
    prestige_gap = max(0, ELITE_PROGRAM_THRESHOLD - prestige)

    # The bigger the gap between their quality and their program's prestige,
    # and the higher their ambition, the more likely they leave
    quality_factor  = quality_gap / 300.0   # 0.0-1.0 range
    prestige_factor = prestige_gap / 60.0   # 0.0-1.0 range
    ambition_mult   = 0.10 + (ambition / 20.0) * 0.60

    base_prob = 0.10 + (quality_factor * prestige_factor * 0.30)
    prob      = base_prob * ambition_mult * patience_mult
    return random.random() < prob


def _trigger_top_recruit_stuck(player, program, patience_mult):
    """
    Trigger 4: High-talent recruit at a non-elite program.
    The 4-star who ended up at a mid-major because of the coach relationship,
    now realizes they may have undersold themselves.
    Interacts with prestige_ambition and inversely with role_acceptance
    (a player willing to be a role player at a big school is more likely to go).
    """
    quality = _get_primary_quality(player)
    if quality < HIGH_TALENT_THRESHOLD:
        return False

    prestige = program.get("prestige_current", 50)
    if prestige >= ELITE_PROGRAM_THRESHOLD:
        return False   # They're already at a good program

    year = player.get("year", "Freshman")
    # Only Sophomores and Juniors -- Freshmen need the patience discount,
    # Seniors are graduating
    if year not in ("Sophomore", "Junior"):
        return False

    ambition     = player.get("prestige_ambition", 10)
    role_accept  = player.get("role_acceptance", 10)

    # High ambition + high role acceptance = most likely to leave
    # (wants to go up AND willing to not start there)
    combined = (ambition / 20.0) * 0.60 + (role_accept / 20.0) * 0.40

    base_prob = 0.12
    prob      = base_prob * combined * patience_mult
    return random.random() < prob


def _trigger_role_player_up(player, program, current_minutes, patience_mult):
    """
    Trigger 5: Role player willing to move up.
    A bench/role player at a lower-prestige program who explicitly
    embraces being a role player at a higher-level school.
    High role_acceptance + high prestige_ambition + not a starter = this trigger.
    """
    if current_minutes >= STARTER_MINUTES_THRESHOLD:
        return False   # They're starting -- different triggers handle this

    prestige     = program.get("prestige_current", 50)
    if prestige >= ELITE_PROGRAM_THRESHOLD:
        return False   # Already at a quality program

    ambition    = player.get("prestige_ambition", 10)
    role_accept = player.get("role_acceptance", 10)

    # Both must be reasonably high for this to fire
    if ambition < 10 or role_accept < 10:
        return False

    combined  = ((ambition - 10) / 10.0) * ((role_accept - 10) / 10.0)
    base_prob = 0.08
    prob      = base_prob * combined * patience_mult
    return random.random() < prob


def _trigger_volatility(player, patience_mult):
    """
    Trigger 6: Pure volatility.
    The player who just... leaves. Homesickness, a bad interaction with a coach,
    a friend transferring and wanting to follow. No specific in-game reason.
    Low base rate but affected strongly by the volatility attribute.
    """
    vol = player.get("volatility", 5)
    # Base 2% chance at vol=10. At vol=20 it's ~6%. At vol=1 it's ~0.3%.
    base_prob = 0.002 + (vol / 20.0) * 0.04
    prob      = base_prob * patience_mult
    return random.random() < prob


# -----------------------------------------
# MAIN PORTAL ENTRY FILTER
# -----------------------------------------

def run_portal_entry_filter(all_programs, season_year, verbose=True):
    """
    Evaluates every rostered player for portal entry.
    Removes portal entrants from their program's roster.
    Stores portal_status = "entered" on each departing player.

    Returns:
        all_programs  -- modified in place, portal players removed from rosters
        portal_pool   -- list of player dicts who entered the portal
        portal_report -- summary dict for logging
    """
    portal_pool   = []
    portal_report = {
        "season_year":       season_year,
        "total_evaluated":   0,
        "total_entered":     0,
        "by_trigger":        {
            "minutes_crash":      0,
            "pure_bench":         0,
            "small_fish":         0,
            "top_recruit_stuck":  0,
            "role_player_up":     0,
            "volatility":         0,
        },
        "by_year": {
            "Freshman": 0, "Sophomore": 0, "Junior": 0, "Senior": 0,
        },
        "by_conf_tier": {},
        "program_losses": {},   # program_name -> count
    }

    for program in all_programs:
        roster          = program.get("roster", [])
        conf_name       = program.get("conference", "Unknown")
        program_name    = program.get("name", "Unknown")

        players_leaving = []

        for player in roster:
            year = player.get("year", "Freshman")

            # Seniors are graduating -- never portal
            if year == "Senior":
                continue

            # Ensure personality attributes exist (retroactive migration)
            ensure_player_personality(player)

            portal_report["total_evaluated"] += 1

            # Patience multiplier by year
            if year == "Freshman":
                patience_mult = FRESHMAN_PATIENCE
            elif year == "Sophomore":
                patience_mult = SOPHOMORE_PATIENCE
            else:
                patience_mult = 1.0

            current_minutes = _get_last_season_minutes(player, program)
            prev_minutes    = _get_previous_minutes(player)

            # Evaluate all triggers independently
            # Track which trigger fired first (for reporting)
            trigger_fired = None

            if _trigger_minutes_crash(player, current_minutes, prev_minutes, patience_mult):
                trigger_fired = "minutes_crash"
            elif _trigger_pure_bench(player, current_minutes, patience_mult):
                trigger_fired = "pure_bench"
            elif _trigger_small_fish(player, program, current_minutes, patience_mult):
                trigger_fired = "small_fish"
            elif _trigger_top_recruit_stuck(player, program, patience_mult):
                trigger_fired = "top_recruit_stuck"
            elif _trigger_role_player_up(player, program, current_minutes, patience_mult):
                trigger_fired = "role_player_up"
            elif _trigger_volatility(player, patience_mult):
                trigger_fired = "volatility"

            if trigger_fired:
                # Mark player as portal entrant
                player["portal_status"]   = "entered"
                player["portal_year"]     = season_year
                player["portal_from"]     = program_name
                player["portal_trigger"]  = trigger_fired
                player["previous_school"] = program_name

                # Classic era: mark sit-out year
                if TRANSFER_RULES_ERA == "classic":
                    player["portal_sit_year"] = True
                else:
                    player["portal_sit_year"] = False

                players_leaving.append(player)

                # Update report
                portal_report["total_entered"] += 1
                portal_report["by_trigger"][trigger_fired] += 1
                portal_report["by_year"][year] = portal_report["by_year"].get(year, 0) + 1
                portal_report["program_losses"][program_name] = \
                    portal_report["program_losses"].get(program_name, 0) + 1

        # Remove departing players from roster
        if players_leaving:
            leaving_names = set(p["name"] for p in players_leaving)
            program["roster"] = [p for p in roster if p["name"] not in leaving_names]
            portal_pool.extend(players_leaving)

        # Store current minutes as previous for next season's comparison
        # Done for ALL players, not just portal entrants
        for player in program.get("roster", []):
            current_min = _get_last_season_minutes(player, program)
            player["portal_prev_minutes"] = current_min

    if verbose:
        _print_portal_report(portal_report, portal_pool)

    return all_programs, portal_pool, portal_report


# -----------------------------------------
# STUB: DESTINATION MATCHING
# Phase 2 -- not yet built.
# Portal pool players currently exit the world (undrafted).
# -----------------------------------------

def run_portal_destination_matching(all_programs, portal_pool, season_year, verbose=True):
    """
    STUB -- Phase 2, not yet built.

    Eventually: programs post roster needs, players self-select destinations
    based on prestige fit, playing time probability, and home proximity.
    Players who don't find a match exit the world as "undrafted".

    For now: all portal players become undrafted and are discarded.
    Roster slots freed by their departure are available for recruiting.
    """
    undrafted_count = 0
    for player in portal_pool:
        player["portal_status"] = "undrafted"
        undrafted_count += 1

    if verbose and undrafted_count > 0:
        print("  [Portal] Destination matching not yet built -- " +
              str(undrafted_count) + " portal players exit the world (undrafted)")
        print("  [Portal] Their roster slots are available for recruiting.")

    return all_programs, portal_pool


# -----------------------------------------
# FULL PORTAL CYCLE
# Called by season.py
# -----------------------------------------

def run_transfer_portal(all_programs, season_year, verbose=True):
    """
    Runs the complete portal cycle for a season.
    Phase 1 (entry filter) is live.
    Phase 2 (destination matching) is stubbed.

    Returns:
        all_programs  -- with portal players removed from rosters
        portal_pool   -- list of player dicts who entered (for logging/future use)
        portal_report -- summary dict
    """
    if verbose:
        print("")
        print("--- " + str(season_year) + " Transfer Portal ---")
        print("  Rules era: " + TRANSFER_RULES_ERA)

    all_programs, portal_pool, portal_report = run_portal_entry_filter(
        all_programs, season_year, verbose=verbose
    )

    all_programs, portal_pool = run_portal_destination_matching(
        all_programs, portal_pool, season_year, verbose=verbose
    )

    return all_programs, portal_pool, portal_report


# -----------------------------------------
# REPORTING
# -----------------------------------------

def _print_portal_report(report, portal_pool):
    """Prints a readable portal entry summary."""
    print("  Evaluated: " + str(report["total_evaluated"]) +
          "  |  Entered: " + str(report["total_entered"]))

    if report["total_entered"] == 0:
        return

    entry_rate = round(report["total_entered"] / max(1, report["total_evaluated"]) * 100, 1)
    print("  Entry rate: " + str(entry_rate) + "%")

    print("")
    print("  By trigger:")
    for trigger, count in sorted(report["by_trigger"].items(),
                                  key=lambda x: x[1], reverse=True):
        if count > 0:
            print("    {:<22} {}".format(trigger, count))

    print("")
    print("  By year:")
    for year in ["Freshman", "Sophomore", "Junior"]:
        count = report["by_year"].get(year, 0)
        if count > 0:
            print("    {:<12} {}".format(year, count))

    # Top 5 programs by losses
    if report["program_losses"]:
        top_losers = sorted(report["program_losses"].items(),
                            key=lambda x: x[1], reverse=True)[:5]
        print("")
        print("  Programs with most departures:")
        for prog_name, count in top_losers:
            print("    {:<26} {} player(s)".format(prog_name, count))

    # Sample of notable portal entrants
    notable = sorted(portal_pool,
                     key=lambda p: _get_primary_quality(p),
                     reverse=True)[:8]
    if notable:
        print("")
        print("  Notable portal entrants:")
        for p in notable:
            quality = round(_get_primary_quality(p), 0)
            print("    {:<22} {:<5} {:<12} from: {:<26} trigger: {}  quality: {}".format(
                p["name"][:21], p.get("position", "?"), p.get("year", "?"),
                p.get("portal_from", "?")[:25],
                p.get("portal_trigger", "?"),
                int(quality)
            ))


def print_portal_summary(portal_report, season_year):
    """
    External summary printer for season.py to call.
    Lighter version of the full report.
    """
    print("")
    print("--- " + str(season_year) + " Transfer Portal Summary ---")
    print("  Players entered portal: " + str(portal_report["total_entered"]))
    print("  Rules era: " + TRANSFER_RULES_ERA)
    if portal_report["total_entered"] > 0:
        top_trigger = max(portal_report["by_trigger"].items(),
                          key=lambda x: x[1])
        print("  Top trigger: " + top_trigger[0] + " (" + str(top_trigger[1]) + ")")


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":
    from programs_data import build_all_d1_programs
    from roster_minutes import allocate_minutes

    print("Loading programs...")
    all_programs = build_all_d1_programs()

    print("Allocating minutes (needed for trigger evaluation)...")
    for program in all_programs:
        allocate_minutes(program)

    print("")
    print("=" * 60)
    print("  TRANSFER PORTAL v1.0 -- ENTRY FILTER TEST")
    print("  Era: " + TRANSFER_RULES_ERA)
    print("=" * 60)

    all_programs, portal_pool, portal_report = run_transfer_portal(
        all_programs, season_year=2024, verbose=True
    )

    print("")
    print("=== POST-PORTAL ROSTER INTEGRITY ===")
    thin = [p for p in all_programs if len(p.get("roster", [])) < 7]
    if thin:
        print("WARNING: " + str(len(thin)) + " programs with fewer than 7 players after portal:")
        for p in thin[:10]:
            print("  " + p["name"] + ": " + str(len(p["roster"])) + " players")
    else:
        print("PASS: All programs have 7+ players after portal exit.")

    print("")
    print("=== PERSONALITY DISTRIBUTION IN PORTAL POOL ===")
    if portal_pool:
        attrs = ["volatility", "playing_time_hunger", "home_loyalty",
                 "prestige_ambition", "role_acceptance"]
        print("  Portal entrant avg personality vs general population:")
        print("  {:<22} {:<12} {}".format("Attribute", "Portal avg", "Expected avg"))
        print("  " + "-" * 46)
        for a in attrs:
            portal_avg = round(sum(p.get(a, 10) for p in portal_pool) /
                               max(1, len(portal_pool)), 1)
            print("  {:<22} {:<12} ~7.5".format(a, portal_avg))
        print("")
        print("  (Portal players should score higher than average on")
        print("   playing_time_hunger, prestige_ambition, volatility)")
    else:
        print("  No portal entries this cycle.")
