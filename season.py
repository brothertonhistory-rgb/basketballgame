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
# COLLEGE HOOPS SIM -- Season Calendar v0.5
# Full world simulation -- all 326 D1 programs
# All conferences simulate simultaneously
#
# v0.5 CHANGES -- Prestige Stability Overhaul (Part 2):
#
#   CHANGE 3: apply_gravity_drift() slowed significantly.
#     - Minimum history window raised from 3 seasons to 5.
#       Gravity anchors do not move until there is a real performance
#       trend, not a single Cinderella run.
#     - Drift rate cut from 3.0 to 1.5. The anchor moves like a
#       glacier. A sustained 10-year overperformance might earn a
#       program +5 to +8 anchor points. A single hot stretch earns
#       almost nothing.
#     - Annual drift cap tightened from ±1.5 to ±0.75 per season.
#       Even if a program dominates for a decade, the anchor moves
#       slowly.
#
#   CHANGE 4: apply_universe_gravity() -- new function.
#     The world has a target prestige distribution (bottom-heavy
#     pyramid reflecting real D1). Each season, tiers that are
#     overpopulated apply a gentle additional nudge pushing programs
#     back toward the correct population shape.
#     Strength: subtle whisper. Noticeable over 10+ seasons.
#     Conference floors always win as a hard stop.
#     See UNIVERSE_TIERS and UNIVERSE_NUDGE_STRENGTH below.
# -----------------------------------------


# -----------------------------------------
# UNIVERSE GRAVITY CONSTANTS
# Bottom-heavy pyramid -- reflects real D1 population shape
# Target counts based on ~326 programs
# -----------------------------------------

UNIVERSE_TIERS = [
    # (tier_name, prestige_min, prestige_max, target_count)
    ("elite",      75, 100,  26),
    ("high_major", 55,  74,  49),
    ("mid_major",  35,  54,  88),
    ("low_major",  15,  34, 104),
    ("floor",       1,  14,  59),
]

# Nudge strength by overflow severity.
# If a tier is within 20% of target: no nudge.
# If 20-40% over target: small nudge.
# If 40%+ over target: moderate nudge.
# These are intentionally tiny -- whisper, not shout.
UNIVERSE_NUDGE_NONE    = 0.0
UNIVERSE_NUDGE_SMALL   = 0.15   # tier is 20-40% overpopulated
UNIVERSE_NUDGE_MODERATE = 0.30  # tier is 40%+ overpopulated


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
        games   = p["wins"] + p["losses"]
        win_pct = p["wins"] / games if games > 0 else 0.0

        made_tournament = p["conf_wins"] >= (len(conference_programs) // 2)
        tournament_wins = max(0, p["conf_wins"] - len(conference_programs) // 2)

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
    """
    Slowly adjusts the gravity anchor based on rolling performance history.

    v0.5 changes:
      - Minimum history window raised from 3 to 5 seasons.
        No drift until a real trend exists.
      - Drift rate cut from 3.0 to 1.5.
      - Annual cap tightened from ±1.5 to ±0.75 per season.

    The anchor is geological. A Cinderella season does not move it.
    A sustained decade of overperformance moves it meaningfully but slowly.
    Conference floor always protects the lower bound.
    """
    if "performance_history" not in program:
        program["performance_history"] = []

    program["performance_history"].append({
        "year": season_year, "win_pct": round(win_pct, 3)
    })

    history = program["performance_history"]

    # v0.5: require 5 seasons of history before drift activates (was 3)
    if len(history) < 5:
        return

    window           = history[-10:]
    avg_win_pct      = sum(s["win_pct"] for s in window) / len(window)
    gravity          = program["prestige_gravity"]
    expected_win_pct = 0.35 + (gravity / 100) * 0.45
    performance_gap  = avg_win_pct - expected_win_pct

    # v0.5: rate cut from 3.0 to 1.5, cap cut from ±1.5 to ±0.75
    gravity_delta = max(-0.75, min(0.75, performance_gap * 1.5))

    from programs_data import CONFERENCE_FLOORS
    floor      = CONFERENCE_FLOORS.get(program["conference"], 15)
    new_gravity = max(floor, min(100, program["prestige_gravity"] + gravity_delta))
    program["prestige_gravity"] = round(new_gravity, 1)


def apply_universe_gravity(all_programs):
    """
    Applies world-level population pressure to prestige values.

    The D1 world has a natural shape: bottom-heavy pyramid.
    If too many programs crowd into a tier, each program in that
    tier gets a gentle additional nudge back toward the correct
    population shape.

    Strength: subtle whisper. ±0.15 or ±0.30 per season.
    Over 10+ seasons this creates 1.5-3.0 points of cumulative
    pressure on overcrowded tiers. Barely visible year to year.

    Conference floors always win as a hard stop.
    Called once per season in simulate_world_season(), after all
    individual prestige updates are complete.

    Returns all_programs (modified in place).
    """
    from programs_data import CONFERENCE_FLOORS

    # --- COUNT ACTUAL POPULATION PER TIER ---
    tier_counts = {}
    program_tiers = {}   # program_name -> (tier_name, target_count)

    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        count = sum(
            1 for p in all_programs
            if p_min <= p["prestige_current"] <= p_max
        )
        tier_counts[tier_name] = count

    # --- CALCULATE NUDGE PER TIER ---
    tier_nudges = {}
    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        actual  = tier_counts[tier_name]
        if target == 0:
            tier_nudges[tier_name] = UNIVERSE_NUDGE_NONE
            continue

        overflow_pct = (actual - target) / target   # positive = overcrowded

        if overflow_pct >= 0.40:
            # 40%+ over target: moderate nudge pushing programs down
            tier_nudges[tier_name] = -UNIVERSE_NUDGE_MODERATE
        elif overflow_pct >= 0.20:
            # 20-40% over target: small nudge pushing programs down
            tier_nudges[tier_name] = -UNIVERSE_NUDGE_SMALL
        elif overflow_pct <= -0.40:
            # 40%+ under target: moderate nudge pulling programs up
            tier_nudges[tier_name] = UNIVERSE_NUDGE_MODERATE
        elif overflow_pct <= -0.20:
            # 20-40% under target: small nudge pulling programs up
            tier_nudges[tier_name] = UNIVERSE_NUDGE_SMALL
        else:
            # Within 20% of target: no nudge
            tier_nudges[tier_name] = UNIVERSE_NUDGE_NONE

    # --- APPLY NUDGE TO EACH PROGRAM ---
    for program in all_programs:
        current = program["prestige_current"]

        # Find which tier this program is in
        nudge = 0.0
        for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
            if p_min <= current <= p_max:
                nudge = tier_nudges[tier_name]
                break

        if nudge == 0.0:
            continue

        # Conference floor always wins -- never push below floor
        floor       = CONFERENCE_FLOORS.get(program["conference"], 15)
        new_prestige = current + nudge
        new_prestige = max(floor, min(100, new_prestige))

        program["prestige_current"] = round(new_prestige, 1)
        program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    return all_programs


def get_universe_tier_snapshot(all_programs):
    """
    Returns a dict showing current population vs target for each tier.
    Used for reporting and debugging.
    """
    snapshot = []
    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        actual = sum(
            1 for p in all_programs
            if p_min <= p["prestige_current"] <= p_max
        )
        overflow = actual - target
        overflow_pct = round((actual - target) / max(1, target) * 100, 1)
        snapshot.append({
            "tier":         tier_name,
            "range":        str(p_min) + "-" + str(p_max),
            "target":       target,
            "actual":       actual,
            "overflow":     overflow,
            "overflow_pct": overflow_pct,
        })
    return snapshot


def print_tier_snapshot(all_programs, season_year):
    """Prints the universe tier population snapshot."""
    snapshot = get_universe_tier_snapshot(all_programs)
    total    = len(all_programs)

    print("")
    print("--- " + str(season_year) + " Universe Tier Distribution ---")
    print("{:<12} {:<8} {:<8} {:<8} {:<10} {}".format(
        "Tier", "Range", "Target", "Actual", "Overflow", "Bar"))
    print("-" * 65)
    for row in snapshot:
        overflow_str = ("+" if row["overflow"] >= 0 else "") + str(row["overflow"])
        overflow_pct_str = ("+" if row["overflow_pct"] >= 0 else "") + str(row["overflow_pct"]) + "%"
        bar_fill  = min(40, int(row["actual"] / max(1, total) * 80))
        bar_target = min(40, int(row["target"] / max(1, total) * 80))
        bar = "█" * bar_fill + ("░" * max(0, bar_target - bar_fill) if bar_fill < bar_target else "")
        print("{:<12} {:<8} {:<8} {:<8} {:<10} {}".format(
            row["tier"],
            row["range"],
            row["target"],
            row["actual"],
            overflow_str + " (" + overflow_pct_str + ")",
            bar,
        ))


def simulate_world_season(all_programs, season_year, verbose=True):
    """
    Simulates a COMPLETE year for the entire world.

    Step 1 -- Minutes allocation + stat initialization.
    Step 2 -- Cohesion initialization (first season only).
    Step 3 -- Season simulation: every conference plays its full schedule.
    Step 4 -- Universe gravity: world-level population pressure applied.
    Step 5 -- Recruiting cycle: offers, interest, commitments.
    Step 6 -- Finalize season stats.
    Step 7 -- Lifecycle: graduation, aging, enrollment, cohesion update.

    Returns (all_programs, recruiting_class, cycle_summary, lifecycle_summary)
    """
    from roster_minutes import allocate_minutes
    from cohesion import update_cohesion
    from game_engine import initialize_season_stats, finalize_season_stats

    # -------------------------------------------
    # STEP 1: MINUTES ALLOCATION + STAT INIT
    # -------------------------------------------
    for program in all_programs:
        allocate_minutes(program)
        if "cohesion_score" not in program:
            update_cohesion(program, previous_minutes=None)
        initialize_season_stats(program, season_year=season_year)

    # -------------------------------------------
    # STEP 3: SEASON SIMULATION
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
    # STEP 4: UNIVERSE GRAVITY
    # Applied after all individual prestige updates are done.
    # Subtle population-level pressure toward the target distribution.
    # -------------------------------------------
    apply_universe_gravity(all_programs)

    # -------------------------------------------
    # STEP 5: RECRUITING CYCLE
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
    # STEP 6: FINALIZE SEASON STATS
    # Must happen before lifecycle so graduating seniors
    # get their career stats archived before they leave
    # -------------------------------------------
    for program in all_programs:
        finalize_season_stats(program, season_year=season_year)

    # -------------------------------------------
    # STEP 7: LIFECYCLE -- graduation, aging, enrollment, cohesion
    # -------------------------------------------
    if verbose:
        print("")
        print("--- " + str(season_year) + " Roster Turnover ---")

    all_programs, lifecycle_summary = advance_season(all_programs, recruiting_class)

    if verbose:
        print("  Seniors graduated: " + str(lifecycle_summary["total_graduated"]))
        print("  Recruits enrolled: " + str(lifecycle_summary["total_enrolled"]))

        reports = lifecycle_summary.get("program_reports", [])
        if reports:
            avg_cohesion = sum(r.get("cohesion", 50) for r in reports) / len(reports)
            high_coh     = [r for r in reports if r.get("cohesion_tier") in ("very_high", "high")]
            low_coh      = [r for r in reports if r.get("cohesion_tier") in ("low", "very_low")]
            total_bonds  = sum(r.get("combo_bonds", 0) for r in reports)
            print("  Avg cohesion:      " + str(round(avg_cohesion, 1)) + "/100")
            print("  High cohesion:     " + str(len(high_coh)) + " programs")
            print("  Low cohesion:      " + str(len(low_coh)) + " programs")
            print("  Veteran bonds:     " + str(total_bonds) + " total")

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
        start  = start_prestiges.get(p["name"], p["prestige_current"])
        change = p["prestige_current"] - start
        changes.append((p["name"], p["conference"], start, p["prestige_current"], change))

    changes.sort(key=lambda x: x[4], reverse=True)

    print("")
    print("--- " + str(season_year) + " Biggest Prestige Movers ---")
    print("Top 10 risers:")
    for name, conf, start, end, change in changes[:10]:
        print("  +" + str(round(change, 1)) + "  " + name +
              " (" + conf + ")  " + str(start) + " -> " + str(end))
    print("Top 10 fallers:")
    for name, conf, start, end, change in changes[-10:]:
        print("  " + str(round(change, 1)) + "  " + name +
              " (" + conf + ")  " + str(start) + " -> " + str(end))


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
# TEST -- 10-season world simulation
# Long enough for universe gravity and drift changes to show their effect.
# Watch the tier distribution stabilize over time.
# -----------------------------------------

if __name__ == "__main__":

    print("Loading all D1 programs...")
    all_programs = build_all_d1_programs()
    print("Loaded " + str(len(all_programs)) + " programs")

    # Snapshot starting distribution
    print("")
    print("=== STARTING TIER DISTRIBUTION ===")
    print_tier_snapshot(all_programs, "PRE-SIM")

    start_prestiges_global = {p["name"]: p["prestige_current"] for p in all_programs}
    start_prestiges        = {p["name"]: p["prestige_current"] for p in all_programs}

    # -------------------------------------------
    # 10-SEASON SIMULATION
    # -------------------------------------------
    for year in range(2024, 2034):

        all_programs, recruiting_class, cycle_summary, lifecycle_summary = simulate_world_season(
            all_programs, season_year=year, verbose=True
        )

        print_prestige_movers(all_programs, start_prestiges, year)
        print_tier_snapshot(all_programs, year)

        start_prestiges = {p["name"]: p["prestige_current"] for p in all_programs}

    # -------------------------------------------
    # 10-YEAR FINAL REPORT
    # -------------------------------------------
    print("")
    print("=" * 60)
    print("  10-YEAR WORLD SIMULATION COMPLETE")
    print("=" * 60)

    print("")
    print("=== FINAL TIER DISTRIBUTION (vs starting) ===")
    print_tier_snapshot(all_programs, "FINAL")

    # Overall prestige stability check -- how much did programs move?
    all_changes = []
    for p in all_programs:
        start  = start_prestiges_global.get(p["name"], p["prestige_current"])
        change = p["prestige_current"] - start
        all_changes.append(abs(change))

    avg_abs_change = sum(all_changes) / max(1, len(all_changes))
    max_change     = max(all_changes)
    big_movers     = sum(1 for c in all_changes if c > 15)

    print("")
    print("=== PRESTIGE STABILITY OVER 10 SEASONS ===")
    print("  Avg absolute prestige change:  " + str(round(avg_abs_change, 1)) + " points")
    print("  Max prestige change (any program): " + str(round(max_change, 1)) + " points")
    print("  Programs that moved 15+ points:    " + str(big_movers) +
          " of " + str(len(all_programs)))
    print("  (Target: avg < 8, max < 20, big movers < 10% of programs)")

    # Show programs that moved the most -- should be mid-tier programs
    # not already-elite programs that shouldn't be reshaping
    sorted_by_change = sorted(
        [(p["name"], p["conference"],
          start_prestiges_global.get(p["name"], p["prestige_current"]),
          p["prestige_current"]) for p in all_programs],
        key=lambda x: abs(x[3] - x[2]),
        reverse=True
    )
    print("")
    print("  Top 10 programs by total prestige movement (10 years):")
    print("  {:<24} {:<20} {:<10} {:<10} {:<8}".format(
        "Program", "Conference", "Start", "End", "Change"))
    print("  " + "-" * 72)
    for name, conf, start, end in sorted_by_change[:10]:
        change = round(end - start, 1)
        sign   = "+" if change >= 0 else ""
        print("  {:<24} {:<20} {:<10} {:<10} {:<8}".format(
            name, conf[:19], str(start), str(round(end, 1)),
            sign + str(change)
        ))

    # Oklahoma State 10-year journey
    osu = next((p for p in all_programs if p["name"] == "Oklahoma State"), None)
    if osu:
        print("")
        print("=== Oklahoma State -- 10-Year Journey ===")
        print("Start prestige: " + str(start_prestiges_global.get("Oklahoma State", "?")))
        print("End prestige:   " + str(osu["prestige_current"]) + " (" + osu["prestige_grade"] + ")")
        print("Gravity anchor: " + str(osu["prestige_gravity"]))
        print("Season history:")
        for s in osu.get("season_history", []):
            print("  " + str(s["year"]) + ": " + str(s["wins"]) + "-" + str(s["losses"]) +
                  " (conf: " + str(s["conf_wins"]) + "-" + str(s["conf_losses"]) + ")" +
                  "  Prestige: " + str(s["prestige_end"]))

    # Kentucky roster check
    kentucky = next((p for p in all_programs if p["name"] == "Kentucky"), None)
    if kentucky:
        print("")
        print("=== Kentucky -- Roster After 10 Seasons ===")
        print_roster_evolution(kentucky)

    # Thin roster warning
    thin = [p for p in all_programs if len(p["roster"]) < 8]
    print("")
    if thin:
        print("WARNING: " + str(len(thin)) + " programs with thin rosters (<8 players):")
        for p in thin:
            print("  " + p["name"] + ": " + str(len(p["roster"])) + " players")
    else:
        print("PASS: All programs have 8+ players after 10 seasons.")
