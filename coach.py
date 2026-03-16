# -----------------------------------------
# COLLEGE HOOPS SIM -- Coaching Philosophy v0.7
#
# v0.7 CHANGES -- Contract System + Legacy Seeding:
#
#   CONTRACT SYSTEM:
#     Every coach gets contract_years (length of deal) and
#     contract_years_remaining (seasons left on deal) at hire.
#
#     Contract length is hybrid:
#       Base by prestige:
#         95+:     6 years
#         79-94:   5 years
#         59-78:   4 years
#         39-58:   3 years
#         below:   2 years
#       Board patience modifier (from program carousel_state):
#         patience 8-10: -1 year (impatient boards give shorter deals)
#         patience 1-3:  +1 year (stable boards give longer security)
#       Min 1 year, max 7 years.
#
#     While contract_years_remaining > 0, firing threshold is
#     suppressed by CONTRACT_PROTECTION_POINTS in coaching_carousel.py.
#     Hard floor (security <= 15) and stale meter still fire regardless.
#
#     contract_years_remaining decrements each season in
#     _update_coach_career_record(). When it hits 0 and the coach
#     is still employed, they're considered out-of-contract and normal
#     thresholds resume.
#
#   LEGACY SEEDING:
#     seed_legacy_coach() -- called at world-build for programs with
#     prestige >= 75. Gives the coach simulated pre-sim history so
#     they don't start with 0 career wins and no contract protection.
#
#     Seeded values:
#       coach_seasons:          4-8 years (weighted by prestige)
#       career_wins/losses:     based on expected win% at prestige level
#       contract_years_remaining: 2-4 (mid-contract at world-build)
#       ncaa_wins_last_3:        small seed for high-prestige programs
#       conf_top_third_last_3:   1-2 for established programs
#
# v0.6 CHANGES (preserved):
#   Breakout candidate system (update_coach_buzz_history, is_breakout_candidate).
# v0.5 CHANGES (preserved):
#   coach_id, home_region, alma_mater, ambition, rebuild_tolerance, loyalty.
# -----------------------------------------

import random

_COACH_ID_COUNTER = [0]

def _next_coach_id():
    _COACH_ID_COUNTER[0] += 1
    return _COACH_ID_COUNTER[0]


COACH_REGIONS   = ["northeast", "southeast", "midwest", "southwest", "west"]
_REGION_WEIGHTS = [15, 25, 25, 20, 15]

_REGIONAL_PROGRAMS = {
    "northeast": ["Connecticut", "Syracuse", "Providence", "Seton Hall", "St. John's",
                  "Villanova", "Georgetown", "Pittsburgh", "Penn State", "Rutgers",
                  "Boston College", "Rhode Island", "UMass", "Maine", "Vermont"],
    "southeast": ["Duke", "North Carolina", "Kentucky", "Louisville", "Tennessee",
                  "Florida", "Georgia", "Alabama", "Auburn", "LSU", "Mississippi State",
                  "South Carolina", "Clemson", "Wake Forest", "Virginia",
                  "NC State", "Georgia Tech", "Vanderbilt", "Ole Miss"],
    "midwest":   ["Michigan", "Michigan State", "Ohio State", "Indiana", "Purdue",
                  "Illinois", "Iowa", "Wisconsin", "Minnesota", "Northwestern",
                  "Kansas", "Missouri", "Iowa State", "Kansas State", "Creighton",
                  "Notre Dame", "Butler", "Xavier", "Dayton", "Cincinnati"],
    "southwest": ["Texas", "Oklahoma", "Texas A&M", "Baylor", "TCU",
                  "Texas Tech", "Oklahoma State", "Arkansas", "Houston", "SMU",
                  "UTEP", "Texas State", "Stephen F. Austin", "Sam Houston",
                  "New Mexico", "UNLV", "Utah State", "Fresno State"],
    "west":      ["UCLA", "USC", "Oregon", "Washington", "Arizona",
                  "Arizona State", "Stanford", "California", "Utah", "Colorado",
                  "Gonzaga", "BYU", "San Diego State", "Nevada", "Boise State",
                  "Sacramento State", "Montana", "Idaho"],
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
        "rotation_size_bias": -1, "slot_strictness_bias": 3,
        "rotation_flexibility_bias": 2,
        "ambition_bias": -3, "rebuild_tolerance_bias": 4, "loyalty_bias": 3,
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
        "rotation_size_bias": 2, "slot_strictness_bias": -2,
        "rotation_flexibility_bias": 7,
        "ambition_bias": 3, "rebuild_tolerance_bias": -2, "loyalty_bias": -2,
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
        "rotation_size_bias": -2, "slot_strictness_bias": 4,
        "rotation_flexibility_bias": 2,
        "ambition_bias": -2, "rebuild_tolerance_bias": 3, "loyalty_bias": 4,
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
        "rotation_size_bias": 0, "slot_strictness_bias": 1,
        "rotation_flexibility_bias": 5,
        "ambition_bias": 0, "rebuild_tolerance_bias": 1, "loyalty_bias": 1,
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
        "rotation_size_bias": 1, "slot_strictness_bias": -1,
        "rotation_flexibility_bias": 7,
        "ambition_bias": 2, "rebuild_tolerance_bias": -1, "loyalty_bias": -1,
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
        "rotation_size_bias": -1, "slot_strictness_bias": 3,
        "rotation_flexibility_bias": 3,
        "ambition_bias": -1, "rebuild_tolerance_bias": 2, "loyalty_bias": 2,
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
        "rotation_size_bias": 2, "slot_strictness_bias": 1,
        "rotation_flexibility_bias": 7,
        "ambition_bias": 2, "rebuild_tolerance_bias": 0, "loyalty_bias": 0,
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
        "rotation_size_bias": -1, "slot_strictness_bias": 2,
        "rotation_flexibility_bias": 2,
        "ambition_bias": -1, "rebuild_tolerance_bias": 2, "loyalty_bias": 3,
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
        "rotation_size_bias": 1, "slot_strictness_bias": 0,
        "rotation_flexibility_bias": 6,
        "ambition_bias": 3, "rebuild_tolerance_bias": -2, "loyalty_bias": -1,
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
        "rotation_size_bias": 0, "slot_strictness_bias": 0,
        "rotation_flexibility_bias": 5,
        "ambition_bias": 0, "rebuild_tolerance_bias": 0, "loyalty_bias": 0,
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

BREAKOUT_MIN_NCAA_WINS   = 1
BREAKOUT_MIN_TOP_THIRD   = 2
BREAKOUT_MIN_RATINGS_AVG = 12


def _pick_archetype():
    archetypes = list(ARCHETYPE_WEIGHTS.keys())
    weights    = list(ARCHETYPE_WEIGHTS.values())
    return random.choices(archetypes, weights=weights, k=1)[0]


def _slider(base, noise=SLIDER_NOISE):
    return max(1, min(100, int(random.gauss(base, noise))))


def _scale(val, lo, hi):
    if hi == lo: return 0.0
    return (val - lo) / (hi - lo)


def _scale_attr(val):
    return _scale(val, 1, 1000)


def _rand_carousel(base, noise=3):
    return max(1, min(20, int(random.gauss(base, noise))))


def _derive_roster_fill_aggressiveness(rotation_size, player_development, slot_strictness):
    raw = (
        ((rotation_size - 6) / 5.0)         * 0.45 +
        ((player_development - 1) / 19.0)   * 0.30 +
        ((10 - slot_strictness) / 9.0)       * 0.25
    )
    return max(1, min(10, round(raw * 10) + random.randint(-1, 1)))


def _calc_contract_years(prestige, board_patience=5):
    """
    Returns contract length in years based on program prestige and board patience.
    Hybrid: prestige sets base, board patience modifies ±1.
    """
    if prestige >= 95:   base = 6
    elif prestige >= 79: base = 5
    elif prestige >= 59: base = 4
    elif prestige >= 39: base = 3
    else:                base = 2

    if board_patience >= 8:   modifier = -1   # impatient = shorter deal
    elif board_patience <= 3: modifier = +1   # stable = longer security
    else:                     modifier = 0

    return max(1, min(7, base + modifier))


def generate_coach(name, prestige=50, archetype=None, experience=None,
                   board_patience=5, age=None):
    """
    Generates a full coach object.
    board_patience: passed from program carousel_state to calculate contract length.
    age: if None, derived from experience. Pass explicitly for precise control.
    """
    if archetype is None:
        archetype = _pick_archetype()
    t = COACH_ARCHETYPES[archetype]

    if experience is None:
        experience = random.randint(0, 25)

    # Age derived from experience if not provided.
    # A coach with 20 years experience is realistically in their early-to-mid 40s.
    # Small random spread reflects that some coaches start young, some start late.
    if age is None:
        age = max(24, min(78, 22 + experience + random.randint(0, 6)))

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

    exp_bonus      = min(4, experience // 6)
    prestige_bonus = min(3, prestige // 35)
    competence     = _generate_competence(t, exp_bonus, prestige_bonus)

    pace_driven   = 7 + int((philosophy["pace"] / 100) * 3)
    rotation_size = max(6, min(11, pace_driven + t["rotation_size_bias"] + random.randint(-1, 1)))

    slot_base       = 5 + t["slot_strictness_bias"]
    slot_strictness = max(1, min(10, slot_base + random.randint(-2, 2)))

    flex_base            = t.get("rotation_flexibility_bias", 5)
    rotation_flexibility = max(1, min(10, flex_base + random.randint(-2, 2)))

    roster_values = _generate_roster_values(archetype, philosophy)
    roster_fill   = _derive_roster_fill_aggressiveness(
        rotation_size, competence["player_development"], slot_strictness)

    home_region = _pick_home_region()
    alma_mater  = _pick_alma_mater(home_region)

    ambition          = _rand_carousel(10 + t.get("ambition_bias", 0) + min(3, prestige // 35))
    rebuild_tolerance = _rand_carousel(10 + t.get("rebuild_tolerance_bias", 0))
    loyalty           = _rand_carousel(10 + t.get("loyalty_bias", 0))

    contract_yrs = _calc_contract_years(prestige, board_patience)

    coach = {
        # IDENTITY
        "coach_id":   _next_coach_id(),
        "name":       name,
        "archetype":  archetype,
        "experience": experience,
        "age":        age,
        "legacy":     0,
        # STAFF ROLE -- set by generate_staff(), overwritten on hire
        # "head_coach" | "assistant" | "grad_assistant" | "free_agent"
        "staff_role":         "head_coach",
        "seasons_on_staff":   0,       # seasons at current program in any role
        "free_agent_seasons": 0,       # seasons in free agent pool without a job
        # GEOGRAPHY
        "home_region": home_region,
        "alma_mater":  alma_mater,
        # CAROUSEL PERSONALITY
        "ambition":          ambition,
        "rebuild_tolerance": rebuild_tolerance,
        "loyalty":           loyalty,
        # MONEY MOTIVATION -- separate from ambition
        # High greed coaches will take lateral/step-down moves for bigger paychecks
        # Low greed coaches won't leave comfort for money alone
        "greed": _rand_carousel(10 + random.randint(-2, 2)),
        # JOB STABILITY TRACKING
        # cooldown counts seasons since last job change -- suppresses willingness to move again
        "job_change_cooldown":    0,
        # instability_reputation builds with rapid job changes, decays slowly
        # programs check this before hiring -- serial job-hoppers get avoided
        "instability_reputation": 0,
        # SALARY
        # salary_current: what they made at their last job (0 if never been HC)
        # salary_floor: minimum they'll accept (rises with experience/last salary)
        "salary_current": 0,
        "salary_floor":   _calc_salary_floor(prestige, experience),
        # PHILOSOPHY SLIDERS
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
        # COMPETENCE (1-20)
        "offensive_skill":       competence["offensive_skill"],
        "defensive_skill":       competence["defensive_skill"],
        "player_development":    competence["player_development"],
        "tactics":               competence["tactics"],
        "in_game_adaptability":  competence["in_game_adaptability"],
        "scheme_adaptability":   competence["scheme_adaptability"],
        "recruiting_attraction": competence["recruiting_attraction"],
        "roster_fit":            competence["roster_fit"],
        # ROSTER CONSTRUCTION
        "rotation_size":              rotation_size,
        "slot_strictness":            slot_strictness,
        "rotation_flexibility":       rotation_flexibility,
        "roster_fill_aggressiveness": roster_fill,
        # ROSTER VALUES (1-10)
        "values_athleticism":  roster_values["athleticism"],
        "values_iq":           roster_values["iq"],
        "values_size":         roster_values["size"],
        "values_shooting":     roster_values["shooting"],
        "values_defense":      roster_values["defense"],
        "values_toughness":    roster_values["toughness"],
        "values_role_players": roster_values["role_players"],
        # SEASON STATE
        "seasons_at_program": 0,
        "career_wins":        0,
        "career_losses":      0,
        # CONTRACT (v0.7)
        "contract_years":           contract_yrs,
        "contract_years_remaining": contract_yrs,
        # BREAKOUT TRACKING (v0.6)
        "ncaa_wins_last_3":       0,
        "conf_top_third_last_3":  0,
        "breakout_candidate":     False,
        # Rolling lists for precise 3-season window (v0.7 fix)
        "ncaa_wins_history":      [],   # list of last 3 seasons' NCAA wins
        "conf_finish_history":    [],   # list of last 3 seasons' conf_finish_percentile
    }

    return coach


# -----------------------------------------
# SALARY SYSTEM
# -----------------------------------------

# Base salary by prestige tier (annual, USD)
# These are the midpoints -- actual budgets vary by investment_appetite
_SALARY_BY_PRESTIGE = [
    (95,  8_000_000),
    (79,  4_000_000),
    (59,  2_000_000),
    (39,    900_000),
    (21,    400_000),
    ( 1,    200_000),
]

def _calc_salary_floor(prestige, experience):
    """
    Returns the minimum salary a coach will accept.
    Scales with prestige of last job and experience.
    A coach coming off a $3M job won't take $300K unless desperate.
    """
    base = 200_000
    for threshold, salary in _SALARY_BY_PRESTIGE:
        if prestige >= threshold:
            base = salary
            break
    # Experience modifier: veteran coaches expect more
    exp_mult = 1.0 + min(0.5, experience / 50.0)
    # Floor is 60% of base -- they'll take a discount but not a collapse
    return int(base * 0.60 * exp_mult)


def calc_program_budget(prestige, investment_appetite=5):
    """
    Returns annual basketball coaching budget for a program.
    investment_appetite (1-10) scales the budget within the prestige tier.
    Called by program.py create_program() and ensure_program_budget().
    """
    base = 200_000
    for threshold, salary in _SALARY_BY_PRESTIGE:
        if prestige >= threshold:
            base = salary
            break
    # investment_appetite shifts budget ±40% around the base
    appetite_mult = 0.60 + (investment_appetite / 10.0) * 0.80
    return int(base * appetite_mult)


# -----------------------------------------
# RETIREMENT CHECK
# -----------------------------------------

# Retirement probability curve by age bracket
# (min_age, base_prob_per_season)
_RETIREMENT_AGE_CURVE = [
    (72, 0.35),
    (68, 0.20),
    (63, 0.10),
    (58, 0.04),
    (50, 0.01),
    ( 0, 0.001),   # tiny random factor for everyone -- health, pro jobs, burnout
]

def check_retirement(coach, just_fired=False):
    """
    Returns True if this coach retires this offseason.

    Probabilistic -- no hard age cutoff. Factors:
      - Age (primary driver)
      - Ambition (suppresses retirement -- driven coaches coach longer)
      - Greed (slight suppressor -- money keeps them going)
      - just_fired (bump -- indignity of firing accelerates exit for older coaches)
      - free_agent_seasons (multiple seasons without work = higher exit chance)

    The tiny baseline (0.001) applies to everyone regardless of age --
    simulates pro opportunities, health events, personal decisions.
    """
    age              = coach.get("age", 45)
    ambition         = coach.get("ambition", 10)
    greed            = coach.get("greed", 10)
    free_agent_seasons = coach.get("free_agent_seasons", 0)

    # Base probability from age curve
    base_prob = 0.001
    for min_age, prob in _RETIREMENT_AGE_CURVE:
        if age >= min_age:
            base_prob = prob
            break

    # Ambition suppresses retirement -- scale: ambition 20 = 50% reduction
    ambition_suppress = (ambition / 20.0) * 0.50
    # Greed suppresses slightly -- money keeps them going
    greed_suppress    = (greed / 20.0) * 0.15

    prob = base_prob * (1.0 - ambition_suppress - greed_suppress)

    # Being fired (especially when older) nudges toward retirement
    if just_fired and age >= 55:
        prob += 0.08 + (age - 55) * 0.01

    # Multiple seasons without work -- market has spoken
    if free_agent_seasons >= 3:
        prob += 0.15
    elif free_agent_seasons >= 2:
        prob += 0.07

    return random.random() < max(0.0001, prob)


def update_coach_age(coach):
    """Increments coach age by 1. Called once per season."""
    coach["age"] = coach.get("age", 45) + 1
    # Increment cooldown decay
    cooldown = coach.get("job_change_cooldown", 0)
    if cooldown > 0:
        coach["job_change_cooldown"] = max(0, cooldown - 1)
    # Instability reputation decays slowly
    rep = coach.get("instability_reputation", 0)
    if rep > 0:
        coach["instability_reputation"] = max(0, rep - 5)
    return coach


def record_job_change(coach):
    """
    Records a job change on the coach dict.
    Builds instability_reputation for rapid movers.
    Called by coaching_carousel when a coach is hired.
    """
    cooldown = coach.get("job_change_cooldown", 0)
    # If they moved recently, reputation takes a hit
    if cooldown > 0:
        coach["instability_reputation"] = min(
            100, coach.get("instability_reputation", 0) + 20
        )
    coach["job_change_cooldown"] = 3   # suppresses moving again for 3 seasons
    return coach


def get_age_inertia(coach):
    """
    Returns a multiplier (0.1 - 1.0) representing how willing a coach
    is to uproot and move based on age.
    Young coaches: full willingness (1.0)
    55+: meaningfully reduced
    62+: heavy reduction -- this might be their career job
    70+: very unlikely to move unless massive offer
    """
    age = coach.get("age", 40)
    if age >= 70: return 0.15
    if age >= 65: return 0.30
    if age >= 62: return 0.45
    if age >= 58: return 0.65
    if age >= 55: return 0.80
    return 1.0


def generate_staff(program_name, program_prestige=50):
    """
    Generates a coaching staff of 3 assistants + 1 grad assistant.
    Every staff member has the full coach schema -- same visible ratings
    as head coaches. staff_role distinguishes their position.

    Assistants:
      - Experience 2-15 years (weighted toward lower end)
      - Age derived from experience
      - Prestige used for competence scaling is reduced (they haven't run
        a program yet, so their competence reflects that ceiling)
      - Ambition drives whether they pursue head coaching jobs

    Grad assistant:
      - Age 22-27 explicitly
      - Experience 0-2 years
      - Entry-level competence
      - The pipeline's starting point

    Returns a list of 4 coach dicts.
    """
    from names import generate_coach_name

    staff = []

    # --- 3 ASSISTANTS ---
    for _ in range(3):
        exp         = random.randint(2, 15)
        # Competence scales with program prestige but capped lower than HC
        # An assistant at Kentucky is better than one at Lamar, but neither
        # is as polished as a head coach yet
        asst_prestige = max(20, min(75, program_prestige - random.randint(15, 30)))
        age         = max(25, min(65, 22 + exp + random.randint(0, 8)))
        name        = generate_coach_name()
        coach       = generate_coach(name, prestige=asst_prestige,
                                     experience=exp, age=age)
        coach["staff_role"]       = "assistant"
        coach["seasons_on_staff"] = random.randint(0, min(exp, 5))
        staff.append(coach)

    # --- 1 GRAD ASSISTANT ---
    ga_age  = random.randint(22, 27)
    ga_exp  = random.randint(0, 2)
    ga_name = generate_coach_name()
    ga      = generate_coach(ga_name, prestige=max(15, program_prestige - 40),
                              experience=ga_exp, age=ga_age)
    ga["staff_role"]       = "grad_assistant"
    ga["seasons_on_staff"] = random.randint(0, ga_exp)
    staff.append(ga)

    return staff


def seed_legacy_coach(coach, prestige):
    """
    Seeds pre-sim history for coaches at programs with prestige >= 75.
    Called at world-build after create_program().

    Gives established programs institutional memory -- their coach
    didn't just start yesterday. They have contract protection, career
    history, and some tournament credibility built up.

    prestige: current program prestige (determines seeding depth)
    """
    # Seasons at program: more prestigious = longer tenure seed
    if prestige >= 90:
        seasons = random.randint(5, 8)
    elif prestige >= 80:
        seasons = random.randint(4, 7)
    else:
        seasons = random.randint(3, 6)

    coach["seasons_at_program"] = seasons

    # Career record: expected win% scales with prestige
    expected_win_pct = 0.40 + (prestige / 100.0) * 0.35   # 0.40 at p=0, 0.75 at p=100
    games_per_season = 30
    total_games      = seasons * games_per_season

    career_wins   = int(total_games * expected_win_pct * random.uniform(0.90, 1.10))
    career_losses = total_games - career_wins
    coach["career_wins"]   = max(0, career_wins)
    coach["career_losses"] = max(0, career_losses)
    coach["experience"]    = max(coach["experience"], seasons + random.randint(1, 4))

    # Contract: seed mid-contract (2-4 years remaining)
    contract_remaining = random.randint(2, 4)
    coach["contract_years_remaining"] = contract_remaining

    # Breakout history seed: established programs have some tournament credibility
    if prestige >= 85:
        coach["ncaa_wins_history"]   = [random.randint(0, 2) for _ in range(3)]
        coach["conf_finish_history"] = [random.uniform(0.5, 1.0) for _ in range(3)]
    elif prestige >= 75:
        coach["ncaa_wins_history"]   = [random.randint(0, 1) for _ in range(3)]
        coach["conf_finish_history"] = [random.uniform(0.4, 0.9) for _ in range(3)]

    # Update rolling counts from history
    coach["ncaa_wins_last_3"]      = sum(coach["ncaa_wins_history"])
    coach["conf_top_third_last_3"] = sum(1 for f in coach["conf_finish_history"] if f >= 0.67)

    return coach


def update_coach_buzz_history(coach, ncaa_wins_this_season, conf_finish_percentile):
    """
    Updates rolling 3-season history lists for breakout candidate evaluation.
    Uses precise lists instead of decayed integers -- no rounding errors.
    """
    wins_history   = coach.get("ncaa_wins_history", [])
    finish_history = coach.get("conf_finish_history", [])

    wins_history.append(ncaa_wins_this_season)
    finish_history.append(conf_finish_percentile)

    # Keep only last 3 seasons
    coach["ncaa_wins_history"]   = wins_history[-3:]
    coach["conf_finish_history"] = finish_history[-3:]

    # Update summary counts
    coach["ncaa_wins_last_3"]      = sum(coach["ncaa_wins_history"])
    coach["conf_top_third_last_3"] = sum(
        1 for f in coach["conf_finish_history"] if f >= 0.67
    )


def is_breakout_candidate(coach, program_gravity=50):
    """
    Returns True if coach qualifies as a breakout candidate.
    Requirements (ALL must be met):
      1. At least 1 NCAA win in last 3 seasons (hard gate)
      2. Top-third conference finish in 2+ of last 3 seasons
      3. Avg(recruiting_attraction, tactics, player_development) >= threshold
    """
    ncaa_wins  = coach.get("ncaa_wins_last_3", 0)
    top_thirds = coach.get("conf_top_third_last_3", 0)

    if ncaa_wins < BREAKOUT_MIN_NCAA_WINS:
        return False
    if top_thirds < BREAKOUT_MIN_TOP_THIRD:
        return False

    ratings_avg = (
        coach.get("recruiting_attraction", 10) +
        coach.get("tactics", 10) +
        coach.get("player_development", 10)
    ) / 3.0

    if program_gravity < 25:
        threshold = BREAKOUT_MIN_RATINGS_AVG - 1
    elif program_gravity < 45:
        threshold = BREAKOUT_MIN_RATINGS_AVG
    else:
        threshold = BREAKOUT_MIN_RATINGS_AVG + 1

    return ratings_avg >= threshold


def ensure_coach_carousel_attrs(coach):
    """Migration safety. Adds all v0.5-v0.8 carousel attributes if missing."""
    if "coach_id"           not in coach: coach["coach_id"]           = _next_coach_id()
    if "home_region"        not in coach: coach["home_region"]        = _pick_home_region()
    if "alma_mater"         not in coach: coach["alma_mater"]         = _pick_alma_mater(coach["home_region"])
    if "ambition"           not in coach: coach["ambition"]           = random.randint(6, 14)
    if "rebuild_tolerance"  not in coach: coach["rebuild_tolerance"]  = random.randint(6, 14)
    if "loyalty"            not in coach: coach["loyalty"]            = random.randint(6, 14)
    if "greed"              not in coach: coach["greed"]              = random.randint(6, 14)
    if "job_change_cooldown"    not in coach: coach["job_change_cooldown"]    = 0
    if "instability_reputation" not in coach: coach["instability_reputation"] = 0
    if "salary_current"     not in coach: coach["salary_current"]     = 0
    if "salary_floor"       not in coach:
        coach["salary_floor"] = _calc_salary_floor(
            coach.get("experience", 5) * 5, coach.get("experience", 5))
    if "contract_years"     not in coach: coach["contract_years"]     = 3
    if "contract_years_remaining" not in coach: coach["contract_years_remaining"] = random.randint(1, 3)
    if "ncaa_wins_last_3"       not in coach: coach["ncaa_wins_last_3"]       = 0
    if "conf_top_third_last_3"  not in coach: coach["conf_top_third_last_3"]  = 0
    if "breakout_candidate"     not in coach: coach["breakout_candidate"]     = False
    if "ncaa_wins_history"      not in coach: coach["ncaa_wins_history"]      = []
    if "conf_finish_history"    not in coach: coach["conf_finish_history"]    = []
    if "age"                not in coach:
        exp = coach.get("experience", 10)
        coach["age"] = max(24, min(78, 22 + exp + random.randint(0, 6)))
    if "staff_role"         not in coach: coach["staff_role"]         = "head_coach"
    if "seasons_on_staff"   not in coach: coach["seasons_on_staff"]   = 0
    if "free_agent_seasons" not in coach: coach["free_agent_seasons"] = 0
    return coach


def experience_edge(coach):
    """Returns a subtle tactical edge multiplier (0.97-1.06)."""
    experience = coach.get("experience", 0)
    wins       = coach.get("career_wins", 0)
    losses     = coach.get("career_losses", 0)
    total      = wins + losses
    win_pct    = (wins / total) if total > 0 else 0.500
    exp_factor = min(1.0, experience / 25.0)

    if win_pct >= 0.600:   quality_weight = 1.0
    elif win_pct >= 0.500: quality_weight = 0.5 + (win_pct - 0.500) * 5.0
    elif win_pct >= 0.400: quality_weight = 0.2 + (win_pct - 0.400) * 3.0
    else:                  quality_weight = 0.1

    raw_edge = exp_factor * quality_weight * 0.09
    if experience < 2:
        return max(0.97, 1.0 - 0.03 + raw_edge)
    return min(1.06, 1.0 + raw_edge)


def _generate_competence(template, exp_bonus, prestige_bonus):
    bonus = min(3, exp_bonus + prestige_bonus)
    keys  = ["offensive_skill", "defensive_skill", "player_development", "tactics",
             "in_game_adaptability", "scheme_adaptability", "recruiting_attraction", "roster_fit"]
    return {k: max(1, min(20, int(random.gauss(template.get(k, 11) + bonus, COMPETENCE_NOISE))))
            for k in keys}


def _generate_roster_values(archetype, philosophy):
    def clamp(val): return max(1, min(10, val + random.randint(-1, 2)))
    role_archetypes = ["grinder", "princeton_style", "motion_offense", "post_centric", "zone_specialist"]
    return {
        "athleticism":  clamp(int((philosophy["pace"] + philosophy["personnel"]) / 20)),
        "iq":           clamp(int((philosophy["shot_selection"] + philosophy["ball_movement"]) / 20)),
        "size":         clamp(10 - int(philosophy["personnel"] / 14)),
        "shooting":     clamp(int(philosophy["shot_profile"] / 11)),
        "defense":      clamp(int((philosophy["pressure"] + philosophy["philosophy"]) / 20)),
        "toughness":    clamp(int((philosophy["off_rebounding"] + philosophy["def_rebounding"]) / 20)),
        "role_players": max(1, min(10, (7 if archetype in role_archetypes else 4) + random.randint(-2, 2))),
    }


def calculate_style_fit(player, coach):
    """Calculates how well a player fits a coach's system. Returns 0-100."""
    fit_points = 0
    checks     = 0

    def contrib(player_val, weight):
        return _scale_attr(player_val) * weight

    if coach["pace"] >= 60:
        fit_points += contrib(player.get("speed", 10), coach["pace"] / 100); checks += 1
    if coach["shot_profile"] >= 55:
        avg = (player.get("three_point", 10) + player.get("finishing", 10)) / 2
        fit_points += contrib(avg, coach["shot_profile"] / 100); checks += 1
    if coach["ball_movement"] >= 60:
        avg = (player.get("passing", 10) + player.get("court_vision", 10)) / 2
        fit_points += contrib(avg, coach["ball_movement"] / 100); checks += 1
    if coach["personnel"] >= 65:
        avg = (player.get("ball_handling", 10) + player.get("speed", 10)) / 2
        fit_points += contrib(avg, coach["personnel"] / 100); checks += 1
    if coach["philosophy"] >= 65:
        avg = (player.get("steal_tendency", 10) + player.get("lateral_quickness", 10)) / 2
        fit_points += contrib(avg, coach["philosophy"] / 100); checks += 1
    if coach["off_rebounding"] >= 65 or coach["def_rebounding"] >= 65:
        avg = (player.get("rebounding", 10) + player.get("strength", 10)) / 2
        fit_points += contrib(avg, 1.0); checks += 1
    if coach["shot_profile"] <= 35 and coach["personnel"] <= 35:
        avg = (player.get("post_scoring", 10) + player.get("strength", 10)) / 2
        fit_points += contrib(avg, 1.0); checks += 1

    if checks == 0: return 50
    return max(0, min(100, int((fit_points / checks) * 100)))


if __name__ == "__main__":
    print("=" * 65)
    print("  COACH v0.7 -- CONTRACT + LEGACY SEEDING TEST")
    print("=" * 65)

    from names import generate_coach_name

    test_cases = [
        ("Blue Blood Coach",  95, 9),
        ("Elite Coach",       82, 5),
        ("Mid Major Coach",   55, 4),
        ("Floor Coach",       12, 3),
    ]

    for label, prestige, patience in test_cases:
        name  = generate_coach_name()
        coach = generate_coach(name, prestige=prestige, board_patience=patience)
        print("  {:<20} prestige={:<4} patience={:<3} contract={}yr  remaining={}yr".format(
            label, prestige, patience,
            coach["contract_years"], coach["contract_years_remaining"]))

    print("")
    print("  Legacy seeding test (prestige 90 program):")
    name  = generate_coach_name()
    coach = generate_coach(name, prestige=90)
    seed_legacy_coach(coach, prestige=90)
    print("  seasons_at_program: {}  career: {}-{}  contract_remaining: {}  ncaa_wins_3yr: {}  top_thirds: {}".format(
        coach["seasons_at_program"],
        coach["career_wins"], coach["career_losses"],
        coach["contract_years_remaining"],
        coach["ncaa_wins_last_3"],
        coach["conf_top_third_last_3"],
    ))

    print("")
    print("  Breakout candidate test after good run:")
    update_coach_buzz_history(coach, ncaa_wins_this_season=2, conf_finish_percentile=0.85)
    update_coach_buzz_history(coach, ncaa_wins_this_season=1, conf_finish_percentile=0.90)
    update_coach_buzz_history(coach, ncaa_wins_this_season=0, conf_finish_percentile=0.70)
    coach["recruiting_attraction"] = 14
    coach["tactics"]               = 14
    coach["player_development"]    = 13
    result = is_breakout_candidate(coach, program_gravity=30)
    print("  is_breakout_candidate (low gravity program): " + str(result))
    print("  ncaa_wins_last_3: {}  top_thirds: {}".format(
        coach["ncaa_wins_last_3"], coach["conf_top_third_last_3"]))
