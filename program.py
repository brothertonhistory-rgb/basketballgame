import random
from player import generate_team, get_team_ratings

# -----------------------------------------
# COLLEGE HOOPS SIM -- Program Database v0.1
# System 6 of the Design Bible
# Defines what a program IS -- persistent across seasons
# -----------------------------------------

# Division definitions
DIVISIONS = ["D1", "D2", "D3", "JUCO"]

# Conference definitions -- approximately 2008 NCAA alignment per the Bible
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
                   prestige_gravity, coach_name):
    """
    Creates a program object.
    This is the persistent identity of a school across all seasons.

    prestige_current  -- where the program is right now (1-100)
    prestige_gravity  -- historical anchor, pulls current toward it each season (1-100)
    gravity_pull_rate -- how fast current moves toward gravity (0.0 to 1.0)
                         0.05 = moves 5% of the gap each season (slow, realistic)
    """

    # Gravity pull rate -- slow by default, per the Bible
    # Blue bloods have stronger gravity (they bounce back faster)
    if prestige_gravity >= 80:
        gravity_pull_rate = 0.08   # Elite programs snap back quickly
    elif prestige_gravity >= 60:
        gravity_pull_rate = 0.05   # Good programs drift back moderately
    else:
        gravity_pull_rate = 0.03   # Small programs change slowly

    # Convert prestige to 1-20 scale for player generation
    prestige_for_players = max(1, min(20, int(prestige_current / 5)))

    # Generate the roster based on current prestige
    roster_data = generate_team(name, prestige=prestige_for_players)

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
        "venue_rating": venue_rating,   # 1-100, affects home court advantage

        # --- PRESTIGE -- two-value model per the Bible ---
        "prestige_current":    prestige_current,    # Where they are now
        "prestige_gravity":    prestige_gravity,    # Where they naturally belong
        "prestige_grade":      prestige_grade(prestige_current),
        "gravity_pull_rate":   gravity_pull_rate,   # How fast they drift back

        # --- COACHING ---
        "coach_name":   coach_name,
        "coach_seasons": 0,            # Seasons with this coach

        # --- INSTITUTIONAL CHARACTER -- System 9 ---
        "investment_appetite":   random.randint(1, 10),   # How much they spend
        "prestige_sensitivity":  random.randint(1, 10),   # How much fans care
        "community_pressure":    random.randint(1, 10),   # External pressure
        "leadership_stability":  random.randint(1, 10),   # AD/president stability

        # --- JOB SECURITY ---
        "job_security":  75,    # 0-100, starts neutral, moves with results

        # --- CURRENT SEASON STATE ---
        "wins":   0,
        "losses": 0,
        "conf_wins":   0,
        "conf_losses": 0,
        "season_results": [],   # List of game result dicts

        # --- ROSTER ---
        "roster": roster_data["roster"],

        # --- HISTORY -- grows each season ---
        "season_history": [],   # One entry per completed season
    }

    return program


def apply_gravity_pull(program):
    """
    Pulls current prestige toward historical gravity anchor.
    Called once per season at season end.
    The gap shrinks by gravity_pull_rate each season.
    Example: current=60, gravity=80, rate=0.05
             gap = 20, pull = 1.0 point toward 80
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
    Winning pushes prestige up. Losing pulls it down.
    Tournament runs give a bigger boost.
    """
    current = program["prestige_current"]

    # Win/loss impact -- winning percentage vs expected
    games = wins + losses
    if games > 0:
        win_pct = wins / games
        # Expected win pct based on prestige -- elite teams should win more
        expected_win_pct = 0.35 + (current / 100) * 0.45
        performance_delta = (win_pct - expected_win_pct) * 10
    else:
        performance_delta = 0

    # Tournament impact
    tournament_bonus = 0
    if made_tournament:
        tournament_bonus += 2
        tournament_bonus += tournament_wins * 1.5   # Each win is worth more

    # Apply changes -- clamped 1-100
    new_prestige = current + performance_delta + tournament_bonus
    new_prestige = max(1, min(100, new_prestige))

    program["prestige_current"] = round(new_prestige, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    return program


def record_game_result(program, opponent_name, points_for, points_against, is_home, is_conference):
    """Records a single game result on the program."""
    won = points_for > points_against

    result = {
        "opponent":      opponent_name,
        "points_for":    points_for,
        "points_against":points_against,
        "won":           won,
        "is_home":       is_home,
        "is_conference": is_conference,
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

    # Blue blood -- Kentucky
    programs.append(create_program(
        name="Kentucky",
        nickname="Wildcats",
        city="Lexington",
        state="KY",
        division="D1",
        conference="SEC",
        home_court="Rupp Arena",
        venue_rating=97,
        prestige_current=92,
        prestige_gravity=90,
        coach_name="Coach Calipari",
    ))

    # Big 12 power -- Kansas
    programs.append(create_program(
        name="Kansas",
        nickname="Jayhawks",
        city="Lawrence",
        state="KS",
        division="D1",
        conference="Big 12",
        home_court="Allen Fieldhouse",
        venue_rating=98,
        prestige_current=91,
        prestige_gravity=89,
        coach_name="Coach Self",
    ))

    # ACC power -- Duke
    programs.append(create_program(
        name="Duke",
        nickname="Blue Devils",
        city="Durham",
        state="NC",
        division="D1",
        conference="ACC",
        home_court="Cameron Indoor Stadium",
        venue_rating=99,
        prestige_current=93,
        prestige_gravity=91,
        coach_name="Coach K",
    ))

    # Good mid-major -- Gonzaga
    programs.append(create_program(
        name="Gonzaga",
        nickname="Bulldogs",
        city="Spokane",
        state="WA",
        division="D1",
        conference="WCC",
        home_court="McCarthey Athletic Center",
        venue_rating=82,
        prestige_current=78,
        prestige_gravity=72,
        coach_name="Coach Few",
    ))

    # Average mid-major
    programs.append(create_program(
        name="Drake",
        nickname="Bulldogs",
        city="Des Moines",
        state="IA",
        division="D1",
        conference="Missouri Valley",
        home_court="Knapp Center",
        venue_rating=61,
        prestige_current=54,
        prestige_gravity=52,
        coach_name="Coach Johnson",
    ))

    # Low major
    programs.append(create_program(
        name="Eastern Illinois",
        nickname="Panthers",
        city="Charleston",
        state="IL",
        division="D1",
        conference="Big South",
        home_court="Lantz Arena",
        venue_rating=42,
        prestige_current=31,
        prestige_gravity=30,
        coach_name="Coach Williams",
    ))

    return programs


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("Building sample programs...")
    programs = build_sample_programs()

    # Print summaries
    for p in programs:
        print_program_summary(p)

    # Test gravity pull
    print("")
    print("=== Gravity Pull Test -- 5 seasons ===")
    kentucky = programs[0]
    # Simulate Kentucky having a rough patch -- drop prestige
    kentucky["prestige_current"] = 70
    print("Kentucky prestige dropped to 70 (gravity anchor: " + str(kentucky["prestige_gravity"]) + ")")
    print("")
    for season in range(1, 6):
        kentucky = apply_gravity_pull(kentucky)
        print("After season " + str(season) + ": " +
              str(kentucky["prestige_current"]) + " (" + kentucky["prestige_grade"] + ")")

    print("")
    print("=== Record Tracking Test ===")
    drake = programs[4]
    record_game_result(drake, "Kentucky", 58, 72, is_home=False, is_conference=False)
    record_game_result(drake, "Illinois State", 71, 65, is_home=True, is_conference=True)
    record_game_result(drake, "Bradley", 68, 60, is_home=True, is_conference=True)
    record_game_result(drake, "Northern Iowa", 55, 61, is_home=False, is_conference=True)
    print("Drake record after 4 games: " + get_record_string(drake))
