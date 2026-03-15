import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting Offers & Interest v0.1
# System 3 of the Design Bible
# Offer system -- programs identify position needs and
# make offers to recruits within their prestige range
#
# Core rules:
#   1. Programs assess roster needs by position
#   2. Programs offer recruits that fit their prestige range
#   3. Offers are essentially free -- the constraint comes later
#      when relationship-building actions (visits, calls) are added
#   4. Recruits track which programs have offered them
# -----------------------------------------


# How many offers per needed position per prestige tier
# Elite programs cast wider nets -- more offers per position need
OFFERS_PER_NEED = {
    "elite":   15,   # 80+ prestige
    "good":    11,   # 60-79
    "average":  8,   # 40-59
    "low":      6,   # 20-39
    "bottom":   4,   # under 20
}

# How far outside their star range programs will reach
# Elite programs occasionally offer 3-stars (reach down)
# Low programs occasionally offer 4-stars (reach up, hoping)
STAR_RANGE = {
    "elite":   (3, 5),   # mostly 4-5 star, will dip to 3
    "good":    (3, 5),   # mix of 3-4 star, occasional 5
    "average": (2, 4),   # mostly 2-3 star, occasional 4
    "low":     (2, 3),   # mostly 2-star
    "bottom":  (1, 2),   # 1-2 star only
}

# Target roster size -- how many players a program wants total
TARGET_ROSTER_SIZE = 13

# Minimum players needed at each position on a full roster
POSITION_MINIMUMS = {
    "PG": 2,
    "SG": 2,
    "SF": 3,
    "PF": 3,
    "C":  2,
}


# -----------------------------------------
# ROSTER NEED ASSESSMENT
# -----------------------------------------

def assess_roster_needs(program):
    """
    Returns how many players a program needs at each position this cycle.

    NOTE: Full graduation/attrition system comes later when the player
    lifecycle is built. For now every program recruits a class of 4
    distributed across positions by a realistic pattern.

    Standard class of 4:
      PG: 1, SG: 1, SF: 1, PF: 1
    With random variation -- occasionally a program doubles up at a
    position and skips another, mirroring real recruiting patterns.

    Returns a dict like {"PG": 1, "SG": 1, "SF": 1, "PF": 1, "C": 0}
    """

    # Base class -- one player at each of the four non-center positions
    needs = {"PG": 1, "SG": 1, "SF": 1, "PF": 1, "C": 0}

    # 40% chance of needing a center this cycle
    if random.random() < 0.40:
        needs["C"] = 1

    # 30% chance of doubling up at one position and skipping another
    # Mirrors real recruiting -- teams sometimes take two PGs, zero SGs etc.
    if random.random() < 0.30:
        positions  = ["PG", "SG", "SF", "PF"]
        double_pos = random.choice(positions)
        skip_pos   = random.choice([p for p in positions if p != double_pos])
        needs[double_pos] += 1
        needs[skip_pos]    = max(0, needs[skip_pos] - 1)

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
    Main entry point. Processes all programs and generates offers
    to recruits in the recruiting class.

    Modifies recruits in place -- adds program names to their offer_list.
    Modifies programs in place -- adds recruit ids to their recruiting_board.

    Returns (all_programs, recruiting_class) with offers populated.
    """

    # Build position lookup for fast filtering
    # {position: [recruit, recruit, ...]}
    recruits_by_position = {}
    for recruit in recruiting_class:
        pos = recruit["position"]
        if pos not in recruits_by_position:
            recruits_by_position[pos] = []
        recruits_by_position[pos].append(recruit)

    # Process each program
    for program in all_programs:
        prestige   = program["prestige_current"]
        tier       = get_prestige_tier(prestige)
        star_min, star_max = STAR_RANGE[tier]
        offers_per_need    = OFFERS_PER_NEED[tier]

        # Assess what positions this program needs
        needs = assess_roster_needs(program)

        # Initialize recruiting board on program if not present
        if "recruiting_board" not in program:
            program["recruiting_board"] = []

        # For each position need, make offers
        for position, need_count in needs.items():
            if need_count == 0:
                continue

            # Get recruits at this position in this program's star range
            position_pool = recruits_by_position.get(position, [])
            eligible = [
                r for r in position_pool
                if star_min <= r["stars_consensus"] <= star_max
                and r["status"] == "available"
            ]

            if not eligible:
                continue

            # Shuffle so offers aren't always to the same top recruits
            random.shuffle(eligible)

            # Make offers -- offers_per_need per position slot needed
            total_offers = need_count * offers_per_need
            offered_count = 0

            for recruit in eligible:
                if offered_count >= total_offers:
                    break

                # Make the offer -- add to both sides
                program_name = program["name"]
                if program_name not in recruit["offer_list"]:
                    recruit["offer_list"].append(program_name)

                recruit_id = recruit["name"] + "_" + str(recruit["season"])
                if recruit_id not in program["recruiting_board"]:
                    program["recruiting_board"].append(recruit_id)

                offered_count += 1

    return all_programs, recruiting_class


# -----------------------------------------
# INTEREST SCORE CALCULATOR
# -----------------------------------------

def calculate_interest_scores(all_programs, recruiting_class):
    """
    After offers are made, each recruit calculates a base interest score
    for every program that offered them.

    Interest is driven by the recruit's hidden priority weights against
    what each program offers. This is the BASE score -- relationship-
    building actions (visits, calls) will move these scores later.

    Score range: 1-100
    Recruits only calculate interest for programs that have offered them.
    """

    # Build program lookup for fast access
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

    Each factor scores 0-10, multiplied by the recruit's weight for that
    factor (1-10), then normalized to a 1-100 scale.
    """

    scores = {}

    # --- PRESTIGE ---
    # Higher prestige programs score higher here
    prestige = program["prestige_current"]
    scores["prestige"] = min(10, prestige / 10)

    # --- PLAYING TIME ---
    # Estimate playing time opportunity based on roster need
    needs = assess_roster_needs(program)
    pos_need = needs.get(recruit["position"], 0)
    # More need = more PT opportunity
    scores["playing_time"] = min(10, pos_need * 3 + random.randint(1, 3))

    # --- LOCATION / FAMILY PROXIMITY ---
    # Compare recruit home state to program state
    recruit_state  = recruit["home_state"]
    program_state  = program["state"]
    if recruit_state == program_state:
        proximity_score = 10    # same state
    elif _same_region(recruit_state, program_state):
        proximity_score = 6     # neighboring region
    else:
        proximity_score = 2     # far away
    scores["location"]          = proximity_score
    scores["family_proximity"]  = proximity_score

    # --- COACH RELATIONSHIP ---
    # Starts low for everyone -- no relationship built yet
    # Will be moved by calls, visits, home visits later
    scores["coach_relationship"] = random.randint(1, 3)

    # --- PLAYING STYLE ---
    # Placeholder until coaching philosophy system is built
    # Random mild variance for now
    scores["playing_style"] = random.randint(3, 7)

    # --- ACADEMICS ---
    # Rough proxy -- venue rating correlates loosely with academic resources
    scores["academics"] = min(10, program["venue_rating"] / 12)

    # --- NIL ---
    # Prestige-driven for now -- bigger programs have bigger NIL
    # Will be replaced by actual NIL budget system later
    scores["nil"] = min(10, prestige / 11)

    # --- CALCULATE WEIGHTED TOTAL ---
    weighted_sum = (
        scores["prestige"]          * recruit["priority_prestige"] +
        scores["playing_time"]      * recruit["priority_playing_time"] +
        scores["location"]          * recruit["priority_location"] +
        scores["family_proximity"]  * recruit["priority_family_proximity"] +
        scores["coach_relationship"]* recruit["priority_coach_relationship"] +
        scores["playing_style"]     * recruit["priority_playing_style"] +
        scores["academics"]         * recruit["priority_academics"] +
        scores["nil"]               * recruit["priority_nil"]
    )

    # Max possible weighted sum: 10 * 10 * 8 factors = 800
    # Normalize to 1-100
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
    """
    Returns True if two states are in the same broad geographic region.
    Used for proximity scoring.
    """
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

    total_offers = sum(len(r["offer_list"]) for r in recruiting_class)
    most_offered = max(recruiting_class, key=lambda r: len(r["offer_list"]))
    least_offered = min(
        [r for r in recruiting_class if r["stars_consensus"] >= 3],
        key=lambda r: len(r["offer_list"])
    )

    print("")
    print("=== OFFER SUMMARY ===")
    print("  Total offers made: " + str(total_offers))
    print("  Avg offers per recruit: " + str(round(total_offers / len(recruiting_class), 1)))
    print("  Most offered: " + most_offered["name"] +
          " (" + str(len(most_offered["offer_list"])) + " offers)")
    print("  Least offered 3+ star: " + least_offered["name"] +
          " (" + str(len(least_offered["offer_list"])) + " offers)")

    # Offer counts by star level
    print("")
    print("  Avg offers by star rating:")
    for stars in [5, 4, 3, 2, 1]:
        group = [r for r in recruiting_class if r["stars_consensus"] == stars]
        if group:
            avg = round(sum(len(r["offer_list"]) for r in group) / len(group), 1)
            print("    " + str(stars) + "-star: " + str(avg) + " offers avg")


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
    """Prints a program's recruiting board sorted by recruit interest in them."""
    board_ids = program.get("recruiting_board", [])
    if not board_ids:
        print("  " + program["name"] + ": no recruiting board yet")
        return

    # Find recruits on this board
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

    # Generate offers
    print("")
    print("Generating offers...")
    all_programs, recruiting_class = generate_offers(all_programs, recruiting_class)

    # Calculate interest scores
    print("Calculating interest scores...")
    all_programs, recruiting_class = calculate_interest_scores(
        all_programs, recruiting_class
    )

    # Summary
    print_offer_summary(all_programs, recruiting_class)

    # Show top 5 recruits and who is after them
    print("")
    print("=== TOP 5 RECRUITS -- WHO IS AFTER THEM ===")
    for recruit in recruiting_class[:5]:
        print_recruit_offers(recruit, top_n=8)

    # Show Kentucky's and Wagner's recruiting boards
    kentucky = next(p for p in all_programs if p["name"] == "Kentucky")
    wagner   = next(p for p in all_programs if p["name"] == "Wagner")

    print_program_board(kentucky, recruiting_class, top_n=15)
    print_program_board(wagner,   recruiting_class, top_n=10)

    # Verify position needs work correctly
    print("")
    print("=== POSITION NEED VERIFICATION ===")
    for program in [kentucky, wagner]:
        needs = assess_roster_needs(program)
        total_need = sum(needs.values())
        print("  " + program["name"] + " needs: " +
              "  ".join(pos + ": " + str(n) for pos, n in needs.items()) +
              "  (total: " + str(total_need) + ")")
