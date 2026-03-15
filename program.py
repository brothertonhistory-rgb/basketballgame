import random
from player import generate_team, get_team_ratings
from coach import generate_coach

# -----------------------------------------
# COLLEGE HOOPS SIM -- Program Database v0.5
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
# v0.5 CHANGES -- Gravity Pull Rate Overhaul:
#
#   OLD BEHAVIOR (wrong): Low anchor = weakest pull (0.03).
#     This meant floor-tier programs that spiked up barely felt
#     any force pulling them back down. A SWAC team that had a
#     great season drifted upward and stayed there.
#
#   NEW BEHAVIOR (correct): Low anchor = strongest pull.
#     Rock bottom programs snap back hard if they spike up.
#     Blue blood programs (high anchor) drift back slowly --
#     they have institutional gravity that lets them coast
#     through a few bad seasons before snapping back.
#
#   PULL RATE TABLE (by prestige_gravity):
#     anchor < 20:  0.15  -- rock bottom, very strong snap-back
#     anchor < 35:  0.10  -- floor tier, strong pull
#     anchor < 50:  0.07  -- low major range
#     anchor < 65:  0.05  -- mid major range
#     anchor < 80:  0.04  -- high major range
#     anchor >= 80: 0.03  -- blue blood, slow drift back
#
#   recalculate_gravity_pull_rate() is now called every season
#   after apply_gravity_drift() so pull rate stays in sync
#   with the anchor as it moves over time.
#
#   DESIGN NOTE: The pull rate acts on the gap between
#   prestige_current and prestige_gravity. A floor program at
#   prestige 8 that spikes to 25 has a gap of 17. With pull
#   rate 0.15, that's -2.55 per season -- they fall back fast.
#   A Duke at prestige 85 with gravity 90 has a gap of -5.
#   With pull rate 0.03, that's +0.15 per season -- slow recovery,
#   which is correct. Duke's AD hires a good coach long before
#   gravity does all the work.
# -----------------------------------------

DIVISIONS = ["D1", "D2", "D3", "JUCO"]

PERFORMANCE_MULTIPLIER = 3
SEASON_PRESTIGE_CAP    = 4.0
CEILING_DRAG     = {1: 0.3, 2: 0.6}
CEILING_DRAG_MAX = 1.0
FLOOR_LIFT     = {1: 0.2, 2: 0.4}
FLOOR_LIFT_MAX = 0.7


def prestige_grade(score):
    if score >= 95: return "A+"
    if score >= 88: return "A"
    if score >= 82: return "A-"
    if score >= 76: return "B+"
    if score >= 70: return "B"
    if score >= 64: return "B-"
    if score >= 58: return "C+"
    if score >= 52: return "C"
    if score >= 46: return "C-"
    if score >= 40: return "D+"
    if score >= 34: return "D"
    if score >= 28: return "D-"
    return "F"


def _calc_gravity_pull_rate(prestige_gravity):
    """
    Inverted pull rate -- low anchor programs snap back hard.
    High anchor programs (blue bloods) drift back slowly.

    This reflects reality: a SWAC team that has one good year
    is still a SWAC team. Duke having three bad years is still Duke --
    but the AD will act long before gravity does all the work.
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
    Call this each season after apply_gravity_drift() so the pull rate
    stays in sync as anchors move over a multi-decade simulation.
    """
    program["gravity_pull_rate"] = _calc_gravity_pull_rate(
        program["prestige_gravity"]
    )
    return program


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
    current = program["prestige_current"]
    games   = wins + losses
    if games > 0:
        win_pct           = wins / games
        expected_win_pct  = 0.35 + (current / 100) * 0.45
        performance_delta = (win_pct - expected_win_pct) * PERFORMANCE_MULTIPLIER
    else:
        performance_delta = 0

    tournament_bonus = 0
    if made_tournament:
        tournament_bonus += 0.5
        tournament_bonus += tournament_wins * 0.75

    total_delta = max(-SEASON_PRESTIGE_CAP, min(SEASON_PRESTIGE_CAP,
                      performance_delta + tournament_bonus))
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
    print("Gravity:     " + str(program["prestige_gravity"]) +
          "  pull_rate: " + str(program["gravity_pull_rate"]))
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

    print("=== PULL RATE VERIFICATION ===")
    print("Confirming inverted pull rates at world-build:")
    print("")
    for p in programs:
        print("  {:<20} gravity: {:>4}  pull_rate: {}".format(
            p["name"], p["prestige_gravity"], p["gravity_pull_rate"]))

    print("")
    print("=== SNAP-BACK TEST ===")
    print("SWAC team (gravity=18) spikes to 35 -- how fast do they fall?")
    print("")
    swac = programs[3]
    swac["prestige_current"] = 35
    swac["prestige_gravity"] = 18
    print("  {:<10} {:<10} {:<10}".format("Season", "Prestige", "Pull Rate"))
    print("  " + "-" * 30)
    for yr in range(1, 8):
        apply_gravity_pull(swac)
        recalculate_gravity_pull_rate(swac)
        print("  {:<10} {:<10} {:<10}".format(
            "Year " + str(yr),
            str(swac["prestige_current"]),
            str(swac["gravity_pull_rate"])))

    print("")
    print("=== BLUE BLOOD COAST TEST ===")
    print("Kentucky (gravity=90) drops to 70 -- how slowly do they recover?")
    print("")
    ky = programs[0]
    ky["prestige_current"] = 70
    ky["prestige_gravity"] = 90
    print("  {:<10} {:<10} {:<10}".format("Season", "Prestige", "Pull Rate"))
    print("  " + "-" * 30)
    for yr in range(1, 8):
        apply_gravity_pull(ky)
        recalculate_gravity_pull_rate(ky)
        print("  {:<10} {:<10} {:<10}".format(
            "Year " + str(yr),
            str(ky["prestige_current"]),
            str(ky["gravity_pull_rate"])))

    print("")
    print("=== CONFERENCE TIER PRESSURE TESTS ===")

    print("\n--- SWAC Dynasty (ceiling=40): 10 dominant seasons ---")
    swac = programs[3]
    swac["prestige_current"] = 35
    swac["prestige_gravity"] = 18
    print("  {:<10} {:<10} {:<8} {:<8}".format("Season","Prestige","Grade","Above"))
    print("  " + "-"*36)
    for yr in range(1, 11):
        update_prestige_for_results(swac, 26, 4, True, 2)
        apply_gravity_pull(swac)
        recalculate_gravity_pull_rate(swac)
        apply_conference_tier_pressure(swac)
        state = swac["conference_tier_state"]
        print("  {:<10} {:<10} {:<8} {:<8}".format(
            "Year "+str(yr), str(swac["prestige_current"]),
            swac["prestige_grade"], str(state["seasons_above_ceiling"])))

    print("\n--- Power conference: No ceiling (Kentucky/SEC) ---")
    ky = programs[0]
    ky["prestige_current"] = 92
    ky["prestige_gravity"] = 90
    print("  {:<10} {:<10} {:<8}".format("Season","Prestige","Grade"))
    print("  " + "-"*28)
    for yr in range(1, 11):
        update_prestige_for_results(ky, 32, 4, True, 4)
        apply_gravity_pull(ky)
        recalculate_gravity_pull_rate(ky)
        apply_conference_tier_pressure(ky)
        print("  {:<10} {:<10} {:<8}".format(
            "Year "+str(yr), str(ky["prestige_current"]), ky["prestige_grade"]))
