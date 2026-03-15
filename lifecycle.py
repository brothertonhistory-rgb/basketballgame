# -----------------------------------------
# COLLEGE HOOPS SIM -- Player Lifecycle v0.4
# Closes the loop between recruiting and rosters.
#
# Called once per season, AFTER simulate_world_season()
# and AFTER resolve_full_recruiting_cycle().
#
# Order of operations every season turnover:
#   1. Develop returning players  (NEW in v0.4)
#   2. Graduate seniors           (remove from roster)
#   3. Age remaining players      (Fr->So->Jr->Sr)
#   4. Enroll committed recruits  (add to roster as Freshmen)
#   5. Reset recruiting state     (clear boards for next cycle)
#
# v0.4 CHANGES:
#   - Development runs BEFORE graduation so seniors get their final
#     offseason improvement before they leave.
#   - develop_player() from player.py is called on every player.
#   - Breakthroughs are tracked world-wide and reported.
#   - Development summary added to lifecycle_summary.
# -----------------------------------------

from player import create_player, develop_player

YEAR_PROGRESSION = {
    "Freshman":  "Sophomore",
    "Sophomore": "Junior",
    "Junior":    "Senior",
    "Senior":    "Senior",
}


# -----------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------

def advance_season(all_programs, recruiting_class, season_year=2025):
    """
    Call this once per year after the season and recruiting cycle are done.
    Returns (all_programs, lifecycle_summary).

    v0.4: Development now runs first, before graduation.
    """
    total_graduated    = 0
    total_enrolled     = 0
    total_developed    = 0
    total_breakthroughs = 0
    breakthrough_log   = []
    program_reports    = []

    for program in all_programs:
        coach = program.get("coach", {})

        # --- STEP 1: DEVELOP RETURNING PLAYERS ---
        # Every player gets an offseason. Seniors too -- they develop
        # then graduate. This is their final offseason improvement.
        dev_count, bt_count, bt_events = _develop_roster(
            program, coach, season_year
        )
        total_developed     += dev_count
        total_breakthroughs += bt_count
        breakthrough_log.extend(bt_events)

        # --- STEP 2: GRADUATE SENIORS ---
        graduated = _graduate_seniors(program)

        # --- STEP 3: AGE REMAINING PLAYERS ---
        _age_roster(program)

        # --- STEP 4: ENROLL COMMITTED RECRUITS ---
        enrolled = _enroll_recruits(program, recruiting_class)

        # --- STEP 5: RESET RECRUITING STATE ---
        _reset_recruiting_state(program)

        total_graduated += graduated
        total_enrolled  += enrolled

        program_reports.append({
            "name":        program["name"],
            "graduated":   graduated,
            "enrolled":    enrolled,
            "roster_size": len(program["roster"]),
            "developed":   dev_count,
            "breakthroughs": bt_count,
        })

    summary = {
        "total_graduated":     total_graduated,
        "total_enrolled":      total_enrolled,
        "total_developed":     total_developed,
        "total_breakthroughs": total_breakthroughs,
        "breakthrough_log":    breakthrough_log,
        "program_reports":     program_reports,
    }

    return all_programs, summary


# -----------------------------------------
# STEP 1: DEVELOP ROSTER
# -----------------------------------------

def _develop_roster(program, coach, season_year):
    """
    Runs development for every player on the roster.
    Returns (dev_count, breakthrough_count, breakthrough_events).

    Seniors develop too -- this is their final offseason.
    Freshmen who just enrolled this cycle are NOT developed yet --
    they enrolled after the season, so their development starts
    next offseason.
    """
    dev_count       = 0
    bt_count        = 0
    breakthrough_events = []

    for player in program["roster"]:
        # Skip players who just enrolled (status still "enrolled" from
        # this cycle's recruiting -- they haven't played a season yet)
        # Note: newly enrolled freshmen won't have this flag set in the
        # current cycle since development runs before enrollment.
        # All current roster players have played at least one season.

        player, report = develop_player(
            player, coach, season_year,
            training_focus=None,   # FUTURE HOOK: training camp
            morale_modifier=1.0,   # FUTURE HOOK: playing time morale
        )

        if report["total_gain"] > 0:
            dev_count += 1

        if report["breakthrough"]:
            bt_count += 1
            breakthrough_events.append({
                "program":  program["name"],
                "player":   player["name"],
                "position": player["position"],
                "year":     player["year"],
                "arc_type": player["arc_type"],
                "attrs":    report["breakthrough_attrs"],
                "total_gain": report["total_gain"],
            })

    return dev_count, bt_count, breakthrough_events


# -----------------------------------------
# STEP 2: GRADUATE SENIORS
# -----------------------------------------

def _graduate_seniors(program):
    """Removes all Seniors from the roster. Returns count removed."""
    seniors = [p for p in program["roster"] if p.get("year", "") == "Senior"]
    program["roster"] = [p for p in program["roster"] if p.get("year", "") != "Senior"]
    return len(seniors)


# -----------------------------------------
# STEP 3: AGE REMAINING PLAYERS
# -----------------------------------------

def _age_roster(program):
    """Advances every remaining player one year."""
    for player in program["roster"]:
        current_year = player.get("year", "Freshman")
        player["year"] = YEAR_PROGRESSION.get(current_year, "Sophomore")


# -----------------------------------------
# STEP 4: ENROLL COMMITTED RECRUITS
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
    """Converts a recruit dict into a player dict."""
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
# STEP 5: RESET RECRUITING STATE
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
    print("  Players graduated:   " + str(lifecycle_summary["total_graduated"]))
    print("  Recruits enrolled:   " + str(lifecycle_summary["total_enrolled"]))
    print("  Players developed:   " + str(lifecycle_summary["total_developed"]))
    print("  Breakthroughs:       " + str(lifecycle_summary["total_breakthroughs"]))

    thin_rosters = [
        r for r in lifecycle_summary["program_reports"]
        if r["roster_size"] < 7
    ]
    if thin_rosters:
        print("")
        print("  WARNING -- programs with thin rosters (<7 players):")
        for r in thin_rosters:
            print("    " + r["name"] + ": " + str(r["roster_size"]) + " players")

    # Print breakthroughs
    bt_log = lifecycle_summary.get("breakthrough_log", [])
    if bt_log:
        print("")
        print("  BREAKTHROUGH PLAYERS this offseason:")
        for bt in bt_log[:15]:   # cap at 15 for readability
            attr_str = ", ".join(
                a["attr"] + " " + str(a["from"]) + "->" + str(a["to"])
                for a in bt["attrs"]
            )
            print("    " + bt["player"].ljust(22) +
                  bt["position"] + " " + bt["year"].ljust(12) +
                  bt["program"].ljust(24) +
                  "(" + bt["arc_type"] + ")  " + attr_str)
        if len(bt_log) > 15:
            print("    ... and " + str(len(bt_log) - 15) + " more")

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

    # Snapshot a player BEFORE development
    kentucky = next(p for p in all_programs if p["name"] == "Kentucky")
    if kentucky["roster"]:
        test_player = next(
            (p for p in kentucky["roster"] if p.get("year") == "Sophomore"),
            kentucky["roster"][0]
        )
        before_finishing  = test_player["finishing"]
        before_rebounding = test_player["rebounding"]
        before_passing    = test_player["passing"]
        test_name         = test_player["name"]

    print("")
    print("Running lifecycle with development...")
    all_programs, lifecycle_summary = advance_season(
        all_programs, recruiting_class, season_year=2025
    )

    print_lifecycle_summary(lifecycle_summary, season_year=2025)

    # Development verification
    print("")
    print("=== DEVELOPMENT VERIFICATION ===")
    print("  Total players developed: " + str(lifecycle_summary["total_developed"]))
    print("  Breakthroughs:           " + str(lifecycle_summary["total_breakthroughs"]))

    total_players = sum(len(p["roster"]) for p in all_programs)
    print("  Total players on rosters: " + str(total_players))
    bt_rate = lifecycle_summary["total_breakthroughs"] / max(1, total_players) * 100
    print("  Breakthrough rate: " + str(round(bt_rate, 2)) + "%")
    print("  (healthy: 1-4% of players = ~30-120 per season)")

    # Verify rosters are still healthy
    thin = [p for p in all_programs if len(p.get("roster", [])) < 8]
    if thin:
        print("")
        print("WARNING: " + str(len(thin)) + " programs with thin rosters:")
        for p in thin[:5]:
            print("  " + p["name"] + ": " + str(len(p["roster"])) + " players")
    else:
        print("")
        print("PASS: All programs have 8+ players after lifecycle.")

    # Spot check: development comparison between high and low dev coaches
    print("")
    print("=== COACH DEVELOPMENT COMPARISON ===")
    print("  Finding programs with high vs low player_development coaches...")

    high_dev_programs = sorted(
        [p for p in all_programs if p.get("coach", {}).get("player_development", 0) >= 16],
        key=lambda p: p["coach"]["player_development"],
        reverse=True
    )[:3]

    low_dev_programs = sorted(
        [p for p in all_programs if p.get("coach", {}).get("player_development", 0) <= 7],
        key=lambda p: p["coach"]["player_development"]
    )[:3]

    print("")
    print("  High development coaches:")
    for p in high_dev_programs:
        dev_rating = p["coach"]["player_development"]
        bts = next((r["breakthroughs"] for r in lifecycle_summary["program_reports"]
                    if r["name"] == p["name"]), 0)
        devs = next((r["developed"] for r in lifecycle_summary["program_reports"]
                     if r["name"] == p["name"]), 0)
        print("    " + p["name"].ljust(24) +
              "dev_rating: " + str(dev_rating) +
              "  players improved: " + str(devs) +
              "  breakthroughs: " + str(bts))

    print("")
    print("  Low development coaches:")
    for p in low_dev_programs:
        dev_rating = p["coach"]["player_development"]
        bts = next((r["breakthroughs"] for r in lifecycle_summary["program_reports"]
                    if r["name"] == p["name"]), 0)
        devs = next((r["developed"] for r in lifecycle_summary["program_reports"]
                     if r["name"] == p["name"]), 0)
        print("    " + p["name"].ljust(24) +
              "dev_rating: " + str(dev_rating) +
              "  players improved: " + str(devs) +
              "  breakthroughs: " + str(bts))
