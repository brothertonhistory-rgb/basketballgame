import random
from names import generate_player_name

# -----------------------------------------
# COLLEGE HOOPS SIM -- Player System v0.3
# System 2 of the Design Bible
# All attributes on 1-20 scale. No overall rating.
#
# v0.3 CHANGES:
#   - develop_player() added. Called once per offseason per returning
#     player. Implements the full development model:
#
#     SELF-IMPROVEMENT (always happens)
#       Every player improves on his natural attributes regardless of
#       coach quality. Driven by work_ethic. Floor of development.
#
#     COACH MULTIPLIER
#       player_development rating (1-20) multiplies the baseline.
#       A 17/20 developer meaningfully accelerates every player.
#       A 5/20 developer barely moves the needle beyond self-improvement.
#
#     CEILING PROXIMITY DAMPENING
#       As attributes approach potential_high (converted to 1-20 scale),
#       improvement slows and eventually stops.
#       potential_high is stored as a 1-100 talent score.
#       Ceiling conversion: attr_ceiling = 8 + (potential_high / 100) * 12
#       This maps potential_high 40 -> attr ceiling ~13,
#                                65 -> attr ceiling ~16,
#                                85 -> attr ceiling ~18.
#       A polished 5-star (potential_high 80+) arrives close to his
#       ceiling on key attributes. A raw player with potential_high 85
#       but low starting attributes has enormous room to grow.
#
#     ARC TYPE TIMING
#       late_bloomer  -- year 1 almost nothing, years 2-3 big jumps
#       steady        -- consistent moderate improvement every year
#       overachiever  -- big years 1-2, then slows
#       plateau       -- decent year 1, then nearly flat
#       bust          -- minimal all four years
#
#     BREAKTHROUGH EVENT (~2-3% of players per season)
#       A small number of players each season just figure something out.
#       2-3 key attributes jump significantly in one offseason.
#       Independent of coach quality. Weighted toward sophomores/juniors,
#       late_bloomer/steady arcs, high work_ethic, wide ceiling gap.
#
#     TRAINING CAMP HOOK (future feature)
#       develop_player() accepts training_focus dict {attr: bonus}.
#       Currently pass None. AI auto-allocates when training camp built.
#
#     MORALE HOOK (future feature)
#       develop_player() accepts morale_modifier (0.0-1.0).
#       Currently pass 1.0. Reduced when player loses role.
# -----------------------------------------

POSITIONS = ["PG", "SG", "SF", "PF", "C"]
YEARS     = ["Freshman", "Sophomore", "Junior", "Senior"]
ARC_TYPES = ["bust", "plateau", "steady", "overachiever", "late_bloomer"]

# All developable skill attributes -- mental attributes never change
DEVELOPABLE_ATTRIBUTES = [
    "catch_and_shoot", "off_dribble", "mid_range", "three_point", "free_throw",
    "finishing", "post_scoring",
    "passing", "ball_handling", "court_vision", "decision_making",
    "on_ball_defense", "help_defense", "rebounding", "shot_blocking",
    "steal_tendency",
    "speed", "lateral_quickness", "strength", "vertical",
]

# Natural attributes by position -- self-improvement focuses here
NATURAL_ATTRIBUTES = {
    "PG": ["ball_handling", "passing", "court_vision", "decision_making",
           "speed", "catch_and_shoot", "three_point"],
    "SG": ["catch_and_shoot", "three_point", "off_dribble", "free_throw",
           "lateral_quickness", "speed"],
    "SF": ["finishing", "speed", "vertical", "on_ball_defense",
           "catch_and_shoot", "rebounding"],
    "PF": ["rebounding", "finishing", "post_scoring", "strength",
           "help_defense", "shot_blocking"],
    "C":  ["rebounding", "shot_blocking", "strength", "post_scoring",
           "finishing", "help_defense"],
}

# Arc multipliers by year (0=Freshman, 1=Sophomore, 2=Junior, 3=Senior)
ARC_YEAR_MULTIPLIERS = {
    "late_bloomer":  [0.15, 1.00, 1.30, 0.80],
    "steady":        [0.70, 0.80, 0.75, 0.55],
    "overachiever":  [1.10, 1.00, 0.60, 0.30],
    "plateau":       [0.80, 0.40, 0.20, 0.10],
    "bust":          [0.30, 0.20, 0.15, 0.10],
}

YEAR_INDEX = {
    "Freshman":  0,
    "Sophomore": 1,
    "Junior":    2,
    "Senior":    3,
}

# Breakthrough probability weights by arc type
BREAKTHROUGH_ARC_WEIGHTS = {
    "late_bloomer":  3.0,
    "steady":        1.5,
    "overachiever":  1.2,
    "plateau":       0.3,
    "bust":          0.1,
}


# -----------------------------------------
# CEILING CONVERSION
# -----------------------------------------

def _potential_to_attr_ceiling(potential_high):
    """
    Converts potential_high (1-100 talent score) to an attribute ceiling
    on the 1-20 scale.

    Mapping:
      potential_high 20  -> ceiling ~10  (very limited player)
      potential_high 40  -> ceiling ~13  (role player ceiling)
      potential_high 60  -> ceiling ~15  (solid contributor ceiling)
      potential_high 75  -> ceiling ~17  (good player ceiling)
      potential_high 85  -> ceiling ~18  (star ceiling)
      potential_high 95  -> ceiling ~19  (elite ceiling)
      potential_high 100 -> ceiling 20   (generational ceiling)

    Formula: 8 + (potential_high / 100) * 12
    """
    return min(20, int(8 + (potential_high / 100.0) * 12))


# -----------------------------------------
# MAIN DEVELOPMENT FUNCTION
# -----------------------------------------

def develop_player(player, coach, season_year,
                   training_focus=None, morale_modifier=1.0):
    """
    Develops a player through one offseason.

    player          -- full player dict
    coach           -- full coach dict (or None)
    season_year     -- current season year
    training_focus  -- FUTURE HOOK: {attr: bonus} from training camp
    morale_modifier -- FUTURE HOOK: 0.0-1.0 from morale/playing time

    Returns (player, development_report).
    """

    year         = player.get("year", "Freshman")
    arc_type     = player.get("arc_type", "steady")
    work_ethic   = player.get("work_ethic", 10)
    coachability = player.get("coachability", 10)
    position     = player.get("position", "SF")
    potential_h  = player.get("potential_high", 50)

    # Seniors don't develop
    if year == "Senior":
        return player, {"improved": [], "breakthrough": False,
                        "breakthrough_attrs": [], "total_gain": 0,
                        "dev_score": 0}

    year_idx = YEAR_INDEX.get(year, 0)

    # --- COACH QUALITY ---
    dev_rating = 10
    if coach:
        dev_rating = coach.get("player_development", 10)

    # --- BASE DEVELOPMENT SCORE ---
    # Self-improvement: always happens, driven by work_ethic
    self_improvement = work_ethic / 20.0          # 0.05 - 1.0

    # Coach factor: how much he accelerates beyond self-improvement
    coach_factor = dev_rating / 20.0              # 0.05 - 1.0

    # Coachability: how much of the coach's quality the player absorbs
    coachability_factor = 0.4 + (coachability / 20.0) * 0.6   # 0.43 - 1.0

    # Combined base: self-improvement always contributes,
    # coach quality multiplied by coachability
    base_dev = (self_improvement * 0.45) + (coach_factor * coachability_factor * 0.55)

    # Arc timing
    arc_mults = ARC_YEAR_MULTIPLIERS.get(arc_type, ARC_YEAR_MULTIPLIERS["steady"])
    arc_mult  = arc_mults[min(year_idx, 3)]

    combined_dev = base_dev * arc_mult * morale_modifier

    # --- ATTRIBUTE CEILING (converted to 1-20 scale) ---
    global_ceiling = _potential_to_attr_ceiling(potential_h)

    # --- DETERMINE ATTRIBUTE IMPROVEMENTS ---
    natural_attrs = NATURAL_ATTRIBUTES.get(position, DEVELOPABLE_ATTRIBUTES)
    focus_attrs   = list(training_focus.keys()) if training_focus else []

    improved   = []
    total_gain = 0

    for attr in DEVELOPABLE_ATTRIBUTES:
        current = player.get(attr, 10)

        # Each attribute has the global ceiling as its max.
        # Ensure at least 3 points of room above current value so
        # ceiling dampening doesn't kill all growth for low-ceiling
        # players who start close to their potential_high.
        attr_ceiling = max(current + 3, global_ceiling)

        # Already at or above ceiling -- no growth
        if current >= attr_ceiling:
            continue

        # Ceiling proximity dampening
        # At 100% of ceiling: multiplier = 0.0
        # At 75% of ceiling: multiplier ~0.44
        # At 50% of ceiling: multiplier ~1.0
        # At 25% of ceiling: multiplier ~1.0 (uncapped below 50%)
        proximity      = current / attr_ceiling
        ceiling_dampen = max(0.0, 1.0 - (max(0.0, proximity - 0.5) * 2.0) ** 2)

        if ceiling_dampen < 0.05:
            continue

        # Attribute weighting
        attr_weight = 1.0
        if attr in natural_attrs:
            attr_weight = 1.5   # Natural attributes improve faster
        if attr in focus_attrs:
            attr_weight += 1.0  # Training camp focus bonus (future)

        # Raw gain calculation
        # Max possible: ~2.0 points per attribute per season for great
        # coach + great player + natural attribute + no ceiling pressure
        raw_gain = combined_dev * attr_weight * ceiling_dampen * 2.0

        # Noise
        noise     = random.gauss(0, 0.25)
        final_gain = max(0.0, raw_gain + noise)

        # Apply only if meaningful
        if final_gain >= 0.50:
            new_val = min(attr_ceiling, int(current + final_gain))
            if new_val > current:
                player[attr] = new_val
                improved.append({
                    "attr": attr,
                    "from": current,
                    "to":   new_val,
                    "gain": new_val - current,
                })
                total_gain += (new_val - current)

    # --- BREAKTHROUGH CHECK ---
    breakthrough       = False
    breakthrough_attrs = []

    arc_weight   = BREAKTHROUGH_ARC_WEIGHTS.get(arc_type, 1.0)
    ethic_weight = work_ethic / 12.0   # 0.08 - 1.67

    # Ceiling gap weight: wide gap = more likely to break through
    ceiling_gap  = global_ceiling - _avg_key_attrs(player, position)
    gap_weight   = max(0.3, min(2.0, ceiling_gap / 6.0))

    # Base breakthrough chance: ~1.0% per player per season
    breakthrough_chance = 0.06 * arc_weight * ethic_weight

    # Gap weight: wide ceiling gap increases chance but floor is higher
    # so even players near their ceiling can occasionally break through
    gap_weight          = max(0.6, min(2.0, ceiling_gap / 5.0))
    breakthrough_chance *= gap_weight

    # Sophomores and juniors more likely
    if year == "Sophomore":
        breakthrough_chance *= 1.6
    elif year == "Junior":
        breakthrough_chance *= 1.2

    if random.random() < breakthrough_chance:
        key_attrs = natural_attrs[:5]
        num_attrs = random.randint(2, 3)
        chosen    = random.sample(key_attrs, min(num_attrs, len(key_attrs)))

        bt_gain_this_event = 0
        temp_attrs = []

        for attr in chosen:
            current = player.get(attr, 10)
            room    = max(0, global_ceiling - current)
            # Breakthrough minimum jump is 2 -- a 1-point nudge isn't a breakthrough
            if room < 2:
                continue
            jump = random.randint(2, max(2, min(4, room)))
            temp_attrs.append({
                "attr": attr,
                "from": current,
                "to":   current + jump,
                "gain": jump,
            })
            bt_gain_this_event += jump

        # Only count as a breakthrough if total gain is at least 3 points
        # A real breakthrough is meaningful -- one strong jump counts
        if bt_gain_this_event >= 3 and temp_attrs:
            breakthrough = True
            for entry in temp_attrs:
                player[entry["attr"]] = entry["to"]
                breakthrough_attrs.append(entry)
                total_gain += entry["gain"]

    report = {
        "name":               player["name"],
        "position":           position,
        "year":               year,
        "arc_type":           arc_type,
        "improved":           improved,
        "breakthrough":       breakthrough,
        "breakthrough_attrs": breakthrough_attrs,
        "total_gain":         total_gain,
        "dev_score":          round(combined_dev, 3),
    }

    return player, report


def _avg_key_attrs(player, position):
    """Average of the top natural attributes for this position."""
    natural = NATURAL_ATTRIBUTES.get(position, DEVELOPABLE_ATTRIBUTES[:5])
    vals    = [player.get(a, 10) for a in natural[:5]]
    return sum(vals) / max(1, len(vals))


# -----------------------------------------
# EXISTING FUNCTIONS -- unchanged from v0.2
# -----------------------------------------

def create_player(name, position, year, conference="",
                  shooting=None, defense=None, rebounding=None,
                  playmaking=None, athleticism=None, mental=None,
                  potential=None, heritage=None):

    if shooting    is None: shooting    = generate_shooting(position)
    if defense     is None: defense     = generate_defense(position)
    if rebounding  is None: rebounding  = generate_rebounding(position)
    if playmaking  is None: playmaking  = generate_playmaking(position)
    if athleticism is None: athleticism = generate_athleticism(position)
    if mental      is None: mental      = generate_mental()
    if potential   is None: potential   = generate_potential()

    if not name or "Player" in name:
        generated_name, generated_heritage = generate_player_name(conference=conference)
        name = generated_name
        if heritage is None:
            heritage = generated_heritage
    elif heritage is None:
        _, heritage = generate_player_name(conference=conference)

    player = {
        "name":       name,
        "position":   position,
        "year":       year,
        "heritage":   heritage,

        "catch_and_shoot": shooting["catch_and_shoot"],
        "off_dribble":     shooting["off_dribble"],
        "mid_range":       shooting["mid_range"],
        "three_point":     shooting["three_point"],
        "free_throw":      shooting["free_throw"],
        "finishing":       shooting["finishing"],
        "post_scoring":    shooting["post_scoring"],

        "passing":         playmaking["passing"],
        "ball_handling":   playmaking["ball_handling"],
        "court_vision":    playmaking["court_vision"],
        "decision_making": playmaking["decision_making"],

        "on_ball_defense": defense["on_ball_defense"],
        "help_defense":    defense["help_defense"],
        "rebounding":      rebounding,
        "shot_blocking":   defense["shot_blocking"],
        "steal_tendency":  defense["steal_tendency"],
        "foul_tendency":   defense["foul_tendency"],

        "speed":             athleticism["speed"],
        "lateral_quickness": athleticism["lateral_quickness"],
        "strength":          athleticism["strength"],
        "vertical":          athleticism["vertical"],

        "basketball_iq": mental["basketball_iq"],
        "clutch":        mental["clutch"],
        "composure":     mental["composure"],
        "coachability":  mental["coachability"],
        "work_ethic":    mental["work_ethic"],
        "leadership":    mental["leadership"],

        "potential_low":  potential["low"],
        "potential_high": potential["high"],
        "arc_type":       potential["arc_type"],

        "fatigue":    0.0,
        "foul_count": 0,
        "in_game":    True,
    }

    return player


def rand_attr(base, spread=3):
    val = int(random.gauss(base, spread))
    return max(1, min(20, val))


def generate_shooting(position):
    if position == "PG":
        return {"catch_and_shoot": rand_attr(11), "off_dribble": rand_attr(12),
                "mid_range": rand_attr(11), "three_point": rand_attr(11),
                "free_throw": rand_attr(12), "finishing": rand_attr(11), "post_scoring": rand_attr(7)}
    elif position == "SG":
        return {"catch_and_shoot": rand_attr(13), "off_dribble": rand_attr(12),
                "mid_range": rand_attr(12), "three_point": rand_attr(12),
                "free_throw": rand_attr(12), "finishing": rand_attr(11), "post_scoring": rand_attr(8)}
    elif position == "SF":
        return {"catch_and_shoot": rand_attr(11), "off_dribble": rand_attr(10),
                "mid_range": rand_attr(11), "three_point": rand_attr(10),
                "free_throw": rand_attr(11), "finishing": rand_attr(12), "post_scoring": rand_attr(10)}
    elif position == "PF":
        return {"catch_and_shoot": rand_attr(9), "off_dribble": rand_attr(8),
                "mid_range": rand_attr(10), "three_point": rand_attr(8),
                "free_throw": rand_attr(10), "finishing": rand_attr(13), "post_scoring": rand_attr(12)}
    else:
        return {"catch_and_shoot": rand_attr(7), "off_dribble": rand_attr(6),
                "mid_range": rand_attr(8), "three_point": rand_attr(6),
                "free_throw": rand_attr(9), "finishing": rand_attr(14), "post_scoring": rand_attr(13)}


def generate_defense(position):
    if position in ["PG", "SG"]:
        return {"on_ball_defense": rand_attr(10), "help_defense": rand_attr(10),
                "shot_blocking": rand_attr(5), "steal_tendency": rand_attr(11), "foul_tendency": rand_attr(10)}
    elif position == "SF":
        return {"on_ball_defense": rand_attr(11), "help_defense": rand_attr(11),
                "shot_blocking": rand_attr(8), "steal_tendency": rand_attr(10), "foul_tendency": rand_attr(10)}
    else:
        return {"on_ball_defense": rand_attr(10), "help_defense": rand_attr(12),
                "shot_blocking": rand_attr(12), "steal_tendency": rand_attr(8), "foul_tendency": rand_attr(11)}


def generate_rebounding(position):
    bases = {"PG": 7, "SG": 8, "SF": 10, "PF": 13, "C": 14}
    return rand_attr(bases.get(position, 10))


def generate_playmaking(position):
    if position == "PG":
        return {"passing": rand_attr(13), "ball_handling": rand_attr(13),
                "court_vision": rand_attr(12), "decision_making": rand_attr(12)}
    elif position == "SG":
        return {"passing": rand_attr(11), "ball_handling": rand_attr(12),
                "court_vision": rand_attr(10), "decision_making": rand_attr(11)}
    elif position == "SF":
        return {"passing": rand_attr(10), "ball_handling": rand_attr(10),
                "court_vision": rand_attr(10), "decision_making": rand_attr(10)}
    else:
        return {"passing": rand_attr(8), "ball_handling": rand_attr(7),
                "court_vision": rand_attr(8), "decision_making": rand_attr(9)}


def generate_athleticism(position):
    if position in ["PG", "SG"]:
        return {"speed": rand_attr(13), "lateral_quickness": rand_attr(13),
                "strength": rand_attr(9), "vertical": rand_attr(12)}
    elif position == "SF":
        return {"speed": rand_attr(11), "lateral_quickness": rand_attr(11),
                "strength": rand_attr(11), "vertical": rand_attr(11)}
    else:
        return {"speed": rand_attr(9), "lateral_quickness": rand_attr(9),
                "strength": rand_attr(13), "vertical": rand_attr(10)}


def generate_mental():
    return {
        "basketball_iq": rand_attr(10, 2), "clutch":       rand_attr(10, 2),
        "composure":     rand_attr(10, 2), "coachability": rand_attr(10, 2),
        "work_ethic":    rand_attr(10, 2), "leadership":   rand_attr(10, 2),
    }


def generate_potential():
    arc  = random.choice(ARC_TYPES)
    base = random.randint(8, 18)
    if arc == "bust":
        return {"low": max(1, base-4), "high": base,   "arc_type": arc}
    elif arc == "plateau":
        return {"low": base,           "high": base+1,  "arc_type": arc}
    elif arc == "steady":
        return {"low": base,           "high": base+3,  "arc_type": arc}
    elif arc == "overachiever":
        return {"low": base+2,         "high": base+5,  "arc_type": arc}
    else:
        return {"low": max(1, base-2), "high": base+6,  "arc_type": arc}


def generate_team(name, prestige=10, conference=""):
    roster = []
    positions_needed = ["PG","PG","SG","SG","SF","SF","SF","PF","PF","C","C","PG","SG"]
    years = ["Freshman","Sophomore","Junior","Senior"]

    for i, pos in enumerate(positions_needed):
        year = years[i % 4]
        prestige_bonus = (prestige - 10) * 0.3
        player = create_player("", pos, year, conference=conference)
        for attr in ["catch_and_shoot","off_dribble","finishing","on_ball_defense",
                     "help_defense","rebounding","passing","ball_handling"]:
            player[attr] = max(1, min(20, int(player[attr] + prestige_bonus)))
        roster.append(player)

    return {"name": name, "prestige": prestige, "roster": roster}


def get_team_ratings(team):
    roster = team["roster"]
    if not roster:
        return {"shooting": 10, "defense": 10, "rebounding": 10, "foul_draw": 10}

    avg_shooting   = sum((p["catch_and_shoot"]+p["off_dribble"]+p["finishing"])/3 for p in roster) / len(roster)
    avg_defense    = sum((p["on_ball_defense"]+p["help_defense"])/2 for p in roster) / len(roster)
    avg_rebounding = sum(p["rebounding"] for p in roster) / len(roster)
    avg_foul_draw  = sum(p["finishing"] for p in roster) / len(roster)

    return {
        "name":       team["name"],
        "shooting":   round(avg_shooting, 1),
        "defense":    round(avg_defense, 1),
        "rebounding": round(avg_rebounding, 1),
        "foul_draw":  round(avg_foul_draw, 1),
    }


def print_roster(team):
    print("")
    print("=== " + team["name"] + " Roster (Prestige: " + str(team["prestige"]) + ") ===")
    print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
        "Name", "Pos", "Year", "Shoot", "Defense", "Reb", "Play"))
    print("-" * 80)
    for p in team["roster"]:
        avg_shoot = round((p["catch_and_shoot"]+p["finishing"]+p["three_point"])/3, 1)
        avg_def   = round((p["on_ball_defense"]+p["help_defense"])/2, 1)
        avg_play  = round((p["passing"]+p["ball_handling"])/2, 1)
        print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
            p["name"], p["position"], p["year"],
            avg_shoot, avg_def, p["rebounding"], avg_play))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from coach import generate_coach

    print("=" * 65)
    print("  PLAYER DEVELOPMENT TEST -- v0.3")
    print("=" * 65)

    def make_test_player(name, arc, work_ethic_val, potential_high_val):
        p = create_player(name, "SF", "Freshman")
        p["arc_type"]       = arc
        p["work_ethic"]     = work_ethic_val
        p["coachability"]   = 12
        p["potential_high"] = potential_high_val
        # Start attributes at realistic mid-low values
        # so there is genuine room to grow
        p["finishing"]        = 10
        p["catch_and_shoot"]  = 9
        p["on_ball_defense"]  = 10
        p["speed"]            = 11
        p["rebounding"]       = 9
        return p

    great_coach = generate_coach("Dev Master", prestige=80,
                                  archetype="motion_offense", experience=20)
    great_coach["player_development"] = 18

    poor_coach = generate_coach("Stagnator", prestige=50,
                                 archetype="dribble_drive", experience=5)
    poor_coach["player_development"] = 5

    test_cases = [
        ("Late Bloomer / High Ceiling",  "late_bloomer",  14, 85),
        ("Steady / Medium Ceiling",      "steady",        12, 65),
        ("Plateau / Low Ceiling",        "plateau",       10, 50),
        ("Bust / Narrow Ceiling",        "bust",           7, 40),
        ("Overachiever / Good Ceiling",  "overachiever",  15, 72),
    ]

    years = ["Freshman", "Sophomore", "Junior"]

    for case_name, arc, ethic, ceiling in test_cases:
        print("")
        print("  " + case_name + " (work_ethic=" + str(ethic) +
              ", potential_high=" + str(ceiling) +
              ", attr_ceiling=" + str(_potential_to_attr_ceiling(ceiling)) + ")")
        print("  {:<12} {:<25} {:<25}".format(
            "Year", "Great Coach (18)", "Poor Coach (5)"))
        print("  " + "-" * 62)

        p_great = make_test_player("Player A", arc, ethic, ceiling)
        p_poor  = make_test_player("Player B", arc, ethic, ceiling)

        for year in years:
            p_great["year"] = year
            p_poor["year"]  = year

            before_great = sum(p_great.get(a, 10) for a in
                               ["finishing", "catch_and_shoot", "on_ball_defense",
                                "speed", "rebounding"])
            before_poor  = sum(p_poor.get(a, 10) for a in
                               ["finishing", "catch_and_shoot", "on_ball_defense",
                                "speed", "rebounding"])

            p_great, report_g = develop_player(p_great, great_coach, 2025)
            p_poor,  report_p = develop_player(p_poor,  poor_coach,  2025)

            after_great = sum(p_great.get(a, 10) for a in
                              ["finishing", "catch_and_shoot", "on_ball_defense",
                               "speed", "rebounding"])
            after_poor  = sum(p_poor.get(a, 10) for a in
                              ["finishing", "catch_and_shoot", "on_ball_defense",
                               "speed", "rebounding"])

            gain_g = after_great - before_great
            gain_p = after_poor  - before_poor
            bt_g   = " BREAKTHROUGH!" if report_g["breakthrough"] else ""
            bt_p   = " BREAKTHROUGH!" if report_p["breakthrough"] else ""

            great_str = "+" + str(gain_g) + bt_g
            poor_str  = "+" + str(gain_p) + bt_p

            print("  {:<12} {:<25} {}".format(year, great_str, poor_str))

    # Breakthrough frequency test
    print("")
    print("=" * 65)
    print("  BREAKTHROUGH FREQUENCY TEST -- 326 programs x 10 players")
    print("  Expected: 2-3% of players = ~65-100 breakthroughs")
    print("=" * 65)

    total_breakthroughs = 0
    total_players       = 0
    coach = generate_coach("Average", prestige=55, experience=10)

    for _ in range(326):
        for year in ["Freshman", "Sophomore", "Junior"]:
            p = make_test_player("Test", "steady", 11, 65)
            p["year"] = year
            _, report = develop_player(p, coach, 2025)
            if report["breakthrough"]:
                total_breakthroughs += 1
            total_players += 1

    print("  Total players: " + str(total_players))
    print("  Breakthroughs: " + str(total_breakthroughs))
    print("  Rate:          " + str(round(total_breakthroughs / total_players * 100, 2)) + "%")
    print("  (target: 2-3%)")
