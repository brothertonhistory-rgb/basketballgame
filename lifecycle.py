# -----------------------------------------
# COLLEGE HOOPS SIM -- Player Lifecycle v0.6
# Closes the loop between recruiting and rosters.
#
# Called once per season, AFTER simulate_world_season()
# and AFTER resolve_full_recruiting_cycle().
#
# Order of operations every season turnover:
#   1. Develop returning players
#   2. Graduate seniors
#   3. Age remaining players
#   4. Enroll committed recruits        <-- v0.6: stamp recruited_by here
#   5. Reset recruiting state
#   6. POST-ENROLLMENT ROSTER FLOOR CHECK
#   7. Allocate minutes for new roster
#   8. Update cohesion
#
# v0.6 CHANGES -- recruited_by stamping:
#
#   When a recruit enrolls, their player dict gets:
#     player["recruited_by"] = coach["coach_id"]
#
#   This is the key relationship that coaching_carousel.py uses for:
#     - Portal wave probability (anchor lost when coach leaves)
#     - Poach check (coach pulls former players to new school)
#
#   Floor fill enrollments also get stamped.
#
# v0.5 CHANGES (preserved):
#   Post-enrollment roster floor check.
#   roster_fill_aggressiveness drives talent bar.
# -----------------------------------------

from player import create_player, develop_player

YEAR_PROGRESSION = {
    "Freshman":  "Sophomore",
    "Sophomore": "Junior",
    "Junior":    "Senior",
    "Senior":    "Senior",
}

ROSTER_FLOOR_CONFIG = {
    "power":      {"target": 12, "floor": 10},
    "high_major": {"target": 12, "floor": 11},
    "mid_major":  {"target": 13, "floor": 11},
    "low_major":  {"target": 13, "floor": 11},
    "floor_conf": {"target": 13, "floor": 11},
}
_DEFAULT_FLOOR_CONFIG = {"target": 13, "floor": 11}

AGGRESSIVENESS_TALENT_BAR = {
    "high":   5,
    "medium": 10,
    "low":    20,
}


def _get_aggressiveness_tier(aggressiveness):
    if aggressiveness >= 7: return "high"
    if aggressiveness >= 4: return "medium"
    return "low"


def _get_floor_config(conference):
    from programs_data import get_conference_tier
    tier_name = get_conference_tier(conference)["tier"]
    return ROSTER_FLOOR_CONFIG.get(tier_name, _DEFAULT_FLOOR_CONFIG)


# -----------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------

def advance_season(all_programs, recruiting_class, season_year=2025):
    """
    Call this once per year after the season and recruiting cycle are done.
    Returns (all_programs, lifecycle_summary).
    """
    from roster_minutes import allocate_minutes
    from cohesion import update_cohesion

    total_graduated     = 0
    total_enrolled      = 0
    total_floor_fills   = 0
    total_developed     = 0
    total_breakthroughs = 0
    breakthrough_log    = []
    program_reports     = []

    unsigned_pool = [
        r for r in recruiting_class
        if r.get("status") in ("unsigned", "available")
    ]
    unsigned_pool.sort(key=lambda r: r.get("true_talent", 0), reverse=True)

    for program in all_programs:
        coach = program.get("coach", {})

        previous_minutes = dict(program.get("minutes_allocation", {}))

        # --- STEP 1: DEVELOP ---
        dev_count, bt_count, bt_events = _develop_roster(
            program, coach, season_year
        )
        total_developed     += dev_count
        total_breakthroughs += bt_count
        breakthrough_log.extend(bt_events)

        # --- STEP 2: GRADUATE SENIORS ---
        graduated = _graduate_seniors(program)

        # --- STEP 3: AGE ---
        _age_roster(program)

        # --- STEP 4: ENROLL COMMITTED RECRUITS ---
        enrolled = _enroll_recruits(program, recruiting_class)

        # --- STEP 5: RESET RECRUITING STATE ---
        _reset_recruiting_state(program)

        # --- STEP 6: ROSTER FLOOR CHECK ---
        floor_filled = _enforce_roster_floor(program, coach, unsigned_pool)
        total_floor_fills += floor_filled
        enrolled += floor_filled

        # --- STEP 7: ALLOCATE MINUTES ---
        allocate_minutes(program)

        # --- STEP 8: UPDATE COHESION ---
        update_cohesion(program, previous_minutes=previous_minutes)

        total_graduated += graduated
        total_enrolled  += enrolled

        program_reports.append({
            "name":          program["name"],
            "graduated":     graduated,
            "enrolled":      enrolled,
            "floor_filled":  floor_filled,
            "roster_size":   len(program["roster"]),
            "developed":     dev_count,
            "breakthroughs": bt_count,
            "cohesion":      program.get("cohesion_score", 50),
            "cohesion_tier": program.get("cohesion_tier", "average"),
            "combo_bonds":   len(program.get("combo_bonds", [])),
        })

    summary = {
        "total_graduated":     total_graduated,
        "total_enrolled":      total_enrolled,
        "total_floor_fills":   total_floor_fills,
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
    dev_count           = 0
    bt_count            = 0
    breakthrough_events = []

    for player in program["roster"]:
        player, report = develop_player(
            player, coach, season_year,
            training_focus=None,
            morale_modifier=1.0,
        )

        if report["total_gain"] > 0:
            dev_count += 1

        if report["breakthrough"]:
            bt_count += 1
            breakthrough_events.append({
                "program":    program["name"],
                "player":     player["name"],
                "position":   player["position"],
                "year":       player["year"],
                "arc_type":   player["arc_type"],
                "attrs":      report["breakthrough_attrs"],
                "total_gain": report["total_gain"],
            })

    return dev_count, bt_count, breakthrough_events


# -----------------------------------------
# STEP 2: GRADUATE SENIORS
# -----------------------------------------

def _graduate_seniors(program):
    seniors = [p for p in program["roster"] if p.get("year", "") == "Senior"]
    program["roster"] = [p for p in program["roster"] if p.get("year", "") != "Senior"]
    return len(seniors)


# -----------------------------------------
# STEP 3: AGE REMAINING PLAYERS
# -----------------------------------------

def _age_roster(program):
    for player in program["roster"]:
        current_year = player.get("year", "Freshman")
        player["year"] = YEAR_PROGRESSION.get(current_year, "Sophomore")


# -----------------------------------------
# STEP 4: ENROLL COMMITTED RECRUITS
# v0.6: stamp recruited_by = current coach_id on every enrollee
# -----------------------------------------

def _enroll_recruits(program, recruiting_class):
    program_name = program["name"]
    coach        = program.get("coach", {})
    coach_id     = coach.get("coach_id", None)   # v0.6: for recruited_by stamp

    incoming = [
        r for r in recruiting_class
        if r.get("committed_to") == program_name
        and r.get("status") == "committed"
    ]

    enrolled = 0
    for recruit in incoming:
        if len(program["roster"]) >= 13:
            break
        player = _recruit_to_player(recruit, program.get("conference", ""))

        # v0.6: stamp the recruiting coach's ID on this player
        player["recruited_by"] = coach_id

        program["roster"].append(player)
        recruit["status"] = "enrolled"
        enrolled += 1

    return enrolled


# -----------------------------------------
# STEP 6: ROSTER FLOOR CHECK (v0.5)
# v0.6: stamp recruited_by on floor-fill enrollees too
# -----------------------------------------

def _enforce_roster_floor(program, coach, unsigned_pool):
    conference   = program.get("conference", "")
    floor_config = _get_floor_config(conference)
    target       = floor_config["target"]
    abs_floor    = floor_config["floor"]
    coach_id     = coach.get("coach_id", None)   # v0.6

    current_size = len(program["roster"])

    if current_size >= target:
        return 0

    aggressiveness = coach.get("roster_fill_aggressiveness", 5)
    agg_tier       = _get_aggressiveness_tier(aggressiveness)
    talent_bar     = AGGRESSIVENESS_TALENT_BAR[agg_tier]

    enrolled = 0

    pos_counts = {}
    for p in program["roster"]:
        pos = p.get("position", "SF")
        pos_counts[pos] = pos_counts.get(pos, 0) + 1

    position_needs = {
        "PG": max(0, 2 - pos_counts.get("PG", 0)),
        "SG": max(0, 2 - pos_counts.get("SG", 0)),
        "SF": max(0, 3 - pos_counts.get("SF", 0)),
        "PF": max(0, 3 - pos_counts.get("PF", 0)),
        "C":  max(0, 2 - pos_counts.get("C",  0)),
    }

    slots_to_fill = min(target, 13) - current_size
    slots_to_fill = max(0, slots_to_fill)

    for _ in range(slots_to_fill):
        if len(program["roster"]) >= min(target, 13):
            break

        current_size    = len(program["roster"])
        below_abs_floor = current_size < abs_floor
        effective_bar   = 0 if below_abs_floor else talent_bar

        filled = False

        sorted_needs = sorted(
            position_needs.items(), key=lambda x: x[1], reverse=True
        )

        for pos, need in sorted_needs:
            if need <= 0:
                continue
            for i, recruit in enumerate(unsigned_pool):
                if recruit.get("status") not in ("unsigned", "available"):
                    continue
                if recruit.get("position") != pos:
                    continue
                if recruit.get("true_talent", 0) < effective_bar:
                    continue

                player = _recruit_to_player(recruit, program.get("conference", ""))
                player["recruited_by"] = coach_id   # v0.6 stamp
                program["roster"].append(player)
                recruit["status"] = "enrolled"
                recruit["committed_to"] = program["name"]
                unsigned_pool.pop(i)
                position_needs[pos] = max(0, position_needs[pos] - 1)
                enrolled += 1
                filled = True
                break

            if filled:
                break

        if not filled:
            for i, recruit in enumerate(unsigned_pool):
                if recruit.get("status") not in ("unsigned", "available"):
                    continue
                if recruit.get("true_talent", 0) < effective_bar:
                    continue

                player = _recruit_to_player(recruit, program.get("conference", ""))
                player["recruited_by"] = coach_id   # v0.6 stamp
                program["roster"].append(player)
                recruit["status"] = "enrolled"
                recruit["committed_to"] = program["name"]
                unsigned_pool.pop(i)
                pos = recruit.get("position", "SF")
                position_needs[pos] = max(0, position_needs.get(pos, 0) - 1)
                enrolled += 1
                filled = True
                break

        if not filled:
            break

    return enrolled


def _recruit_to_player(recruit, conference=""):
    player = create_player(
        name       = recruit["name"],
        position   = recruit["position"],
        year       = "Freshman",
        conference = conference,
        heritage   = recruit.get("heritage"),
        shooting = {
            "catch_and_shoot": recruit.get("catch_and_shoot", 500),
            "off_dribble":     recruit.get("off_dribble",     500),
            "mid_range":       recruit.get("mid_range",       500),
            "three_point":     recruit.get("three_point",     500),
            "free_throw":      recruit.get("free_throw",      500),
            "finishing":       recruit.get("finishing",       500),
            "post_scoring":    recruit.get("post_scoring",    500),
        },
        defense = {
            "on_ball_defense": recruit.get("on_ball_defense", 500),
            "help_defense":    recruit.get("help_defense",    500),
            "shot_blocking":   recruit.get("shot_blocking",   500),
            "steal_tendency":  recruit.get("steal_tendency",  500),
            "foul_tendency":   recruit.get("foul_tendency",   500),
        },
        rebounding  = recruit.get("rebounding", 500),
        playmaking  = {
            "passing":         recruit.get("passing",         500),
            "ball_handling":   recruit.get("ball_handling",   500),
            "court_vision":    recruit.get("court_vision",    500),
            "decision_making": recruit.get("decision_making", 500),
        },
        athleticism = {
            "speed":             recruit.get("speed",             500),
            "lateral_quickness": recruit.get("lateral_quickness", 500),
            "strength":          recruit.get("strength",          500),
            "vertical":          recruit.get("vertical",          500),
            "endurance":         recruit.get("endurance",         500),
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
    program["recruiting_board"]   = []
    program["committed_recruits"] = []


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_lifecycle_summary(lifecycle_summary, season_year):
    print("")
    print("=" * 60)
    print("  " + str(season_year) + " SEASON TURNOVER -- ROSTER LIFECYCLE")
    print("=" * 60)
    print("  Players graduated:   " + str(lifecycle_summary["total_graduated"]))
    print("  Recruits enrolled:   " + str(lifecycle_summary["total_enrolled"]))
    print("  Floor fills:         " + str(lifecycle_summary.get("total_floor_fills", 0)))
    print("  Players developed:   " + str(lifecycle_summary["total_developed"]))
    print("  Breakthroughs:       " + str(lifecycle_summary["total_breakthroughs"]))

    thin_rosters = [
        r for r in lifecycle_summary["program_reports"]
        if r["roster_size"] < 10
    ]
    if thin_rosters:
        print("")
        print("  WARNING -- programs below absolute floor (<10 players):")
        for r in thin_rosters:
            print("    " + r["name"] + ": " + str(r["roster_size"]) + " players")

    bt_log = lifecycle_summary.get("breakthrough_log", [])
    if bt_log:
        print("")
        print("  BREAKTHROUGH PLAYERS this offseason:")
        for bt in bt_log[:15]:
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
        floor_note = (" [+" + str(r["floor_filled"]) + " floor]"
                      if r.get("floor_filled", 0) > 0 else "")
        print("    " + r["name"].ljust(24) +
              str(r["enrolled"]) + " enrolled" + floor_note +
              "  |  " + str(r["roster_size"]) + " on roster")


def print_program_roster_state(program):
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

    print("Running lifecycle with recruited_by stamping...")
    all_programs, lifecycle_summary = advance_season(
        all_programs, recruiting_class, season_year=2025
    )

    print_lifecycle_summary(lifecycle_summary, season_year=2025)

    print("")
    print("=== RECRUITED_BY STAMP VERIFICATION ===")
    stamped   = 0
    unstamped = 0
    for prog in all_programs:
        coach_id = prog.get("coach", {}).get("coach_id")
        for player in prog.get("roster", []):
            if player.get("year") == "Freshman":
                if player.get("recruited_by") == coach_id:
                    stamped += 1
                else:
                    unstamped += 1
    print("  Freshmen with correct recruited_by stamp: " + str(stamped))
    print("  Freshmen missing stamp:                   " + str(unstamped))

    print("")
    print("=== ROSTER FLOOR VERIFICATION ===")
    thin = [p for p in all_programs if len(p.get("roster", [])) < 10]
    if thin:
        print("FAIL: " + str(len(thin)) + " programs below absolute floor:")
        for p in thin:
            print("  " + p["name"] + ": " + str(len(p["roster"])) + " players")
    else:
        print("PASS: All programs at 10+ players.")
