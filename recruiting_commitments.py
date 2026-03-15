import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting Commitments v0.3
# System 3 of the Design Bible
#
# v0.3 CHANGES:
#   - Added PHASE 4: Emergency Signing Period.
#     After late signing, any program projected to have fewer than
#     ROSTER_FLOOR players forces a match with remaining unsigned recruits.
#     Threshold dropped to near zero -- desperate programs take anyone.
#     This acts as a hard floor enforcement: having fewer than 10 players
#     is treated as a crisis and the system resolves it automatically.
#   - MAX_CLASS_SIZE raised across all tiers so programs can absorb
#     more players when the emergency period fires.
#   - LATE_SIGNING_THRESHOLD lowered to 20 to let more recruits clear
#     the normal late period before the emergency period is needed.
# -----------------------------------------

# Signing thresholds (1-100 interest scale)
EARLY_SIGNING_THRESHOLD  = 58
LATE_SIGNING_THRESHOLD   = 20    # Lowered from 28 -- more recruits clear normally

# Loyalty threshold for early committers
EARLY_COMMITTER_LOYALTY_THRESHOLD = 10

# In-season contact movement
INSEASON_INTEREST_BUMP = 3
INSEASON_INTEREST_DROP = 1

# Upset factor
UPSET_FACTOR = 0.08

# Indecision rate
INDECISION_RATE = 0.08

# Max class size per prestige tier
# Raised so programs can take more players when needed
MAX_CLASS_SIZE = {
    "elite":   7,    # 80+ prestige
    "good":    7,    # 60-79
    "average": 6,    # 40-59
    "low":     6,    # 20-39
    "bottom":  5,    # under 20
}

# Hard roster floor -- below this triggers the emergency signing period
# Any program projected to end the cycle with fewer than this many players
# will forcibly sign unsigned recruits until they hit this number.
ROSTER_FLOOR = 10

# Emergency signing threshold -- effectively zero resistance
# Programs in crisis will take any available recruit at any position
EMERGENCY_SIGNING_THRESHOLD = 5


# -----------------------------------------
# HELPERS
# -----------------------------------------

def _get_prestige_tier(prestige):
    if prestige >= 80: return "elite"
    if prestige >= 60: return "good"
    if prestige >= 40: return "average"
    if prestige >= 20: return "low"
    return "bottom"


def _build_full_programs_set(programs_by_name):
    """Returns set of program names that have hit their class size cap."""
    full = set()
    for name, program in programs_by_name.items():
        committed = program.get("committed_recruits", [])
        tier = _get_prestige_tier(program["prestige_current"])
        cap  = MAX_CLASS_SIZE.get(tier, 5)
        if len(committed) >= cap:
            full.add(name)
    return full


def _get_top_interest(recruit, full_programs=None):
    """Returns (program_name, score) for the program a recruit is most interested in."""
    if not recruit["interest_levels"]:
        return None, 0
    candidates = list(recruit["interest_levels"].items())
    if full_programs:
        candidates = [(p, s) for p, s in candidates if p not in full_programs]
    if not candidates:
        return None, 0
    top = max(candidates, key=lambda x: x[1])
    return top[0], top[1]


def _commit_recruit(recruit, program_name, programs_by_name):
    """Marks a recruit as committed. Updates both recruit and program."""
    recruit["status"]       = "committed"
    recruit["committed_to"] = program_name
    program = programs_by_name.get(program_name)
    if program:
        if "committed_recruits" not in program:
            program["committed_recruits"] = []
        program["committed_recruits"].append(recruit["name"])


def _apply_upset_factor(recruit, top_program, programs_by_name, full_programs):
    """Occasionally a lower-prestige program wins a recruit."""
    if random.random() > UPSET_FACTOR:
        return top_program

    sorted_programs = sorted(
        [(p, s) for p, s in recruit["interest_levels"].items()
         if p not in full_programs],
        key=lambda x: x[1], reverse=True
    )[:3]

    if len(sorted_programs) < 2:
        return top_program

    choices = [p[0] for p in sorted_programs]
    weights = [3, 2, 1][:len(choices)]
    return random.choices(choices, weights=weights, k=1)[0]


def _projected_roster_size(program):
    """
    Estimates how many players this program will have after graduation
    and after currently committed recruits enroll.
    Used to determine if the emergency period should fire.
    """
    roster = program.get("roster", [])
    returning = sum(1 for p in roster if p.get("year") != "Senior")
    committed = len(program.get("committed_recruits", []))
    return returning + committed


# -----------------------------------------
# PHASE 1 -- EARLY SIGNING PERIOD
# -----------------------------------------

def resolve_early_signing(all_programs, recruiting_class):
    """
    Loyal recruits with high interest commit here.
    Roughly 30-40% of eventual commits happen here.
    """
    early_commits    = []
    programs_by_name = {p["name"]: p for p in all_programs}

    for recruit in recruiting_class:
        if recruit["status"] != "available":
            continue
        if not recruit["interest_levels"]:
            continue

        full_programs = _build_full_programs_set(programs_by_name)
        is_early_committer = recruit["loyalty"] >= EARLY_COMMITTER_LOYALTY_THRESHOLD
        top_program, top_score = _get_top_interest(recruit, full_programs)

        if top_program is None:
            continue

        threshold = EARLY_SIGNING_THRESHOLD
        if not is_early_committer:
            threshold += 10

        if random.random() < INDECISION_RATE:
            continue

        if top_score >= threshold:
            _commit_recruit(recruit, top_program, programs_by_name)
            early_commits.append((recruit, top_program))

    return all_programs, recruiting_class, early_commits


# -----------------------------------------
# PHASE 2 -- IN-SEASON INTEREST SHIFTS
# -----------------------------------------

def resolve_inseason_shifts(all_programs, recruiting_class):
    """
    Limited in-season contact. Top program maintains interest.
    Programs outside top 3 decay slightly.
    Hot teams can spike interest.
    """
    programs_by_name = {p["name"]: p for p in all_programs}

    for recruit in recruiting_class:
        if recruit["status"] != "available":
            continue
        if not recruit["interest_levels"]:
            continue

        top_program, _ = _get_top_interest(recruit)
        if top_program:
            current = recruit["interest_levels"].get(top_program, 0)
            bump = random.randint(1, INSEASON_INTEREST_BUMP)
            recruit["interest_levels"][top_program] = min(100, current + bump)

        sorted_programs = sorted(
            recruit["interest_levels"].items(),
            key=lambda x: x[1], reverse=True
        )
        for i, (prog_name, score) in enumerate(sorted_programs):
            if i >= 3:
                recruit["interest_levels"][prog_name] = max(
                    1, score - INSEASON_INTEREST_DROP
                )

        if random.random() < 0.10 and recruit["interest_levels"]:
            random_prog = random.choice(list(recruit["interest_levels"].keys()))
            program = programs_by_name.get(random_prog)
            if program:
                win_pct = program["wins"] / max(1, program["wins"] + program["losses"])
                if win_pct > 0.65:
                    current = recruit["interest_levels"][random_prog]
                    recruit["interest_levels"][random_prog] = min(100, current + 5)

    return all_programs, recruiting_class


# -----------------------------------------
# PHASE 3 -- LATE SIGNING PERIOD
# -----------------------------------------

def resolve_late_signing(all_programs, recruiting_class):
    """
    All remaining unsigned recruits make a decision.
    Lower threshold -- recruits run out of time and options.
    """
    late_commits     = []
    unsigned         = []
    programs_by_name = {p["name"]: p for p in all_programs}

    for recruit in recruiting_class:
        if recruit["status"] != "available":
            continue
        if not recruit["interest_levels"]:
            unsigned.append(recruit)
            continue

        full_programs = _build_full_programs_set(programs_by_name)
        top_program, top_score = _get_top_interest(recruit, full_programs)

        if top_program is None:
            unsigned.append(recruit)
            continue

        if top_score >= LATE_SIGNING_THRESHOLD:
            final_program = _apply_upset_factor(
                recruit, top_program, programs_by_name, full_programs
            )
            _commit_recruit(recruit, final_program, programs_by_name)
            late_commits.append((recruit, final_program))
        else:
            recruit["status"] = "unsigned"
            unsigned.append(recruit)

    return all_programs, recruiting_class, late_commits, unsigned


# -----------------------------------------
# PHASE 4 -- EMERGENCY SIGNING PERIOD
# -----------------------------------------

def resolve_emergency_signing(all_programs, recruiting_class):
    """
    Hard floor enforcement. Any program projected to end the cycle
    with fewer than ROSTER_FLOOR players gets a forced match with
    unsigned recruits regardless of interest score.

    This models walk-ons, late signees, and emergency offers -- the
    real-world phenomenon where programs fill rosters through any
    available means. Having fewer than 10 players is treated as
    a crisis. The program will take any available recruit at their
    most needed position first, then any position.

    Programs in the emergency period bypass MAX_CLASS_SIZE -- filling
    the roster to the floor is more important than class size limits.
    """
    emergency_commits = []
    programs_by_name  = {p["name"]: p for p in all_programs}

    # Only unsigned recruits are available
    available = [r for r in recruiting_class if r["status"] == "unsigned"
                 or r["status"] == "available"]

    if not available:
        return all_programs, recruiting_class, emergency_commits

    # Sort available recruits by true_talent desc -- programs get best available
    available_by_position = {}
    for r in available:
        pos = r["position"]
        if pos not in available_by_position:
            available_by_position[pos] = []
        available_by_position[pos].append(r)

    # Sort each position pool by true_talent descending
    for pos in available_by_position:
        available_by_position[pos].sort(
            key=lambda r: r["true_talent"], reverse=True
        )

    # Build a flat pool as fallback
    flat_pool = sorted(available, key=lambda r: r["true_talent"], reverse=True)

    for program in all_programs:
        projected = _projected_roster_size(program)

        if projected >= ROSTER_FLOOR:
            continue

        # This program is in crisis -- fill to ROSTER_FLOOR
        slots_needed = ROSTER_FLOOR - projected

        for _ in range(slots_needed):
            # Try to find a recruit at a needed position first
            filled = False
            roster = program.get("roster", [])
            pos_counts = {}
            for p in roster:
                pos = p.get("position", "SF")
                pos_counts[pos] = pos_counts.get(pos, 0) + 1
            for p in program.get("committed_recruits", []):
                # We only have names here, not positions -- skip position logic
                pass

            # Try each position, most needed first
            position_needs = {
                "PG": max(0, 2 - pos_counts.get("PG", 0)),
                "SG": max(0, 2 - pos_counts.get("SG", 0)),
                "SF": max(0, 3 - pos_counts.get("SF", 0)),
                "PF": max(0, 3 - pos_counts.get("PF", 0)),
                "C":  max(0, 2 - pos_counts.get("C",  0)),
            }
            sorted_needs = sorted(
                position_needs.items(), key=lambda x: x[1], reverse=True
            )

            for pos, need in sorted_needs:
                if need <= 0:
                    continue
                pool = available_by_position.get(pos, [])
                for recruit in pool:
                    if recruit["status"] in ("available", "unsigned"):
                        _commit_recruit(recruit, program["name"], programs_by_name)
                        emergency_commits.append((recruit, program["name"]))
                        pool.remove(recruit)
                        # Also remove from flat pool
                        if recruit in flat_pool:
                            flat_pool.remove(recruit)
                        filled = True
                        break
                if filled:
                    break

            # If no position-specific recruit found, take anyone
            if not filled:
                for recruit in flat_pool:
                    if recruit["status"] in ("available", "unsigned"):
                        _commit_recruit(recruit, program["name"], programs_by_name)
                        emergency_commits.append((recruit, program["name"]))
                        flat_pool.remove(recruit)
                        pos = recruit["position"]
                        pool = available_by_position.get(pos, [])
                        if recruit in pool:
                            pool.remove(recruit)
                        filled = True
                        break

            if not filled:
                break   # No recruits left anywhere

    return all_programs, recruiting_class, emergency_commits


# -----------------------------------------
# FULL CYCLE RESOLVER
# -----------------------------------------

def resolve_full_recruiting_cycle(all_programs, recruiting_class, verbose=True):
    """
    Runs the complete recruiting cycle end to end.
    Phase 1: Early signing
    Phase 2: In-season shifts
    Phase 3: Late signing
    Phase 4: Emergency signing (hard roster floor enforcement)
    """
    if verbose:
        print("")
        print("--- Recruiting Cycle: Early Signing Period ---")

    all_programs, recruiting_class, early_commits = resolve_early_signing(
        all_programs, recruiting_class
    )

    if verbose:
        print("  Early commits: " + str(len(early_commits)))
        print("--- Recruiting Cycle: In-Season ---")

    all_programs, recruiting_class = resolve_inseason_shifts(
        all_programs, recruiting_class
    )

    if verbose:
        print("  Interest scores updated for unsigned recruits")
        print("--- Recruiting Cycle: Late Signing Period ---")

    all_programs, recruiting_class, late_commits, unsigned = resolve_late_signing(
        all_programs, recruiting_class
    )

    if verbose:
        print("  Late commits: " + str(len(late_commits)))
        print("  Unsigned:     " + str(len(unsigned)))
        print("--- Recruiting Cycle: Emergency Signing Period ---")

    all_programs, recruiting_class, emergency_commits = resolve_emergency_signing(
        all_programs, recruiting_class
    )

    if verbose:
        print("  Emergency commits: " + str(len(emergency_commits)))

    cycle_summary = {
        "early_commits":     early_commits,
        "late_commits":      late_commits,
        "emergency_commits": emergency_commits,
        "unsigned":          unsigned,
        "total_commits":     len(early_commits) + len(late_commits) + len(emergency_commits),
    }

    return all_programs, recruiting_class, cycle_summary


# -----------------------------------------
# DISPLAY HELPERS
# -----------------------------------------

def print_cycle_summary(cycle_summary, recruiting_class, season_year):
    total     = cycle_summary["total_commits"]
    early     = len(cycle_summary["early_commits"])
    late      = len(cycle_summary["late_commits"])
    emergency = len(cycle_summary["emergency_commits"])
    unsigned  = len(cycle_summary["unsigned"])

    print("")
    print("=" * 65)
    print("  " + str(season_year) + " RECRUITING CYCLE -- FINAL RESULTS")
    print("=" * 65)
    print("  Total signed:     " + str(total))
    print("  Early signing:    " + str(early) +
          " (" + str(round(early / max(1, total) * 100)) + "%)")
    print("  Late signing:     " + str(late) +
          " (" + str(round(late / max(1, total) * 100)) + "%)")
    print("  Emergency period: " + str(emergency) +
          " (" + str(round(emergency / max(1, total) * 100)) + "%)")
    print("  Unsigned:         " + str(unsigned))

    print("")
    print("  Commits by star rating:")
    all_commits = (
        [(r, p) for r, p in cycle_summary["early_commits"]] +
        [(r, p) for r, p in cycle_summary["late_commits"]] +
        [(r, p) for r, p in cycle_summary["emergency_commits"]]
    )
    star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for recruit, _ in all_commits:
        star_counts[recruit["stars_consensus"]] += 1
    for stars in [5, 4, 3, 2, 1]:
        print("    " + str(stars) + "-star: " + str(star_counts[stars]))

    print("")
    print("  Five-star destinations:")
    five_star_commits = [
        (r, p) for r, p in all_commits if r["stars_consensus"] == 5
    ]
    if five_star_commits:
        for recruit, program_name in five_star_commits:
            print("    " + recruit["name"].ljust(22) +
                  recruit["position"] + "  ->  " + program_name)
    else:
        print("    (no five-stars committed this cycle)")

    print("")
    print("  Top 10 recruiting classes:")
    program_classes = {}
    for recruit, program_name in all_commits:
        if program_name not in program_classes:
            program_classes[program_name] = []
        program_classes[program_name].append(recruit)

    class_scores = {}
    for prog_name, recruits in program_classes.items():
        avg_talent = sum(r["true_talent"] for r in recruits) / len(recruits)
        class_scores[prog_name] = (avg_talent, len(recruits), recruits)

    top_classes = sorted(
        class_scores.items(), key=lambda x: x[1][0], reverse=True
    )[:10]
    for i, (prog_name, (avg_talent, count, recruits)) in enumerate(top_classes):
        stars    = [r["stars_consensus"] for r in recruits]
        star_str = " ".join(str(s) + "★" for s in sorted(stars, reverse=True))
        print("    " + str(i+1).rjust(2) + ". " + prog_name.ljust(22) +
              str(count) + " players  " + star_str)


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from recruiting import generate_recruiting_class
    from recruiting_offers import generate_offers, calculate_interest_scores

    print("Loading programs and generating recruiting class...")
    all_programs     = build_all_d1_programs()
    recruiting_class = generate_recruiting_class(season=2025)
    print("Programs: " + str(len(all_programs)))
    print("Recruits: " + str(len(recruiting_class)))

    print("Generating offers and interest scores...")
    all_programs, recruiting_class = generate_offers(all_programs, recruiting_class)
    all_programs, recruiting_class = calculate_interest_scores(
        all_programs, recruiting_class
    )

    all_programs, recruiting_class, cycle_summary = resolve_full_recruiting_cycle(
        all_programs, recruiting_class, verbose=True
    )

    print_cycle_summary(cycle_summary, recruiting_class, season_year=2025)

    print("")
    print("=== ROSTER FLOOR VERIFICATION ===")
    thin = [p for p in all_programs
            if (sum(1 for pl in p.get("roster", []) if pl.get("year") != "Senior") +
                len(p.get("committed_recruits", []))) < ROSTER_FLOOR]
    print("  Programs still projected below " + str(ROSTER_FLOOR) +
          " after emergency period: " + str(len(thin)))
    if thin:
        for p in thin[:10]:
            projected = (sum(1 for pl in p.get("roster", []) if pl.get("year") != "Senior") +
                         len(p.get("committed_recruits", [])))
            print("    " + p["name"] + ": " + str(projected) + " projected")

    print("")
    print("Programs that signed at least one player: " +
          str(len([p for p in all_programs if p.get("committed_recruits")])) +
          " of " + str(len(all_programs)))
