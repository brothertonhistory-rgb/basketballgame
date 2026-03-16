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
# DESTINATION MATCHING -- PHASE 2
#
# Four-phase matching engine:
#
#   Phase A: Player self-nomination
#     Each player builds a ranked target list based on:
#       - Prestige band (ambition sets ceiling, current prestige sets floor)
#       - Offensive role projection (role_acceptance sets how deep they'll slot)
#       - Personal fit score (home proximity, prestige fit, role quality)
#     Player approaches top 5 schools on their list.
#
#   Phase B: Program needs assessment
#     Each program identifies open scholarship slots and positional gaps.
#     Generates a ranked want list from the portal pool.
#
#   Phase C: Tiered matching
#     Round 1: Player approaches Dream school. Mutual match = commit.
#     Round 2: If a lower school offers, player sends hard yes/no up the list.
#       Best yes above the offer wins. If nobody above says yes, take the offer.
#
#   Phase D: Open pool sweep
#     Unmatched players and programs with open slots do a general round.
#     Looser filters, wider nets.
#
#   Phase E: Undrafted
#     Still unmatched after Phase D -- exit the world.
# -----------------------------------------

# How many schools a player proactively approaches in Phase A
PLAYER_APPROACH_COUNT = 5

# Scholarship cap -- hard 13
SCHOLARSHIP_CAP = 13

# Quality floor by prestige tier for program acceptance
# (base floor, senior_floor)
# Senior floor is lower -- one-year depth guys accepted more readily
PROGRAM_QUALITY_FLOORS = {
    "blue_blood":    (750, 550),   # 95+
    "elite":         (700, 500),   # 79-94
    "strong":        (620, 430),   # 59-78
    "average":       (530, 360),   # 39-58
    "below_average": (430, 280),   # 21-38
    "poor":          (300, 150),   # 1-20
}

# Prestige band a player targets based on their quality and ambition
# Player quality -> realistic prestige ceiling they can reach
def _quality_to_prestige_ceiling(quality, prestige_ambition):
    """
    Maps a player's primary quality score to the highest prestige program
    they realistically target. Ambition scales the ceiling upward.
    """
    # Base ceiling from quality alone
    if quality >= 850:   base = 100
    elif quality >= 750: base = 90
    elif quality >= 650: base = 78
    elif quality >= 580: base = 65
    elif quality >= 500: base = 52
    elif quality >= 420: base = 40
    else:                base = 28

    # Ambition bonus -- high ambition players shoot higher
    ambition_bonus = (prestige_ambition - 10) / 10.0 * 12
    return min(100, base + ambition_bonus)


def _quality_to_prestige_floor(quality, current_prestige):
    """
    Minimum prestige a player will consider.
    Ambitious players won't lateral or go down.
    """
    # Never go below current program prestige (no lateral moves)
    # unless current program is already at the bottom
    if current_prestige <= 15:
        return max(1, current_prestige - 5)
    return max(1, current_prestige)


# -----------------------------------------
# OFFENSIVE HIERARCHY
# -----------------------------------------

def _offensive_score(player):
    """
    Scores a player's offensive threat level.
    Position-aware: guards weight ball creation, bigs weight post dominance.
    Used to rank players within a roster and project where a transfer slots in.

    Returns a float on roughly the same scale as primary attributes (1-1000).
    """
    pos = player.get("position", "SF")

    scoring = (
        player.get("finishing",    400) * 1.0 +
        player.get("mid_range",    400) * 0.6 +
        player.get("three_point",  400) * 0.8 +
        player.get("post_scoring", 400) * 0.7 +
        player.get("free_throw",   400) * 0.3
    ) / 3.4   # normalize divisor = sum of weights

    if pos in ("PG", "SG"):
        # Guards: creation matters -- ball handling and court vision add usage weight
        usage = (
            player.get("ball_handling", 400) * 0.5 +
            player.get("court_vision",  400) * 0.3
        ) / 0.8
        return scoring * 0.65 + usage * 0.35

    elif pos == "SF":
        usage = player.get("ball_handling", 400) * 0.3
        return scoring * 0.75 + usage * 0.25

    else:  # PF, C
        # Bigs: post dominance + rebounding as usage proxy
        post_dom = (
            player.get("post_scoring", 400) * 0.6 +
            player.get("rebounding",   400) * 0.4
        )
        return scoring * 0.60 + post_dom * 0.40


def _projected_offensive_slot(player, program_roster):
    """
    Projects where a transfer would rank offensively on a target roster.
    Returns slot number: 1 = top option, 2 = second option, etc.
    Lower is better for a player who wants to be the guy.
    """
    if not program_roster:
        return 1

    transfer_score = _offensive_score(player)
    scores = sorted(
        [_offensive_score(p) for p in program_roster],
        reverse=True
    )

    slot = 1
    for s in scores:
        if transfer_score < s:
            slot += 1
        else:
            break

    return slot


# -----------------------------------------
# PROGRAM NEEDS ASSESSMENT
# -----------------------------------------

def _get_open_slots(program):
    """Returns number of open scholarship slots (max 13 - current roster)."""
    return max(0, SCHOLARSHIP_CAP - len(program.get("roster", [])))


def _get_positional_needs(program):
    """
    Returns a dict of positional need scores.
    Higher = more urgent need at that position.
    0 = position is full (3+ players)
    1 = light (2 players)
    2 = thin (1 player)
    3 = emergency (0 players)
    """
    roster = program.get("roster", [])
    pos_counts = {"PG": 0, "SG": 0, "SF": 0, "PF": 0, "C": 0}
    for p in roster:
        pos = p.get("position", "SF")
        if pos in pos_counts:
            pos_counts[pos] += 1

    needs = {}
    for pos, count in pos_counts.items():
        if count == 0:   needs[pos] = 3
        elif count == 1: needs[pos] = 2
        elif count == 2: needs[pos] = 1
        else:            needs[pos] = 0
    return needs


def _prestige_tier_label(prestige):
    """Maps prestige score to tier label for quality floor lookup."""
    if prestige >= 95:   return "blue_blood"
    elif prestige >= 79: return "elite"
    elif prestige >= 59: return "strong"
    elif prestige >= 39: return "average"
    elif prestige >= 21: return "below_average"
    else:                return "poor"


def _program_will_accept(program, player, open_slots, pos_needs,
                         enforce_ceiling=True):
    """
    Returns True if a program will accept this portal player.

    open_slots is the authoritative count -- never re-reads roster length.
    This is critical: roster dict is not updated during matching, only
    prog_open_slots is decremented. Always pass the tracked value.

    Conditions:
      1. Open scholarship slot exists (uses passed open_slots)
      2. Position fills a need (or at least isn't already packed)
      3. Player quality clears the prestige-relative floor
         -- Seniors get a lower floor (one-year depth value)
         -- Emergency positional need lowers floor further
      4. Player quality doesn't exceed prestige-relative ceiling
         -- A quality-900 player won't land at a prestige-15 program
         -- enforce_ceiling=False in open pool for relaxed matching
    """
    if open_slots <= 0:
        return False

    pos  = player.get("position", "SF")
    need = pos_needs.get(pos, 0)

    # If position is completely full (need=0), only accept if player is
    # significantly better than current weakest at that position
    if need == 0:
        roster = program.get("roster", [])
        pos_players = [p for p in roster if p.get("position") == pos]
        if pos_players:
            weakest = min(_offensive_score(p) for p in pos_players)
            transfer_score = _offensive_score(player)
            if transfer_score < weakest * 1.10:
                return False

    prestige   = program.get("prestige_current", 50)
    tier_label = _prestige_tier_label(prestige)
    base_floor, senior_floor = PROGRAM_QUALITY_FLOORS.get(
        tier_label, (500, 350)
    )

    year    = player.get("year", "Sophomore")
    quality = _get_primary_quality(player)

    floor = senior_floor if year == "Senior" else base_floor

    # Emergency need -- lower floor 15%
    if need == 3:
        floor = int(floor * 0.85)

    if quality < floor:
        return False

    # Quality ceiling -- programs won't take a player far above their level
    # A quality-900 player at a prestige-15 program is implausible.
    # Ceiling = base_floor * 2.2 gives reasonable headroom.
    # Only enforced in Phase C (not open pool Phase D which uses enforce_ceiling=False).
    if enforce_ceiling:
        ceiling = base_floor * 2.2
        if quality > ceiling:
            return False

    return True


# -----------------------------------------
# PLAYER TARGET LIST BUILDER
# -----------------------------------------

def _build_player_target_list(player, all_programs):
    """
    Builds a ranked list of target schools for a portal player.

    Filters by:
      1. Prestige band (ambition ceiling, current prestige floor)
      2. Offensive role projection (role_acceptance sets max slot)
      3. Not their current school

    Scores each eligible school:
      - Prestige fit (how close to their ceiling, not too far below)
      - Projected offensive slot (lower slot = better for low role_acceptance)
      - Home proximity (home_loyalty weight)
      - Slight noise (personal preference)

    VOLATILITY SCRAMBLE:
      High-volatility players don't always follow rational logic.
      A volatile player may throw a wild card school into their list --
      a low-major where they'd dominate, a school near home, anything.
      At max volatility, their entire rational list may be discarded.

      Low  (1-7):  pure rational list
      Mid  (8-13): 15% chance one wild card slot replaces a rational slot
      High (14-17): 35% wild card chance, 10% full random list
      Max  (18-20): 50% wild card chance, 25% full random list

    Returns top PLAYER_APPROACH_COUNT schools as ordered list.
    """
    ambition      = player.get("prestige_ambition", 10)
    role_accept   = player.get("role_acceptance", 10)
    home_loyalty  = player.get("home_loyalty", 10)
    home_state    = player.get("home_state", "TX")
    current_prog  = player.get("portal_from", "")
    volatility    = player.get("volatility", 5)
    quality       = _get_primary_quality(player)

    # Prestige band
    p_ceiling = _quality_to_prestige_ceiling(quality, ambition)
    p_floor   = _quality_to_prestige_floor(quality,
                    player.get("_current_prestige", 30))

    # Role band: how deep into a roster will they accept?
    if role_accept <= 5:
        max_slot = 2
    elif role_accept <= 12:
        max_slot = 3
    else:
        max_slot = 4

    # --- VOLATILITY SCRAMBLE SETUP ---
    # Determine scramble mode before building the rational list
    go_full_random   = False
    inject_wild_card = False

    if volatility >= 18:
        if random.random() < 0.25:
            go_full_random = True
        elif random.random() < 0.50:
            inject_wild_card = True
    elif volatility >= 14:
        if random.random() < 0.10:
            go_full_random = True
        elif random.random() < 0.35:
            inject_wild_card = True
    elif volatility >= 8:
        if random.random() < 0.15:
            inject_wild_card = True

    # --- FULL RANDOM LIST ---
    # Ignores prestige band, offensive role, everything.
    # Player picks from any open program with a small home proximity weight.
    if go_full_random:
        candidates = [
            p for p in all_programs
            if p["name"] != current_prog
        ]
        random.shuffle(candidates)
        # Weight toward home region slightly even in chaos
        def _chaos_score(prog):
            dist = get_distance_tier(home_state, prog.get("state", ""))
            prox = {"same_state": 4, "same_region": 2,
                    "adjacent_region": 1, "far": 0}.get(dist, 0)
            return prox + random.random() * 3   # mostly random, home bias slight

        candidates.sort(key=_chaos_score, reverse=True)
        # Return as (prog, projected_slot) pairs
        result = []
        for prog in candidates[:PLAYER_APPROACH_COUNT]:
            slot = _projected_offensive_slot(player, prog.get("roster", []))
            result.append((prog, slot))
        return result

    # --- RATIONAL LIST ---
    scored = []
    for prog in all_programs:
        if prog["name"] == current_prog:
            continue

        prestige = prog.get("prestige_current", 50)
        if prestige < p_floor or prestige > p_ceiling:
            continue

        slot = _projected_offensive_slot(player, prog.get("roster", []))
        if slot > max_slot:
            continue

        prestige_gap       = p_ceiling - prestige
        prestige_score     = max(0, 40 - prestige_gap)
        slot_score         = (5 - slot) * 15
        prog_state         = prog.get("state", "")
        dist_tier          = get_distance_tier(home_state, prog_state)
        proximity_scores   = {
            "same_state": 25, "same_region": 15,
            "adjacent_region": 8, "far": 0,
        }
        proximity_weighted = proximity_scores.get(dist_tier, 0) * (home_loyalty / 10.0)
        noise              = random.gauss(0, 5)
        total_score        = prestige_score + slot_score + proximity_weighted + noise
        scored.append((prog, total_score, slot))

    scored.sort(key=lambda x: x[1], reverse=True)
    rational_list = [(prog, slot) for prog, score, slot in scored[:PLAYER_APPROACH_COUNT]]

    # --- INJECT WILD CARD ---
    # Replace one slot in the rational list with a random school
    # outside their normal prestige band. Favors programs where
    # the player would be the clear top option (slot 1).
    if inject_wild_card and rational_list:
        wild_candidates = [
            p for p in all_programs
            if p["name"] != current_prog
            and p.get("prestige_current", 50) < p_floor   # outside their normal range
        ]
        if wild_candidates:
            # Slight home proximity weight even on wild card
            def _wild_score(prog):
                dist = get_distance_tier(home_state, prog.get("state", ""))
                prox = {"same_state": 3, "same_region": 1,
                        "adjacent_region": 0, "far": 0}.get(dist, 0)
                return prox + random.random() * 5

            wild_candidates.sort(key=_wild_score, reverse=True)
            wild_prog = wild_candidates[0]
            wild_slot = _projected_offensive_slot(player, wild_prog.get("roster", []))

            # Insert wild card at a random position in the list
            insert_pos = random.randint(0, len(rational_list) - 1)
            rational_list[insert_pos] = (wild_prog, wild_slot)

    return rational_list


# -----------------------------------------
# MAIN DESTINATION MATCHING ENGINE
# -----------------------------------------

def run_portal_destination_matching(all_programs, portal_pool, season_year, verbose=True):
    """
    Full Phase A/B/C/D destination matching engine.

    Phase A: Players build ranked target lists and approach top schools.
    Phase B: Programs assess needs and build want lists.
    Phase C: Tiered matching -- mutual matches first, then ego-check cascades.
    Phase D: Open pool sweep for unmatched players/programs.
    Phase E: Remaining unmatched players exit the world (undrafted).
    """
    if not portal_pool:
        return all_programs, portal_pool

    # Build a quick lookup: program name -> program dict
    prog_lookup = {p["name"]: p for p in all_programs}

    # Stamp each portal player with their origin program's prestige
    # so target list builder can use it without re-searching
    for player in portal_pool:
        origin = prog_lookup.get(player.get("portal_from", ""))
        player["_current_prestige"] = origin["prestige_current"] if origin else 30

    # -----------------------------------------------
    # PHASE A: Player target lists
    # -----------------------------------------------
    player_targets = {}   # player_id -> [(program, projected_slot), ...]
    for player in portal_pool:
        pid = player["player_id"]
        player_targets[pid] = _build_player_target_list(player, all_programs)

    # -----------------------------------------------
    # PHASE B: Program needs
    # -----------------------------------------------
    # Snapshot open slots and needs at start of matching
    # Updated as players commit
    prog_open_slots = {
        p["name"]: _get_open_slots(p) for p in all_programs
    }
    prog_pos_needs = {
        p["name"]: _get_positional_needs(p) for p in all_programs
    }

    # Track committed players by player_id
    committed = set()
    # Track which program each player landed at
    player_destination = {}   # player_id -> program_name

    # -----------------------------------------------
    # PHASE C: Tiered matching
    # -----------------------------------------------

    # Build approach registry: program_name -> list of players who approached
    # Each entry is (player, rank_on_player_list) so program knows how desired it is
    program_approaches = {p["name"]: [] for p in all_programs}

    for player in portal_pool:
        pid     = player["player_id"]
        targets = player_targets.get(pid, [])
        for rank, (prog, slot) in enumerate(targets):
            program_approaches[prog["name"]].append((player, rank))

    # Round 1: Dream school mutual matches
    # Player approached school + school wants player = immediate commit
    for player in portal_pool:
        pid     = player["player_id"]
        targets = player_targets.get(pid, [])
        if not targets:
            continue

        dream_prog, dream_slot = targets[0]
        prog_name = dream_prog["name"]

        open_slots = prog_open_slots.get(prog_name, 0)
        pos_needs  = prog_pos_needs.get(prog_name, {})

        if _program_will_accept(dream_prog, player, open_slots, pos_needs):
            # Mutual match -- player commits to dream school
            committed.add(pid)
            player_destination[pid] = prog_name
            prog_open_slots[prog_name] = max(0, open_slots - 1)
            # Update positional needs
            pos = player.get("position", "SF")
            prog_pos_needs[prog_name][pos] = max(
                0, prog_pos_needs[prog_name].get(pos, 0) - 1
            )

    # Round 2: Ego-check cascade
    # Programs with open slots make offers to portal players on their want list.
    # When a player receives an offer from school ranked < #1, they send
    # a hard yes/no request up the list to every school ranked above.

    # Build each program's portal want list
    prog_want_lists = {}
    for prog in all_programs:
        prog_name  = prog["name"]
        open_slots = prog_open_slots.get(prog_name, 0)
        if open_slots <= 0:
            continue

        pos_needs = prog_pos_needs.get(prog_name, {})
        candidates = []

        for player in portal_pool:
            if player["player_id"] in committed:
                continue
            if not _program_will_accept(prog, player, open_slots, pos_needs):
                continue
            # Score this player for this program's needs
            pos  = player.get("position", "SF")
            need = pos_needs.get(pos, 0)
            q    = _get_primary_quality(player)
            # Programs prefer players who fill urgent needs and are higher quality
            score = q + (need * 50)
            candidates.append((player, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        prog_want_lists[prog_name] = [p for p, _ in candidates]

    # Ego-check round: process uncommitted players
    for player in portal_pool:
        pid = player["player_id"]
        if pid in committed:
            continue

        targets = player_targets.get(pid, [])
        if not targets:
            continue

        # Find the best offer this player has received (lowest rank = best)
        # An "offer" = program wants them AND has a slot
        best_offer_rank = None
        best_offer_prog = None

        for rank, (prog, slot) in enumerate(targets):
            prog_name  = prog["name"]
            open_slots = prog_open_slots.get(prog_name, 0)
            pos_needs  = prog_pos_needs.get(prog_name, {})

            want_list = prog_want_lists.get(prog_name, [])
            player_wanted = any(p["player_id"] == pid for p in want_list)

            if player_wanted and _program_will_accept(
                prog, player, open_slots, pos_needs
            ):
                best_offer_rank = rank
                best_offer_prog = prog
                break   # take lowest rank (best school) that has offered

        if best_offer_prog is None:
            continue   # no offers -- falls to open pool

        # Ego check: send hard yes/no to every school ranked ABOVE the offer
        accepted_prog = best_offer_prog
        accepted_rank = best_offer_rank

        for rank in range(best_offer_rank):
            prog, slot = targets[rank]
            prog_name  = prog["name"]
            open_slots = prog_open_slots.get(prog_name, 0)
            pos_needs  = prog_pos_needs.get(prog_name, {})

            if _program_will_accept(prog, player, open_slots, pos_needs):
                # School above the offer said YES -- take the best one
                accepted_prog = prog
                accepted_rank = rank
                break   # takes the highest-ranked yes

        # Commit to accepted school
        committed.add(pid)
        player_destination[pid] = accepted_prog["name"]
        prog_name = accepted_prog["name"]
        prog_open_slots[prog_name] = max(0, prog_open_slots[prog_name] - 1)
        pos = player.get("position", "SF")
        prog_pos_needs[prog_name][pos] = max(
            0, prog_pos_needs[prog_name].get(pos, 0) - 1
        )

    # -----------------------------------------------
    # PHASE D: Open pool sweep
    # -----------------------------------------------
    # Looser matching for remaining unmatched players.
    # Still enforces a prestige band -- quality-900 players don't land
    # at prestige-15 programs just because Phase C didn't place them.
    # Not everyone finds a spot -- realistic undrafted rate expected.

    for player in portal_pool:
        pid = player["player_id"]
        if pid in committed:
            continue

        quality      = _get_primary_quality(player)
        ambition     = player.get("prestige_ambition", 10)
        home_state   = player.get("home_state", "TX")
        year         = player.get("year", "Sophomore")

        # Prestige band for open pool -- relaxed but not eliminated
        # Player will accept lower than their Phase A floor, but
        # quality still limits the ceiling of what they'd realistically land at
        open_p_ceiling = _quality_to_prestige_ceiling(quality, ambition)
        # Floor drops significantly -- desperate players accept worse situations
        open_p_floor   = max(1, player.get("_current_prestige", 30) - 20)

        candidates = []
        for prog in all_programs:
            prog_name  = prog["name"]
            open_slots = prog_open_slots.get(prog_name, 0)
            if open_slots <= 0:
                continue
            if prog_name == player.get("portal_from", ""):
                continue

            prestige = prog.get("prestige_current", 50)

            # Enforce prestige band -- quality ceiling still matters
            if prestige > open_p_ceiling:
                continue
            if prestige < open_p_floor:
                continue

            pos_needs = prog_pos_needs.get(prog_name, {})

            # Use relaxed acceptance (no ceiling enforcement, 20% lower floor)
            tier_label = _prestige_tier_label(prestige)
            base_floor, senior_floor = PROGRAM_QUALITY_FLOORS.get(
                tier_label, (500, 350)
            )
            floor = (senior_floor if year == "Senior" else base_floor) * 0.80
            if quality < floor:
                continue

            pos  = player.get("position", "SF")
            need = pos_needs.get(pos, 0)

            # Home proximity bonus
            prog_state = prog.get("state", "")
            dist_tier  = get_distance_tier(home_state, prog_state)
            prox = {"same_state": 20, "same_region": 10,
                    "adjacent_region": 5, "far": 0}.get(dist_tier, 0)

            score = quality + (need * 40) + prox + random.gauss(0, 10)
            candidates.append((prog, score))

        if not candidates:
            continue

        # Not everyone in the open pool gets placed.
        # High-quality players who can't find a realistic fit go undrafted
        # rather than landing at a random school.
        # Chance of placement scales down with quality mismatch.
        # Base 70% chance, reduced further for high-quality players
        # whose best option in the open pool is still a bad fit.
        best_prog_prestige = max(c[0].get("prestige_current", 50)
                                 for c in candidates)
        quality_prestige_gap = max(0, open_p_ceiling - best_prog_prestige)
        # Gap > 30 means best available is well below what they deserve
        placement_chance = 0.70 - (quality_prestige_gap / 100.0) * 0.40
        placement_chance = max(0.25, min(0.90, placement_chance))

        if random.random() > placement_chance:
            continue   # undrafted -- couldn't find a realistic fit

        candidates.sort(key=lambda x: x[1], reverse=True)
        best_prog = candidates[0][0]
        prog_name = best_prog["name"]

        committed.add(pid)
        player_destination[pid] = prog_name
        prog_open_slots[prog_name] = max(0, prog_open_slots[prog_name] - 1)
        pos = player.get("position", "SF")
        prog_pos_needs[prog_name][pos] = max(
            0, prog_pos_needs[prog_name].get(pos, 0) - 1
        )

    # -----------------------------------------------
    # PHASE E: Finalize -- add committed players to rosters
    # Hard 13-scholarship cap enforced here as a safety net.
    # prog_open_slots should already prevent overcrowding but
    # this guarantees no roster ever exceeds SCHOLARSHIP_CAP.
    # -----------------------------------------------
    committed_count  = 0
    undrafted_count  = 0

    for player in portal_pool:
        pid = player["player_id"]

        if pid in player_destination:
            dest_name = player_destination[pid]
            dest_prog = prog_lookup.get(dest_name)

            if dest_prog is not None:
                # Hard cap check -- never exceed 13
                if len(dest_prog.get("roster", [])) >= SCHOLARSHIP_CAP:
                    player["portal_status"] = "undrafted"
                    undrafted_count += 1
                    continue

                # Reset portal state for new school
                player["portal_status"]   = "committed"
                player["portal_dest"]     = dest_name
                player["previous_school"] = player.get("portal_from", "")
                # Classic era: sit-out year flag already set
                dest_prog["roster"].append(player)
                committed_count += 1
            else:
                player["portal_status"] = "undrafted"
                undrafted_count += 1
        else:
            player["portal_status"] = "undrafted"
            undrafted_count += 1

    # Clean up temp prestige stamp
    for player in portal_pool:
        player.pop("_current_prestige", None)

    if verbose:
        placed_pct = round(committed_count / max(1, len(portal_pool)) * 100, 1)
        print("  Placed: " + str(committed_count) +
              "  |  Undrafted: " + str(undrafted_count) +
              "  |  Placement rate: " + str(placed_pct) + "%")

        # Notable placements -- highest quality transfers and where they landed
        notable = sorted(
            [p for p in portal_pool if p.get("portal_status") == "committed"],
            key=lambda p: _get_primary_quality(p),
            reverse=True
        )[:6]
        if notable:
            print("")
            print("  Notable placements:")
            for p in notable:
                q = int(_get_primary_quality(p))
                print("    {:<22} {:<5} {:<12} {} -> {}  (quality: {})".format(
                    p["name"][:21], p.get("position", "?"), p.get("year", "?"),
                    p.get("portal_from", "?")[:20],
                    p.get("portal_dest", "?")[:20],
                    q
                ))

    return all_programs, portal_pool


# -----------------------------------------
# FULL PORTAL CYCLE
# Called by season.py
# -----------------------------------------

def run_transfer_portal(all_programs, season_year, verbose=True,
                        extra_portal_players=None):
    """
    Runs the complete portal cycle for a season.
    Phase 1: Entry filter (who leaves)
    Phase 2: Destination matching (where they go)

    extra_portal_players:
        Optional list of player dicts already removed from their rosters
        by the coaching carousel (portal wave + poach victims who need
        destination matching). These are prepended to the portal pool
        before destination matching runs. They skip the entry filter
        since they've already been evaluated and removed.

    Returns:
        all_programs  -- portal players removed from origins, added to destinations
        portal_pool   -- list of all player dicts who entered the portal
        portal_report -- summary dict
    """
    if verbose:
        print("")
        print("--- " + str(season_year) + " Transfer Portal ---")
        print("  Rules era: " + TRANSFER_RULES_ERA)

    all_programs, portal_pool, portal_report = run_portal_entry_filter(
        all_programs, season_year, verbose=verbose
    )

    # Inject carousel-generated portal players (portal wave + poach victims)
    # These have already been removed from their rosters by coaching_carousel.py
    if extra_portal_players:
        for player in extra_portal_players:
            # Ensure portal state is set correctly
            if not player.get("portal_status"):
                player["portal_status"]  = "entered"
                player["portal_year"]    = season_year
                player["portal_trigger"] = "coaching_change"
                if not player.get("portal_from"):
                    player["portal_from"] = player.get("previous_school", "unknown")
                if TRANSFER_RULES_ERA == "classic":
                    player["portal_sit_year"] = True
                else:
                    player["portal_sit_year"] = False
        portal_pool = extra_portal_players + portal_pool
        portal_report["total_entered"] += len(extra_portal_players)
        if verbose:
            print("  Carousel additions to portal: " + str(len(extra_portal_players)))

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
        print("PASS: All programs have 7+ players after portal.")

    print("")
    print("=== PLACEMENT VERIFICATION ===")
    committed = [p for p in portal_pool if p.get("portal_status") == "committed"]
    undrafted = [p for p in portal_pool if p.get("portal_status") == "undrafted"]
    print("  Total portal:  " + str(len(portal_pool)))
    print("  Placed:        " + str(len(committed)))
    print("  Undrafted:     " + str(len(undrafted)))

    print("")
    print("=== SAMPLE MOVES (top 15 by quality) ===")
    top_movers = sorted(committed, key=lambda p: _get_primary_quality(p), reverse=True)[:15]
    print("  {:<22} {:<5} {:<12} {:<24} -> {}".format(
        "Name", "Pos", "Year", "From", "To"))
    print("  " + "-" * 80)
    for p in top_movers:
        print("  {:<22} {:<5} {:<12} {:<24} -> {}".format(
            p["name"][:21], p.get("position","?"), p.get("year","?"),
            p.get("portal_from","?")[:23], p.get("portal_dest","?")
        ))

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
