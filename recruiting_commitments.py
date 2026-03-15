import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting Commitments v0.2
# System 3 of the Design Bible
# Commitment resolution -- recruits decide where to go
#
# Three phases mirror the real NCAA calendar:
#   1. Early signing period (November)
#   2. In-season (limited -- interest shifts only)
#   3. Late signing period (April)
#
# All AI programs auto-resolve. Human player layer added later.
#
# CALIBRATION KNOBS -- adjust these to tune recruiting behavior:
# -----------------------------------------

# How high interest must be to commit in each phase (1-100 scale)
EARLY_SIGNING_THRESHOLD  = 58    # Moderate bar for early signing
LATE_SIGNING_THRESHOLD   = 28    # Lowered -- more recruits find a home late

# Loyalty threshold for early committers
# Recruits with loyalty >= this will commit early if interest is high enough
EARLY_COMMITTER_LOYALTY_THRESHOLD = 10

# How much in-season contact moves interest scores
INSEASON_INTEREST_BUMP  = 3     # Max points interest can move per program
INSEASON_INTEREST_DROP  = 1     # Passive decay if no contact

# Upset factor -- chance a lower-prestige program steals a recruit
# 0.0 = never, 0.15 = occasionally
UPSET_FACTOR = 0.08

# Indecision rate -- fraction of recruits who delay even when threshold met
INDECISION_RATE = 0.08   # Lowered -- fewer recruits stall out unsigned

# Max players a program can sign per cycle -- prevents hoarding
# Raised across the board so rosters stay healthy after graduation
MAX_CLASS_SIZE = {
    "elite":   6,    # 80+ prestige
    "good":    6,    # 60-79
    "average": 5,    # 40-59
    "low":     5,    # 20-39
    "bottom":  4,    # under 20
}


# -----------------------------------------
# HELPERS
# -----------------------------------------

def _get_prestige_tier(prestige):
    """Returns prestige tier label."""
    if prestige >= 80: return "elite"
    if prestige >= 60: return "good"
    if prestige >= 40: return "average"
    if prestige >= 20: return "low"
    return "bottom"


def _build_full_programs_set(programs_by_name):
    """
    Returns a set of program names that have hit their class size cap.
    Called before each commit decision -- programs fill up mid-cycle.
    """
    full = set()
    for name, program in programs_by_name.items():
        committed = program.get("committed_recruits", [])
        tier = _get_prestige_tier(program["prestige_current"])
        cap  = MAX_CLASS_SIZE.get(tier, 4)
        if len(committed) >= cap:
            full.add(name)
    return full


def _get_top_interest(recruit, full_programs=None):
    """
    Returns (program_name, score) for the program a recruit is most
    interested in that still has room in their class.
    """
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
    """
    Occasionally a lower-prestige program wins a recruit
    even when a higher-prestige program has more interest.
    Driven by UPSET_FACTOR -- relationship can overcome prestige.
    """
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


# -----------------------------------------
# PHASE 1 -- EARLY SIGNING PERIOD
# -----------------------------------------

def resolve_early_signing(all_programs, recruiting_class):
    """
    Resolves the early signing period.
    Loyal recruits with high interest commit here.
    Programs capped at MAX_CLASS_SIZE -- once full they stop receiving commits.
    Roughly 30-40% of eventual commits happen here.
    """
    early_commits    = []
    programs_by_name = {p["name"]: p for p in all_programs}

    for recruit in recruiting_class:
        if recruit["status"] != "available":
            continue
        if not recruit["interest_levels"]:
            continue

        # Rebuild full set each time -- programs fill up during the loop
        full_programs = _build_full_programs_set(programs_by_name)

        is_early_committer = recruit["loyalty"] >= EARLY_COMMITTER_LOYALTY_THRESHOLD
        top_program, top_score = _get_top_interest(recruit, full_programs)

        if top_program is None:
            continue

        # Non-loyal recruits need a higher bar to commit early
        threshold = EARLY_SIGNING_THRESHOLD
        if not is_early_committer:
            threshold += 10

        # Indecision -- some recruits wait even when convinced
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
    Simulates limited in-season recruiting contact.
    Top program maintains contact -- small interest bump.
    Programs not in top 3 decay slightly.
    Random event -- a program's great season can spike interest.
    """
    programs_by_name = {p["name"]: p for p in all_programs}

    for recruit in recruiting_class:
        if recruit["status"] != "available":
            continue
        if not recruit["interest_levels"]:
            continue

        # Top program keeps in contact
        top_program, _ = _get_top_interest(recruit)
        if top_program:
            current = recruit["interest_levels"].get(top_program, 0)
            bump = random.randint(1, INSEASON_INTEREST_BUMP)
            recruit["interest_levels"][top_program] = min(100, current + bump)

        # Programs outside top 3 decay
        sorted_programs = sorted(
            recruit["interest_levels"].items(),
            key=lambda x: x[1], reverse=True
        )
        for i, (prog_name, score) in enumerate(sorted_programs):
            if i >= 3:
                recruit["interest_levels"][prog_name] = max(
                    1, score - INSEASON_INTEREST_DROP
                )

        # Random event -- hot team spikes interest
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
    Resolves the late signing period.
    All remaining unsigned recruits make a decision.
    Lower threshold -- recruits run out of time and options.
    Programs still capped at MAX_CLASS_SIZE.
    Recruits with no viable option go unsigned.
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
# FULL CYCLE RESOLVER
# -----------------------------------------

def resolve_full_recruiting_cycle(all_programs, recruiting_class, verbose=True):
    """
    Runs the complete recruiting cycle end to end.
    Phase 1: Early signing
    Phase 2: In-season shifts
    Phase 3: Late signing
    Returns (all_programs, recruiting_class, cycle_summary)
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

    cycle_summary = {
        "early_commits": early_commits,
        "late_commits":  late_commits,
        "unsigned":      unsigned,
        "total_commits": len(early_commits) + len(late_commits),
    }

    return all_programs, recruiting_class, cycle_summary


# -----------------------------------------
# DISPLAY HELPERS
# -----------------------------------------

def print_cycle_summary(cycle_summary, recruiting_class, season_year):
    """Prints a full recruiting cycle summary."""
    total    = cycle_summary["total_commits"]
    early    = len(cycle_summary["early_commits"])
    late     = len(cycle_summary["late_commits"])
    unsigned = len(cycle_summary["unsigned"])

    print("")
    print("=" * 65)
    print("  " + str(season_year) + " RECRUITING CYCLE -- FINAL RESULTS")
    print("=" * 65)
    print("  Total signed:  " + str(total))
    print("  Early signing: " + str(early) +
          " (" + str(round(early / max(1, total) * 100)) + "%)")
    print("  Late signing:  " + str(late) +
          " (" + str(round(late / max(1, total) * 100)) + "%)")
    print("  Unsigned:      " + str(unsigned))

    print("")
    print("  Commits by star rating:")
    all_commits = (
        [(r, p) for r, p in cycle_summary["early_commits"]] +
        [(r, p) for r, p in cycle_summary["late_commits"]]
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
            signing = "early" if (recruit, program_name) in cycle_summary["early_commits"] else "late"
            print("    " + recruit["name"].ljust(22) +
                  recruit["position"] + "  ->  " +
                  program_name + " (" + signing + ")")
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
    print("=== SPOT CHECKS ===")
    for recruit in recruiting_class[:10]:
        status      = recruit["status"]
        destination = recruit.get("committed_to", "unsigned")
        print("  " + recruit["name"].ljust(22) +
              str(recruit["stars_consensus"]) + "★  " +
              status.ljust(12) + "  " +
              (destination or ""))

    programs_with_commits = [
        p for p in all_programs if p.get("committed_recruits")
    ]
    print("")
    print("Programs that signed at least one player: " +
          str(len(programs_with_commits)) + " of " + str(len(all_programs)))
