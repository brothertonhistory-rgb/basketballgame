import random
from game_engine import simulate_game
from program import (create_program, build_sample_programs,
                     record_game_result, apply_gravity_pull,
                     update_prestige_for_results, get_record_string,
                     print_program_summary)

# -----------------------------------------
# COLLEGE HOOPS SIM -- Season Calendar v0.1
# Connects program.py + game_engine.py
# Simulates a full season for a group of programs
# -----------------------------------------

# How many games per team
CONFERENCE_GAMES = 18       # Each team plays 18 conference games
NON_CONFERENCE_GAMES = 12   # Each team plays 12 non-conference games
TOTAL_GAMES = CONFERENCE_GAMES + NON_CONFERENCE_GAMES


def build_conference_schedule(programs):
    """
    Builds a round-robin style conference schedule.
    Each team plays every other conference team at least once.
    Returns a list of matchups: {home, away, is_conference}
    """
    matchups = []
    n = len(programs)

    for i in range(n):
        for j in range(i + 1, n):
            # Home and away game for each pair
            matchups.append({
                "home": programs[i],
                "away": programs[j],
                "is_conference": True,
                "played": False,
                "result": None,
            })
            matchups.append({
                "home": programs[j],
                "away": programs[i],
                "is_conference": True,
                "played": False,
                "result": None,
            })

    return matchups


def build_non_conference_schedule(programs, all_programs, games_per_team=12):
    """
    Builds non-conference games for each program.
    Picks opponents from outside their conference.
    Returns a list of matchups.
    """
    matchups = []
    conf_names = set(p["conference"] for p in programs)

    # Pool of non-conference opponents
    non_conf_pool = [p for p in all_programs if p["conference"] not in conf_names]

    if len(non_conf_pool) < 2:
        return matchups  # Not enough opponents -- skip

    for program in programs:
        games_scheduled = 0
        attempts = 0
        while games_scheduled < games_per_team and attempts < 100:
            attempts += 1
            opponent = random.choice(non_conf_pool)
            if opponent["name"] == program["name"]:
                continue

            # Alternate home and away
            if games_scheduled % 2 == 0:
                matchups.append({
                    "home": program,
                    "away": opponent,
                    "is_conference": False,
                    "played": False,
                    "result": None,
                })
            else:
                matchups.append({
                    "home": opponent,
                    "away": program,
                    "is_conference": False,
                    "played": False,
                    "result": None,
                })
            games_scheduled += 1

    return matchups


def simulate_season(conference_programs, all_programs, season_year=2008, verbose=True):
    """
    Simulates a full season for a conference.
    conference_programs -- the programs in this conference
    all_programs        -- all programs in the world (for non-conf scheduling)
    season_year         -- the year label for this season
    """

    if verbose:
        print("")
        print("=" * 60)
        print("SEASON " + str(season_year) + " -- " +
              conference_programs[0]["conference"] + " Conference")
        print("=" * 60)

    # Reset season state for all programs
    for p in conference_programs:
        p["wins"] = 0
        p["losses"] = 0
        p["conf_wins"] = 0
        p["conf_losses"] = 0
        p["season_results"] = []

    # Build schedule
    conf_schedule = build_conference_schedule(conference_programs)
    non_conf_schedule = build_non_conference_schedule(
        conference_programs, all_programs, games_per_team=6
    )

    full_schedule = conf_schedule + non_conf_schedule

    # Shuffle schedule so conference and non-conference games are mixed
    random.shuffle(full_schedule)

    if verbose:
        print("Schedule built: " + str(len(full_schedule)) + " total games")
        print("Simulating season...")
        print("")

    # Simulate every game
    for matchup in full_schedule:
        home = matchup["home"]
        away = matchup["away"]

        result = simulate_game(home, away, verbose=False)

        # Record result on both programs
        record_game_result(
            home,
            away["name"],
            result["home"],
            result["away"],
            is_home=True,
            is_conference=matchup["is_conference"]
        )
        record_game_result(
            away,
            home["name"],
            result["away"],
            result["home"],
            is_home=False,
            is_conference=matchup["is_conference"]
        )

        matchup["played"] = True
        matchup["result"] = result

    # Print standings
    if verbose:
        print_standings(conference_programs, season_year)

    # End of season -- update prestige and gravity for conference programs
    for p in conference_programs:
        made_tournament = p["conf_wins"] >= (len(conference_programs) // 2)
        tournament_wins = max(0, p["conf_wins"] - len(conference_programs) // 2)

        update_prestige_for_results(p, p["wins"], p["losses"],
                                    made_tournament, tournament_wins)
        apply_gravity_pull(p)

        # Update rolling performance history for gravity drift
        games = p["wins"] + p["losses"]
        if games > 0:
            win_pct = p["wins"] / games
        else:
            win_pct = 0.0

        if "performance_history" not in p:
            p["performance_history"] = []

        p["performance_history"].append({
            "year": season_year,
            "wins": p["wins"],
            "losses": p["losses"],
            "win_pct": round(win_pct, 3),
            "prestige_end": p["prestige_current"],
        })

        # Drift gravity based on rolling 10-year performance window
        apply_gravity_drift(p)

        # Archive this season
        p["season_history"].append({
            "year": season_year,
            "wins": p["wins"],
            "losses": p["losses"],
            "conf_wins": p["conf_wins"],
            "conf_losses": p["conf_losses"],
            "prestige_end": p["prestige_current"],
        })

        p["coach_seasons"] += 1

    return conference_programs


def apply_gravity_drift(program):
    """
    Slowly adjusts the gravity anchor based on rolling 10-year performance.
    Sustained success pulls gravity up. Sustained failure pulls it down.
    Gravity moves much slower than current prestige -- max 1.5 points per season.
    """
    history = program.get("performance_history", [])

    # Need at least 3 seasons of history to start drifting
    if len(history) < 3:
        return program

    # Look at last 10 seasons (or however many we have)
    window = history[-10:]
    avg_win_pct = sum(s["win_pct"] for s in window) / len(window)

    # What win percentage does their current gravity suggest they should have?
    gravity = program["prestige_gravity"]
    expected_win_pct = 0.35 + (gravity / 100) * 0.45

    # How far off are they from expected?
    performance_gap = avg_win_pct - expected_win_pct

    # Gravity drifts slowly -- max 1.5 points per season
    gravity_delta = performance_gap * 3.0
    gravity_delta = max(-1.5, min(1.5, gravity_delta))

    new_gravity = program["prestige_gravity"] + gravity_delta
    new_gravity = max(1, min(100, new_gravity))

    program["prestige_gravity"] = round(new_gravity, 1)

    return program


def print_standings(programs, season_year):
    """Prints a formatted standings table."""
    # Sort by conference wins, then overall wins
    sorted_programs = sorted(
        programs,
        key=lambda p: (p["conf_wins"], p["wins"]),
        reverse=True
    )

    print("--- " + str(season_year) + " Final Standings ---")
    print("{:<22} {:<10} {:<10} {:<8}".format(
        "Team", "Overall", "Conf", "Prestige"))
    print("-" * 55)

    for p in sorted_programs:
        overall = str(p["wins"]) + "-" + str(p["losses"])
        conf    = str(p["conf_wins"]) + "-" + str(p["conf_losses"])
        print("{:<22} {:<10} {:<10} {:<8}".format(
            p["name"],
            overall,
            conf,
            str(p["prestige_current"]) + " (" + p["prestige_grade"] + ")"
        ))


def print_multi_season_summary(programs, seasons):
    """Shows how programs evolved over multiple seasons."""
    print("")
    print("=" * 60)
    print("MULTI-SEASON SUMMARY -- " + str(seasons) + " seasons")
    print("=" * 60)

    for p in programs:
        print("")
        print(p["name"] + " -- Gravity: " + str(p["prestige_gravity"]) +
              "  Current Prestige: " + str(p["prestige_current"]) +
              " (" + p["prestige_grade"] + ")")
        if p.get("season_history"):
            print("  Season history:")
            for s in p["season_history"]:
                print("    " + str(s["year"]) + ": " +
                      str(s["wins"]) + "-" + str(s["losses"]) +
                      " (conf: " + str(s["conf_wins"]) + "-" + str(s["conf_losses"]) + ")" +
                      "  Prestige: " + str(s["prestige_end"]))


# -----------------------------------------
# BUILD ALL SAMPLE PROGRAMS
# -----------------------------------------

def build_all_programs():
    """Builds the full set of sample programs across conferences."""

    programs = []

    # --- BIG 12 ---
    programs.append(create_program(
        name="Oklahoma State", nickname="Cowboys",
        city="Stillwater", state="OK",
        division="D1", conference="Big 12",
        home_court="Gallagher-Iba Arena", venue_rating=88,
        prestige_current=72, prestige_gravity=70,
        coach_name="Coach Sutton",
    ))
    programs.append(create_program(
        name="Kansas", nickname="Jayhawks",
        city="Lawrence", state="KS",
        division="D1", conference="Big 12",
        home_court="Allen Fieldhouse", venue_rating=98,
        prestige_current=91, prestige_gravity=89,
        coach_name="Coach Self",
    ))
    programs.append(create_program(
        name="Texas", nickname="Longhorns",
        city="Austin", state="TX",
        division="D1", conference="Big 12",
        home_court="Frank Erwin Center", venue_rating=84,
        prestige_current=76, prestige_gravity=74,
        coach_name="Coach Barnes",
    ))
    programs.append(create_program(
        name="Oklahoma", nickname="Sooners",
        city="Norman", state="OK",
        division="D1", conference="Big 12",
        home_court="Lloyd Noble Center", venue_rating=79,
        prestige_current=68, prestige_gravity=66,
        coach_name="Coach Sampson",
    ))
    programs.append(create_program(
        name="Kansas State", nickname="Wildcats",
        city="Manhattan", state="KS",
        division="D1", conference="Big 12",
        home_court="Bramlage Coliseum", venue_rating=76,
        prestige_current=64, prestige_gravity=62,
        coach_name="Coach Martin",
    ))
    programs.append(create_program(
        name="Baylor", nickname="Bears",
        city="Waco", state="TX",
        division="D1", conference="Big 12",
        home_court="Ferrell Center", venue_rating=74,
        prestige_current=60, prestige_gravity=58,
        coach_name="Coach Drew",
    ))

    # --- SEC ---
    programs.append(create_program(
        name="Kentucky", nickname="Wildcats",
        city="Lexington", state="KY",
        division="D1", conference="SEC",
        home_court="Rupp Arena", venue_rating=97,
        prestige_current=92, prestige_gravity=90,
        coach_name="Coach Calipari",
    ))
    programs.append(create_program(
        name="Florida", nickname="Gators",
        city="Gainesville", state="FL",
        division="D1", conference="SEC",
        home_court="O'Connell Center", venue_rating=81,
        prestige_current=74, prestige_gravity=70,
        coach_name="Coach Donovan",
    ))
    programs.append(create_program(
        name="Tennessee", nickname="Volunteers",
        city="Knoxville", state="TN",
        division="D1", conference="SEC",
        home_court="Thompson-Boling Arena", venue_rating=83,
        prestige_current=69, prestige_gravity=67,
        coach_name="Coach Pearl",
    ))
    programs.append(create_program(
        name="LSU", nickname="Tigers",
        city="Baton Rouge", state="LA",
        division="D1", conference="SEC",
        home_court="Pete Maravich Assembly Center", venue_rating=80,
        prestige_current=65, prestige_gravity=63,
        coach_name="Coach Trent",
    ))

    # --- ACC ---
    programs.append(create_program(
        name="Duke", nickname="Blue Devils",
        city="Durham", state="NC",
        division="D1", conference="ACC",
        home_court="Cameron Indoor Stadium", venue_rating=99,
        prestige_current=93, prestige_gravity=91,
        coach_name="Coach K",
    ))
    programs.append(create_program(
        name="North Carolina", nickname="Tar Heels",
        city="Chapel Hill", state="NC",
        division="D1", conference="ACC",
        home_court="Dean Smith Center", venue_rating=91,
        prestige_current=89, prestige_gravity=87,
        coach_name="Coach Williams",
    ))
    programs.append(create_program(
        name="Wake Forest", nickname="Demon Deacons",
        city="Winston-Salem", state="NC",
        division="D1", conference="ACC",
        home_court="Lawrence Joel Coliseum", venue_rating=70,
        prestige_current=58, prestige_gravity=56,
        coach_name="Coach Prosser",
    ))

    # --- WCC (mid-major) ---
    programs.append(create_program(
        name="Gonzaga", nickname="Bulldogs",
        city="Spokane", state="WA",
        division="D1", conference="WCC",
        home_court="McCarthey Athletic Center", venue_rating=82,
        prestige_current=78, prestige_gravity=72,
        coach_name="Coach Few",
    ))
    programs.append(create_program(
        name="Saint Mary's", nickname="Gaels",
        city="Moraga", state="CA",
        division="D1", conference="WCC",
        home_court="McKeon Pavilion", venue_rating=62,
        prestige_current=55, prestige_gravity=53,
        coach_name="Coach Bennett",
    ))

    # --- MISSOURI VALLEY (mid-major) ---
    programs.append(create_program(
        name="Drake", nickname="Bulldogs",
        city="Des Moines", state="IA",
        division="D1", conference="Missouri Valley",
        home_court="Knapp Center", venue_rating=61,
        prestige_current=54, prestige_gravity=52,
        coach_name="Coach Johnson",
    ))
    programs.append(create_program(
        name="Northern Iowa", nickname="Panthers",
        city="Cedar Falls", state="IA",
        division="D1", conference="Missouri Valley",
        home_court="McLeod Center", venue_rating=64,
        prestige_current=56, prestige_gravity=54,
        coach_name="Coach Jacobson",
    ))
    programs.append(create_program(
        name="Illinois State", nickname="Redbirds",
        city="Normal", state="IL",
        division="D1", conference="Missouri Valley",
        home_court="Redbird Arena", venue_rating=59,
        prestige_current=50, prestige_gravity=49,
        coach_name="Coach Muller",
    ))

    return programs


# -----------------------------------------
# TEST -- Simulate a full Big 12 season
# -----------------------------------------

if __name__ == "__main__":

    print("Building programs...")
    all_programs = build_all_programs()

    # Pull out just the Big 12 for the first season sim
    big12 = [p for p in all_programs if p["conference"] == "Big 12"]

    print("Simulating Big 12 season...")

    # Simulate 3 seasons to see gravity drift in action
    for year in range(2008, 2011):
        simulate_season(big12, all_programs, season_year=year, verbose=True)

    # Show how programs evolved
    print_multi_season_summary(big12, 3)
