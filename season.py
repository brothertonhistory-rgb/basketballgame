import random
from game_engine import simulate_game
from program import (create_program, record_game_result, apply_gravity_pull,
                     update_prestige_for_results, get_record_string, prestige_grade)
from programs_data import build_all_d1_programs
from recruiting import generate_recruiting_class, print_class_summary
from recruiting_offers import generate_offers, calculate_interest_scores
from recruiting_commitments import resolve_full_recruiting_cycle, print_cycle_summary
from lifecycle import advance_season, print_lifecycle_summary

# -----------------------------------------
# COLLEGE HOOPS SIM -- Season Calendar v0.4
# Full world simulation -- all 328 D1 programs
# All conferences simulate simultaneously
# NOW FULLY CONNECTED:
#   1. Season simulation (games, standings, prestige)
#   2. Recruiting cycle  (offers, interest, commitments)
#   3. Player lifecycle  (graduation, aging, enrollment)
# The world now evolves season to season.
# -----------------------------------------

def build_conference_schedule(programs):
    """Round robin -- every team plays every other team home and away."""
    matchups = []
    n = len(programs)
    for i in range(n):
        for j in range(i + 1, n):
            matchups.append({"home": programs[i], "away": programs[j], "is_conference": True})
            matchups.append({"home": programs[j], "away": programs[i], "is_conference": True})
    return matchups


def build_non_conference_schedule(programs, all_programs, games_per_team=8):
    """
    Each program plays some non-conference games.
    Opponents pulled from outside their conference.
    Prestige-aware -- better programs schedule better opponents.
    """
    matchups = []
    conf_names = set(p["conference"] for p in programs)
    non_conf_pool = [p for p in all_programs if p["conference"] not in conf_names]

    if len(non_conf_pool) < 2:
        return matchups

    for program in programs:
        games_scheduled = 0
        attempts = 0
        while games_scheduled < games_per_team and attempts < 200:
            attempts += 1

            prestige_diff_limit = 30 + random.randint(0, 30)
            candidate = random.choice(non_conf_pool)

            if candidate["name"] == program["name"]:
                continue
            if abs(candidate["prestige_current"] - program["prestige_current"]) > prestige_diff_limit:
                continue

            if games_scheduled % 2 == 0:
                matchups.append({"home": program,    "away": candidate, "is_conference": False})
            else:
                matchups.append({"home": candidate,  "away": program,   "is_conference": False})
            games_scheduled += 1

    return matchups


def simulate_conference_season(conference_programs, all_programs, season_year, verbose=False):
    """
    Simulates one conference's full season.
    Returns the programs with updated records and prestige.
    """
    for p in conference_programs:
        p["wins"] = 0
        p["losses"] = 0
        p["conf_wins"] = 0
        p["conf_losses"] = 0
        p["season_results"] = []

    conf_schedule     = build_conference_schedule(conference_programs)
    non_conf_schedule = build_non_conference_schedule(
        conference_programs, all_programs, games_per_team=6
    )
    full_schedule = conf_schedule + non_conf_schedule
    random.shuffle(full_schedule)

    for matchup in full_schedule:
        home = matchup["home"]
        away = matchup["away"]
        result = simulate_game(home, away, verbose=False)

        record_game_result(home, away["name"], result["home"], result["away"],
                           is_home=True,  is_conference=matchup["is_conference"])
        record_game_result(away, home["name"], result["away"], result["home"],
                           is_home=False, is_conference=matchup["is_conference"])

    for p in conference_programs:
        games = p["wins"] + p["losses"]
        win_pct = p["wins"] / games if games > 0 else 0.0

        made_tournament  = p["conf_wins"] >= (len(conference_programs) // 2)
        tournament_wins  = max(0, p["conf_wins"] - len(conference_programs) // 2)

        update_prestige_for_results(p, p["wins"], p["losses"], made_tournament, tournament_wins)
        apply_gravity_pull(p)
        apply_gravity_drift(p, season_year, win_pct)

        if "season_history" not in p:
            p["season_history"] = []
        p["season_history"].append({
            "year":         season_year,
            "wins":         p["wins"],
            "losses":       p["losses"],
            "conf_wins":    p["conf_wins"],
            "conf_losses":  p["conf_losses"],
            "prestige_end": p["prestige_current"],
        })
        p["coach_seasons"] += 1

    return conference_programs


def apply_gravity_drift(program, season_year, win_pct):
    """Slowly adjusts gravity anchor based on rolling 10-year performance."""
    if "performance_history" not in program:
        program["performance_history"] = []

    program["performance_history"].append({
        "year": season_year, "win_pct": round(win_pct, 3)
    })

    history = program["performance_history"]
    if len(history) < 3:
        return

    window = history[-10:]
    avg_win_pct      = sum(s["win_pct"] for s in window) / len(window)
    gravity          = program["prestige_gravity"]
    expected_win_pct = 0.35 + (gravity / 100) * 0.45
    performance_gap  = avg_win_pct - expected_win_pct
    gravity_delta    = max(-1.5, min(1.5, performance_gap * 3.0))

    from programs_data import CONFERENCE_FLOORS
    floor = CONFERENCE_FLOORS.get(program["conference"], 15)
    new_gravity = max(floor, min(100, program["prestige_gravity"] + gravity_delta))
    program["prestige_gravity"] = round(new_gravity, 1)


def simulate_world_season(all_programs, season_year, verbose=True):
    """
    Simulates a COMPLETE year for the entire world.

    Step 1 -- Season simulation: every conference plays its full schedule,
              records update, prestige shifts.
    Step 2 -- Recruiting cycle: class generated, offers made, interest
              calculated, commitments resolved.
    Step 3 -- Lifecycle: seniors graduate, players age, recruits enroll.

    Returns (all_programs, recruiting_class, cycle_summary, lifecycle_summary)
    """

    # -------------------------------------------
    # STEP 1: SEASON SIMULATION
    # -------------------------------------------
    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)

    if verbose:
        print("")
        print("=" * 60)
        print("WORLD SEASON " + str(season_year))
        print(str(len(all_programs)) + " programs across " + str(len(conferences)) + " conferences")
        print("=" * 60)

    for conf_name, conf_programs in conferences.items():
        if len(conf_programs) < 2:
            continue
        simulate_conference_season(conf_programs, all_programs, season_year, verbose=False)

    if verbose:
        print_national_standings(all_programs, season_year)

    # -------------------------------------------
    # STEP 2: RECRUITING CYCLE
    # -------------------------------------------
    if verbose:
        print("")
        print("--- " + str(season_year) + " Recruiting Cycle ---")

    recruiting_class = generate_recruiting_class(season=season_year)

    if verbose:
        print("  Class generated: " + str(len(recruiting_class)) + " prospects")

    all_programs, recruiting_class = generate_offers(all_programs, recruiting_class)
    all_programs, recruiting_class = calculate_interest_scores(all_programs, recruiting_class)

    all_programs, recruiting_class, cycle_summary = resolve_full_recruiting_cycle(
        all_programs, recruiting_class, verbose=False
    )

    if verbose:
        print("  Offers sent and interest calculated")
        print("  Early signings:  " + str(len(cycle_summary["early_commits"])))
        print("  Late signings:   " + str(len(cycle_summary["late_commits"])))
        print("  Total committed: " + str(cycle_summary["total_commits"]))
        print("  Unsigned:        " + str(len(cycle_summary["unsigned"])))

    # -------------------------------------------
    # STEP 3: LIFECYCLE -- graduation, aging, enrollment
    # -------------------------------------------
    if verbose:
        print("")
        print("--- " + str(season_year) + " Roster Turnover ---")

    all_programs, lifecycle_summary = advance_season(all_programs, recruiting_class)

    if verbose:
        print("  Seniors graduated: " + str(lifecycle_summary["total_graduated"]))
        print("  Recruits enrolled: " + str(lifecycle_summary["total_enrolled"]))

    return all_programs, recruiting_class, cycle_summary, lifecycle_summary


def print_national_standings(all_programs, season_year):
    """Prints top 25 and conference leaders."""
    ranked = sorted(
        [p for p in all_programs if p["wins"] + p["losses"] > 0],
        key=lambda p: (p["wins"] / max(1, p["wins"] + p["losses"]), p["wins"]),
        reverse=True
    )

    print("")
    print("--- " + str(season_year) + " National Top 25 ---")
    print("{:<3} {:<22} {:<18} {:<10} {:<10}".format(
        "#", "Team", "Conference", "Record", "Prestige"))
    print("-" * 68)
    for i, p in enumerate(ranked[:25]):
        overall = str(p["wins"]) + "-" + str(p["losses"])
        print("{:<3} {:<22} {:<18} {:<10} {:<10}".format(
            i+1, p["name"], p["conference"][:17], overall,
            str(p["prestige_current"]) + " (" + p["prestige_grade"] + ")"
        ))

    print("")
    print("--- " + str(season_year) + " Conference Leaders ---")
    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)

    conf_leaders = []
    for conf_name, conf_programs in sorted(conferences.items()):
        if not conf_programs:
            continue
        leader = max(conf_programs, key=lambda p: (p["conf_wins"], p["wins"]))
        conf_leaders.append((conf_name, leader))

    for conf_name, leader in conf_leaders:
        conf_record = str(leader["conf_wins"]) + "-" + str(leader["conf_losses"])
        overall     = str(leader["wins"]) + "-" + str(leader["losses"])
        print("{:<20} {:<22} {:<10} {:<10}".format(
            conf_name[:19], leader["name"], overall, conf_record + " conf"))


def print_prestige_movers(all_programs, start_prestiges, season_year):
    """Shows biggest prestige gainers and losers."""
    changes = []
    for p in all_programs:
        start = start_prestiges.get(p["name"], p["prestige_current"])
        change = p["prestige_current"] - start
        changes.append((p["name"], p["conference"], start, p["prestige_current"], change))

    changes.sort(key=lambda x: x[4], reverse=True)

    print("")
    print("--- " + str(season_year) + " Biggest Prestige Movers ---")
    print("Top 10 risers:")
    for name, conf, start, end, change in changes[:10]:
        print("  +" + str(round(change,1)) + "  " + name + " (" + conf + ")  " +
              str(start) + " -> " + str(end))
    print("Top 10 fallers:")
    for name, conf, start, end, change in changes[-10:]:
        print("  " + str(round(change,1)) + "  " + name + " (" + conf + ")  " +
              str(start) + " -> " + str(end))


def print_roster_evolution(program):
    """Shows a program's roster year-by-year breakdown."""
    roster = program.get("roster", [])
    year_counts = {"Freshman": 0, "Sophomore": 0, "Junior": 0, "Senior": 0}
    for p in roster:
        yr = p.get("year", "Unknown")
        if yr in year_counts:
            year_counts[yr] += 1
    print("  " + program["name"] + " roster (" + str(len(roster)) + " players):  " +
          "Fr:" + str(year_counts["Freshman"]) +
          " So:" + str(year_counts["Sophomore"]) +
          " Jr:" + str(year_counts["Junior"]) +
          " Sr:" + str(year_counts["Senior"]))


# -----------------------------------------
# TEST -- Full connected world simulation
# Run this to simulate multiple complete seasons
# and watch programs, rosters, and prestige evolve
# -----------------------------------------

if __name__ == "__main__":

    print("Loading all D1 programs...")
    all_programs = build_all_d1_programs()
    print("Loaded " + str(len(all_programs)) + " programs")

    start_prestiges = {p["name"]: p["prestige_current"] for p in all_programs}

    # Simulate 3 complete seasons -- games + recruiting + lifecycle all connected
    for year in range(2024, 2027):

        all_programs, recruiting_class, cycle_summary, lifecycle_summary = simulate_world_season(
            all_programs, season_year=year, verbose=True
        )

        print_prestige_movers(all_programs, start_prestiges, year)
        start_prestiges = {p["name"]: p["prestige_current"] for p in all_programs}

    # -------------------------------------------
    # END OF 3-YEAR REPORT
    # -------------------------------------------
    print("")
    print("=" * 60)
    print("  3-YEAR WORLD SIMULATION COMPLETE")
    print("=" * 60)

    # Show Oklahoma State's full journey
    osu = next(p for p in all_programs if p["name"] == "Oklahoma State")
    print("")
    print("=== Oklahoma State -- 3-Year Journey ===")
    print("Current prestige: " + str(osu["prestige_current"]) + " (" + osu["prestige_grade"] + ")")
    print("Gravity anchor:   " + str(osu["prestige_gravity"]))
    print("Season history:")
    for s in osu.get("season_history", []):
        print("  " + str(s["year"]) + ": " + str(s["wins"]) + "-" + str(s["losses"]) +
              " (conf: " + str(s["conf_wins"]) + "-" + str(s["conf_losses"]) + ")" +
              "  Prestige: " + str(s["prestige_end"]))
    print_roster_evolution(osu)

    # Show Kentucky's roster evolution
    kentucky = next(p for p in all_programs if p["name"] == "Kentucky")
    print("")
    print("=== Kentucky -- Roster After 3 Seasons ===")
    print_roster_evolution(kentucky)
    freshmen = [p for p in kentucky["roster"] if p["year"] == "Freshman"]
    print("  Current freshmen:")
    for p in freshmen:
        print("    " + p["name"] + "  " + p["position"])

    # Thin roster warning -- any program below 8 players is a problem
    thin = [p for p in all_programs if len(p["roster"]) < 8]
    print("")
    if thin:
        print("WARNING: " + str(len(thin)) + " programs with thin rosters (<8 players):")
        for p in thin:
            print("  " + p["name"] + ": " + str(len(p["roster"])) + " players")
    else:
        print("PASS: All programs have 8+ players on roster after 3 seasons.")
