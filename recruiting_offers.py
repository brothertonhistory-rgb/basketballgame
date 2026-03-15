import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting Offers & Interest v0.5
# System 3 of the Design Bible
#
# v0.5 CHANGES:
#
#   SPIKE SCOUT PASS
#     After the normal star-range offer pass, every program runs a
#     second pass -- the spike scout -- that scans the ENTIRE available
#     pool regardless of star rating. If a recruit has one attribute
#     that clears the program's spike threshold, they get an offer.
#     Cap: 2 spike offers per position per program per cycle.
#
#     Spike threshold by prestige tier:
#       elite:   720+  (Kentucky sees the elite shooter at #700)
#       good:    680+
#       average: 640+
#       low:     600+
#       bottom:  560+
#
#     Coach-values-aware: a pace-and-space coach scans for shooting
#     spikes. A grinder scans for rebounding and defense spikes.
#
#   PRESTIGE SUPPRESSION
#     A recruit with high priority_prestige has his interest in
#     lower-prestige programs dampened when a better offer exists.
#     Suppression scales with prestige gap and how much the recruit
#     cares about prestige. Cap: 50% reduction.
#
#   COMMITTED RECRUITS SKIPPED
#     Both offer passes skip committed recruits entirely.
#     Their word is their bond.
#
# v0.4 CHANGES:
#   - _roster_value_score() normalized against 1000 for skill attrs.
# v0.3 CHANGES:
#   - MIN_CLASS_SIZE enforcement, STAR_RANGE floors, OFFERS_PER_NEED.
# -----------------------------------------


OFFERS_PER_NEED = {
    "elite":   15,
    "good":    12,
    "average": 10,
    "low":     12,
    "bottom":  12,
}

STAR_RANGE = {
    "elite":   (3, 5),
    "good":    (2, 5),
    "average": (2, 4),
    "low":     (1, 3),
    "bottom":  (1, 2),
}

SPIKE_THRESHOLD = {
    "elite":   720,
    "good":    680,
    "average": 640,
    "low":     600,
    "bottom":  560,
}

SPIKE_OFFERS_PER_POSITION = 2

TARGET_ROSTER_SIZE = 13
MIN_CLASS_SIZE     = 3

POSITION_MINIMUMS = {
    "PG": 2,
    "SG": 2,
    "SF": 3,
    "PF": 3,
    "C":  2,
}

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
    roster = program.get("roster", [])

    returning = {}
    for pos in POSITION_MINIMUMS:
        returning[pos] = sum(
            1 for p in roster
            if p.get("position") == pos and p.get("year") != "Senior"
        )

    seniors_by_pos = {}
    for pos in POSITION_MINIMUMS:
        seniors_by_pos[pos] = sum(
            1 for p in roster
            if p.get("position") == pos and p.get("year") == "Senior"
        )

    total_returning = sum(returning.values())
    open_slots = max(0, TARGET_ROSTER_SIZE - total_returning)

    if open_slots == 0:
        needs = {pos: 0 for pos in POSITION_MINIMUMS}
    else:
        needs = {}
        for pos in POSITION_MINIMUMS:
            after_graduation = returning[pos]
            minimum          = POSITION_MINIMUMS[pos]
            needs[pos]       = max(0, minimum - after_graduation + seniors_by_pos[pos])

        total_needs = sum(needs.values())
        if total_needs > open_slots:
            for pos in needs:
                needs[pos] = max(0, round(needs[pos] * open_slots / total_needs))

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
    if prestige >= 80: return "elite"
    if prestige >= 60: return "good"
    if prestige >= 40: return "average"
    if prestige >= 20: return "low"
    return "bottom"


# -----------------------------------------
# SPIKE SCOUT HELPERS
# -----------------------------------------

# Applicable skill pairs -- BOTH attributes must clear threshold.
# These represent complete, deployable skills a coach can actually use.
# Single attributes don't count -- lateral_quickness alone doesn't
# get you a Kentucky offer. Lateral quickness + on_ball_defense does.
APPLICABLE_SKILL_PAIRS = {
    "floor_spacer":       ("catch_and_shoot", "three_point"),
    "perimeter_defender": ("on_ball_defense",  "lateral_quickness"),
    "rim_protector":      ("shot_blocking",     "vertical"),
    "rebounder":          ("rebounding",        "strength"),
    "playmaker":          ("passing",           "court_vision"),
    "finisher":           ("finishing",         "speed"),
    "post_scorer":        ("post_scoring",      "finishing"),
    "energy_big":         ("rebounding",        "help_defense"),
}

# Map coach values to which skill pairs they scout for
COACH_VALUE_TO_PAIRS = {
    "values_shooting":    ["floor_spacer"],
    "values_athleticism": ["finisher", "perimeter_defender"],
    "values_defense":     ["perimeter_defender", "rim_protector"],
    "values_size":        ["rebounder", "rim_protector", "post_scorer"],
    "values_iq":          ["playmaker"],
    "values_toughness":   ["rebounder", "energy_big"],
}


def _get_skill_pairs_for_coach(coach):
    """
    Returns list of applicable skill pair names this coach scouts for,
    ordered by how much the coach values that skill type.
    """
    if not coach:
        return ["floor_spacer", "perimeter_defender", "rebounder", "finisher"]

    value_keys = [
        "values_shooting", "values_athleticism", "values_defense",
        "values_size", "values_iq", "values_toughness",
    ]
    sorted_values = sorted(
        value_keys,
        key=lambda k: coach.get(k, 5),
        reverse=True
    )

    skill_pairs = []
    for val_key in sorted_values[:3]:
        for pair_name in COACH_VALUE_TO_PAIRS.get(val_key, []):
            if pair_name not in skill_pairs:
                skill_pairs.append(pair_name)

    return skill_pairs if skill_pairs else list(APPLICABLE_SKILL_PAIRS.keys())


def _recruit_paired_spike_score(recruit, skill_pairs, threshold):
    """
    Checks if a recruit has a complete applicable skill.
    Both attributes in ANY of the skill pairs must clear threshold.
    Returns the highest paired value found, or 0 if nothing qualifies.
    """
    best = 0
    for pair_name in skill_pairs:
        pair = APPLICABLE_SKILL_PAIRS.get(pair_name)
        if not pair:
            continue
        attr1, attr2 = pair
        val1 = recruit.get(attr1, 0)
        val2 = recruit.get(attr2, 0)
        # Both must clear threshold
        if isinstance(val1, int) and isinstance(val2, int):
            if val1 >= threshold and val2 >= threshold:
                # Score is the weaker of the two -- both matter
                best = max(best, min(val1, val2))
    return best


# -----------------------------------------
# OFFER GENERATION
# -----------------------------------------

def generate_offers(all_programs, recruiting_class):
    """
    Two-pass offer generation.

    Pass 1: Normal star-range offers. Philosophy-aware sorting.
    Pass 2: Spike scout. Scans all available recruits regardless of stars
            for one elite attribute. Coach-values-aware. Cap: 2 per position.

    Both passes skip committed recruits.
    """
    from coach import calculate_style_fit

    recruits_by_position = {}
    for recruit in recruiting_class:
        if recruit["status"] != "available":
            continue
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
        spike_threshold    = SPIKE_THRESHOLD[tier]

        needs = assess_roster_needs(program)

        if "recruiting_board" not in program:
            program["recruiting_board"] = []

        # --- PASS 1: NORMAL STAR-RANGE OFFERS ---
        for position, need_count in needs.items():
            if need_count == 0:
                continue

            position_pool = recruits_by_position.get(position, [])
            eligible = [
                r for r in position_pool
                if star_min <= r["stars_consensus"] <= star_max
            ]

            if not eligible:
                continue

            if coach:
                scored = []
                for r in eligible:
                    style_score = calculate_style_fit(r, coach)
                    value_score = _roster_value_score(r, coach)
                    star_norm   = r["stars_consensus"] / 5.0
                    blend = (
                        star_norm             * 0.60 +
                        (style_score / 100.0) * 0.25 +
                        (value_score / 10.0)  * 0.15
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
                _make_offer(recruit, program)
                offered_count += 1

        # --- PASS 2: SPIKE SCOUT ---
        skill_pairs = _get_skill_pairs_for_coach(coach)

        for position, need_count in needs.items():
            if need_count == 0:
                continue

            position_pool = recruits_by_position.get(position, [])

            spike_candidates = []
            for r in position_pool:
                if program["name"] in r["offer_list"]:
                    continue
                paired_score = _recruit_paired_spike_score(
                    r, skill_pairs, spike_threshold
                )
                if paired_score > 0:
                    spike_candidates.append((r, paired_score))

            spike_candidates.sort(key=lambda x: x[1], reverse=True)

            spike_offered = 0
            for recruit, paired_score in spike_candidates:
                if spike_offered >= SPIKE_OFFERS_PER_POSITION:
                    break
                _make_offer(recruit, program)
                spike_offered += 1

    return all_programs, recruiting_class


def _make_offer(recruit, program):
    program_name = program["name"]
    if program_name not in recruit["offer_list"]:
        recruit["offer_list"].append(program_name)
    recruit_id = recruit["name"] + "_" + str(recruit["season"])
    if recruit_id not in program["recruiting_board"]:
        program["recruiting_board"].append(recruit_id)


# -----------------------------------------
# ROSTER VALUE SCORER
# -----------------------------------------

def _roster_value_score(recruit, coach):
    def avg(*keys):
        vals = [recruit.get(k, 10) for k in keys]
        return sum(vals) / len(vals)

    score = 0
    score += coach.get("values_athleticism",  5) * (avg("speed", "lateral_quickness", "vertical") / 1000)
    score += coach.get("values_iq",           5) * (avg("basketball_iq", "decision_making", "court_vision") / 20)
    score += coach.get("values_size",         5) * (avg("rebounding", "strength") / 1000)
    score += coach.get("values_shooting",     5) * (avg("three_point", "catch_and_shoot", "free_throw") / 1000)
    score += coach.get("values_defense",      5) * (avg("on_ball_defense", "help_defense", "steal_tendency") / 1000)
    score += coach.get("values_toughness",    5) * (avg("strength", "rebounding") / 1000)
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
    Calculates base interest for each program that offered a recruit.
    v0.5: Prestige suppression -- high prestige-priority recruits have
    dampened interest in lower-prestige programs when a better offer exists.
    """
    programs_by_name = {p["name"]: p for p in all_programs}

    for recruit in recruiting_class:
        if not recruit["offer_list"]:
            continue

        best_offer_prestige = max(
            (programs_by_name[pn]["prestige_current"]
             for pn in recruit["offer_list"]
             if pn in programs_by_name),
            default=0
        )

        for program_name in recruit["offer_list"]:
            program = programs_by_name.get(program_name)
            if not program:
                continue

            score = _calculate_base_interest(recruit, program)

            prestige_priority = recruit.get("priority_prestige", 5)
            this_prestige     = program["prestige_current"]
            gap               = best_offer_prestige - this_prestige

            if gap > 15 and prestige_priority >= 6:
                suppression = (gap / 100.0) * (prestige_priority / 10.0) * 0.4
                suppression = min(0.50, suppression)
                score       = max(1, round(score * (1.0 - suppression)))

            recruit["interest_levels"][program_name] = score

    return all_programs, recruiting_class


def _calculate_base_interest(recruit, program):
    scores = {}

    prestige = program["prestige_current"]
    scores["prestige"] = min(10, prestige / 10)

    needs    = assess_roster_needs(program)
    pos_need = needs.get(recruit["position"], 0)
    scores["playing_time"] = min(10, pos_need * 3 + random.randint(1, 3))

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
    scores["coach_relationship"] = random.randint(1, 3)

    from coach import calculate_style_fit
    coach = program.get("coach", {})
    if coach:
        style_fit = calculate_style_fit(recruit, coach)
        scores["playing_style"] = max(1, min(10, round(style_fit / 10)))
    else:
        scores["playing_style"] = random.randint(3, 7)

    scores["academics"] = min(10, program["venue_rating"] / 12)
    scores["nil"]       = min(10, prestige / 11)

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
    total_offers = sum(len(r["offer_list"]) for r in recruiting_class)
    most_offered = max(recruiting_class, key=lambda r: len(r["offer_list"]))
    three_plus   = [r for r in recruiting_class if r["stars_consensus"] >= 3]
    least_offered = min(three_plus, key=lambda r: len(r["offer_list"])) if three_plus else None

    print("")
    print("=== OFFER SUMMARY ===")
    print("  Total offers made: " + str(total_offers))
    print("  Avg offers per recruit: " +
          str(round(total_offers / max(1, len(recruiting_class)), 1)))
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
    zero_offers = [r for r in recruiting_class if len(r["offer_list"]) == 0]
    print("  Recruits with zero offers: " + str(len(zero_offers)))
    by_stars = {}
    for r in zero_offers:
        s = r["stars_consensus"]
        by_stars[s] = by_stars.get(s, 0) + 1
    for s in sorted(by_stars.keys(), reverse=True):
        print("    " + str(s) + "-star with no offers: " + str(by_stars[s]))


def print_recruit_offers(recruit, top_n=5):
    if not recruit["interest_levels"]:
        print("  " + recruit["name"] + ": no offers yet")
        return
    sorted_interest = sorted(
        recruit["interest_levels"].items(),
        key=lambda x: x[1], reverse=True
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
          " (" + program.get("prestige_grade", "?") + ")")
    coach = program.get("coach", {})
    if coach:
        print("  Coach: " + coach.get("archetype", "?") +
              "  values_shooting: " + str(coach.get("values_shooting", "?")) +
              "  values_defense: " + str(coach.get("values_defense", "?")))
    print("  Board size: " + str(len(board_recruits)))
    print("")
    print("  {:<22} {:<5} {:<7} {:<6} {:<10} {}".format(
        "Name", "Pos", "Stars", "State", "Interest", "Note"))
    print("  " + "-" * 62)
    for recruit, interest in board_recruits[:top_n]:
        from recruiting import stars_display
        note = "[spike]" if recruit["stars_consensus"] <= 2 else ""
        print("  {:<22} {:<5} {:<7} {:<6} {:<10} {}".format(
            recruit["name"], recruit["position"],
            stars_display(recruit["stars_consensus"]),
            recruit["home_state"],
            str(interest) + "/100",
            note,
        ))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from recruiting import generate_recruiting_class, stars_display, POSITION_ARCHETYPES
    from display import display_attr

    print("Loading programs and generating recruiting class...")
    all_programs     = build_all_d1_programs()
    recruiting_class = generate_recruiting_class(season=2025)
    print("Programs: " + str(len(all_programs)))
    print("Recruits: " + str(len(recruiting_class)))

    print("Generating offers (v0.5 -- spike scout active)...")
    all_programs, recruiting_class = generate_offers(all_programs, recruiting_class)

    print("Calculating interest scores (v0.5 -- prestige suppression active)...")
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

    # --- SPIKE SCOUT VERIFICATION ---
    print("")
    print("=== SPIKE SCOUT VERIFICATION ===")
    print("  1-2 star recruits on Kentucky's board:")
    board_ids = kentucky.get("recruiting_board", [])
    recruit_lookup = {r["name"] + "_" + str(r["season"]): r
                      for r in recruiting_class}
    low_star_on_ky = []
    for rid in board_ids:
        r = recruit_lookup.get(rid)
        if r and r["stars_consensus"] <= 2:
            low_star_on_ky.append(r)
    print("  Found: " + str(len(low_star_on_ky)))
    for r in low_star_on_ky[:5]:
        pos     = r["position"]
        primary = POSITION_ARCHETYPES.get(pos, {}).get("primary", [])
        top_attr = max(primary, key=lambda a: r.get(a, 0)) if primary else "?"
        top_val  = r.get(top_attr, 0)
        print("    " + r["name"].ljust(22) + r["position"] +
              "  " + str(r["stars_consensus"]) + "-star" +
              "  top attr: " + top_attr + " = " + str(top_val) +
              " (" + display_attr(top_val, "letter") + ")")

    # --- PRESTIGE SUPPRESSION CHECK ---
    print("")
    print("=== PRESTIGE SUPPRESSION CHECK ===")
    programs_by_name = {p["name"]: p for p in all_programs}
    suppressed_examples = []
    for r in recruiting_class:
        if r.get("priority_prestige", 0) < 7:
            continue
        if len(r["offer_list"]) < 2:
            continue
        best_pn  = max(r["offer_list"],
                       key=lambda pn: programs_by_name.get(pn, {}).get("prestige_current", 0))
        worst_pn = min(r["offer_list"],
                       key=lambda pn: programs_by_name.get(pn, {}).get("prestige_current", 0))
        best_p   = programs_by_name.get(best_pn, {}).get("prestige_current", 0)
        worst_p  = programs_by_name.get(worst_pn, {}).get("prestige_current", 0)
        if best_p - worst_p >= 30:
            suppressed_examples.append((r, best_pn, worst_pn,
                                        r["interest_levels"].get(best_pn, 0),
                                        r["interest_levels"].get(worst_pn, 0)))

    for r, best_pn, worst_pn, best_s, worst_s in suppressed_examples[:5]:
        print("  " + r["name"].ljust(22) +
              " pres_priority=" + str(r["priority_prestige"]) +
              "  " + best_pn[:20] + " (" + str(best_s) + ")" +
              "  vs  " + worst_pn[:20] + " (" + str(worst_s) + ")")

    print("")
    print("=== ROSTER NEED VERIFICATION ===")
    for program in [kentucky, wagner]:
        needs = assess_roster_needs(program)
        total_need = sum(needs.values())
        print("  " + program["name"] + " needs: " +
              "  ".join(pos + ": " + str(n) for pos, n in needs.items()) +
              "  (total: " + str(total_need) + ")")
