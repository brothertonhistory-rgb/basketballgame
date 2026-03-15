import random
from player import generate_team, get_team_ratings
from coach import generate_coach

# -----------------------------------------
# COLLEGE HOOPS SIM -- Program Database v0.4
# System 6 of the Design Bible
#
# v0.3 CHANGES -- Prestige Stability:
#   Performance multiplier: 3 (was 6). Hard cap: +-4 pts/season.
#   Tournament bonus: +0.5 qualify, +0.75/win (recalibrated).
#
# v0.4 CHANGES -- Conference Tier System:
#   conference_tier_state nested dict on every program.
#   apply_conference_tier_pressure() enforces soft ceiling/floor.
#
#   CEILING: programs above conf ceiling accumulate seasons_above_ceiling.
#     1 season above: -0.3/yr drag
#     2 seasons above: -0.6/yr drag
#     3+ seasons above: -1.0/yr drag (snap-back)
#     Power conferences (ceiling=100) EXEMPT.
#
#   FLOOR: programs below conf floor accumulate seasons_below_floor.
#     1 season below: +0.2/yr lift
#     2 seasons below: +0.4/yr lift
#     3+ seasons below: +0.7/yr lift
#     Conference floor is absolute hard stop.
#
#   Nested state is the pattern for ALL future system state.
# -----------------------------------------

DIVISIONS = ["D1", "D2", "D3", "JUCO"]

PERFORMANCE_MULTIPLIER = 3
SEASON_PRESTIGE_CAP    = 4.0
CEILING_DRAG     = {1: 0.3, 2: 0.6}
CEILING_DRAG_MAX = 1.0
FLOOR_LIFT     = {1: 0.2, 2: 0.4}
FLOOR_LIFT_MAX = 0.7


def _calc_gravity_pull_rate(prestige_gravity):
    """
    Inverted pull rate -- low anchor programs snap back hard.
    High anchor programs (blue bloods) drift back slowly.
    """
    if prestige_gravity < 20:  return 0.15
    if prestige_gravity < 35:  return 0.10
    if prestige_gravity < 50:  return 0.07
    if prestige_gravity < 65:  return 0.05
    if prestige_gravity < 80:  return 0.04
    return 0.03


def recalculate_gravity_pull_rate(program):
    """
    Updates gravity_pull_rate to match current prestige_gravity anchor.
    Call each season after apply_gravity_drift() so pull rate stays
    in sync as anchors move over a multi-decade simulation.
    """
    program["gravity_pull_rate"] = _calc_gravity_pull_rate(
        program["prestige_gravity"]
    )
    return program


def prestige_grade(score):
    if score >= 95: return "BB"   # Blue Blood
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


def create_program(name, nickname, city, state, division, conference,
                   home_court, venue_rating, prestige_current,
                   prestige_gravity, coach_name, coach_archetype=None):

    roster_data = generate_team(name, prestige=prestige_current)
    coach       = generate_coach(coach_name, prestige=prestige_current,
                                 archetype=coach_archetype)

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
        "investment_appetite":   random.randint(1, 10),
        "prestige_sensitivity":  random.randint(1, 10),
        "community_pressure":    random.randint(1, 10),
        "leadership_stability":  random.randint(1, 10),
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
    }


def apply_gravity_pull(program):
    current = program["prestige_current"]
    pull    = (program["prestige_gravity"] - current) * program["gravity_pull_rate"]
    program["prestige_current"] = round(current + pull, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])
    return program


def update_prestige_for_results(program, wins, losses, made_tournament, tournament_wins):
    """
    Updates prestige based on seasonal performance.

    v0.5 CHANGE -- Tier-aware expected win pct and performance multiplier.
    v0.6 CHANGE -- Tiered prestige cap. The ladder gets harder at both ends.

    PRESTIGE CAP BY CURRENT PRESTIGE LEVEL:
      1-20  (floor):        cap 1.5  -- slow climb at the bottom
      21-38 (low_major):    cap 2.5
      39-58 (mid_major):    cap 4.0  -- fastest movement, most room to express
      59-78 (high_major):   cap 3.0
      79-88 (elite lower):  cap 2.0
      89-94 (elite upper):  cap 1.2  -- grind to threaten blue blood
      95+   (blue blood):   cap 0.6  -- barely moves once there

    CONFERENCE TIER determines expected win pct and performance multiplier.
    """
    from programs_data import get_conference_tier
    tier    = get_conference_tier(program["conference"])["tier"]
    current = program["prestige_current"]

    # Tiered season prestige cap -- harder at the top, more movement in the middle
    # Bottom tiers get reasonable movement -- the identity pull handles keeping
    # them down, not the cap. Cap is primarily to slow the elite/blue blood climb.
    if current >= 95:
        season_cap = 0.6
    elif current >= 89:
        season_cap = 1.2
    elif current >= 79:
        season_cap = 2.0
    elif current >= 59:
        season_cap = 3.0
    elif current >= 39:
        season_cap = 4.0
    elif current >= 21:
        season_cap = 3.5
    else:
        season_cap = 2.5

    # Tier-aware expected win pct and multiplier
    if tier == "floor_conf":
        expected_base   = 0.50
        expected_scale  = 0.30
        perf_multiplier = 1.0
        tourn_qualify   = 0.1
        tourn_win       = 0.2
    elif tier == "low_major":
        expected_base   = 0.45
        expected_scale  = 0.35
        perf_multiplier = 1.5
        tourn_qualify   = 0.2
        tourn_win       = 0.4
    elif tier == "mid_major":
        expected_base   = 0.40
        expected_scale  = 0.40
        perf_multiplier = 2.0
        tourn_qualify   = 0.3
        tourn_win       = 0.5
    else:
        # high_major and power
        expected_base   = 0.35
        expected_scale  = 0.45
        perf_multiplier = PERFORMANCE_MULTIPLIER
        tourn_qualify   = 0.5
        tourn_win       = 0.75

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
    """
    Soft ceiling and floor enforcement. Called LAST in prestige pipeline.
    Power conferences (ceiling=100) exempt from ceiling pressure.
    Conference floor is absolute hard stop.
    """
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
    state = program.get("conference_tier_state", {})
    print("\n=== " + program["name"] + " " + program["nickname"] + " ===")
    print("Conference:  " + program["conference"])
    print("Prestige:    " + str(program["prestige_current"]) + " (" + program["prestige_grade"] + ")")
    print("Gravity:     " + str(program["prestige_gravity"]))
    print("Conf limits: ceiling=" + str(get_conference_ceiling(program["conference"])) +
          "  floor=" + str(get_conference_floor(program["conference"])) +
          "  seasons_above=" + str(state.get("seasons_above_ceiling", 0)) +
          "  seasons_below=" + str(state.get("seasons_below_floor", 0)))
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
    print("  CONFERENCE TIER PRESSURE TESTS")
    print("="*60)

    print("\n--- SWAC Dynasty (ceiling=40): 10 dominant seasons ---")
    swac = programs[3]
    swac["prestige_current"] = 35
    swac["prestige_gravity"] = 18
    print("  {:<10} {:<10} {:<8} {:<8}".format("Season","Prestige","Grade","Above"))
    print("  " + "-"*36)
    for yr in range(1, 11):
        update_prestige_for_results(swac, 26, 4, True, 2)
        apply_gravity_pull(swac)
        apply_conference_tier_pressure(swac)
        state = swac["conference_tier_state"]
        print("  {:<10} {:<10} {:<8} {:<8}".format(
            "Year "+str(yr), str(swac["prestige_current"]),
            swac["prestige_grade"], str(state["seasons_above_ceiling"])))

    print("\n--- WCC Ceiling (Gonzaga, ceiling=85): 10 dominant seasons ---")
    gonz = programs[1]
    gonz["prestige_current"] = 78
    gonz["prestige_gravity"] = 72
    print("  {:<10} {:<10} {:<8} {:<8}".format("Season","Prestige","Grade","Above"))
    print("  " + "-"*36)
    for yr in range(1, 11):
        update_prestige_for_results(gonz, 28, 6, True, 2)
        apply_gravity_pull(gonz)
        apply_conference_tier_pressure(gonz)
        state = gonz["conference_tier_state"]
        print("  {:<10} {:<10} {:<8} {:<8}".format(
            "Year "+str(yr), str(gonz["prestige_current"]),
            gonz["prestige_grade"], str(state["seasons_above_ceiling"])))

    print("\n--- MVC Floor (Drake, floor=20): 10 terrible seasons ---")
    drake = programs[2]
    drake["prestige_current"] = 54
    drake["prestige_gravity"] = 52
    print("  {:<10} {:<10} {:<8} {:<8}".format("Season","Prestige","Grade","Below"))
    print("  " + "-"*36)
    for yr in range(1, 11):
        update_prestige_for_results(drake, 6, 26, False, 0)
        apply_gravity_pull(drake)
        apply_conference_tier_pressure(drake)
        state = drake["conference_tier_state"]
        print("  {:<10} {:<10} {:<8} {:<8}".format(
            "Year "+str(yr), str(drake["prestige_current"]),
            drake["prestige_grade"], str(state["seasons_below_floor"])))

    print("\n--- Power conference: No ceiling (Kentucky/SEC) ---")
    ky = programs[0]
    ky["prestige_current"] = 92
    ky["prestige_gravity"] = 90
    print("  {:<10} {:<10} {:<8}".format("Season","Prestige","Grade"))
    print("  " + "-"*28)
    for yr in range(1, 11):
        update_prestige_for_results(ky, 32, 4, True, 4)
        apply_gravity_pull(ky)
        apply_conference_tier_pressure(ky)
        print("  {:<10} {:<10} {:<8}".format(
            "Year "+str(yr), str(ky["prestige_current"]), ky["prestige_grade"]))
