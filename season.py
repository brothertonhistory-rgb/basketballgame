import random
from game_engine import simulate_game
from program import (create_program, record_game_result, apply_gravity_pull,
                     update_prestige_for_results, get_record_string, prestige_grade,
                     apply_conference_tier_pressure)
from programs_data import (build_all_d1_programs, get_conference_ceiling,
                            get_conference_floor)
from recruiting import generate_recruiting_class, print_class_summary
from recruiting_offers import generate_offers, calculate_interest_scores
from recruiting_commitments import resolve_full_recruiting_cycle, print_cycle_summary
from lifecycle import advance_season, print_lifecycle_summary

# -----------------------------------------
# COLLEGE HOOPS SIM -- Season Calendar v0.7
# Full world simulation -- all 326 D1 programs
#
# v0.5 CHANGES -- Prestige System Overhaul:
#
#   CHANGE 3: apply_gravity_drift() slowed significantly.
#     - Min 5 seasons history before drift activates (was 3).
#     - Drift rate 1.5 (was 3.0). Annual cap +-0.75 (was +-1.5).
#     - Anchor is geological. One Cinderella run doesn't move it.
#
#   CHANGE 4: apply_universe_gravity() -- world population correction.
#     Bottom-heavy pyramid target distribution. Subtle whisper strength.
#     Conference floors always protected as hard stop.
#
#   CHANGE 5: apply_conference_tier_pressure() in pipeline.
#
# v0.6 CHANGES -- Non-conference double-counting fix:
#
#   ROOT CAUSE OF RUNAWAY PRESTIGE BUG:
#     build_non_conference_schedule() was alternating home/away and
#     calling record_game_result() on BOTH teams. This meant Texas
#     (Big 12) accumulated wins as an away team in every other
#     conference's simulation. By season end, Texas had 150+ games
#     recorded and update_prestige_for_results() saw a massive win
#     total -- gaining 28 prestige points in a single season.
#
#   FIX: Non-conference matchups always have the conference's own
#     program as HOME. record_game_result() is only called for a
#     team if they belong to the conference currently being simulated.
#     Away non-conference opponents get their result recorded when
#     their OWN conference simulation runs.
#     Called as LAST prestige step each season, after gravity drift.
#     Conference identity enforced via soft ceiling/floor.
#
# SEASON PRESTIGE PIPELINE ORDER (per program per season):
#   1. update_prestige_for_results()    -- performance delta, hard cap
#   2. apply_gravity_pull()             -- pull toward historical anchor
#   3. apply_gravity_drift()            -- slowly adjust anchor itself
#   4. apply_conference_tier_pressure() -- conf ceiling/floor enforcement
#   5. apply_universe_gravity()         -- world population correction
# -----------------------------------------

# -----------------------------------------
# UNIVERSE GRAVITY
# Bottom-heavy pyramid -- reflects real D1 population shape
# ~326 programs total
# -----------------------------------------

UNIVERSE_TIERS = [
    ("elite",       75, 100,  26),
    ("high_major",  55,  74,  49),
    ("mid_major",   35,  54,  88),
    ("low_major",   15,  34, 104),
    ("floor",        1,  14,  59),
]

UNIVERSE_NUDGE_NONE     = 0.0
UNIVERSE_NUDGE_SMALL    = 0.25
UNIVERSE_NUDGE_MODERATE = 0.50

# Gravity drift annual cap by conference tier.
# Low major anchors are nearly geological -- a MEAC dynasty earns
# maybe +1.5 points of anchor movement over a decade, not +7.
# Power conference programs have more legitimate room to grow.
GRAVITY_DRIFT_CAP = {
    "power":      0.50,
    "high_major": 0.35,
    "mid_major":  0.25,
    "low_major":  0.15,
    "floor_conf": 0.10,
}
_DEFAULT_DRIFT_CAP = 0.25


# -----------------------------------------
# SCHEDULE BUILDERS
# -----------------------------------------

def build_conference_schedule(programs):
    matchups = []
    n = len(programs)
    for i in range(n):
        for j in range(i + 1, n):
            matchups.append({"home": programs[i], "away": programs[j], "is_conference": True})
            matchups.append({"home": programs[j], "away": programs[i], "is_conference": True})
    return matchups


def build_non_conference_schedule(programs, all_programs, games_per_team=6):
    """
    Builds non-conference HOME games only for this conference's programs.

    CRITICAL FIX (v0.6): Every matchup has the conference program as HOME.
    record_game_result() is only called for the HOME team in the conference
    simulation loop. The away (opponent) team's result is NOT recorded here
    -- it gets recorded when THEIR conference simulation runs their home games.

    The old code alternated home/away and called record_game_result() on both
    teams, meaning every out-of-conference team accumulated wins from every
    other conference's simulation. Texas was showing 150+ wins/season and
    gaining 28 prestige points in one year because update_prestige_for_results()
    saw a massive win total from all these phantom games.
    """
    matchups      = []
    conf_names    = set(p["conference"] for p in programs)
    non_conf_pool = [p for p in all_programs if p["conference"] not in conf_names]

    if len(non_conf_pool) < 2:
        return matchups

    for program in programs:
        scheduled = 0
        attempts  = 0
        while scheduled < games_per_team and attempts < 200:
            attempts += 1
            limit     = 30 + random.randint(0, 30)
            candidate = random.choice(non_conf_pool)
            if candidate["name"] == program["name"]:
                continue
            if abs(candidate["prestige_current"] - program["prestige_current"]) > limit:
                continue
            # Conference program is always HOME. Away team's result recorded by their conf.
            matchups.append({"home": program, "away": candidate, "is_conference": False})
            scheduled += 1

    return matchups


# -----------------------------------------
# GRAVITY DRIFT
# -----------------------------------------

def apply_gravity_drift(program, season_year, win_pct):
    """
    Slowly adjusts gravity anchor based on rolling performance.

    v0.6: Annual drift cap is now tiered by conference tier.
    A MEAC or SWAC program winning consistently earns a tiny
    anchor nudge -- their identity is that conference. A power
    conference program has more legitimate room to grow.

    Caps by tier:
      power:      +-0.50/season  (up to +-5.0 over a decade)
      high_major: +-0.35/season  (up to +-3.5 over a decade)
      mid_major:  +-0.25/season  (up to +-2.5 over a decade)
      low_major:  +-0.15/season  (up to +-1.5 over a decade)
      floor_conf: +-0.10/season  (up to +-1.0 over a decade)
    """
    from programs_data import get_conference_tier

    if "performance_history" not in program:
        program["performance_history"] = []

    program["performance_history"].append({"year": season_year, "win_pct": round(win_pct, 3)})

    history = program["performance_history"]
    if len(history) < 5:
        return

    window           = history[-10:]
    avg_win_pct      = sum(s["win_pct"] for s in window) / len(window)
    gravity          = program["prestige_gravity"]
    expected_win_pct = 0.35 + (gravity / 100) * 0.45
    performance_gap  = avg_win_pct - expected_win_pct

    # Tier-aware annual cap -- low major anchors barely move
    tier_name = get_conference_tier(program["conference"])["tier"]
    annual_cap = GRAVITY_DRIFT_CAP.get(tier_name, _DEFAULT_DRIFT_CAP)

    gravity_delta = max(-annual_cap, min(annual_cap, performance_gap * 1.5))

    floor       = get_conference_floor(program["conference"])
    new_gravity = max(floor, min(100, gravity + gravity_delta))
    program["prestige_gravity"] = round(new_gravity, 1)


# -----------------------------------------
# UNIVERSE GRAVITY
# -----------------------------------------

def apply_universe_gravity(all_programs):
    """
    World-level population pressure toward bottom-heavy pyramid.
    Subtle whisper -- +-0.15 or +-0.30 per season.
    Conference floors always protected.
    Called once per season AFTER all individual prestige updates.
    """
    tier_counts = {}
    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        tier_counts[tier_name] = sum(
            1 for p in all_programs
            if p_min <= p["prestige_current"] <= p_max
        )

    tier_nudges = {}
    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        actual       = tier_counts[tier_name]
        overflow_pct = (actual - target) / max(1, target)
        # v0.6: Thresholds tightened (20%/40% -> 15%/30%) and nudges
        # strengthened (0.25/0.50) so mid/low tier overflow actually corrects.
        if overflow_pct >= 0.30:
            tier_nudges[tier_name] = -UNIVERSE_NUDGE_MODERATE
        elif overflow_pct >= 0.15:
            tier_nudges[tier_name] = -UNIVERSE_NUDGE_SMALL
        elif overflow_pct <= -0.30:
            tier_nudges[tier_name] = UNIVERSE_NUDGE_MODERATE
        elif overflow_pct <= -0.15:
            tier_nudges[tier_name] = UNIVERSE_NUDGE_SMALL
        else:
            tier_nudges[tier_name] = UNIVERSE_NUDGE_NONE

    for program in all_programs:
        current = program["prestige_current"]
        nudge   = 0.0
        for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
            if p_min <= current <= p_max:
                nudge = tier_nudges[tier_name]
                break
        if nudge == 0.0:
            continue
        floor        = get_conference_floor(program["conference"])
        new_prestige = max(floor, min(100, current + nudge))
        program["prestige_current"] = round(new_prestige, 1)
        program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    return all_programs


def get_universe_tier_snapshot(all_programs):
    snapshot = []
    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        actual       = sum(1 for p in all_programs if p_min <= p["prestige_current"] <= p_max)
        overflow     = actual - target
        overflow_pct = round((actual - target) / max(1, target) * 100, 1)
        snapshot.append({
            "tier": tier_name, "range": str(p_min) + "-" + str(p_max),
            "target": target, "actual": actual,
            "overflow": overflow, "overflow_pct": overflow_pct,
        })
    return snapshot


def print_tier_snapshot(all_programs, season_year):
    snapshot = get_universe_tier_snapshot(all_programs)
    total    = len(all_programs)
    print("")
    print("--- " + str(season_year) + " Universe Tier Distribution ---")
    print("{:<12} {:<8} {:<8} {:<8} {:<12} {}".format(
        "Tier", "Range", "Target", "Actual", "Overflow", "Bar"))
    print("-" * 65)
    for row in snapshot:
        overflow_str = ("+" if row["overflow"] >= 0 else "") + str(row["overflow"])
        pct_str      = ("+" if row["overflow_pct"] >= 0 else "") + str(row["overflow_pct"]) + "%"
        bar_fill     = min(40, int(row["actual"] / max(1, total) * 80))
        bar_target   = min(40, int(row["target"] / max(1, total) * 80))
        bar = "█" * bar_fill + ("░" * max(0, bar_target - bar_fill) if bar_fill < bar_target else "")
        print("{:<12} {:<8} {:<8} {:<8} {:<12} {}".format(
            row["tier"], row["range"], row["target"], row["actual"],
            overflow_str + " (" + pct_str + ")", bar))


def print_ceiling_breakers(all_programs, season_year):
    """Shows programs currently above their conference ceiling."""
    breakers = []
    for p in all_programs:
        ceiling = get_conference_ceiling(p["conference"])
        if p["prestige_current"] > ceiling and ceiling < 100:
            state = p.get("conference_tier_state", {})
            breakers.append((
                p["name"], p["conference"], ceiling,
                p["prestige_current"],
                state.get("seasons_above_ceiling", 0)
            ))
    if not breakers:
        return
    breakers.sort(key=lambda x: x[3] - x[2], reverse=True)
    print("")
    print("--- " + str(season_year) + " Programs Above Conference Ceiling ---")
    print("{:<24} {:<20} {:<8} {:<10} {:<8}".format(
        "Program", "Conference", "Ceiling", "Prestige", "Seasons"))
    print("-" * 70)
    for name, conf, ceiling, prestige, seasons in breakers[:15]:
        print("{:<24} {:<20} {:<8} {:<10} {:<8}".format(
            name, conf[:19], str(ceiling), str(prestige), str(seasons)))


# -----------------------------------------
# CONFERENCE SEASON
# -----------------------------------------

def simulate_conference_season(conference_programs, all_programs, season_year, verbose=False):
    for p in conference_programs:
        p["wins"] = 0; p["losses"] = 0
        p["conf_wins"] = 0; p["conf_losses"] = 0
        p["season_results"] = []

    conf_schedule     = build_conference_schedule(conference_programs)
    non_conf_schedule = build_non_conference_schedule(conference_programs, all_programs)
    full_schedule     = conf_schedule + non_conf_schedule
    random.shuffle(full_schedule)

    conf_program_names = set(p["name"] for p in conference_programs)

    for matchup in full_schedule:
        home   = matchup["home"]
        away   = matchup["away"]
        result = simulate_game(home, away, verbose=False)

        # Always record result for the home team if they belong to this conference
        if home["name"] in conf_program_names:
            record_game_result(home, away["name"], result["home"], result["away"],
                               is_home=True, is_conference=matchup["is_conference"])

        # Only record result for the away team if they ALSO belong to this conference
        # (i.e. conference games). Non-conference away teams get their result
        # recorded by their own conference simulation.
        if away["name"] in conf_program_names:
            record_game_result(away, home["name"], result["away"], result["home"],
                               is_home=False, is_conference=matchup["is_conference"])

    for p in conference_programs:
        games   = p["wins"] + p["losses"]
        win_pct = p["wins"] / games if games > 0 else 0.0

        # Cap games used for prestige calculation to a realistic D1 season.
        # If a program somehow accumulated extra games (scheduling artifacts),
        # we normalize to at most 36 games so inflated win totals cannot
        # inflate prestige. We preserve the win percentage, not raw wins.
        PRESTIGE_GAME_CAP = 36
        if games > PRESTIGE_GAME_CAP:
            capped_wins   = round(win_pct * PRESTIGE_GAME_CAP)
            capped_losses = PRESTIGE_GAME_CAP - capped_wins
        else:
            capped_wins   = p["wins"]
            capped_losses = p["losses"]

        made_tournament = p["conf_wins"] >= (len(conference_programs) // 2)
        tournament_wins = max(0, p["conf_wins"] - len(conference_programs) // 2)

        # Prestige pipeline steps 1-4
        update_prestige_for_results(p, capped_wins, capped_losses, made_tournament, tournament_wins)
        apply_gravity_pull(p)
        apply_gravity_drift(p, season_year, win_pct)
        apply_conference_tier_pressure(p)

        if "season_history" not in p:
            p["season_history"] = []
        p["season_history"].append({
            "year": season_year, "wins": p["wins"], "losses": p["losses"],
            "conf_wins": p["conf_wins"], "conf_losses": p["conf_losses"],
            "prestige_end": p["prestige_current"],
        })
        p["coach_seasons"] += 1

    return conference_programs


# -----------------------------------------
# WORLD SEASON
# -----------------------------------------

def simulate_world_season(all_programs, season_year, verbose=True):
    """
    Simulates a COMPLETE year for the entire world.

    Pipeline:
      Step 1 -- Minutes allocation + stat init.
      Step 2 -- Cohesion initialization (first season).
      Step 3 -- Season simulation (games + per-program prestige pipeline).
      Step 4 -- Universe gravity (world population correction).
      Step 5 -- Recruiting cycle.
      Step 6 -- Finalize season stats.
      Step 7 -- Lifecycle (graduation, aging, enrollment, cohesion).
    """
    from roster_minutes import allocate_minutes
    from cohesion import update_cohesion
    from game_engine import initialize_season_stats, finalize_season_stats

    for program in all_programs:
        allocate_minutes(program)
        if "cohesion_score" not in program:
            update_cohesion(program, previous_minutes=None)
        initialize_season_stats(program, season_year=season_year)

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

    # Step 4: Universe gravity
    apply_universe_gravity(all_programs)

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
        print("  Early signings:  " + str(len(cycle_summary["early_commits"])))
        print("  Late signings:   " + str(len(cycle_summary["late_commits"])))
        print("  Total committed: " + str(cycle_summary["total_commits"]))
        print("  Unsigned:        " + str(len(cycle_summary["unsigned"])))

    for program in all_programs:
        finalize_season_stats(program, season_year=season_year)

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


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_national_standings(all_programs, season_year):
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
            str(p["prestige_current"]) + " (" + p["prestige_grade"] + ")"))

    print("")
    print("--- " + str(season_year) + " Conference Leaders ---")
    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)
    for conf_name, conf_programs in sorted(conferences.items()):
        if not conf_programs:
            continue
        leader      = max(conf_programs, key=lambda p: (p["conf_wins"], p["wins"]))
        conf_record = str(leader["conf_wins"]) + "-" + str(leader["conf_losses"])
        overall     = str(leader["wins"]) + "-" + str(leader["losses"])
        print("{:<20} {:<22} {:<10} {:<10}".format(
            conf_name[:19], leader["name"], overall, conf_record + " conf"))


def print_prestige_movers(all_programs, start_prestiges, season_year):
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
# -----------------------------------------

if __name__ == "__main__":

    print("Loading all D1 programs...")
    all_programs = build_all_d1_programs()
    print("Loaded " + str(len(all_programs)) + " programs")

    print("")
    print("=== STARTING TIER DISTRIBUTION ===")
    print_tier_snapshot(all_programs, "PRE-SIM")
    print_ceiling_breakers(all_programs, "PRE-SIM")

    start_prestiges_global = {p["name"]: p["prestige_current"] for p in all_programs}
    start_prestiges        = {p["name"]: p["prestige_current"] for p in all_programs}

    for year in range(2024, 2030):
        all_programs, recruiting_class, cycle_summary, lifecycle_summary = simulate_world_season(
            all_programs, season_year=year, verbose=True
        )
        print_prestige_movers(all_programs, start_prestiges, year)
        print_tier_snapshot(all_programs, year)
        print_ceiling_breakers(all_programs, year)
        start_prestiges = {p["name"]: p["prestige_current"] for p in all_programs}

    print("")
    print("=" * 60)
    print("  10-YEAR WORLD SIMULATION COMPLETE")
    print("=" * 60)

    print("")
    print("=== FINAL TIER DISTRIBUTION ===")
    print_tier_snapshot(all_programs, "FINAL")

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
    print("  Avg absolute change:            " + str(round(avg_abs_change, 1)) + " points")
    print("  Max change (any program):       " + str(round(max_change, 1)) + " points")
    print("  Programs that moved 15+ points: " + str(big_movers) + " of " + str(len(all_programs)))
    print("  (Target: avg < 8, max < 20, big movers < 10% of programs)")

    sorted_by_change = sorted(
        [(p["name"], p["conference"],
          start_prestiges_global.get(p["name"], p["prestige_current"]),
          p["prestige_current"]) for p in all_programs],
        key=lambda x: abs(x[3] - x[2]), reverse=True
    )
    print("")
    print("  Top 10 programs by total movement:")
    print("  {:<24} {:<20} {:<8} {:<8} {:<8}".format(
        "Program", "Conference", "Start", "End", "Change"))
    print("  " + "-" * 68)
    for name, conf, start, end in sorted_by_change[:10]:
        change = round(end - start, 1)
        sign   = "+" if change >= 0 else ""
        print("  {:<24} {:<20} {:<8} {:<8} {:<8}".format(
            name, conf[:19], str(start), str(round(end, 1)), sign + str(change)))

    print("")
    print("=== CONFERENCE CEILING CONTAINMENT ===")
    print_ceiling_breakers(all_programs, "FINAL")

    osu = next((p for p in all_programs if p["name"] == "Oklahoma State"), None)
    if osu:
        print("")
        print("=== Oklahoma State -- 10-Year Journey ===")
        print("Start: " + str(start_prestiges_global.get("Oklahoma State", "?")))
        print("End:   " + str(osu["prestige_current"]) + " (" + osu["prestige_grade"] + ")")
        print("Anchor:" + str(osu["prestige_gravity"]))
        for s in osu.get("season_history", []):
            print("  " + str(s["year"]) + ": " + str(s["wins"]) + "-" + str(s["losses"]) +
                  "  Prestige: " + str(s["prestige_end"]))

    kentucky = next((p for p in all_programs if p["name"] == "Kentucky"), None)
    if kentucky:
        print("")
        print("=== Kentucky -- Roster After 10 Seasons ===")
        print_roster_evolution(kentucky)

    thin = [p for p in all_programs if len(p["roster"]) < 8]
    print("")
    if thin:
        print("WARNING: " + str(len(thin)) + " programs with thin rosters (<8 players):")
        for p in thin:
            print("  " + p["name"] + ": " + str(len(p["roster"])) + " players")
    else:
        print("PASS: All programs have 8+ players after 10 seasons.")
