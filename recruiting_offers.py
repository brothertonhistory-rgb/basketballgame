import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting Offers & Interest v0.3
# System 3 of the Design Bible
#
# v0.3 CHANGES:
#   - assess_roster_needs() now enforces a minimum class size of 3
#     regardless of roster math. This ensures programs always recruit
#     even when the position math returns low numbers on fresh rosters.
#   - STAR_RANGE floors lowered: low/bottom programs now explicitly
#     target 1-2 star recruits. Previously the floor was 1 but the
#     offer logic never reached them because need was satisfied early.
#   - OFFERS_PER_NEED raised for low/bottom tiers so 1-2 star recruits
#     actually accumulate offers instead of sitting at zero.
#   - Added MIN_CLASS_SIZE constant -- easy to tune.
#
# v0.2 CHANGES:
#   - assess_roster_needs() reads actual roster instead of flat stub
#   - generate_offers() is philosophy-aware (style fit + roster values)
#   - playing_style interest score uses calculate_style_fit() from coach.py
#   - _roster_value_score() helper added
# -----------------------------------------


# How many offers per needed position per prestige tier
OFFERS_PER_NEED = {
    "elite":   15,   # 80+ prestige
    "good":    12,   # 60-79
    "average": 10,   # 40-59
    "low":     12,   # 20-39  -- raised: must reach deep into 1-2 star pool
    "bottom":  12,   # under 20 -- raised: cast wide net to survive
}

# Star range by prestige tier
STAR_RANGE = {
    "elite":   (3, 5),   # 3-5 star
    "good":    (2, 5),   # 2-5 star -- widened to help fill rosters
    "average": (2, 4),   # 2-4 star
    "low":     (1, 3),   # 1-3 star -- explicit 1-star targeting
    "bottom":  (1, 2),   # 1-2 star -- their realistic range
}

# Target roster size
TARGET_ROSTER_SIZE = 13

# Minimum class size -- programs always recruit at least this many
# regardless of what the roster math returns.
MIN_CLASS_SIZE = 3

# Minimum players needed at each position on a full roster
POSITION_MINIMUMS = {
    "PG": 2,
    "SG": 2,
    "SF": 3,
    "PF": 3,
    "C":  2,
}

# Default class distribution when MIN_CLASS_SIZE kicks in
DEFAULT_MIN_CLASS = {
    "PG": 1,
    "SG": 1,
    "SF": 1,
    "PF": 0,
    "C":  0,
}


# -----------------------------------------
# ROSTER NEED ASSESSMENT
# -----------------------------------------

def assess_roster_needs(program):
    """
    Returns how many players a program needs at each position this cycle.

    Reads the actual roster -- counts returning players by position
    (excluding seniors who graduate), then targets POSITION_MINIMUMS
    and overall TARGET_ROSTER_SIZE.

    Always recruits at least MIN_CLASS_SIZE players total. This prevents
    the world from losing players every season on fresh rosters where the
    position math returns artificially low numbers.
    """
    roster = program.get("roster", [])

    # Count returning players by position (non-seniors)
    returning = {}
    for pos in POSITION_MINIMUMS:
        returning[pos] = sum(
            1 for p in roster
            if p.get("position") == pos and p.get("year") != "Senior"
        )

    # Count seniors by position -- these slots open after graduation
    seniors_by_pos = {}
    for pos in POSITION_MINIMUMS:
        seniors_by_pos[pos] = sum(
            1 for p in roster
            if p.get("position") == pos and p.get("year") == "Senior"
        )

    # Total open slots after graduation
    total_returning = sum(returning.values())
    open_slots = max(0, TARGET_ROSTER_SIZE - total_returning)

    # Build position needs
    if open_slots == 0:
        needs = {pos: 0 for pos in POSITION_MINIMUMS}
    else:
        needs = {}
        for pos in POSITION_MINIMUMS:
            after_graduation = returning[pos]
            minimum          = POSITION_MINIMUMS[pos]
            needs[pos]       = max(0, minimum - after_graduation + seniors_by_pos[pos])

        # Cap to open slots
        total_needs = sum(needs.values())
        if total_needs > open_slots:
            for pos in needs:
                needs[pos] = max(0, round(needs[pos] * open_slots / total_needs))

    # --- ENFORCE MINIMUM CLASS SIZE ---
    # Always recruit at least MIN_CLASS_SIZE players.
    total_needs = sum(needs.values())
    if total_needs < MIN_CLASS_SIZE:
        shortfall = MIN_CLASS_SIZE - total_needs
        for pos, count in DEFAULT_MIN_CLASS.items():
            if shortfall <= 0:
                break
            add = min(count, shortfall)
            needs[pos] = needs.get(pos, 0) + add
            shortfall -= add

    return needs


def get_prestige_tier(prestige):
    """Returns the prestige tier label for a program."""
    if prestige >= 80: return "elite"
    if prestige >= 60: return "good"
    if prestige >= 40: return "average"
    if prestige >= 20: return "low"
    return "bottom"


# -----------------------------------------
# OFFER GENERATION
# -----------------------------------------

def generate_offers(all_programs, recruiting_class):
    """
    Main entry point. Programs identify needs and make offers.

    Philosophy-aware: coaches sort offer targets by a blend of
    star rating, style fit, and roster values.

    v0.3: MIN_CLASS_SIZE ensures every program makes offers deep enough
    into the pool to reach 1-2 star recruits.
    """
    from coach import calculate_style_fit

    # Build position lookup
    recruits_by_position = {}
    for recruit in recruiting_class:
        pos = recruit["position"]
        if pos not in recruits_by_position:
            recruits_by_position[pos] = []
        recruits_by_position[pos].append(recruit)

    for program in all_programs:
        prestige           = program["prestige_current"]
        tier               = get_prestige_tier(prestige)
        star_min, star_max = STAR_RANGE[tier]
        offers_per_need    = OFFERS_PER_NEED[tier]
        coach              = program.get("coach", {})

        needs = assess_roster_needs(program)

        if "recruiting_board" not in program:
            program["recruiting_board"] = []

        for position, need_count in needs.items():
            if need_count == 0:
                continue

            position_pool = recruits_by_position.get(position, [])
            eligible = [
                r for r in position_pool
                if star_min <= r["stars_consensus"] <= star_max
                and r["status"] == "available"
            ]

            if not eligible:
                continue

            # Philosophy-aware sorting
            if coach:
                scored = []
                for r in eligible:
                    style_score = calculate_style_fit(r, coach)
                    value_score = _roster_value_score(r, coach)
                    star_norm   = r["stars_consensus"] / 5.0
                    blend = (
                        star_norm            * 0.60 +
                        (style_score / 100.0)* 0.25 +
                        (value_score / 10.0) * 0.15
                    )
                    blend += random.uniform(-0.05, 0.05)
                    scored.append((r, blend))
                scored.sort(key=lambda x: x[1], reverse=True)
                eligible = [r for r, _ in scored]
            else:
                random.shuffle(eligible)

            total_offers  = need_count * offers_per_need
            offered_count = 0

            for recruit in eligible:
                if offered_count >= total_offers:
                    break

                program_name = program["name"]
                if program_name not in recruit["offer_list"]:
                    recruit["offer_list"].append(program_name)

                recruit_id = recruit["name"] + "_" + str(recruit["season"])
                if recruit_id not in program["recruiting_board"]:
                    program["recruiting_board"].append(recruit_id)

                offered_count += 1

    return all_programs, recruiting_class


# -----------------------------------------
# ROSTER VALUE SCORER
# -----------------------------------------

def _roster_value_score(recruit, coach):
    """
    Scores a recruit against what this coach values in his roster.
    Returns 1-10.
    """
    def avg(*keys):
        vals = [recruit.get(k, 10) for k in keys]
        return sum(vals) / len(vals)

    score = 0
    score += coach.get("values_athleticism",  5) * (avg("speed", "lateral_quickness", "vertical") / 20)
    score += coach.get("values_iq",           5) * (avg("basketball_iq", "decision_making", "court_vision") / 20)
    score += coach.get("values_size",         5) * (avg("rebounding", "strength") / 20)
    score += coach.get("values_shooting",     5) * (avg("three_point", "catch_and_shoot", "free_throw") / 20)
    score += coach.get("values_defense",      5) * (avg("on_ball_defense", "help_defense", "steal_tendency") / 20)
    score += coach.get("values_toughness",    5) * (avg("strength", "rebounding") / 20)
    score += coach.get("values_role_players", 5) * (avg("coachability", "work_ethic") / 20)

    max_possible = sum([
        coach.get("values_athleticism",  5),
        coach.get("values_iq",           5),
        coach.get("values_size",         5),
        coach.get("values_shooting",     5),
        coach.get("values_defense",      5),
        coach.get("values_toughness",    5),
        coach.get("values_role_players", 5),
    ])

    if max_possible == 0:
        return 5

    return max(1, min(10, round((score / max_possible) * 10)))


# -----------------------------------------
# INTEREST SCORE CALCULATOR
# -----------------------------------------

def calculate_interest_scores(all_programs, recruiting_class):
    """
    After offers are made, each recruit calculates a base interest score
    for every program that offered them.
    """
    programs_by_name = {p["name"]: p for p in all_programs}

    for recruit in recruiting_class:
        if not recruit["offer_list"]:
            continue

        for program_name in recruit["offer_list"]:
            program = programs_by_name.get(program_name)
            if not program:
                continue

            score = _calculate_base_interest(recruit, program)
            recruit["interest_levels"][program_name] = score

    return all_programs, recruiting_class


def _calculate_base_interest(recruit, program):
    """
    Calculates a recruit's base interest score for a single program.
    Uses the recruit's eight hidden priority weights.
    Normalized to 1-100.
    """
    scores = {}

    # --- PRESTIGE ---
    prestige = program["prestige_current"]
    scores["prestige"] = min(10, prestige / 10)

    # --- PLAYING TIME ---
    needs    = assess_roster_needs(program)
    pos_need = needs.get(recruit["position"], 0)
    scores["playing_time"] = min(10, pos_need * 3 + random.randint(1, 3))

    # --- LOCATION / FAMILY PROXIMITY ---
    recruit_state = recruit["home_state"]
    program_state = program["state"]
    if recruit_state == program_state:
        proximity_score = 10
    elif _same_region(recruit_state, program_state):
        proximity_score = 6
    else:
        proximity_score = 2

    scores["location"]         = proximity_score
    scores["family_proximity"] = proximity_score

    # --- COACH RELATIONSHIP ---
    scores["coach_relationship"] = random.randint(1, 3)

    # --- PLAYING STYLE ---
    from coach import calculate_style_fit
    coach = program.get("coach", {})
    if coach:
        style_fit = calculate_style_fit(recruit, coach)
        scores["playing_style"] = max(1, min(10, round(style_fit / 10)))
    else:
        scores["playing_style"] = random.randint(3, 7)

    # --- ACADEMICS ---
    scores["academics"] = min(10, program["venue_rating"] / 12)

    # --- NIL ---
    scores["nil"] = min(10, prestige / 11)

    # --- WEIGHTED TOTAL ---
    weighted_sum = (
        scores["prestige"]           * recruit["priority_prestige"] +
        scores["playing_time"]       * recruit["priority_playing_time"] +
        scores["location"]           * recruit["priority_location"] +
        scores["family_proximity"]   * recruit["priority_family_proximity"] +
        scores["coach_relationship"] * recruit["priority_coach_relationship"] +
        scores["playing_style"]      * recruit["priority_playing_style"] +
        scores["academics"]          * recruit["priority_academics"] +
        scores["nil"]                * recruit["priority_nil"]
    )

    max_possible = 10 * (
        recruit["priority_prestige"] +
        recruit["priority_playing_time"] +
        recruit["priority_location"] +
        recruit["priority_family_proximity"] +
        recruit["priority_coach_relationship"] +
        recruit["priority_playing_style"] +
        recruit["priority_academics"] +
        recruit["priority_nil"]
    )

    if max_possible == 0:
        return 1

    normalized = (weighted_sum / max_possible) * 100
    return max(1, min(100, round(normalized)))


def _same_region(state1, state2):
    """Returns True if two states are in the same broad geographic region."""
    regions = [
        {"CA", "OR", "WA", "AZ", "NV", "UT", "CO", "ID", "MT", "WY"},
        {"TX", "OK", "AR", "LA", "MS", "AL", "TN", "KY"},
        {"FL", "GA", "SC", "NC", "VA", "MD", "DC", "WV"},
        {"OH", "IN", "MI", "IL", "WI", "MN", "IA", "MO"},
        {"PA", "NY", "NJ", "CT", "MA", "RI", "VT", "NH", "ME", "DE"},
        {"KS", "NE", "SD", "ND", "MN"},
        {"NM", "AZ", "TX"},
    ]
    for region in regions:
        if state1 in region and state2 in region:
            return True
    return False


# -----------------------------------------
# DISPLAY HELPERS
# -----------------------------------------

def print_offer_summary(all_programs, recruiting_class):
    """Prints a summary of offers made across the whole recruiting class."""

    total_offers  = sum(len(r["offer_list"]) for r in recruiting_class)
    most_offered  = max(recruiting_class, key=lambda r: len(r["offer_list"]))
    three_plus    = [r for r in recruiting_class if r["stars_consensus"] >= 3]
    least_offered = min(three_plus, key=lambda r: len(r["offer_list"])) if three_plus else None

    print("")
    print("=== OFFER SUMMARY ===")
    print("  Total offers made: " + str(total_offers))
    print("  Avg offers per recruit: " + str(round(total_offers / max(1, len(recruiting_class)), 1)))
    print("  Most offered: " + most_offered["name"] +
          " (" + str(len(most_offered["offer_list"])) + " offers)")
    if least_offered:
        print("  Least offered 3+ star: " + least_offered["name"] +
              " (" + str(len(least_offered["offer_list"])) + " offers)")

    print("")
    print("  Avg offers by star rating:")
    for stars in [5, 4, 3, 2, 1]:
        group = [r for r in recruiting_class if r["stars_consensus"] == stars]
        if group:
            avg = round(sum(len(r["offer_list"]) for r in group) / len(group), 1)
            print("    " + str(stars) + "-star: " + str(avg) + " offers avg")

    print("")
    print("  Recruits with zero offers:")
    zero_offers = [r for r in recruiting_class if len(r["offer_list"]) == 0]
    print("    Total: " + str(len(zero_offers)))
    by_stars = {}
    for r in zero_offers:
        s = r["stars_consensus"]
        by_stars[s] = by_stars.get(s, 0) + 1
    for s in sorted(by_stars.keys(), reverse=True):
        print("    " + str(s) + "-star: " + str(by_stars[s]) + " with no offers")


def print_recruit_offers(recruit, top_n=5):
    """Prints the top programs interested in a recruit by interest score."""
    if not recruit["interest_levels"]:
        print("  " + recruit["name"] + ": no offers yet")
        return

    sorted_interest = sorted(
        recruit["interest_levels"].items(),
        key=lambda x: x[1],
        reverse=True
    )

    print("")
    print("  " + recruit["name"] + " | " + recruit["position"] +
          " | " + str(recruit["stars_consensus"]) + "-star | " +
          recruit["home_state"])
    print("  Offers: " + str(len(recruit["offer_list"])))
    print("  Top programs by interest:")
    for program_name, score in sorted_interest[:top_n]:
        bar = "█" * (score // 10)
        print("    " + str(score).rjust(3) + "  " + bar + "  " + program_name)


def print_program_board(program, recruiting_class, top_n=10):
    """Prints a program's recruiting board."""
    board_ids = program.get("recruiting_board", [])
    if not board_ids:
        print("  " + program["name"] + ": no recruiting board yet")
        return

    recruit_lookup = {
        r["name"] + "_" + str(r["season"]): r
        for r in recruiting_class
    }

    board_recruits = []
    for rid in board_ids:
        r = recruit_lookup.get(rid)
        if r:
            interest = r["interest_levels"].get(program["name"], 0)
            board_recruits.append((r, interest))

    board_recruits.sort(key=lambda x: x[1], reverse=True)

    print("")
    print("  === " + program["name"] + " Recruiting Board ===")
    print("  Prestige: " + str(program["prestige_current"]) +
          " (" + program["prestige_grade"] + ")")
    coach = program.get("coach", {})
    if coach:
        print("  Coach archetype: " + coach.get("archetype", "unknown") +
              "  |  values_shooting: " + str(coach.get("values_shooting", "?")) +
              "  values_athleticism: " + str(coach.get("values_athleticism", "?")) +
              "  values_defense: " + str(coach.get("values_defense", "?")))
    print("  Board size: " + str(len(board_recruits)))
    print("")
    print("  {:<22} {:<5} {:<7} {:<6} {}".format(
        "Name", "Pos", "Stars", "State", "Interest"))
    print("  " + "-" * 55)
    for recruit, interest in board_recruits[:top_n]:
        from recruiting import stars_display
        print("  {:<22} {:<5} {:<7} {:<6} {}".format(
            recruit["name"],
            recruit["position"],
            stars_display(recruit["stars_consensus"]),
            recruit["home_state"],
            str(interest) + "/100"
        ))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from recruiting import generate_recruiting_class, stars_display

    print("Loading programs and generating recruiting class...")
    all_programs     = build_all_d1_programs()
    recruiting_class = generate_recruiting_class(season=2025)
    print("Programs: " + str(len(all_programs)))
    print("Recruits: " + str(len(recruiting_class)))

    print("")
    print("Generating offers...")
    all_programs, recruiting_class = generate_offers(all_programs, recruiting_class)

    print("Calculating interest scores...")
    all_programs, recruiting_class = calculate_interest_scores(
        all_programs, recruiting_class
    )

    print_offer_summary(all_programs, recruiting_class)

    print("")
    print("=== TOP 5 RECRUITS -- WHO IS AFTER THEM ===")
    for recruit in recruiting_class[:5]:
        print_recruit_offers(recruit, top_n=8)

    kentucky = next(p for p in all_programs if p["name"] == "Kentucky")
    wagner   = next(p for p in all_programs if p["name"] == "Wagner")

    print_program_board(kentucky, recruiting_class, top_n=15)
    print_program_board(wagner,   recruiting_class, top_n=10)

    print("")
    print("=== ROSTER NEED VERIFICATION ===")
    for program in [kentucky, wagner]:
        needs = assess_roster_needs(program)
        total_need = sum(needs.values())
        print("  " + program["name"] + " needs: " +
              "  ".join(pos + ": " + str(n) for pos, n in needs.items()) +
              "  (total: " + str(total_need) + ")")

    print("")
    print("=== 1-STAR AND 2-STAR SPOT CHECK ===")
    one_stars = [r for r in recruiting_class if r["stars_consensus"] == 1]
    two_stars = [r for r in recruiting_class if r["stars_consensus"] == 2]
    print("  1-star recruits with at least 1 offer: " +
          str(sum(1 for r in one_stars if len(r["offer_list"]) > 0)) +
          " of " + str(len(one_stars)))
    print("  2-star recruits with at least 1 offer: " +
          str(sum(1 for r in two_stars if len(r["offer_list"]) > 0)) +
          " of " + str(len(two_stars)))
    print("")
    print("  Sample 1-star recruits and their offers:")
    for r in one_stars[:5]:
        print("    " + r["name"].ljust(22) + r["position"] +
              "  offers: " + str(len(r["offer_list"])))
