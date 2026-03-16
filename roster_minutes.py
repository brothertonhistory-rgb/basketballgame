import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Roster Minutes v1.0
# System 4 support module
#
# Allocates minutes per game to every player on the roster.
# Called once per season at season start, before games are simulated.
# Results stored on the program dict and used by:
#   - cohesion.py (duo/unit bond calculation)
#   - develop_player() (playing time is primary development driver)
#   - game_engine.py (future: individual player game impact)
#
# ALLOCATION MODEL:
#   Total minutes per game = 200 (5 players * 40 min)
#   Coach's rotation_size determines how many players get meaningful minutes.
#   Players are ranked by overall quality at their position.
#   Minutes follow a decay curve from starters down to bench.
#   Endurance modifies the curve -- high-endurance players can sustain
#   more minutes without performance decay.
#
# THRESHOLDS (for cohesion duo qualification):
#   Starter:          28+ minutes per game
#   Heavy rotation:   20-27 minutes per game
#   Rotation:         12-19 minutes per game
#   Bench:            under 12 minutes per game
#
# ENDURANCE INTERACTION:
#   A coach with a high-pace system and limited endurance players is
#   forced to go deeper into the rotation or accept fatigue penalties.
#   rotation_size is adjusted upward if average endurance is low.
#
# SEASON-LONG FATIGUE: FUTURE HOOK
#   cumulative_minutes tracked but not yet used as a penalty.
#   When season-long fatigue is built, this feeds directly into it.
# -----------------------------------------

# Minutes thresholds
STARTER_THRESHOLD       = 28
HEAVY_ROTATION_THRESHOLD = 20
ROTATION_THRESHOLD      = 12

# Total minutes available per game (5 players * 40 minutes)
TOTAL_GAME_MINUTES = 200

# Endurance threshold below which a coach is forced to expand rotation
# A player averaging 30+ min/game needs endurance above this or they
# drag down in the 4th quarter
LOW_ENDURANCE_THRESHOLD = 400


def allocate_minutes(program):
    """
    Allocates average minutes per game to every player on the roster.

    Uses:
      - Player overall quality at their position (primary sort)
      - Player endurance (modifies sustainability at high minutes)
      - Coach rotation_size (how many players get real time)
      - Coach rotation_flexibility (how rigid the distribution is)
      - Coach pace (high pace = more minutes pressure = endurance matters more)

    Stores results on program["minutes_allocation"]:
      { player_name: avg_minutes_per_game }

    Also stores program["rotation_order"]:
      List of player names in rotation order (best to last)

    Returns program (modified in place).
    """
    roster = program.get("roster", [])
    if not roster:
        program["minutes_allocation"] = {}
        program["rotation_order"]     = []
        return program

    coach             = program.get("coach", {})
    rotation_size     = coach.get("rotation_size", 8)
    rotation_flex     = coach.get("rotation_flexibility", 5)   # 1-10
    pace              = coach.get("pace", 50)                  # 1-100

    # --- RANK PLAYERS BY QUALITY ---
    ranked = _rank_roster(roster)

    # --- ENDURANCE ADJUSTMENT ---
    # If pace is high and average endurance of top players is low,
    # the coach is forced to go deeper into the rotation
    adjusted_rotation = _adjust_rotation_for_endurance(
        ranked, rotation_size, pace
    )

    # --- DISTRIBUTE MINUTES ---
    minutes = _distribute_minutes(
        ranked, adjusted_rotation, rotation_flex, TOTAL_GAME_MINUTES
    )

    program["minutes_allocation"] = minutes
    program["rotation_order"]     = [p["name"] for p in ranked]

    return program


def _rank_roster(roster):
    """
    Ranks players by overall quality at their position.
    Returns sorted list of player dicts (best first).

    Quality = weighted average of position-primary attributes.
    Endurance is NOT a quality factor -- it's a sustainability factor.
    """
    from recruiting import POSITION_ARCHETYPES

    scored = []
    for player in roster:
        pos     = player.get("position", "SF")
        arch    = POSITION_ARCHETYPES.get(pos, {})
        primary = arch.get("primary", [])

        if primary:
            quality = sum(player.get(a, 400) for a in primary) / len(primary)
        else:
            quality = 400

        # Small noise so identical players don't always sort the same way
        quality += random.gauss(0, 10)

        scored.append((player, quality))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored]


def _adjust_rotation_for_endurance(ranked, rotation_size, pace):
    """
    Adjusts effective rotation size based on endurance of top players.

    High pace + low endurance in starters = forced deeper rotation.
    High pace + high endurance = coach can play tight rotation.

    Returns adjusted rotation size (int).
    """
    if not ranked:
        return rotation_size

    # Check endurance of players who would be in base rotation
    top_players  = ranked[:rotation_size]
    avg_endurance = sum(
        p.get("endurance", 500) for p in top_players
    ) / max(1, len(top_players))

    # High pace systems demand more from endurance
    # pace 85+ with avg endurance below 400 forces +2 rotation
    # pace 85+ with avg endurance below 500 forces +1 rotation
    pace_pressure = (pace - 50) / 50.0   # -1.0 to +1.0

    if pace_pressure > 0.5:   # pace 75+
        if avg_endurance < LOW_ENDURANCE_THRESHOLD:
            return min(11, rotation_size + 2)
        elif avg_endurance < 500:
            return min(11, rotation_size + 1)

    return rotation_size


def _distribute_minutes(ranked, rotation_size, rotation_flex, total_minutes):
    """
    Distributes minutes across players with realistic per-player targets.

    Hard constraints:
      - No player exceeds 38 minutes
      - 5 starters always get 28-36 minutes each
      - Rotation guys get 14-22 minutes each
      - Bench gets whatever remains

    rotation_flex shifts minutes from top starters toward bench:
      Low flex (1-3):  top player 35-36, even drop-off
      Mid flex (4-7):  top player 32-33, moderate spread
      High flex (8-10): top player 29-30, flatter distribution

    Total always sums to total_minutes (200).
    """
    if not ranked:
        return {}

    n = len(ranked)

    # --- FIXED STARTER TARGETS ---
    # Always assign 5 starters regardless of roster size
    # rotation_flex controls the spread among starters
    if rotation_flex <= 3:
        starter_targets = [36, 33, 31, 28, 26]
    elif rotation_flex <= 6:
        starter_targets = [34, 31, 29, 28, 26]
    elif rotation_flex <= 8:
        starter_targets = [32, 30, 29, 28, 27]
    else:
        starter_targets = [30, 29, 29, 28, 28]

    num_starters = min(5, n)
    starters     = starter_targets[:num_starters]
    used         = sum(starters)

    # --- FIXED ROTATION TARGETS ---
    # Players 6 through rotation_size
    # Decay from ~20 down to ~14 across the rotation slots
    rotation_base    = [20, 18, 16, 15, 14, 13]
    num_rotation     = max(0, min(rotation_size - 5, n - num_starters))
    rotation_targets = rotation_base[:num_rotation]
    used            += sum(rotation_targets)

    # --- BENCH GETS REMAINDER ---
    num_bench    = n - num_starters - num_rotation
    bench_pool   = max(0, total_minutes - used)
    bench_per    = bench_pool / max(1, num_bench) if num_bench > 0 else 0

    # Bench players get even split of remainder, minimum 1 minute
    bench_targets = [max(1.0, bench_per)] * num_bench

    # --- COMBINE ALL TARGETS ---
    all_targets = starters + rotation_targets + bench_targets

    # Safety: if total exceeds 200, trim bench
    total = sum(all_targets)
    if total > total_minutes and num_bench > 0:
        excess = total - total_minutes
        trim   = excess / max(1, num_bench)
        bench_targets = [max(0, b - trim) for b in bench_targets]
        all_targets   = starters + rotation_targets + bench_targets

    # --- APPLY ENDURANCE PENALTY ---
    # Low-endurance starters get up to 8% reduction
    for i in range(min(rotation_size, n)):
        if i >= len(all_targets):
            break
        endurance = ranked[i].get("endurance", 500)
        if endurance < LOW_ENDURANCE_THRESHOLD and all_targets[i] >= STARTER_THRESHOLD:
            penalty         = all_targets[i] * 0.08
            all_targets[i] -= penalty
            if i + 1 < len(all_targets):
                all_targets[i + 1] = all_targets[i + 1] + penalty

    # --- BUILD RESULT DICT ---
    minutes = {}
    for i, player in enumerate(ranked):
        if i < len(all_targets):
            minutes[player["name"]] = round(max(0, all_targets[i]), 1)
        else:
            minutes[player["name"]] = 0.0

    return minutes


def get_player_minutes(program, player_name):
    """
    Returns average minutes per game for a specific player.
    Returns 0 if player not found or minutes not allocated.
    """
    allocation = program.get("minutes_allocation", {})
    return allocation.get(player_name, 0)


def get_rotation_players(program, min_minutes=HEAVY_ROTATION_THRESHOLD):
    """
    Returns list of players averaging at least min_minutes per game.
    Default threshold is HEAVY_ROTATION_THRESHOLD (20 minutes).
    Used by cohesion.py for duo qualification.
    """
    allocation = program.get("minutes_allocation", {})
    roster     = program.get("roster", [])

    rotation = []
    for player in roster:
        name = player["name"]
        mins = allocation.get(name, 0)
        if mins >= min_minutes:
            rotation.append((player, mins))

    rotation.sort(key=lambda x: x[1], reverse=True)
    return rotation


def get_minutes_summary(program):
    """
    Returns a readable summary of minutes distribution.
    Used for debugging and reporting.
    """
    allocation = program.get("minutes_allocation", {})
    roster     = program.get("roster", [])

    summary = {
        "starters":       [],   # 28+ minutes
        "heavy_rotation": [],   # 20-27 minutes
        "rotation":       [],   # 12-19 minutes
        "bench":          [],   # under 12 minutes
    }

    for player in roster:
        name = player["name"]
        mins = allocation.get(name, 0)
        pos  = player.get("position", "?")
        yr   = player.get("year", "?")
        entry = {"name": name, "position": pos, "year": yr, "minutes": mins}

        if mins >= STARTER_THRESHOLD:
            summary["starters"].append(entry)
        elif mins >= HEAVY_ROTATION_THRESHOLD:
            summary["heavy_rotation"].append(entry)
        elif mins >= ROTATION_THRESHOLD:
            summary["rotation"].append(entry)
        else:
            summary["bench"].append(entry)

    return summary


def print_minutes_summary(program):
    """Prints a readable minutes breakdown for a program."""
    name      = program.get("name", "Unknown")
    coach     = program.get("coach", {})
    rot_size  = coach.get("rotation_size", 8)
    pace      = coach.get("pace", 50)
    archetype = coach.get("archetype", "unknown")

    print("")
    print("=== " + name + " -- Minutes Allocation ===")
    print("  Coach: " + archetype +
          "  Rotation size: " + str(rot_size) +
          "  Pace: " + str(pace))
    print("")

    summary = get_minutes_summary(program)

    for tier_name, tier_label in [
        ("starters",       "Starters (28+ min)"),
        ("heavy_rotation", "Heavy rotation (20-27 min)"),
        ("rotation",       "Rotation (12-19 min)"),
        ("bench",          "Bench (<12 min)"),
    ]:
        players = summary[tier_name]
        if not players:
            continue
        print("  " + tier_label + ":")
        for p in sorted(players, key=lambda x: x["minutes"], reverse=True):
            endurance = program["roster"][0].get("endurance", "?")
            # Find actual player endurance
            for roster_p in program.get("roster", []):
                if roster_p["name"] == p["name"]:
                    endurance = roster_p.get("endurance", 500)
                    break
            print("    {:<22} {:<5} {:<12} {:>5.1f} min  endurance: {}".format(
                p["name"][:21], p["position"], p["year"],
                p["minutes"], endurance
            ))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs

    print("Loading programs...")
    all_programs = build_all_d1_programs()

    print("Allocating minutes for all programs...")
    for program in all_programs:
        allocate_minutes(program)

    print("Done.")
    print("")

    # Show minutes breakdown for a sample of programs
    test_programs = ["Kentucky", "Gonzaga", "Drake", "Wagner"]
    for name in test_programs:
        prog = next((p for p in all_programs if p["name"] == name), None)
        if prog:
            print_minutes_summary(prog)

    print("")
    print("=== ROTATION SIZE VERIFICATION ===")
    print("  Checking that rotation size drives minutes distribution")
    print("")

    for prog in all_programs[:5]:
        coach    = prog.get("coach", {})
        rot_size = coach.get("rotation_size", 8)
        rotation = get_rotation_players(prog, min_minutes=HEAVY_ROTATION_THRESHOLD)
        print("  " + prog["name"].ljust(24) +
              "  rotation_size: " + str(rot_size) +
              "  players with 20+ min: " + str(len(rotation)))

    print("")
    print("=== ENDURANCE IMPACT CHECK ===")
    print("  Looking for programs where endurance forced rotation expansion")
    print("")

    expanded = []
    for prog in all_programs:
        coach        = prog.get("coach", {})
        base_rot     = coach.get("rotation_size", 8)
        pace         = coach.get("pace", 50)
        actual_rot   = len(get_rotation_players(prog, min_minutes=ROTATION_THRESHOLD))
        if pace >= 70 and actual_rot > base_rot:
            expanded.append((prog["name"], base_rot, actual_rot, pace))

    if expanded:
        print("  Programs where pace+endurance forced deeper rotation:")
        for name, base, actual, pace in expanded[:10]:
            print("  " + name.ljust(24) +
                  "  pace: " + str(pace) +
                  "  base rotation: " + str(base) +
                  "  actual: " + str(actual))
    else:
        print("  No forced expansions found -- endurance levels adequate")
