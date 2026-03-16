# -----------------------------------------
# COLLEGE HOOPS SIM -- Coaching Philosophy v0.5
#
# v0.5 CHANGES -- Coaching Carousel Attributes:
#
#   NEW coach attributes for carousel system:
#     coach_id           -- unique integer ID (same system as player_id)
#     alma_mater         -- school name string (flavor/recruiting pull)
#     home_region        -- one of: northeast, southeast, midwest, southwest, west
#     ambition           -- 1-20, how hard they chase power conference jobs
#     rebuild_tolerance  -- 1-20, willingness to stay through a down cycle
#     loyalty            -- 1-20, resistance to leaving a program that's been good to them
#
#   coach_id is the primary key for:
#     - player["recruited_by"] stamping at enrollment
#     - job market recycled coach pool
#     - poach mechanic (coach pulls former players)
#
#   Experience tactical advantage:
#     experience_edge() -- weighted by career win pct, not raw years.
#     A 30-year coach with .380 career record gets a fraction of the edge
#     a 30-year coach with .600 record gets.
#     Used by game_engine.py as a subtle in-game modifier.
#
# v0.4 CHANGES (preserved):
#   roster_fill_aggressiveness derived from existing attributes.
# v0.3 CHANGES (preserved):
#   _generate_competence() bonus capped at 3.
# v0.4 note on scale: All skill attributes on 1-1000. Coach competence stays 1-20.
# -----------------------------------------

import random

# -----------------------------------------
# COACH ID COUNTER
# Same pattern as player_id. Monotonic integer.
# In SQLite migration this becomes the primary key.
# -----------------------------------------

_COACH_ID_COUNTER = [0]

def _next_coach_id():
    _COACH_ID_COUNTER[0] += 1
    return _COACH_ID_COUNTER[0]


# US regions for coach home_region
# Used for recruiting pull and job market preference
COACH_REGIONS = ["northeast", "southeast", "midwest", "southwest", "west"]

_REGION_WEIGHTS = [15, 25, 25, 20, 15]

# Programs by region (flavor -- not exhaustive, used for alma_mater generation)
_REGIONAL_PROGRAMS = {
    "northeast": [
        "Connecticut", "Syracuse", "Providence", "Seton Hall", "St. John's",
        "Villanova", "Georgetown", "Pittsburgh", "Penn State", "Rutgers",
        "Boston College", "Rhode Island", "UMass", "Maine", "Vermont",
    ],
    "southeast": [
        "Duke", "North Carolina", "Kentucky", "Louisville", "Tennessee",
        "Florida", "Georgia", "Alabama", "Auburn", "LSU", "Mississippi State",
        "South Carolina", "Clemson", "Wake Forest", "Virginia",
        "NC State", "Georgia Tech", "Vanderbilt", "Ole Miss",
    ],
    "midwest": [
        "Michigan", "Michigan State", "Ohio State", "Indiana", "Purdue",
        "Illinois", "Iowa", "Wisconsin", "Minnesota", "Northwestern",
        "Kansas", "Missouri", "Iowa State", "Kansas State", "Creighton",
        "Notre Dame", "Butler", "Xavier", "Dayton", "Cincinnati",
    ],
    "southwest": [
        "Texas", "Oklahoma", "Texas A&M", "Baylor", "TCU",
        "Texas Tech", "Oklahoma State", "Arkansas", "Houston", "SMU",
        "UTEP", "Texas State", "Stephen F. Austin", "Sam Houston",
        "New Mexico", "UNLV", "Utah State", "Fresno State",
    ],
    "west": [
        "UCLA", "USC", "Oregon", "Washington", "Arizona",
        "Arizona State", "Stanford", "California", "Utah", "Colorado",
        "Gonzaga", "BYU", "San Diego State", "Nevada", "Boise State",
        "Sacramento State", "Montana", "Idaho",
    ],
}


def _pick_home_region():
    return random.choices(COACH_REGIONS, weights=_REGION_WEIGHTS, k=1)[0]


def _pick_alma_mater(home_region):
    pool = _REGIONAL_PROGRAMS.get(home_region, _REGIONAL_PROGRAMS["midwest"])
    return random.choice(pool)


COACH_ARCHETYPES = {

    "grinder": {
        "pace": 20, "shot_profile": 35, "ball_movement": 40,
        "shot_selection": 75, "personnel": 30, "off_rebounding": 70,
        "pressure": 30, "philosophy": 25, "def_rebounding": 80,
        "screen_defense": 70, "zone_tendency": 20, "late_game": 35,
        "offensive_skill": 13, "defensive_skill": 16,
        "player_development": 14, "tactics": 15,
        "in_game_adaptability": 9, "scheme_adaptability": 7,
        "recruiting_attraction": 12, "roster_fit": 15,
        "rotation_size_bias": -1,
        "slot_strictness_bias": 3,
        "rotation_flexibility_bias": 2,
        # Carousel personality biases
        "ambition_bias": -3,        # grinders don't chase prestige jobs
        "rebuild_tolerance_bias": 4, # they stay through hard times
        "loyalty_bias": 3,
    },

    "pace_and_space": {
        "pace": 85, "shot_profile": 80, "ball_movement": 55,
        "shot_selection": 35, "personnel": 80, "off_rebounding": 35,
        "pressure": 55, "philosophy": 60, "def_rebounding": 40,
        "screen_defense": 30, "zone_tendency": 25, "late_game": 70,
        "offensive_skill": 16, "defensive_skill": 12,
        "player_development": 13, "tactics": 13,
        "in_game_adaptability": 12, "scheme_adaptability": 11,
        "recruiting_attraction": 17, "roster_fit": 10,
        "rotation_size_bias": 2,
        "slot_strictness_bias": -2,
        "rotation_flexibility_bias": 7,
        "ambition_bias": 3,
        "rebuild_tolerance_bias": -2,
        "loyalty_bias": -2,
    },

    "princeton_style": {
        "pace": 15, "shot_profile": 30, "ball_movement": 85,
        "shot_selection": 90, "personnel": 45, "off_rebounding": 40,
        "pressure": 20, "philosophy": 20, "def_rebounding": 55,
        "screen_defense": 65, "zone_tendency": 30, "late_game": 25,
        "offensive_skill": 15, "defensive_skill": 13,
        "player_development": 16, "tactics": 17,
        "in_game_adaptability": 11, "scheme_adaptability": 8,
        "recruiting_attraction": 10, "roster_fit": 17,
        "rotation_size_bias": -2,
        "slot_strictness_bias": 4,
        "rotation_flexibility_bias": 2,
        "ambition_bias": -2,
        "rebuild_tolerance_bias": 3,
        "loyalty_bias": 4,
    },

    "motion_offense": {
        "pace": 55, "shot_profile": 45, "ball_movement": 80,
        "shot_selection": 70, "personnel": 50, "off_rebounding": 50,
        "pressure": 40, "philosophy": 35, "def_rebounding": 60,
        "screen_defense": 60, "zone_tendency": 25, "late_game": 30,
        "offensive_skill": 15, "defensive_skill": 14,
        "player_development": 15, "tactics": 14,
        "in_game_adaptability": 13, "scheme_adaptability": 13,
        "recruiting_attraction": 13, "roster_fit": 14,
        "rotation_size_bias": 0,
        "slot_strictness_bias": 1,
        "rotation_flexibility_bias": 5,
        "ambition_bias": 0,
        "rebuild_tolerance_bias": 1,
        "loyalty_bias": 1,
    },

    "dribble_drive": {
        "pace": 75, "shot_profile": 70, "ball_movement": 35,
        "shot_selection": 30, "personnel": 70, "off_rebounding": 45,
        "pressure": 60, "philosophy": 55, "def_rebounding": 45,
        "screen_defense": 35, "zone_tendency": 20, "late_game": 80,
        "offensive_skill": 15, "defensive_skill": 13,
        "player_development": 12, "tactics": 12,
        "in_game_adaptability": 11, "scheme_adaptability": 10,
        "recruiting_attraction": 14, "roster_fit": 11,
        "rotation_size_bias": 1,
        "slot_strictness_bias": -1,
        "rotation_flexibility_bias": 7,
        "ambition_bias": 2,
        "rebuild_tolerance_bias": -1,
        "loyalty_bias": -1,
    },

    "post_centric": {
        "pace": 35, "shot_profile": 25, "ball_movement": 50,
        "shot_selection": 65, "personnel": 20, "off_rebounding": 65,
        "pressure": 35, "philosophy": 30, "def_rebounding": 75,
        "screen_defense": 65, "zone_tendency": 30, "late_game": 40,
        "offensive_skill": 14, "defensive_skill": 14,
        "player_development": 15, "tactics": 14,
        "in_game_adaptability": 10, "scheme_adaptability": 8,
        "recruiting_attraction": 12, "roster_fit": 15,
        "rotation_size_bias": -1,
        "slot_strictness_bias": 3,
        "rotation_flexibility_bias": 3,
        "ambition_bias": -1,
        "rebuild_tolerance_bias": 2,
        "loyalty_bias": 2,
    },

    "pressure_defense": {
        "pace": 70, "shot_profile": 60, "ball_movement": 50,
        "shot_selection": 40, "personnel": 60, "off_rebounding": 35,
        "pressure": 90, "philosophy": 85, "def_rebounding": 40,
        "screen_defense": 25, "zone_tendency": 45, "late_game": 55,
        "offensive_skill": 14, "defensive_skill": 17,
        "player_development": 13, "tactics": 15,
        "in_game_adaptability": 14, "scheme_adaptability": 12,
        "recruiting_attraction": 15, "roster_fit": 12,
        "rotation_size_bias": 2,
        "slot_strictness_bias": 1,
        "rotation_flexibility_bias": 7,
        "ambition_bias": 2,
        "rebuild_tolerance_bias": 0,
        "loyalty_bias": 0,
    },

    "zone_specialist": {
        "pace": 40, "shot_profile": 40, "ball_movement": 55,
        "shot_selection": 60, "personnel": 35, "off_rebounding": 55,
        "pressure": 35, "philosophy": 40, "def_rebounding": 65,
        "screen_defense": 50, "zone_tendency": 90, "late_game": 40,
        "offensive_skill": 14, "defensive_skill": 16,
        "player_development": 14, "tactics": 15,
        "in_game_adaptability": 9, "scheme_adaptability": 7,
        "recruiting_attraction": 13, "roster_fit": 14,
        "rotation_size_bias": -1,
        "slot_strictness_bias": 2,
        "rotation_flexibility_bias": 2,
        "ambition_bias": -1,
        "rebuild_tolerance_bias": 2,
        "loyalty_bias": 3,
    },

    "analytics_modern": {
        "pace": 65, "shot_profile": 90, "ball_movement": 65,
        "shot_selection": 55, "personnel": 85, "off_rebounding": 30,
        "pressure": 45, "philosophy": 50, "def_rebounding": 35,
        "screen_defense": 20, "zone_tendency": 20, "late_game": 50,
        "offensive_skill": 15, "defensive_skill": 14,
        "player_development": 13, "tactics": 14,
        "in_game_adaptability": 14, "scheme_adaptability": 15,
        "recruiting_attraction": 13, "roster_fit": 16,
        "rotation_size_bias": 1,
        "slot_strictness_bias": 0,
        "rotation_flexibility_bias": 6,
        "ambition_bias": 3,
        "rebuild_tolerance_bias": -2,
        "loyalty_bias": -1,
    },

    "wildcard": {
        "pace": 50, "shot_profile": 50, "ball_movement": 50,
        "shot_selection": 50, "personnel": 50, "off_rebounding": 50,
        "pressure": 50, "philosophy": 50, "def_rebounding": 50,
        "screen_defense": 50, "zone_tendency": 50, "late_game": 50,
        "offensive_skill": 11, "defensive_skill": 11,
        "player_development": 11, "tactics": 11,
        "in_game_adaptability": 11, "scheme_adaptability": 11,
        "recruiting_attraction": 11, "roster_fit": 11,
        "rotation_size_bias": 0,
        "slot_strictness_bias": 0,
        "rotation_flexibility_bias": 5,
        "ambition_bias": 0,
        "rebuild_tolerance_bias": 0,
        "loyalty_bias": 0,
    },
}

ARCHETYPE_WEIGHTS = {
    "grinder":          18,
    "pace_and_space":   14,
    "princeton_style":   6,
    "motion_offense":   16,
    "dribble_drive":    12,
    "post_centric":      8,
    "pressure_defense":  8,
    "zone_specialist":   6,
    "analytics_modern": 10,
    "wildcard":          2,
}

SLIDER_NOISE     = 12
COMPETENCE_NOISE = 2


def _pick_archetype():
    archetypes = list(ARCHETYPE_WEIGHTS.keys())
    weights    = list(ARCHETYPE_WEIGHTS.values())
    return random.choices(archetypes, weights=weights, k=1)[0]


def _slider(base, noise=SLIDER_NOISE):
    val = int(random.gauss(base, noise))
    return max(1, min(100, val))


def _scale(val, lo, hi):
    if hi == lo:
        return 0.0
    return (val - lo) / (hi - lo)


def _scale_attr(val):
    return _scale(val, 1, 1000)


def _rand_carousel(base, noise=3):
    """Generates a 1-20 carousel personality attribute."""
    val = int(random.gauss(base, noise))
    return max(1, min(20, val))


def _derive_roster_fill_aggressiveness(rotation_size, player_development, slot_strictness):
    """
    Derives roster_fill_aggressiveness (1-10) from existing coach attributes.
    Internal only -- never shown to human player.
    """
    rotation_component    = (rotation_size - 6) / 5.0
    development_component = (player_development - 1) / 19.0
    strictness_component  = (10 - slot_strictness) / 9.0

    raw = (
        rotation_component    * 0.45 +
        development_component * 0.30 +
        strictness_component  * 0.25
    )

    base  = round(raw * 10)
    noise = random.randint(-1, 1)
    return max(1, min(10, base + noise))


def generate_coach(name, prestige=50, archetype=None, experience=None):
    """
    Generates a full coach object.

    name       -- coach name string
    prestige   -- program prestige 1-100, raises competence ceiling
    archetype  -- optional, forces archetype. None = weighted random.
    experience -- optional 0-30 years. None = random.
    """

    if archetype is None:
        archetype = _pick_archetype()
    t = COACH_ARCHETYPES[archetype]

    if experience is None:
        experience = random.randint(0, 25)

    # --- PHILOSOPHY SLIDERS ---
    philosophy = {
        "pace":           _slider(t["pace"]),
        "shot_profile":   _slider(t["shot_profile"]),
        "ball_movement":  _slider(t["ball_movement"]),
        "shot_selection": _slider(t["shot_selection"]),
        "personnel":      _slider(t["personnel"]),
        "off_rebounding": _slider(t["off_rebounding"]),
        "pressure":       _slider(t["pressure"]),
        "philosophy":     _slider(t["philosophy"]),
        "def_rebounding": _slider(t["def_rebounding"]),
        "screen_defense": _slider(t["screen_defense"]),
        "zone_tendency":  _slider(t["zone_tendency"]),
        "late_game":      _slider(t["late_game"]),
    }

    # --- COMPETENCE RATINGS ---
    exp_bonus      = min(4, experience // 6)
    prestige_bonus = min(3, prestige // 35)
    competence     = _generate_competence(t, exp_bonus, prestige_bonus)

    # --- ROTATION SIZE ---
    pace_driven   = 7 + int((philosophy["pace"] / 100) * 3)
    bias          = t["rotation_size_bias"]
    rotation_size = max(6, min(11, pace_driven + bias + random.randint(-1, 1)))

    # --- SLOT STRICTNESS ---
    slot_base       = 5 + t["slot_strictness_bias"]
    slot_strictness = max(1, min(10, slot_base + random.randint(-2, 2)))

    # --- ROTATION FLEXIBILITY ---
    flex_base            = t.get("rotation_flexibility_bias", 5)
    rotation_flexibility = max(1, min(10, flex_base + random.randint(-2, 2)))

    # --- ROSTER VALUES ---
    roster_values = _generate_roster_values(archetype, philosophy)

    # --- ROSTER FILL AGGRESSIVENESS (v0.4) ---
    roster_fill_aggressiveness = _derive_roster_fill_aggressiveness(
        rotation_size,
        competence["player_development"],
        slot_strictness,
    )

    # --- CAROUSEL PERSONALITY (v0.5) ---
    home_region = _pick_home_region()
    alma_mater  = _pick_alma_mater(home_region)

    # Ambition: prestige programs attract ambitious coaches
    ambition_base = 10 + t.get("ambition_bias", 0) + min(3, prestige // 35)
    ambition      = _rand_carousel(ambition_base)

    # Rebuild tolerance: inversely related to ambition, archetype-driven
    rebuild_base      = 10 + t.get("rebuild_tolerance_bias", 0)
    rebuild_tolerance = _rand_carousel(rebuild_base)

    # Loyalty: independent personality trait
    loyalty_base = 10 + t.get("loyalty_bias", 0)
    loyalty      = _rand_carousel(loyalty_base)

    coach = {
        # --- IDENTITY ---
        "coach_id":   _next_coach_id(),   # v0.5: unique immutable integer ID
        "name":       name,
        "archetype":  archetype,
        "experience": experience,
        "legacy":     0,

        # --- GEOGRAPHY (v0.5) ---
        "home_region": home_region,
        "alma_mater":  alma_mater,

        # --- CAROUSEL PERSONALITY (v0.5, 1-20) ---
        "ambition":          ambition,
        "rebuild_tolerance": rebuild_tolerance,
        "loyalty":           loyalty,

        # --- PHILOSOPHY SLIDERS ---
        "pace":           philosophy["pace"],
        "shot_profile":   philosophy["shot_profile"],
        "ball_movement":  philosophy["ball_movement"],
        "shot_selection": philosophy["shot_selection"],
        "personnel":      philosophy["personnel"],
        "off_rebounding": philosophy["off_rebounding"],
        "pressure":       philosophy["pressure"],
        "philosophy":     philosophy["philosophy"],
        "def_rebounding": philosophy["def_rebounding"],
        "screen_defense": philosophy["screen_defense"],
        "zone_tendency":  philosophy["zone_tendency"],
        "late_game":      philosophy["late_game"],

        # --- COMPETENCE RATINGS (1-20) ---
        "offensive_skill":       competence["offensive_skill"],
        "defensive_skill":       competence["defensive_skill"],
        "player_development":    competence["player_development"],
        "tactics":               competence["tactics"],
        "in_game_adaptability":  competence["in_game_adaptability"],
        "scheme_adaptability":   competence["scheme_adaptability"],
        "recruiting_attraction": competence["recruiting_attraction"],
        "roster_fit":            competence["roster_fit"],

        # --- ROSTER CONSTRUCTION ---
        "rotation_size":               rotation_size,
        "slot_strictness":             slot_strictness,
        "rotation_flexibility":        rotation_flexibility,
        "roster_fill_aggressiveness":  roster_fill_aggressiveness,

        # --- ROSTER VALUES (1-10) ---
        "values_athleticism":  roster_values["athleticism"],
        "values_iq":           roster_values["iq"],
        "values_size":         roster_values["size"],
        "values_shooting":     roster_values["shooting"],
        "values_defense":      roster_values["defense"],
        "values_toughness":    roster_values["toughness"],
        "values_role_players": roster_values["role_players"],

        # --- SEASON STATE ---
        "seasons_at_program": 0,
        "career_wins":        0,
        "career_losses":      0,
    }

    return coach


def experience_edge(coach):
    """
    Returns a subtle tactical edge multiplier (0.97 - 1.06) based on
    experience weighted by career win percentage.

    A 30-year coach with .600 career record gets the full edge.
    A 30-year coach with .380 career record gets a fraction.
    A first-year coach gets 0.97 (mild disadvantage vs veterans).

    Used by game_engine.py as an in-game modifier on tactics checks.
    Scale is intentionally narrow -- experience is real but subtle.
    """
    experience = coach.get("experience", 0)
    wins       = coach.get("career_wins", 0)
    losses     = coach.get("career_losses", 0)
    total      = wins + losses

    # Career win pct -- default to .500 if no games played (new coach)
    if total > 0:
        win_pct = wins / total
    else:
        win_pct = 0.500

    # Experience factor: 0 at year 0, 1.0 at year 25+
    exp_factor = min(1.0, experience / 25.0)

    # Quality weight: .600 = full credit. .400 = half credit. Below = minimal.
    if win_pct >= 0.600:
        quality_weight = 1.0
    elif win_pct >= 0.500:
        quality_weight = 0.5 + (win_pct - 0.500) * 5.0   # 0.5 to 1.0
    elif win_pct >= 0.400:
        quality_weight = 0.2 + (win_pct - 0.400) * 3.0   # 0.2 to 0.5
    else:
        quality_weight = 0.1

    # Combined edge: max +0.09 for a true veteran with great record
    raw_edge = exp_factor * quality_weight * 0.09

    # New coaches get a small disadvantage (-0.03)
    if experience < 2:
        return max(0.97, 1.0 - 0.03 + raw_edge)

    return min(1.06, 1.0 + raw_edge)


def ensure_coach_carousel_attrs(coach):
    """
    Migration safety. Adds v0.5 carousel attributes to any existing
    coach dict that's missing them. Safe to call multiple times.
    """
    if "coach_id" not in coach:
        coach["coach_id"] = _next_coach_id()

    if "home_region" not in coach:
        coach["home_region"] = _pick_home_region()

    if "alma_mater" not in coach:
        coach["alma_mater"] = _pick_alma_mater(coach["home_region"])

    if "ambition" not in coach:
        coach["ambition"] = random.randint(6, 14)

    if "rebuild_tolerance" not in coach:
        coach["rebuild_tolerance"] = random.randint(6, 14)

    if "loyalty" not in coach:
        coach["loyalty"] = random.randint(6, 14)

    return coach


def _generate_competence(template, exp_bonus, prestige_bonus):
    bonus = min(3, exp_bonus + prestige_bonus)

    ratings = {}
    competence_keys = [
        "offensive_skill", "defensive_skill", "player_development",
        "tactics", "in_game_adaptability", "scheme_adaptability",
        "recruiting_attraction", "roster_fit",
    ]

    for key in competence_keys:
        base = template.get(key, 11)
        val  = int(random.gauss(base + bonus, COMPETENCE_NOISE))
        ratings[key] = max(1, min(20, val))

    return ratings


def _generate_roster_values(archetype, philosophy):
    def clamp(val):
        return max(1, min(10, val + random.randint(-1, 2)))

    athleticism  = clamp(int((philosophy["pace"] + philosophy["personnel"]) / 20))
    iq           = clamp(int((philosophy["shot_selection"] + philosophy["ball_movement"]) / 20))
    size         = clamp(10 - int(philosophy["personnel"] / 14))
    shooting     = clamp(int(philosophy["shot_profile"] / 11))
    defense      = clamp(int((philosophy["pressure"] + philosophy["philosophy"]) / 20))
    toughness    = clamp(int((philosophy["off_rebounding"] + philosophy["def_rebounding"]) / 20))

    role_archetypes = [
        "grinder", "princeton_style", "motion_offense",
        "post_centric", "zone_specialist"
    ]
    role_base    = 7 if archetype in role_archetypes else 4
    role_players = max(1, min(10, role_base + random.randint(-2, 2)))

    return {
        "athleticism":  athleticism,
        "iq":           iq,
        "size":         size,
        "shooting":     shooting,
        "defense":      defense,
        "toughness":    toughness,
        "role_players": role_players,
    }


def calculate_style_fit(player, coach):
    """
    Calculates how well a player fits a coach's system.
    Returns a fit score 0-100.
    """
    fit_points = 0
    checks     = 0

    def contrib(player_val, weight):
        return _scale_attr(player_val) * weight

    if coach["pace"] >= 60:
        fit_points += contrib(player.get("speed", 10), coach["pace"] / 100)
        checks += 1

    if coach["shot_profile"] >= 55:
        avg = (player.get("three_point", 10) + player.get("finishing", 10)) / 2
        fit_points += contrib(avg, coach["shot_profile"] / 100)
        checks += 1

    if coach["ball_movement"] >= 60:
        avg = (player.get("passing", 10) + player.get("court_vision", 10)) / 2
        fit_points += contrib(avg, coach["ball_movement"] / 100)
        checks += 1

    if coach["personnel"] >= 65:
        avg = (player.get("ball_handling", 10) + player.get("speed", 10)) / 2
        fit_points += contrib(avg, coach["personnel"] / 100)
        checks += 1

    if coach["philosophy"] >= 65:
        avg = (player.get("steal_tendency", 10) + player.get("lateral_quickness", 10)) / 2
        fit_points += contrib(avg, coach["philosophy"] / 100)
        checks += 1

    if coach["off_rebounding"] >= 65 or coach["def_rebounding"] >= 65:
        avg = (player.get("rebounding", 10) + player.get("strength", 10)) / 2
        fit_points += contrib(avg, 1.0)
        checks += 1

    if coach["shot_profile"] <= 35 and coach["personnel"] <= 35:
        avg = (player.get("post_scoring", 10) + player.get("strength", 10)) / 2
        fit_points += contrib(avg, 1.0)
        checks += 1

    if checks == 0:
        return 50

    raw = (fit_points / checks) * 100
    return max(0, min(100, int(raw)))


def print_coach_profile(coach, show_archetype=False):
    def bar(val, width=20):
        filled = int((val / 100) * width)
        return "█" * filled + "░" * (width - filled) + "  " + str(val)

    def stars(val, max_val=20):
        filled = round((val / max_val) * 10)
        return "●" * filled + "○" * (10 - filled) + "  " + str(val) + "/20"

    print("")
    print("=" * 65)
    print("  " + coach["name"] + "  [ID:" + str(coach.get("coach_id", "?")) + "]")
    if show_archetype:
        print("  Archetype:      " + coach["archetype"])
    print("  Experience:     " + str(coach["experience"]) + " years")
    print("  Home region:    " + coach.get("home_region", "?"))
    print("  Alma mater:     " + coach.get("alma_mater", "?"))
    print("  Ambition:       " + str(coach.get("ambition", "?")) + "/20")
    print("  Rebuild tol:    " + str(coach.get("rebuild_tolerance", "?")) + "/20")
    print("  Loyalty:        " + str(coach.get("loyalty", "?")) + "/20")
    print("  Rotation size:  " + str(coach["rotation_size"]) + " players")
    print("  Rot flexibility:" + str(coach["rotation_flexibility"]) + "/10")
    print("  Slot strictness:" + str(coach["slot_strictness"]) + "/10")
    print("  Roster fill:    " + str(coach["roster_fill_aggressiveness"]) + "/10" +
          ("  (aggressive filler)" if coach["roster_fill_aggressiveness"] >= 7
           else "  (selective)"       if coach["roster_fill_aggressiveness"] <= 3
           else "  (balanced)"))
    edge = experience_edge(coach)
    print("  Experience edge:" + str(round(edge, 3)) + "x")

    print("")
    print("  -- OFFENSE --")
    print("  Pace            slow  " + bar(coach["pace"]) + "  fast")
    print("  Shot Profile    mid   " + bar(coach["shot_profile"]) + "  rim&3")
    print("  Ball Movement   iso   " + bar(coach["ball_movement"]) + "  motion")
    print("  Shot Selection  quick " + bar(coach["shot_selection"]) + "  patient")
    print("  Personnel       trad  " + bar(coach["personnel"]) + "  positionless")
    print("  Off Rebounding  get back " + bar(coach["off_rebounding"]) + "  crash")

    print("")
    print("  -- DEFENSE --")
    print("  Pressure        set   " + bar(coach["pressure"]) + "  press")
    print("  Philosophy      contain " + bar(coach["philosophy"]) + "  gamble")
    print("  Def Rebounding  leak  " + bar(coach["def_rebounding"]) + "  crash")
    print("  Screen Defense  switch " + bar(coach["screen_defense"]) + "  fight thru")
    print("  Zone Tendency   man   " + bar(coach["zone_tendency"]) + "  zone")

    print("")
    print("  -- LATE GAME --")
    print("  Late Game       sets  " + bar(coach["late_game"]) + "  star iso")

    print("")
    print("  -- COMPETENCE --")
    print("  Offensive Skill:       " + stars(coach["offensive_skill"]))
    print("  Defensive Skill:       " + stars(coach["defensive_skill"]))
    print("  Player Development:    " + stars(coach["player_development"]))
    print("  Tactics:               " + stars(coach["tactics"]))
    print("  In-Game Adaptability:  " + stars(coach["in_game_adaptability"]))
    print("  Scheme Adaptability:   " + stars(coach["scheme_adaptability"]))
    print("  Recruiting Attraction: " + stars(coach["recruiting_attraction"]))
    print("  Roster Fit:            " + stars(coach["roster_fit"]))

    print("")
    print("  -- ROSTER VALUES --")
    print("  Athleticism: " + str(coach["values_athleticism"]) +
          "  IQ: "          + str(coach["values_iq"]) +
          "  Size: "        + str(coach["values_size"]) +
          "  Shooting: "    + str(coach["values_shooting"]))
    print("  Defense: "     + str(coach["values_defense"]) +
          "  Toughness: "   + str(coach["values_toughness"]) +
          "  Role Players: "+ str(coach["values_role_players"]))


if __name__ == "__main__":

    from player import create_player

    print("=" * 65)
    print("  COACH GENERATION TEST -- v0.5")
    print("=" * 65)

    coaches = [
        generate_coach("Tom Izzo Type",     prestige=85, archetype="grinder",          experience=25),
        generate_coach("Cal Type",          prestige=90, archetype="pace_and_space",    experience=20),
        generate_coach("Bennett Type",      prestige=70, archetype="grinder",           experience=15),
        generate_coach("Pitino Type",       prestige=75, archetype="pressure_defense",  experience=30),
        generate_coach("Boeheim Type",      prestige=80, archetype="zone_specialist",   experience=28),
        generate_coach("Analytics Coach",   prestige=60, archetype="analytics_modern",  experience=8),
        generate_coach("Princeton Coach",   prestige=55, archetype="princeton_style",   experience=18),
        generate_coach("Post Coach",        prestige=65, archetype="post_centric",      experience=20),
        generate_coach("SWAC Coach",        prestige=15, archetype="grinder",           experience=5),
        generate_coach("Mid-Major Grinder", prestige=35, archetype="motion_offense",    experience=12),
    ]

    for coach in coaches:
        print_coach_profile(coach, show_archetype=True)

    print("")
    print("=" * 65)
    print("  CAROUSEL PERSONALITY DISTRIBUTION")
    print("=" * 65)
    print("  {:<25} {:<12} {:<10} {:<12} {:<12}".format(
        "Coach", "Archetype", "Ambition", "Rebuild Tol", "Loyalty"))
    print("  " + "-" * 71)
    for c in coaches:
        print("  {:<25} {:<12} {:<10} {:<12} {:<12}".format(
            c["name"], c["archetype"],
            str(c["ambition"]) + "/20",
            str(c["rebuild_tolerance"]) + "/20",
            str(c["loyalty"]) + "/20",
        ))

    print("")
    print("=" * 65)
    print("  EXPERIENCE EDGE TEST")
    print("=" * 65)
    test_cases = [
        (0,  0,  0,   "First year coach"),
        (5,  50, 30,  "5-year coach .625 record"),
        (15, 180, 120, "15-year coach .600 record"),
        (25, 400, 200, "25-year coach .667 record"),
        (25, 200, 350, "25-year coach .364 record (career loser)"),
        (30, 600, 250, "30-year coach .706 record (legend)"),
    ]
    print("  {:<38} {}".format("Profile", "Edge multiplier"))
    print("  " + "-" * 55)
    for exp, wins, losses, label in test_cases:
        fake_coach = {"experience": exp, "career_wins": wins, "career_losses": losses}
        edge = experience_edge(fake_coach)
        print("  {:<38} {}x".format(label, round(edge, 4)))
