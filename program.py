import random
from player import generate_team, get_team_ratings
from coach import generate_coach

# -----------------------------------------
# COLLEGE HOOPS SIM -- Program Database v0.3
# System 6 of the Design Bible
# Defines what a program IS -- persistent across seasons
#
# v0.3 CHANGES -- Prestige Stability Overhaul:
#
#   CHANGE 1: Performance multiplier reduced from 6 to 3.
#     A wildly overperforming season now moves prestige ~1.5 points
#     before gravity, not ~3. Single seasons should not reshape programs.
#
#   CHANGE 2: Hard cap of ±4 points total per season.
#     No program can gain or lose more than 4 prestige points in one
#     season regardless of performance or tournament results.
#     Collapses are symmetric -- they should compound over multiple
#     bad years, not crater after one.
#
#   CHANGE 3: Tournament bonus recalibrated.
#     Making the conference tournament threshold now gives +0.5 (was +2).
#     Each tournament win gives +0.75 (was +1.5).
#     These are included in the ±4 cap.
#     Rationale: in the current sim, "made_tournament" fires for roughly
#     half the conference, making it a normal event. It should not be a
#     major prestige lever until a real postseason exists.
#
#   NOTE: apply_gravity_drift() (the anchor drift logic) lives in
#   season.py and was also slowed there. See season.py v0.5 notes.
# -----------------------------------------

DIVISIONS = ["D1", "D2", "D3", "JUCO"]

CONFERENCES = {
    "D1": [
        "ACC", "Big Ten", "Big 12", "SEC", "Pac-10",
        "Big East", "AAC", "Mountain West", "WCC",
        "Missouri Valley", "Atlantic 10", "Conference USA",
        "Sun Belt", "MAC", "WAC", "Horizon", "Patriot",
        "Colonial", "Big South", "Southland", "SWAC", "MEAC",
        "Independent"
    ],
    "D2": ["D2 Central", "D2 East", "D2 West", "D2 South"],
    "D3": ["D3 North", "D3 South", "D3 East", "D3 West"],
    "JUCO": ["JUCO Region 1", "JUCO Region 2", "JUCO Region 3"],
}

# -----------------------------------------
# PRESTIGE STABILITY CONSTANTS
# -----------------------------------------

# v0.3: reduced from 6. Halves raw season swing before cap applies.
PERFORMANCE_MULTIPLIER = 3

# v0.3: hard ceiling on any single season's prestige movement.
# Applies to the SUM of performance delta + tournament bonus.
# Symmetric: collapses are also capped at -4.
SEASON_PRESTIGE_CAP = 4.0

# -----------------------------------------
# PRESTIGE GRADE -- per the Bible (A+ through F)
# -----------------------------------------

def prestige_grade(score):
    """Converts a 1-100 prestige score to a letter grade."""
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


# -----------------------------------------
# PROGRAM CREATOR
# -----------------------------------------

def create_program(name, nickname, city, state, division, conference,
                   home_court, venue_rating, prestige_current,
                   prestige_gravity, coach_name, coach_archetype=None):
    """
    Creates a program object.
    This is the persistent identity of a school across all seasons.

    prestige_current  -- where the program is right now (1-100)
    prestige_gravity  -- historical anchor, pulls current toward it each season (1-100)
    gravity_pull_rate -- how fast current moves toward gravity (0.0 to 1.0)
                         0.05 = moves 5% of the gap each season (slow, realistic)
    coach_archetype   -- optional coaching system string passed to generate_coach().
                         None = weighted random from ARCHETYPE_WEIGHTS in coach.py.
    """

    if prestige_gravity >= 80:
        gravity_pull_rate = 0.08
    elif prestige_gravity >= 60:
        gravity_pull_rate = 0.05
    else:
        gravity_pull_rate = 0.03

    roster_data = generate_team(name, prestige=prestige_current)
    coach       = generate_coach(coach_name, prestige=prestige_current,
                                 archetype=coach_archetype)

    program = {
        # --- IDENTITY ---
        "name":         name,
        "nickname":     nickname,
        "city":         city,
        "state":        state,
        "division":     division,
        "conference":   conference,

        # --- FACILITIES ---
        "home_court":   home_court,
        "venue_rating": venue_rating,

        # --- PRESTIGE ---
        "prestige_current":    prestige_current,
        "prestige_gravity":    prestige_gravity,
        "prestige_grade":      prestige_grade(prestige_current),
        "gravity_pull_rate":   gravity_pull_rate,

        # --- COACHING ---
        "coach_name":   coach_name,
        "coach_seasons": 0,
        "coach":        coach,

        # --- INSTITUTIONAL CHARACTER ---
        "investment_appetite":   random.randint(1, 10),
        "prestige_sensitivity":  random.randint(1, 10),
        "community_pressure":    random.randint(1, 10),
        "leadership_stability":  random.randint(1, 10),

        # --- JOB SECURITY ---
        "job_security":  75,

        # --- CURRENT SEASON STATE ---
        "wins":   0,
        "losses": 0,
        "conf_wins":   0,
        "conf_losses": 0,
        "season_results": [],

        # --- ROSTER ---
        "roster": roster_data["roster"],

        # --- HISTORY ---
        "season_history": [],
    }

    return program


def apply_gravity_pull(program):
    """
    Pulls current prestige toward historical gravity anchor.
    Called once per season at season end, after update_prestige_for_results().
    """
    current = program["prestige_current"]
    gravity = program["prestige_gravity"]
    rate    = program["gravity_pull_rate"]

    gap  = gravity - current
    pull = gap * rate

    program["prestige_current"] = round(current + pull, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    return program


def update_prestige_for_results(program, wins, losses, made_tournament, tournament_wins):
    """
    Adjusts current prestige based on season results.
    Called at season end BEFORE gravity pull.

    v0.3 changes:
      - Performance multiplier: 3 (was 6, was 10 before that)
      - Tournament bonus recalibrated: +0.5 for qualifying, +0.75 per win
        These bonuses are reasonable for conf tournament, not NCAA tourney.
        When a real postseason exists, this gets a dedicated system.
      - Hard cap: total movement clamped to ±SEASON_PRESTIGE_CAP (4.0)
        before new prestige is written. No single season reshapes a program.
    """
    current = program["prestige_current"]

    games = wins + losses
    if games > 0:
        win_pct          = wins / games
        expected_win_pct = 0.35 + (current / 100) * 0.45
        performance_delta = (win_pct - expected_win_pct) * PERFORMANCE_MULTIPLIER
    else:
        performance_delta = 0

    tournament_bonus = 0
    if made_tournament:
        tournament_bonus += 0.5
        tournament_bonus += tournament_wins * 0.75

    total_delta  = performance_delta + tournament_bonus

    # Hard cap: no program moves more than SEASON_PRESTIGE_CAP in one season
    total_delta  = max(-SEASON_PRESTIGE_CAP, min(SEASON_PRESTIGE_CAP, total_delta))

    new_prestige = current + total_delta
    new_prestige = max(1, min(100, new_prestige))

    program["prestige_current"] = round(new_prestige, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    return program


def record_game_result(program, opponent_name, points_for, points_against, is_home, is_conference):
    """Records a single game result on the program."""
    won = points_for > points_against

    result = {
        "opponent":       opponent_name,
        "points_for":     points_for,
        "points_against": points_against,
        "won":            won,
        "is_home":        is_home,
        "is_conference":  is_conference,
    }

    program["season_results"].append(result)

    if won:
        program["wins"] += 1
        if is_conference:
            program["conf_wins"] += 1
    else:
        program["losses"] += 1
        if is_conference:
            program["conf_losses"] += 1

    return program


def get_record_string(program):
    """Returns a formatted record string like '24-8 (12-6)'."""
    overall = str(program["wins"]) + "-" + str(program["losses"])
    conf    = str(program["conf_wins"]) + "-" + str(program["conf_losses"])
    return overall + " (" + conf + ")"


def print_program_summary(program):
    """Prints a readable summary of a program."""
    print("")
    print("=== " + program["name"] + " " + program["nickname"] + " ===")
    print("Location:    " + program["city"] + ", " + program["state"])
    print("Division:    " + program["division"] + " -- " + program["conference"])
    print("Home Court:  " + program["home_court"] + " (Venue: " + str(program["venue_rating"]) + "/100)")
    print("Prestige:    " + str(program["prestige_current"]) + "/100  (" + program["prestige_grade"] + ")")
    print("Gravity:     " + str(program["prestige_gravity"]) + "/100  (pull rate: " + str(program["gravity_pull_rate"]) + ")")
    print("Coach:       " + program["coach_name"])
    print("Record:      " + get_record_string(program))
    print("Job Security:" + str(program["job_security"]) + "/100")
    print("Roster size: " + str(len(program["roster"])) + " players")


# -----------------------------------------
# SAMPLE PROGRAMS -- real schools for testing
# -----------------------------------------

def build_sample_programs():
    """Builds a small set of sample programs for testing."""

    programs = []

    programs.append(create_program(
        name="Kentucky", nickname="Wildcats", city="Lexington", state="KY",
        division="D1", conference="SEC", home_court="Rupp Arena",
        venue_rating=97, prestige_current=92, prestige_gravity=90,
        coach_name="Coach Calipari",
    ))

    programs.append(create_program(
        name="Kansas", nickname="Jayhawks", city="Lawrence", state="KS",
        division="D1", conference="Big 12", home_court="Allen Fieldhouse",
        venue_rating=98, prestige_current=91, prestige_gravity=89,
        coach_name="Coach Self",
    ))

    programs.append(create_program(
        name="Duke", nickname="Blue Devils", city="Durham", state="NC",
        division="D1", conference="ACC", home_court="Cameron Indoor Stadium",
        venue_rating=99, prestige_current=93, prestige_gravity=91,
        coach_name="Coach K",
    ))

    programs.append(create_program(
        name="Gonzaga", nickname="Bulldogs", city="Spokane", state="WA",
        division="D1", conference="WCC", home_court="McCarthey Athletic Center",
        venue_rating=82, prestige_current=78, prestige_gravity=72,
        coach_name="Coach Few",
    ))

    programs.append(create_program(
        name="Drake", nickname="Bulldogs", city="Des Moines", state="IA",
        division="D1", conference="Missouri Valley", home_court="Knapp Center",
        venue_rating=61, prestige_current=54, prestige_gravity=52,
        coach_name="Coach Johnson",
    ))

    programs.append(create_program(
        name="Eastern Illinois", nickname="Panthers", city="Charleston", state="IL",
        division="D1", conference="Big South", home_court="Lantz Arena",
        venue_rating=42, prestige_current=31, prestige_gravity=30,
        coach_name="Coach Williams",
    ))

    return programs


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("Building sample programs...")
    programs = build_sample_programs()

    for p in programs:
        print_program_summary(p)

    print("")
    print("=== Gravity Pull Test -- 5 seasons ===")
    kentucky = programs[0]
    kentucky["prestige_current"] = 70
    print("Kentucky prestige dropped to 70 (gravity anchor: " + str(kentucky["prestige_gravity"]) + ")")
    print("")
    for season in range(1, 6):
        kentucky = apply_gravity_pull(kentucky)
        print("After season " + str(season) + ": " +
              str(kentucky["prestige_current"]) + " (" + kentucky["prestige_grade"] + ")")

    print("")
    print("=== Prestige Volatility Test -- v0.3 vs v0.2 ===")
    print("  Simulating 10 exceptional seasons for a prestige-54 team (Drake):")
    print("  Should NOT become an elite program. Should plateau and get pushed back.")
    print("")
    test_prog = build_sample_programs()[4]   # Drake
    test_prog["prestige_current"] = 54
    test_prog["prestige_gravity"] = 52
    print("  {:<10} {:<12} {:<10} {:<10}".format("Season", "Prestige", "Grade", "Gravity"))
    print("  " + "-" * 42)
    for year in range(1, 11):
        update_prestige_for_results(test_prog, wins=28, losses=4,
                                    made_tournament=True, tournament_wins=2)
        apply_gravity_pull(test_prog)
        print("  {:<10} {:<12} {:<10} {:<10}".format(
            "Year " + str(year),
            str(test_prog["prestige_current"]),
            test_prog["prestige_grade"],
            str(test_prog["prestige_gravity"]),
        ))

    print("")
    print("=== Collapse Test -- 10 terrible seasons for Kentucky ===")
    print("  Should erode but NOT crater. Floor protects. Gravity pulls back.")
    print("")
    ky = build_sample_programs()[0]
    ky["prestige_current"] = 92
    ky["prestige_gravity"] = 90
    print("  {:<10} {:<12} {:<10} {:<10}".format("Season", "Prestige", "Grade", "Gravity"))
    print("  " + "-" * 42)
    for year in range(1, 11):
        update_prestige_for_results(ky, wins=8, losses=24,
                                    made_tournament=False, tournament_wins=0)
        apply_gravity_pull(ky)
        print("  {:<10} {:<12} {:<10} {:<10}".format(
            "Year " + str(year),
            str(ky["prestige_current"]),
            ky["prestige_grade"],
            str(ky["prestige_gravity"]),
        ))

    print("")
    print("=== Single Season Cap Verification ===")
    print("  Max possible gain in one season should be <= " + str(SEASON_PRESTIGE_CAP))
    cap_test = build_sample_programs()[4]
    cap_test["prestige_current"] = 50
    before = cap_test["prestige_current"]
    update_prestige_for_results(cap_test, wins=32, losses=0,
                                made_tournament=True, tournament_wins=10)
    after = cap_test["prestige_current"]
    delta = round(after - before, 2)
    print("  Before: " + str(before) + "  After: " + str(after) +
          "  Delta: " + str(delta) +
          "  PASS" if abs(delta) <= SEASON_PRESTIGE_CAP + 0.01 else "  FAIL")

    print("")
    print("=== Coach Verification ===")
    for p in programs[:3]:
        c = p["coach"]
        print(p["name"] + " -- Coach: " + c["name"] +
              "  Archetype: " + c["archetype"] +
              "  Pace: " + str(c["pace"]) +
              "  Rotation: " + str(c["rotation_size"]) + "p" +
              "  Off: " + str(c["offensive_skill"]) + "/20" +
              "  Def: " + str(c["defensive_skill"]) + "/20")

    print("")
    print("=== Record Tracking Test ===")
    drake = programs[4]
    record_game_result(drake, "Kentucky", 58, 72, is_home=False, is_conference=False)
    record_game_result(drake, "Illinois State", 71, 65, is_home=True, is_conference=True)
    record_game_result(drake, "Bradley", 68, 60, is_home=True, is_conference=True)
    record_game_result(drake, "Northern Iowa", 55, 61, is_home=False, is_conference=True)
    print("Drake record after 4 games: " + get_record_string(drake))
