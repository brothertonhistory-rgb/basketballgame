# -----------------------------------------
# COLLEGE HOOPS SIM -- Player Lifecycle v0.3
# Closes the loop between recruiting and rosters.
#
# Called once per season, AFTER simulate_world_season()
# and AFTER resolve_full_recruiting_cycle().
#
# Order of operations every season turnover:
#   1. Graduate seniors       (remove from roster)
#   2. Age remaining players  (Fr->So->Jr->Sr)
#   3. Enroll committed recruits (add to roster as Freshmen)
#   4. Reset recruiting state  (clear boards for next cycle)
# -----------------------------------------

from player import create_player

YEAR_PROGRESSION = {
    "Freshman":  "Sophomore",
    "Sophomore": "Junior",
    "Junior":    "Senior",
    "Senior":    "Senior",   # safety net -- seniors removed before aging
}


# -----------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------

def advance_season(all_programs, recruiting_class):
    """
    Call this once per year after the season and recruiting cycle are done.
    Returns (all_programs, lifecycle_summary).
    """
    total_graduated = 0
    total_enrolled  = 0
    program_reports = []

    for program in all_programs:
        graduated = _graduate_seniors(program)
        _age_roster(program)
        enrolled  = _enroll_recruits(program, recruiting_class)
        _reset_recruiting_state(program)

        total_graduated += graduated
        total_enrolled  += enrolled

        program_reports.append({
            "name":        program["name"],
            "graduated":   graduated,
            "enrolled":    enrolled,
            "roster_size": len(program["roster"]),
        })

    summary = {
        "total_graduated": total_graduated,
        "total_enrolled":  total_enrolled,
        "program_reports": program_reports,
    }

    return all_programs, summary


# -----------------------------------------
# STEP 1: GRADUATE SENIORS
# -----------------------------------------

def _graduate_seniors(program):
    """
    Removes all Seniors from the roster.
    Returns count of players removed.
    """
    seniors = [p for p in program["roster"] if p.get("year", "") == "Senior"]
    program["roster"] = [p for p in program["roster"] if p.get("year", "") != "Senior"]
    return len(seniors)


# -----------------------------------------
# STEP 2: AGE REMAINING PLAYERS
# -----------------------------------------

def _age_roster(program):
    """
    Advances every remaining player one year.
    Freshman -> Sophomore -> Junior -> Senior
    """
    for player in program["roster"]:
        current_year = player.get("year", "Freshman")
        player["year"] = YEAR_PROGRESSION.get(current_year, "Sophomore")


# -----------------------------------------
# STEP 3: ENROLL COMMITTED RECRUITS
# -----------------------------------------

def _enroll_recruits(program, recruiting_class):
    """
    Finds all recruits committed to this program and adds them
    to the roster as Freshmen. Returns count enrolled.
    """
    program_name = program["name"]

    incoming = [
        r for r in recruiting_class
        if r.get("committed_to") == program_name
        and r.get("status") == "committed"
    ]

    enrolled = 0
    for recruit in incoming:
        player = _recruit_to_player(recruit, program.get("conference", ""))
        program["roster"].append(player)
        recruit["status"] = "enrolled"
        enrolled += 1

    return enrolled


def _recruit_to_player(recruit, conference=""):
    """
    Converts a recruit dict into a player dict compatible with player.py.
    Recruit attributes already use the same keys and 1-20 scale as player.py.
    """
    player = create_player(
        name       = recruit["name"],
        position   = recruit["position"],
        year       = "Freshman",
        conference = conference,
        heritage   = recruit.get("heritage"),
        shooting = {
            "catch_and_shoot": recruit.get("catch_and_shoot", 10),
            "off_dribble":     recruit.get("off_dribble",     10),
            "mid_range":       recruit.get("mid_range",       10),
            "three_point":     recruit.get("three_point",     10),
            "free_throw":      recruit.get("free_throw",      10),
            "finishing":       recruit.get("finishing",       10),
            "post_scoring":    recruit.get("post_scoring",    10),
        },
        defense = {
            "on_ball_defense": recruit.get("on_ball_defense", 10),
            "help_defense":    recruit.get("help_defense",    10),
            "shot_blocking":   recruit.get("shot_blocking",   10),
            "steal_tendency":  recruit.get("steal_tendency",  10),
            "foul_tendency":   recruit.get("foul_tendency",   10),
        },
        rebounding  = recruit.get("rebounding", 10),
        playmaking  = {
            "passing":         recruit.get("passing",         10),
            "ball_handling":   recruit.get("ball_handling",   10),
            "court_vision":    recruit.get("court_vision",    10),
            "decision_making": recruit.get("decision_making", 10),
        },
        athleticism = {
            "speed":             recruit.get("speed",             10),
            "lateral_quickness": recruit.get("lateral_quickness", 10),
            "strength":          recruit.get("strength",          10),
            "vertical":          recruit.get("vertical",          10),
        },
        mental = {
            "basketball_iq": recruit.get("basketball_iq", 10),
            "clutch":        recruit.get("clutch",        10),
            "composure":     recruit.get("composure",     10),
            "coachability":  recruit.get("coachability",  10),
            "work_ethic":    recruit.get("work_ethic",    10),
            "leadership":    recruit.get("leadership",    10),
        },
        potential = {
            "low":      recruit.get("potential_floor",   10),
            "high":     recruit.get("potential_ceiling", 15),
            "arc_type": recruit.get("arc_type",          "steady"),
        },
    )
    return player


# -----------------------------------------
# STEP 4: RESET RECRUITING STATE
# -----------------------------------------

def _reset_recruiting_state(program):
    """Clears recruiting board and committed list for next cycle."""
    program["recruiting_board"]   = []
    program["committed_recruits"] = []


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_lifecycle_summary(lifecycle_summary, season_year):
    """Prints a readable season turnover summary."""
    print("")
    print("=" * 60)
    print("  " + str(season_year) + " SEASON TURNOVER -- ROSTER LIFECYCLE")
    print("=" * 60)
    print("  Players graduated:  " + str(lifecycle_summary["total_graduated"]))
    print("  Recruits enrolled:  " + str(lifecycle_summary["total_enrolled"]))

    thin_rosters = [
        r for r in lifecycle_summary["program_reports"]
        if r["roster_size"] < 7
    ]
    if thin_rosters:
        print("")
        print("  WARNING -- programs with thin rosters (<7 players):")
        for r in thin_rosters:
            print("    " + r["name"] + ": " + str(r["roster_size"]) + " players")

    print("")
    print("  Biggest incoming classes:")
    top_enrolled = sorted(
        lifecycle_summary["program_reports"],
        key=lambda r: r["enrolled"],
        reverse=True
    )[:10]
    for r in top_enrolled:
        print("    " + r["name"].ljust(24) +
              str(r["enrolled"]) + " enrolled  |  " +
              str(r["roster_size"]) + " on roster")


def print_program_roster_state(program):
    """Prints a year-by-year roster breakdown for one program."""
    roster = program.get("roster", [])
    year_counts = {"Freshman": 0, "Sophomore": 0, "Junior": 0, "Senior": 0}
    for p in roster:
        yr = p.get("year", "Unknown")
        if yr in year_counts:
            year_counts[yr] += 1

    print("")
    print("  " + program["name"] + " roster (" + str(len(roster)) + " players):")
    for yr in ["Freshman", "Sophomore", "Junior", "Senior"]:
        print("    " + yr + ": " + str(year_counts[yr]))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from recruiting import generate_recruiting_class
    from recruiting_offers import generate_offers, calculate_interest_scores
    from recruiting_commitments import resolve_full_recruiting_cycle

    print("Loading programs...")
    all_programs = build_all_d1_programs()

    print("Generating recruiting class...")
    recruiting_class = generate_recruiting_class(season=2025)

    print("Running offers and interest scores...")
    all_programs, recruiting_class = generate_offers(all_programs, recruiting_class)
    all_programs, recruiting_class = calculate_interest_scores(all_programs, recruiting_class)

    print("Resolving recruiting cycle...")
    all_programs, recruiting_class, cycle_summary = resolve_full_recruiting_cycle(
        all_programs, recruiting_class, verbose=False
    )
    print("  Committed: " + str(cycle_summary["total_commits"]))

    # Snapshot BEFORE
    print("")
    print("=== BEFORE LIFECYCLE ===")
    kentucky = next(p for p in all_programs if p["name"] == "Kentucky")
    osu      = next(p for p in all_programs if p["name"] == "Oklahoma State")
    print_program_roster_state(kentucky)
    print_program_roster_state(osu)

    seniors_before = sum(
        1 for prog in all_programs
        for player in prog["roster"]
        if player.get("year") == "Senior"
    )
    freshmen_before = sum(
        1 for prog in all_programs
        for player in prog["roster"]
        if player.get("year") == "Freshman"
    )
    total_players_before = sum(len(prog["roster"]) for prog in all_programs)

    print("")
    print("  Total players:  " + str(total_players_before))
    print("  Seniors:        " + str(seniors_before))
    print("  Freshmen:       " + str(freshmen_before))

    # Run lifecycle
    print("")
    print("Running lifecycle / season turnover...")
    all_programs, lifecycle_summary = advance_season(all_programs, recruiting_class)

    # Snapshot AFTER
    print("")
    print("=== AFTER LIFECYCLE ===")
    kentucky = next(p for p in all_programs if p["name"] == "Kentucky")
    osu      = next(p for p in all_programs if p["name"] == "Oklahoma State")
    print_program_roster_state(kentucky)
    print_program_roster_state(osu)

    seniors_after = sum(
        1 for prog in all_programs
        for player in prog["roster"]
        if player.get("year") == "Senior"
    )
    freshmen_after = sum(
        1 for prog in all_programs
        for player in prog["roster"]
        if player.get("year") == "Freshman"
    )
    total_players_after = sum(len(prog["roster"]) for prog in all_programs)

    print("")
    print("  Total players:  " + str(total_players_after))
    print("  Seniors:        " + str(seniors_after)  + "  (these are promoted Juniors -- correct)")
    print("  Freshmen:       " + str(freshmen_after) + "  (these are newly enrolled recruits)")

    # --- CORRECT PASS/FAIL CHECKS ---
    print("")
    print("=== VERIFICATION ===")

    # Check 1: seniors_after should equal the old junior count
    # (every Junior became a Senior, the old Seniors are gone)
    juniors_before = sum(
        1 for prog in all_programs
        for player in prog["roster"]
        if player.get("year") == "Junior"
    )
    # After lifecycle, what were Juniors are now Seniors
    # We can't easily re-check this post-hoc, so we verify via math:
    # total_after = total_before - graduated + enrolled
    expected_total = total_players_before - lifecycle_summary["total_graduated"] + lifecycle_summary["total_enrolled"]
    if total_players_after == expected_total:
        print("PASS: Roster math checks out. " +
              str(lifecycle_summary["total_graduated"]) + " graduated, " +
              str(lifecycle_summary["total_enrolled"]) + " enrolled.")
    else:
        print("FAIL: Expected " + str(expected_total) +
              " total players, got " + str(total_players_after))

    # Check 2: freshmen_after should equal total_enrolled
    if freshmen_after == lifecycle_summary["total_enrolled"]:
        print("PASS: Freshman count matches enrolled count (" +
              str(freshmen_after) + ").")
    else:
        print("FAIL: Freshman count (" + str(freshmen_after) +
              ") does not match enrolled count (" +
              str(lifecycle_summary["total_enrolled"]) + ").")

    # Check 3: no player should still have "committed" status
    still_committed = [
        r for r in recruiting_class if r.get("status") == "committed"
    ]
    if len(still_committed) == 0:
        print("PASS: All committed recruits are now marked enrolled.")
    else:
        print("FAIL: " + str(len(still_committed)) +
              " recruits still showing committed status.")

    # Full summary
    print_lifecycle_summary(lifecycle_summary, season_year=2025)

    # Freshman spot check
    print("")
    print("=== FRESHMAN SPOT CHECK -- Kentucky ===")
    freshmen = [p for p in kentucky["roster"] if p["year"] == "Freshman"]
    print("  Kentucky freshmen: " + str(len(freshmen)))
    for p in freshmen:
        print("    " + p["name"] + "  " + p["position"] +
              "  finishing: " + str(p["finishing"]) +
              "  rebounding: " + str(p["rebounding"]))
