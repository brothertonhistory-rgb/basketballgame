import random
from player import generate_team, get_team_ratings
from coach import generate_coach

# -----------------------------------------
# COLLEGE HOOPS SIM -- Program Database v0.6
# System 6 of the Design Bible
#
# v0.6 CHANGES -- Coaching Carousel Infrastructure:
#
#   NEW program attributes for carousel system (all nested in "carousel_state"):
#
#   board_patience (1-10):
#     Derived from investment_appetite, prestige_sensitivity,
#     community_pressure, leadership_stability.
#     High = impatient board. Blue bloods always high.
#     Determines effective firing threshold (low patience = fired earlier).
#
#   stale_meter (0-100):
#     Only meaningful for floor_conf and low_major programs.
#     Increments when program finishes bottom half of conference.
#     Partially resets on winning conference season or notable tournament run.
#     When stale_meter hits 100, firing threshold drops even if job_security
#     is in the 30-40 range -- the "same old losing" effect.
#
#   coaching_capital (float):
#     Tournament success reserve that buffers job_security.
#     Final Four: +2.0. Championship: +3.0.
#     Gravity-relative: low-gravity programs get more capital per deep run.
#     First championship ever at a program: +4.0 bonus.
#     Decays 1.0 per season naturally.
#     Capital absorbs bad-season security erosion before job_security bleeds.
#
#   ad_hiring_profile (string):
#     Permanent institutional hiring philosophy.
#     "veteran_preferred"   -- wants 10+ year coaches, won't gamble on first-timers
#     "pedigree_seeker"     -- wants coaches from winning programs
#     "analytics_forward"   -- open to young coaches, values scheme fit
#     "hometown_loyalty"    -- prioritizes regional ties and alma mater connections
#     "opportunist"         -- no preference, takes best available
#
# v0.5 CHANGES (preserved):
#   Tournament buzz system.
#
# v0.4 CHANGES (preserved):
#   conference_tier_state nested dict.
# -----------------------------------------

DIVISIONS = ["D1", "D2", "D3", "JUCO"]

PERFORMANCE_MULTIPLIER = 3
SEASON_PRESTIGE_CAP    = 4.0
CEILING_DRAG     = {1: 0.3, 2: 0.6}
CEILING_DRAG_MAX = 1.0
FLOOR_LIFT     = {1: 0.2, 2: 0.4}
FLOOR_LIFT_MAX = 0.7

# AD hiring profiles -- distributed at world build
_AD_PROFILES      = ["veteran_preferred", "pedigree_seeker", "analytics_forward",
                     "hometown_loyalty", "opportunist"]
_AD_PROFILE_WEIGHTS = [25, 20, 20, 15, 20]

# Stale meter thresholds -- only applied to floor_conf and low_major
STALE_CONF_TIERS = {"floor_conf", "low_major"}
STALE_METER_MAX  = 100
STALE_INCREMENT  = 18   # bottom-half finish: +18 per season
STALE_RESET_WIN  = 35   # winning conf season: -35
STALE_RESET_TOURNEY = 20  # tournament appearance: -20

# Coaching capital -- how much deep runs protect a coach
CAPITAL_DECAY_PER_SEASON = 1.0
CAPITAL_MAX              = 12.0

# Firing thresholds by board patience tier
# job_security must drop BELOW this value to trigger firing
# High patience = lower threshold (harder to fire)
# Low patience  = higher threshold (easier to fire)
_FIRING_THRESHOLD_BASE = 25   # default: fired below 25

def _calc_gravity_pull_rate(prestige_gravity):
    if prestige_gravity < 20:  return 0.15
    if prestige_gravity < 35:  return 0.10
    if prestige_gravity < 50:  return 0.07
    if prestige_gravity < 65:  return 0.05
    if prestige_gravity < 80:  return 0.04
    return 0.03


def recalculate_gravity_pull_rate(program):
    program["gravity_pull_rate"] = _calc_gravity_pull_rate(
        program["prestige_gravity"]
    )
    return program


def prestige_grade(score):
    if score >= 95: return "BB"
    if score >= 88: return "A+"
    if score >= 82: return "A"
    if score >= 76: return "A-"
    if score >= 70: return "B+"
    if score >= 64: return "B"
    if score >= 58: return "B-"
    if score >= 52: return "C+"
    if score >= 46: return "C"
    if score >= 40: return "C-"
    if score >= 34: return "D+"
    if score >= 28: return "D"
    if score >= 22: return "D-"
    return "F"


def _derive_board_patience(investment_appetite, prestige_sensitivity,
                           community_pressure, leadership_stability, prestige):
    """
    Derives board_patience (1-10) from institutional attributes.
    High = impatient board (fires coaches faster).
    Blue bloods get forced minimum of 7.

    investment_appetite:  high = more $ invested = less tolerant of failure
    prestige_sensitivity: high = brand-conscious = impatient
    community_pressure:   high = vocal fanbase = more pressure on results
    leadership_stability: INVERTED -- stable leadership is patient leadership
    prestige:             blue blood programs (95+) always have high expectations
    """
    raw = (
        (investment_appetite  / 10.0) * 0.25 +
        (prestige_sensitivity / 10.0) * 0.30 +
        (community_pressure   / 10.0) * 0.30 +
        ((10 - leadership_stability) / 10.0) * 0.15
    )
    base = max(1, min(10, round(raw * 10)))

    # Blue bloods always impatient
    if prestige >= 95:
        base = max(7, base)
    elif prestige >= 79:
        base = max(5, base)

    return base


def _pick_ad_profile():
    return random.choices(_AD_PROFILES, weights=_AD_PROFILE_WEIGHTS, k=1)[0]


def _init_carousel_state(prestige):
    """Returns a fresh carousel_state dict."""
    return {
        "board_patience":  5,          # set properly in create_program
        "stale_meter":     0,
        "coaching_capital": 0.0,
        "ad_hiring_profile": "opportunist",
        "first_championship": False,   # has this program ever won a title
        "firing_reason":   None,       # last reason a coach was fired (for reporting)
        "last_hire_year":  None,
    }


def _init_tournament_buzz():
    return {
        "current":       0.0,
        "peak":          0.0,
        "last_result":   "none",
        "last_year":     None,
        "consecutive_appearances": 0,
        "deep_run_memory": 0.0,
    }


def create_program(name, nickname, city, state, division, conference,
                   home_court, venue_rating, prestige_current,
                   prestige_gravity, coach_name, coach_archetype=None):

    roster_data = generate_team(name, prestige=prestige_current)
    coach       = generate_coach(coach_name, prestige=prestige_current,
                                 archetype=coach_archetype)

    invest   = random.randint(1, 10)
    pres_sen = random.randint(1, 10)
    comm_p   = random.randint(1, 10)
    lead_s   = random.randint(1, 10)

    board_patience = _derive_board_patience(
        invest, pres_sen, comm_p, lead_s, prestige_current
    )

    carousel = _init_carousel_state(prestige_current)
    carousel["board_patience"]   = board_patience
    carousel["ad_hiring_profile"] = _pick_ad_profile()

    return {
        "name":         name,
        "nickname":     nickname,
        "city":         city,
        "state":        state,
        "division":     division,
        "conference":   conference,
        "home_court":   home_court,
        "venue_rating": venue_rating,
        "prestige_current":    prestige_current,
        "prestige_gravity":    prestige_gravity,
        "prestige_grade":      prestige_grade(prestige_current),
        "gravity_pull_rate":   _calc_gravity_pull_rate(prestige_gravity),
        "coach_name":    coach_name,
        "coach_seasons": 0,
        "coach":         coach,
        "investment_appetite":   invest,
        "prestige_sensitivity":  pres_sen,
        "community_pressure":    comm_p,
        "leadership_stability":  lead_s,
        "job_security": 75,
        "wins":        0,
        "losses":      0,
        "conf_wins":   0,
        "conf_losses": 0,
        "season_results": [],
        "roster": roster_data["roster"],
        "season_history": [],
        # System state nested by design -- never flat
        "conference_tier_state": {
            "seasons_above_ceiling": 0,
            "seasons_below_floor":   0,
            "conference_ceiling":    None,
            "conference_floor":      None,
        },
        # Tournament buzz -- separate from prestige_current
        "tournament_buzz": _init_tournament_buzz(),
        # Coaching carousel state -- nested
        "carousel_state": carousel,
    }


# -----------------------------------------
# CAROUSEL STATE HELPERS
# -----------------------------------------

def ensure_carousel_state(program):
    """Migration safety. Adds carousel_state to any existing program dict."""
    if "carousel_state" not in program:
        prestige = program.get("prestige_current", 50)
        invest   = program.get("investment_appetite", 5)
        pres_sen = program.get("prestige_sensitivity", 5)
        comm_p   = program.get("community_pressure", 5)
        lead_s   = program.get("leadership_stability", 5)

        carousel = _init_carousel_state(prestige)
        carousel["board_patience"]   = _derive_board_patience(
            invest, pres_sen, comm_p, lead_s, prestige
        )
        carousel["ad_hiring_profile"] = _pick_ad_profile()
        program["carousel_state"] = carousel

    # Ensure all keys exist
    defaults = _init_carousel_state(program.get("prestige_current", 50))
    for key, val in defaults.items():
        if key not in program["carousel_state"]:
            program["carousel_state"][key] = val

    return program


def get_firing_threshold(program):
    """
    Returns the job_security level at which this program fires a coach.
    Base is 25. High board_patience programs fire at lower security levels
    (more impatient = pull trigger earlier at higher security numbers).

    board_patience 1-3:  threshold 20 (patient board, hard to fire)
    board_patience 4-6:  threshold 25 (default)
    board_patience 7-8:  threshold 32 (impatient)
    board_patience 9-10: threshold 40 (very impatient -- blue blood tier)
    """
    ensure_carousel_state(program)
    patience = program["carousel_state"]["board_patience"]

    if patience >= 9:   return 40
    if patience >= 7:   return 32
    if patience >= 4:   return 25
    return 20


def update_stale_meter(program, conf_finish_percentile, made_tournament):
    """
    Updates stale_meter for floor_conf and low_major programs only.
    Called each season after the conference season resolves.

    conf_finish_percentile: 0.0 (last) to 1.0 (first)
    made_tournament: bool
    """
    from programs_data import get_conference_tier
    ensure_carousel_state(program)

    tier = get_conference_tier(program["conference"])["tier"]
    if tier not in STALE_CONF_TIERS:
        return program

    carousel = program["carousel_state"]
    meter    = carousel.get("stale_meter", 0)

    # Bottom half of conference = stale increment
    if conf_finish_percentile < 0.50:
        meter = min(STALE_METER_MAX, meter + STALE_INCREMENT)

    # Winning conference season = partial reset
    if conf_finish_percentile >= 0.65:
        meter = max(0, meter - STALE_RESET_WIN)

    # Tournament appearance = partial reset
    if made_tournament:
        meter = max(0, meter - STALE_RESET_TOURNEY)

    carousel["stale_meter"] = meter
    return program


def update_coaching_capital(program, tournament_result, season_year):
    """
    Awards coaching capital based on tournament performance.
    Called after the NCAA tournament resolves each season.
    Capital decays 1.0 per season regardless.

    Gravity-relative: lower-gravity programs earn more capital per deep run.
    First-ever championship earns a permanent +4.0 bonus.
    """
    ensure_carousel_state(program)
    carousel = program["carousel_state"]
    gravity  = program["prestige_gravity"]
    capital  = carousel.get("coaching_capital", 0.0)

    # Decay first
    capital = max(0.0, capital - CAPITAL_DECAY_PER_SEASON)

    # Gravity multiplier -- same logic as tournament buzz
    if gravity >= 90:    mult = 0.3
    elif gravity >= 75:  mult = 0.5
    elif gravity >= 55:  mult = 0.8
    elif gravity >= 35:  mult = 1.3
    elif gravity >= 20:  mult = 1.8
    else:                mult = 2.5

    # Capital award by result
    capital_award = {
        "final_four": 2.0,
        "champion":   3.0,
    }

    result_capital = capital_award.get(tournament_result, 0.0)
    if result_capital > 0.0:
        earned = round(result_capital * mult, 2)

        # First championship bonus
        if (tournament_result == "champion" and
                not carousel.get("first_championship", False)):
            earned += 4.0
            carousel["first_championship"] = True

        capital = min(CAPITAL_MAX, capital + earned)

    carousel["coaching_capital"] = round(capital, 2)
    return program


# -----------------------------------------
# TOURNAMENT BUZZ SYSTEM
# -----------------------------------------

_RESULT_RANK = {
    "none":       0,
    "r64":        1,
    "r32":        2,
    "sweet_16":   3,
    "elite_8":    4,
    "final_four": 5,
    "champion":   6,
}

_BUZZ_BASE = {
    "r64":        0.1,
    "r32":        0.3,
    "sweet_16":   1.0,
    "elite_8":    2.5,
    "final_four": 5.0,
    "champion":   8.0,
}

_DEEP_RUN_RESULTS    = {"final_four", "champion"}
_DEEP_RUN_LINGER_RATE = 0.5


def get_effective_prestige(program):
    buzz = program.get("tournament_buzz", {}).get("current", 0.0)
    return min(100.0, program["prestige_current"] + buzz)


def ensure_tournament_buzz(program):
    if "tournament_buzz" not in program:
        program["tournament_buzz"] = _init_tournament_buzz()
    else:
        defaults = _init_tournament_buzz()
        for key, val in defaults.items():
            if key not in program["tournament_buzz"]:
                program["tournament_buzz"][key] = val
    return program


def apply_tournament_buzz(program, result, season_year):
    ensure_tournament_buzz(program)
    buzz    = program["tournament_buzz"]
    gravity = program["prestige_gravity"]

    base = _BUZZ_BASE.get(result, 0.0)
    if base == 0.0:
        return program

    if gravity >= 90:    mult = 0.3
    elif gravity >= 75:  mult = 0.5
    elif gravity >= 55:  mult = 0.8
    elif gravity >= 35:  mult = 1.3
    elif gravity >= 20:  mult = 1.8
    else:                mult = 2.5

    buzz_earned = round(base * mult, 2)

    buzz["current"]   = round(buzz["current"] + buzz_earned, 2)
    buzz["peak"]      = round(max(buzz["peak"], buzz["current"]), 2)
    buzz["last_result"] = result
    buzz["last_year"]   = season_year
    buzz["consecutive_appearances"] += 1

    if result in _DEEP_RUN_RESULTS:
        buzz["deep_run_memory"] = round(
            buzz.get("deep_run_memory", 0.0) + buzz_earned * 0.3, 2
        )

    return program


def apply_buzz_decay(program, made_tournament, tournament_result, season_year):
    ensure_tournament_buzz(program)
    buzz    = program["tournament_buzz"]
    current = buzz["current"]

    if current <= 0.0:
        return program

    if not made_tournament:
        buzz["consecutive_appearances"] = 0
        base_decay = 0.60
    else:
        result_rank = _RESULT_RANK.get(tournament_result, 0)
        if result_rank <= 1:   base_decay = 0.20
        elif result_rank == 2: base_decay = 0.10
        elif result_rank == 3: base_decay = 0.05
        else:                  base_decay = 0.02

    memory_reduction = min(0.40, buzz.get("deep_run_memory", 0.0) * 0.05)
    effective_decay  = max(0.0, base_decay - memory_reduction)

    if buzz.get("last_result") in _DEEP_RUN_RESULTS and not made_tournament:
        effective_decay *= _DEEP_RUN_LINGER_RATE

    decay_amount    = round(current * effective_decay, 2)
    buzz["current"] = round(max(0.0, current - decay_amount), 2)

    if buzz.get("deep_run_memory", 0.0) > 0:
        buzz["deep_run_memory"] = round(
            max(0.0, buzz["deep_run_memory"] - 0.1), 2
        )


def apply_gravity_pull(program):
    current = program["prestige_current"]
    pull    = (program["prestige_gravity"] - current) * program["gravity_pull_rate"]
    program["prestige_current"] = round(current + pull, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])
    return program


def update_prestige_for_results(program, wins, losses, made_tournament, tournament_wins):
    from programs_data import get_conference_tier
    tier    = get_conference_tier(program["conference"])["tier"]
    current = program["prestige_current"]

    if current >= 95:   season_cap = 0.6
    elif current >= 89: season_cap = 1.2
    elif current >= 79: season_cap = 2.0
    elif current >= 59: season_cap = 3.0
    elif current >= 39: season_cap = 4.0
    elif current >= 21: season_cap = 3.5
    else:               season_cap = 2.5

    if tier == "floor_conf":
        expected_base = 0.50; expected_scale = 0.30
        perf_multiplier = 1.0; tourn_qualify = 0.1; tourn_win = 0.2
    elif tier == "low_major":
        expected_base = 0.45; expected_scale = 0.35
        perf_multiplier = 1.5; tourn_qualify = 0.2; tourn_win = 0.4
    elif tier == "mid_major":
        expected_base = 0.40; expected_scale = 0.40
        perf_multiplier = 2.0; tourn_qualify = 0.3; tourn_win = 0.5
    else:
        expected_base = 0.35; expected_scale = 0.45
        perf_multiplier = PERFORMANCE_MULTIPLIER
        tourn_qualify = 0.5; tourn_win = 0.75

    games = wins + losses

    if games > 0:
        win_pct           = wins / games
        expected_win_pct  = expected_base + (current / 100) * expected_scale
        performance_delta = (win_pct - expected_win_pct) * perf_multiplier
    else:
        performance_delta = 0

    tournament_bonus = 0
    if made_tournament:
        tournament_bonus += tourn_qualify
        tournament_bonus += tournament_wins * tourn_win

    total_delta  = max(-season_cap, min(season_cap, performance_delta + tournament_bonus))
    new_prestige = max(1, min(100, current + total_delta))
    program["prestige_current"] = round(new_prestige, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])
    return program


def apply_conference_tier_pressure(program):
    from programs_data import get_conference_tier

    current = program["prestige_current"]
    tier    = get_conference_tier(program["conference"])
    ceiling = tier["ceiling"]
    floor   = tier["floor"]

    if "conference_tier_state" not in program:
        program["conference_tier_state"] = {
            "seasons_above_ceiling": 0,
            "seasons_below_floor":   0,
            "conference_ceiling":    ceiling,
            "conference_floor":      floor,
        }

    state = program["conference_tier_state"]
    state["conference_ceiling"] = ceiling
    state["conference_floor"]   = floor

    adjustment = 0.0

    if ceiling < 100 and current > ceiling:
        state["seasons_above_ceiling"] += 1
        n = state["seasons_above_ceiling"]
        adjustment -= CEILING_DRAG_MAX if n >= 3 else CEILING_DRAG.get(n, CEILING_DRAG_MAX)
    else:
        state["seasons_above_ceiling"] = 0

    if current < floor:
        state["seasons_below_floor"] += 1
        n = state["seasons_below_floor"]
        adjustment += FLOOR_LIFT_MAX if n >= 3 else FLOOR_LIFT.get(n, FLOOR_LIFT_MAX)
    else:
        state["seasons_below_floor"] = 0

    if adjustment == 0.0:
        return program

    new_prestige = max(floor, min(100, current + adjustment))
    program["prestige_current"] = round(new_prestige, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])
    return program


def record_game_result(program, opponent_name, points_for, points_against, is_home, is_conference):
    won = points_for > points_against
    program["season_results"].append({
        "opponent": opponent_name, "points_for": points_for,
        "points_against": points_against, "won": won,
        "is_home": is_home, "is_conference": is_conference,
    })
    if won:
        program["wins"] += 1
        if is_conference: program["conf_wins"] += 1
    else:
        program["losses"] += 1
        if is_conference: program["conf_losses"] += 1
    return program


def get_record_string(program):
    return (str(program["wins"]) + "-" + str(program["losses"]) +
            " (" + str(program["conf_wins"]) + "-" + str(program["conf_losses"]) + ")")


def print_program_summary(program):
    from programs_data import get_conference_ceiling, get_conference_floor
    state    = program.get("conference_tier_state", {})
    carousel = program.get("carousel_state", {})
    print("\n=== " + program["name"] + " " + program["nickname"] + " ===")
    print("Conference:  " + program["conference"])
    print("Prestige:    " + str(program["prestige_current"]) + " (" + program["prestige_grade"] + ")")
    print("Gravity:     " + str(program["prestige_gravity"]))
    print("Board pat:   " + str(carousel.get("board_patience", "?")) + "/10" +
          "  AD profile: " + carousel.get("ad_hiring_profile", "?"))
    print("Stale meter: " + str(carousel.get("stale_meter", 0)) + "/100" +
          "  Capital: " + str(carousel.get("coaching_capital", 0.0)))
    print("Job security:" + str(program.get("job_security", 75)) +
          "  Fire threshold: " + str(get_firing_threshold(program)))
    print("Conf limits: ceiling=" + str(get_conference_ceiling(program["conference"])) +
          "  floor=" + str(get_conference_floor(program["conference"])))
    print("Record:      " + get_record_string(program))


def build_sample_programs():
    programs = []
    programs.append(create_program("Kentucky","Wildcats","Lexington","KY","D1","SEC","Rupp Arena",97,92,90,"Coach Cal"))
    programs.append(create_program("Gonzaga","Bulldogs","Spokane","WA","D1","WCC","McCarthey Athletic Center",82,78,72,"Coach Few"))
    programs.append(create_program("Drake","Bulldogs","Des Moines","IA","D1","Missouri Valley","Knapp Center",61,54,52,"Coach Johnson"))
    programs.append(create_program("Alabama State","Hornets","Montgomery","AL","D1","SWAC","Dunn-Oliver Acadome",38,20,18,"Coach Thompson"))
    return programs


if __name__ == "__main__":
    programs = build_sample_programs()
    for p in programs:
        print_program_summary(p)

    print("\n" + "="*60)
    print("  BOARD PATIENCE + FIRING THRESHOLD TEST")
    print("="*60)
    for p in programs:
        cs = p["carousel_state"]
        print("  {:<20} patience: {}/10  threshold: {}  AD: {}".format(
            p["name"],
            cs["board_patience"],
            get_firing_threshold(p),
            cs["ad_hiring_profile"],
        ))

    print("\n" + "="*60)
    print("  STALE METER TEST -- 8 seasons of losing at floor_conf")
    print("="*60)
    swac = programs[3]
    for yr in range(1, 9):
        update_stale_meter(swac, conf_finish_percentile=0.20, made_tournament=False)
        print("  Season {}: stale_meter={}".format(
            yr, swac["carousel_state"]["stale_meter"]))

    print("\n" + "="*60)
    print("  COACHING CAPITAL TEST -- Final Four run at low-gravity program")
    print("="*60)
    drake = programs[2]
    drake["prestige_gravity"] = 52
    update_coaching_capital(drake, "final_four", 2025)
    print("  Drake Final Four capital: {}".format(
        drake["carousel_state"]["coaching_capital"]))
    update_coaching_capital(drake, "champion", 2026)
    print("  Drake Championship capital (first ever): {}".format(
        drake["carousel_state"]["coaching_capital"]))
