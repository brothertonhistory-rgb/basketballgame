import random
import uuid
from names import generate_player_name

# -----------------------------------------
# COLLEGE HOOPS SIM -- Player System v0.8
# System 2 of the Design Bible
#
# v0.8 CHANGES -- Phase A: Physical Attributes
#
#   PHYSICAL SIZE (real units, NOT on 1-1000 scale):
#     height   -- inches (68-87). Display layer converts to feet/inches.
#     wingspan -- inches (67-92). Independent from height.
#     weight   -- lbs (160-285). Position-appropriate distributions.
#
#   NEW ATHLETICISM ATTRIBUTES (1-1000 scale):
#     explosiveness -- first-step burst. Different from speed.
#                      Twitchy guards: high explosiveness, avg speed.
#                      Long striders: high speed, avg explosiveness.
#     agility       -- body control, balance. Finishing through contact,
#                      defensive recovery, change of direction in space.
#
#   NEW MENTAL ATTRIBUTES (1-20 scale):
#     ball_dominance    -- permanent personality. How much a player
#                          wants/demands the ball. Never develops much.
#     usage_tendency    -- role acceptance. Can develop with great coaching.
#                          High ball_dominance player CAN develop lower
#                          usage_tendency over time.
#     off_ball_movement -- reads defense, gets to right spot before
#                          ball arrives. Critical for low-usage efficient
#                          players. The dump-off finds him because he's
#                          already there.
#
#   NATURAL POSITION (new field, never changes):
#     natural_position -- "guard", "wing", "post", "guard/wing", "wing/post"
#                         Derived from physical + skill profile at creation.
#                         This is the recruiting/scouting descriptor.
#                         "position" remains the coach's tactical label (PG-C).
#                         In Phase B the engine will derive functional lineup
#                         roles from the five players on the floor together.
#
#   PHYSICAL DEVELOPMENT (inside develop_player):
#     Weight gain: 5-20 lbs over career as players fill out.
#     Height growth: 8% chance freshman->sophomore, 2% sophomore->junior,
#                    never after junior year.
#     Strength tracks weight gain -- heavier players get stronger.
#
#   MIGRATION:
#     ensure_player_physical_attrs() -- safe to call on existing players.
#     Adds all v0.8 attributes without touching existing values.
#
# v0.7 CHANGES (preserved):
#   recruited_by, coach_loyalty
#
# v0.6 CHANGES (preserved):
#   Portal personality attributes, home_state
#
# v0.5 CHANGES (preserved):
#   Unique player_id on every player.
#
# v0.4 CHANGES (preserved):
#   1-1000 internal attribute scale.
# -----------------------------------------

POSITIONS = ["PG", "SG", "SF", "PF", "C"]
YEARS     = ["Freshman", "Sophomore", "Junior", "Senior"]
ARC_TYPES = ["bust", "plateau", "steady", "overachiever", "late_bloomer"]

# Natural position labels -- recruiting/scouting descriptor
NATURAL_POSITIONS = ["guard", "guard/wing", "wing", "wing/post", "post"]

# -----------------------------------------
# PLAYER ID COUNTER
# -----------------------------------------

_PLAYER_ID_COUNTER = [0]

def _next_player_id():
    _PLAYER_ID_COUNTER[0] += 1
    return _PLAYER_ID_COUNTER[0]


# -----------------------------------------
# DEVELOPABLE ATTRIBUTES
# explosiveness and agility added in v0.8
# -----------------------------------------

DEVELOPABLE_ATTRIBUTES = [
    "catch_and_shoot", "off_dribble", "mid_range", "three_point", "free_throw",
    "finishing", "post_scoring",
    "passing", "ball_handling", "court_vision", "decision_making",
    "on_ball_defense", "help_defense", "rebounding", "shot_blocking",
    "steal_tendency",
    "speed", "lateral_quickness", "strength", "vertical",
    "endurance",
    "explosiveness", "agility",   # v0.8 additions
]

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

BREAKTHROUGH_ARC_WEIGHTS = {
    "late_bloomer":  3.0,
    "steady":        1.5,
    "overachiever":  1.2,
    "plateau":       0.3,
    "bust":          0.1,
}

_HOME_STATE_WEIGHTS = {
    "CA": 120, "TX": 110, "FL": 95,  "GA": 90,  "NY": 80,
    "OH": 75,  "IL": 75,  "NC": 70,  "NJ": 65,  "PA": 65,
    "IN": 60,  "MI": 55,  "VA": 55,  "MD": 50,  "TN": 50,
    "AL": 45,  "SC": 45,  "KY": 40,  "MO": 40,  "LA": 40,
    "OK": 35,  "AR": 30,  "MS": 30,  "KS": 28,  "WI": 28,
    "MN": 25,  "CO": 25,  "AZ": 25,  "WA": 22,  "OR": 20,
    "CT": 20,  "MA": 20,  "DC": 18,  "NV": 18,  "UT": 15,
    "IA": 15,  "NE": 12,  "WV": 12,  "DE": 10,  "RI": 8,
    "NH": 6,   "ME": 6,   "VT": 5,   "WY": 5,   "MT": 5,
    "ID": 5,   "SD": 4,   "ND": 4,   "AK": 3,   "HI": 3,
}


def _pick_home_state():
    states  = list(_HOME_STATE_WEIGHTS.keys())
    weights = list(_HOME_STATE_WEIGHTS.values())
    return random.choices(states, weights=weights, k=1)[0]


def _potential_to_attr_ceiling(potential_high):
    return min(950, int(200 + (potential_high / 100.0) * 750))


def generate_portal_personality():
    return {
        "volatility":          _rand_mental(2, 8),
        "playing_time_hunger": _rand_mental(5, 15),
        "home_loyalty":        _rand_mental(3, 14),
        "prestige_ambition":   _rand_mental(4, 14),
        "role_acceptance":     _rand_mental(3, 13),
    }


# -----------------------------------------
# MIGRATION FUNCTIONS
# -----------------------------------------

def ensure_player_personality(player):
    """
    Retroactive migration. Adds portal personality, home_state,
    v0.7 carousel attributes, and v0.8 physical attributes if missing.
    Safe to call multiple times.
    """
    if "volatility" not in player:
        personality = generate_portal_personality()
        for key, val in personality.items():
            player[key] = val

    if "home_state" not in player:
        player["home_state"] = _pick_home_state()

    # v0.7 carousel attributes
    if "coach_loyalty" not in player:
        player["coach_loyalty"] = _rand_mental(3, 15)

    if "recruited_by" not in player:
        player["recruited_by"] = None

    # v0.8 physical attributes
    ensure_player_physical_attrs(player)

    return player


def ensure_player_carousel_attrs(player, coach_id=None):
    """
    v0.7 migration specifically for carousel attributes.
    Call at world-build migration with the program's current coach_id.
    If coach_id is provided and recruited_by is None, stamps it.
    """
    if "coach_loyalty" not in player:
        player["coach_loyalty"] = _rand_mental(3, 15)

    if "recruited_by" not in player:
        player["recruited_by"] = coach_id

    return player


def ensure_player_physical_attrs(player):
    """
    v0.8 migration. Adds all new physical attributes to existing players.
    Safe to call multiple times -- never overwrites existing values.

    For existing players with no physical profile, generates based on
    their position. Not perfect (we don't know their true height) but
    good enough for continuity.
    """
    position = player.get("position", "SF")

    # Physical size (real units)
    if "height" not in player:
        player["height"] = _generate_height(position)
    if "wingspan" not in player:
        player["wingspan"] = _generate_wingspan(player["height"], position)
    if "weight" not in player:
        player["weight"] = _generate_weight(position, player.get("year", "Sophomore"))

    # New athleticism (1-1000)
    if "explosiveness" not in player:
        player["explosiveness"] = _generate_explosiveness(position)
    if "agility" not in player:
        player["agility"] = _generate_agility(position)

    # New mental (1-20)
    if "ball_dominance" not in player:
        player["ball_dominance"] = _rand_mental(3, 16)
    if "usage_tendency" not in player:
        # Correlates loosely with ball_dominance but independent
        bd = player["ball_dominance"]
        base = max(1, min(20, bd + random.randint(-4, 4)))
        player["usage_tendency"] = base
    if "off_ball_movement" not in player:
        player["off_ball_movement"] = _rand_mental(3, 17)

    # Natural position
    if "natural_position" not in player:
        player["natural_position"] = _derive_natural_position(player)

    return player


# -----------------------------------------
# MAIN DEVELOPMENT FUNCTION
# -----------------------------------------

def develop_player(player, coach, season_year,
                   training_focus=None, morale_modifier=1.0):
    year         = player.get("year", "Freshman")
    arc_type     = player.get("arc_type", "steady")
    work_ethic   = player.get("work_ethic", 10)
    coachability = player.get("coachability", 10)
    position     = player.get("position", "SF")
    potential_h  = player.get("potential_high", 50)

    if year == "Senior":
        return player, {"improved": [], "breakthrough": False,
                        "breakthrough_attrs": [], "total_gain": 0,
                        "dev_score": 0}

    year_idx = YEAR_INDEX.get(year, 0)

    dev_rating = 10
    if coach:
        dev_rating = coach.get("player_development", 10)

    self_improvement     = work_ethic / 20.0
    coach_factor         = dev_rating / 20.0
    coachability_factor  = 0.4 + (coachability / 20.0) * 0.6
    base_dev             = (self_improvement * 0.45) + (coach_factor * coachability_factor * 0.55)

    arc_mults    = ARC_YEAR_MULTIPLIERS.get(arc_type, ARC_YEAR_MULTIPLIERS["steady"])
    arc_mult     = arc_mults[min(year_idx, 3)]
    combined_dev = base_dev * arc_mult * morale_modifier

    global_ceiling = _potential_to_attr_ceiling(potential_h)

    natural_attrs = NATURAL_ATTRIBUTES.get(position, DEVELOPABLE_ATTRIBUTES)
    focus_attrs   = list(training_focus.keys()) if training_focus else []

    improved   = []
    total_gain = 0

    for attr in DEVELOPABLE_ATTRIBUTES:
        current      = player.get(attr, 500)
        attr_ceiling = max(current + 30, global_ceiling)

        if current >= attr_ceiling:
            continue

        proximity      = current / attr_ceiling
        ceiling_dampen = max(0.0, 1.0 - (max(0.0, proximity - 0.5) * 2.0) ** 2)

        if ceiling_dampen < 0.05:
            continue

        attr_weight = 1.0
        if attr in natural_attrs:
            attr_weight = 1.5
        if attr in focus_attrs:
            attr_weight += 1.0

        raw_gain   = combined_dev * attr_weight * ceiling_dampen * 15.0
        noise      = random.gauss(0, 8.0)
        final_gain = max(0.0, raw_gain + noise)

        if final_gain >= 3.0:
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
    ethic_weight = work_ethic / 12.0
    ceiling_gap  = global_ceiling - _avg_key_attrs(player, position)
    gap_weight   = max(0.3, min(1.5, ceiling_gap / 600.0))

    breakthrough_chance = 0.06 * arc_weight * ethic_weight * gap_weight

    if year == "Sophomore":
        breakthrough_chance *= 1.6
    elif year == "Junior":
        breakthrough_chance *= 1.2

    if random.random() < breakthrough_chance:
        key_attrs  = natural_attrs[:5]
        num_attrs  = random.randint(2, 3)
        chosen     = random.sample(key_attrs, min(num_attrs, len(key_attrs)))

        bt_gain_this_event = 0
        temp_attrs         = []

        for attr in chosen:
            current = player.get(attr, 500)
            room    = max(0, global_ceiling - current)
            if room < 20:
                continue
            jump = random.randint(20, max(20, min(60, room // 3)))
            temp_attrs.append({
                "attr": attr,
                "from": current,
                "to":   current + jump,
                "gain": jump,
            })
            bt_gain_this_event += jump

        if bt_gain_this_event >= 30 and temp_attrs:
            breakthrough = True
            for entry in temp_attrs:
                player[entry["attr"]] = entry["to"]
                breakthrough_attrs.append(entry)
                total_gain += entry["gain"]

    report = {
        "name":               player["name"],
        "player_id":          player.get("player_id", None),
        "position":           position,
        "year":               year,
        "arc_type":           arc_type,
        "improved":           improved,
        "breakthrough":       breakthrough,
        "breakthrough_attrs": breakthrough_attrs,
        "total_gain":         total_gain,
        "dev_score":          round(combined_dev, 3),
    }

    _develop_endurance(player, coach, combined_dev)
    _develop_physical(player)   # v0.8: weight gain, height growth

    return player, report


def _avg_key_attrs(player, position):
    natural = NATURAL_ATTRIBUTES.get(position, DEVELOPABLE_ATTRIBUTES[:5])
    vals    = [player.get(a, 500) for a in natural[:5]]
    return sum(vals) / max(1, len(vals))


def _develop_endurance(player, coach, combined_dev):
    year = player.get("year", "Freshman")
    if year == "Senior":
        return

    current_endurance = player.get("endurance", 500)
    if current_endurance >= 950:
        return

    pace = 50
    if coach:
        pace = coach.get("pace", 50)
    pace_factor  = pace / 100.0
    work_ethic   = player.get("work_ethic", 10)
    ethic_factor = work_ethic / 20.0
    base_gain    = (pace_factor * 0.65 + ethic_factor * 0.35) * 12.0

    arc_type = player.get("arc_type", "steady")
    arc_endurance_mods = {
        "late_bloomer": 0.8, "steady": 1.0, "overachiever": 1.2,
        "plateau": 0.7, "bust": 0.5,
    }
    base_gain  *= arc_endurance_mods.get(arc_type, 1.0)
    noise       = random.gauss(0, 3.0)
    final_gain  = max(0.0, base_gain + noise)

    if final_gain >= 2.0:
        player["endurance"] = min(950, int(current_endurance + final_gain))


def _develop_physical(player):
    """
    v0.8 -- Physical development each season transition.

    Weight gain:
      All players gain weight as they fill out in college.
      Freshmen gain the most. Seniors gain little or none.
      Gain range: 1-6 lbs per year, weighted toward lower end.

    Height growth:
      8% chance freshman->sophomore (they're still growing)
      2% chance sophomore->junior (rare but happens)
      Never after junior year

    Strength tracks weight:
      Each lb gained adds a small strength bonus.
      The 180lb guy with elite strength still gets moved by
      the 250lb guy -- but he gets stronger as he fills out.
    """
    year = player.get("year", "Freshman")

    # --- WEIGHT GAIN ---
    # Freshmen gain more (still developing), seniors almost none
    weight_gain_by_year = {
        "Freshman":  (2, 6),
        "Sophomore": (1, 5),
        "Junior":    (1, 4),
        "Senior":    (0, 1),
    }
    lo, hi = weight_gain_by_year.get(year, (1, 3))
    gain   = random.randint(lo, hi)

    if gain > 0:
        position    = player.get("position", "SF")
        weight_cap  = _weight_cap(position)
        old_weight  = player.get("weight", _generate_weight(position, year))
        new_weight  = min(weight_cap, old_weight + gain)
        player["weight"] = new_weight

        # Strength bonus from filling out
        # Each lb gained adds ~2-5 strength points (1-1000 scale)
        if new_weight > old_weight:
            lbs_gained     = new_weight - old_weight
            strength_bonus = int(lbs_gained * random.uniform(2.0, 5.0))
            current_str    = player.get("strength", 400)
            player["strength"] = min(950, current_str + strength_bonus)

    # --- HEIGHT GROWTH ---
    # Only happens before junior year, and rarely
    height_grow_chance = {
        "Freshman":  0.08,   # 8% -- still growing
        "Sophomore": 0.02,   # 2% -- rare
        "Junior":    0.0,    # never
        "Senior":    0.0,    # never
    }
    chance = height_grow_chance.get(year, 0.0)
    if chance > 0 and random.random() < chance:
        old_height      = player.get("height", 74)
        position        = player.get("position", "SF")
        height_cap      = _height_cap(position)
        new_height      = min(height_cap, old_height + 1)
        player["height"] = new_height

        # Wingspan may grow slightly with height
        if random.random() < 0.5:
            old_ws = player.get("wingspan", old_height)
            player["wingspan"] = min(92, old_ws + 1)


# -----------------------------------------
# PHYSICAL ATTRIBUTE GENERATORS (v0.8)
# -----------------------------------------

def _generate_height(position):
    """
    Generates height in inches from position-appropriate distribution.
    Uses gaussian around position mean with realistic spread.

    Real D1 averages (approximate):
      PG: 6'2" (74")  SG: 6'4" (76")  SF: 6'7" (79")
      PF: 6'8" (80")  C:  6'10" (82")
    """
    params = {
        "PG": (74.0, 1.8),   # mean 6'2", sd ~2"
        "SG": (76.0, 1.8),   # mean 6'4"
        "SF": (79.0, 1.5),   # mean 6'7"
        "PF": (80.5, 1.5),   # mean 6'8.5"
        "C":  (82.5, 1.5),   # mean 6'10.5"
    }
    mean, sd = params.get(position, (78.0, 2.0))
    raw = int(round(random.gauss(mean, sd)))

    # Hard floor/ceiling per position
    floors   = {"PG": 68, "SG": 70, "SF": 74, "PF": 76, "C": 78}
    ceilings = {"PG": 79, "SG": 81, "SF": 83, "PF": 85, "C": 87}

    return max(floors.get(position, 68), min(ceilings.get(position, 87), raw))


def _height_cap(position):
    """Maximum height a player can reach (growth cap)."""
    return {"PG": 79, "SG": 81, "SF": 83, "PF": 85, "C": 87}.get(position, 83)


def _generate_wingspan(height, position):
    """
    Generates wingspan in inches. Independent from height.
    Most players are within +/- 3" of height.
    Elite length (wingspan >> height) is rare and valuable.

    Wingspan relative to height (design spec):
      wingspan > height + 3: exceptional. Bonus to contests, steals.
      wingspan ~ height:     average. No bonus or penalty.
      wingspan < height - 2: short arms. Penalty to contesting, post D.
    """
    # Most players are close to their height
    # Slight position bias: big men more likely to have long arms
    position_bias = {"PG": -0.5, "SG": 0.0, "SF": 0.5, "PF": 1.0, "C": 1.5}
    bias = position_bias.get(position, 0.0)

    # Gaussian centered at height + bias, spread ~2.5"
    raw = int(round(random.gauss(height + bias, 2.5)))

    # Hard floor/ceiling -- real human range
    return max(height - 5, min(height + 9, max(67, min(92, raw))))


def _generate_weight(position, year="Freshman"):
    """
    Generates weight in lbs from position-appropriate distribution.
    Freshmen arrive lighter -- they haven't filled out yet.
    Uses gaussian around position mean.

    Real D1 averages (approximate):
      PG: 185  SG: 195  SF: 215  PF: 230  C: 250
    """
    params = {
        "PG": (185, 12),
        "SG": (195, 12),
        "SF": (215, 15),
        "PF": (230, 15),
        "C":  (250, 18),
    }
    mean, sd = params.get(position, (210, 15))

    # Freshmen arrive 5-12 lbs lighter
    freshman_penalty = {"Freshman": random.randint(5, 12), "Sophomore": random.randint(2, 6)}
    mean -= freshman_penalty.get(year, 0)

    raw = int(round(random.gauss(mean, sd)))

    floors   = {"PG": 160, "SG": 165, "SF": 185, "PF": 195, "C": 210}
    ceilings = {"PG": 215, "SG": 225, "SF": 245, "PF": 260, "C": 285}

    return max(floors.get(position, 160), min(ceilings.get(position, 285), raw))


def _weight_cap(position):
    """Maximum weight a player can reach."""
    return {"PG": 215, "SG": 225, "SF": 245, "PF": 260, "C": 285}.get(position, 245)


def _generate_explosiveness(position):
    """
    First-step burst. Different from speed.
    Guards and wings tend to be more explosive.
    Bigs can be explosive too -- just rare.
    """
    bases = {"PG": 450, "SG": 440, "SF": 410, "PF": 360, "C": 300}
    return rand_attr(bases.get(position, 380), spread=55)


def _generate_agility(position):
    """
    Body control, balance, change of direction in space.
    Guards have highest agility. Bigs less so.
    Affects finishing through contact, defensive recovery.
    """
    bases = {"PG": 440, "SG": 430, "SF": 410, "PF": 360, "C": 300}
    return rand_attr(bases.get(position, 380), spread=55)


# -----------------------------------------
# NATURAL POSITION DERIVATION (v0.8)
# -----------------------------------------

def _derive_natural_position(player):
    """
    Derives natural_position from physical + skill profile.
    Returns one of: "guard", "guard/wing", "wing", "wing/post", "post"

    Logic:
      Primary driver: height
      Secondary: skill profile (ball handling, post, etc.)
      Result: the scouting/recruiting descriptor, not the tactical label.

    Hybrids are the most interesting cases:
      6'5" with elite ball handling -> "guard/wing"
      6'7" with post skills         -> "wing/post"
      6'6" balanced                 -> "wing"
    """
    height       = player.get("height", 74)
    ball_handling = player.get("ball_handling", 400)
    post_scoring  = player.get("post_scoring", 300)
    passing       = player.get("passing", 350)
    finishing     = player.get("finishing", 400)

    # Guard skill score: ball handling + passing
    guard_skill = (ball_handling + passing) / 2.0
    # Post skill score: post scoring + finishing (for bigs)
    post_skill  = (post_scoring + finishing) / 2.0

    # --- HEIGHT-FIRST CLASSIFICATION ---
    # Then skill profile pushes toward hybrid categories

    if height <= 73:
        # 6'1" and under -- almost certainly a guard
        # Only extreme post skill would push toward wing
        if post_skill > 550 and height >= 72:
            return "guard/wing"
        return "guard"

    elif height <= 76:
        # 6'2" to 6'4"
        if guard_skill >= 450:
            return "guard"          # true PG/SG size, has the skills
        elif guard_skill >= 380:
            return "guard/wing"     # tweener guard
        else:
            return "guard/wing"     # undersized wing

    elif height <= 78:
        # 6'5" to 6'6"
        if guard_skill >= 480:
            return "guard/wing"     # oversized guard, still handles
        elif post_skill >= 450:
            return "wing/post"      # athletic forward type
        else:
            return "wing"           # natural wing

    elif height <= 81:
        # 6'7" to 6'9"
        if guard_skill >= 460:
            return "guard/wing"     # point forward type
        elif post_skill >= 480:
            return "wing/post"      # big wing, posts up
        else:
            return "wing"           # true wing/SF

    elif height <= 83:
        # 6'10" to 6'11"
        if guard_skill >= 440:
            return "wing/post"      # skilled big, handles on perimeter
        elif post_skill >= 430:
            return "post"           # true post player
        else:
            return "wing/post"      # stretch big type

    else:
        # 7'0" and above -- post regardless of skills
        # (a 7-footer with guard skills is still a post/wing/post)
        if guard_skill >= 400:
            return "wing/post"      # unicorn big
        return "post"


# -----------------------------------------
# PLAYER GENERATOR
# -----------------------------------------

def create_player(name, position, year, conference="",
                  shooting=None, defense=None, rebounding=None,
                  playmaking=None, athleticism=None, mental=None,
                  potential=None, heritage=None):

    # Generate physical size first -- height feeds into athleticism penalty
    height   = _generate_height(position)
    wingspan = _generate_wingspan(height, position)
    weight   = _generate_weight(position, year)

    if shooting    is None: shooting    = generate_shooting(position)
    if defense     is None: defense     = generate_defense(position)
    if rebounding  is None: rebounding  = generate_rebounding(position)
    if playmaking  is None: playmaking  = generate_playmaking(position)
    if athleticism is None: athleticism = generate_athleticism(position, height=height)
    if mental      is None: mental      = generate_mental()
    if potential   is None: potential   = generate_potential()

    if not name or "Player" in name:
        generated_name, generated_heritage = generate_player_name(conference=conference)
        name = generated_name
        if heritage is None:
            heritage = generated_heritage
    elif heritage is None:
        _, heritage = generate_player_name(conference=conference)

    personality = generate_portal_personality()

    # Build the player dict -- then derive natural position from full profile
    player = {
        # --- IDENTITY ---
        "player_id": _next_player_id(),
        "name":      name,
        "position":  position,
        "year":      year,
        "heritage":  heritage,

        # --- GEOGRAPHY ---
        "home_state": _pick_home_state(),

        # --- PHYSICAL SIZE (real units, v0.8) ---
        "height":   height,    # inches
        "wingspan": wingspan,  # inches
        "weight":   weight,    # lbs

        # --- SKILL ATTRIBUTES (1-1000) ---
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

        # --- ATHLETICISM (1-1000) ---
        "speed":             athleticism["speed"],
        "lateral_quickness": athleticism["lateral_quickness"],
        "strength":          athleticism["strength"],
        "vertical":          athleticism["vertical"],
        "endurance":         athleticism["endurance"],
        "explosiveness":     athleticism.get("explosiveness",
                                 _generate_explosiveness(position)),
        "agility":           athleticism.get("agility",
                                 _generate_agility(position)),

        # --- MENTAL ATTRIBUTES (1-20) ---
        "basketball_iq": mental["basketball_iq"],
        "clutch":        mental["clutch"],
        "composure":     mental["composure"],
        "coachability":  mental["coachability"],
        "work_ethic":    mental["work_ethic"],
        "leadership":    mental["leadership"],

        # --- NEW MENTAL ATTRIBUTES (1-20, v0.8) ---
        "ball_dominance":    mental.get("ball_dominance",    _rand_mental(3, 16)),
        "usage_tendency":    mental.get("usage_tendency",    _rand_mental(4, 15)),
        "off_ball_movement": mental.get("off_ball_movement", _rand_mental(3, 17)),

        # --- PORTAL PERSONALITY (1-20, permanent identity) ---
        "volatility":           personality["volatility"],
        "playing_time_hunger":  personality["playing_time_hunger"],
        "home_loyalty":         personality["home_loyalty"],
        "prestige_ambition":    personality["prestige_ambition"],
        "role_acceptance":      personality["role_acceptance"],

        # --- CAROUSEL ATTRIBUTES (v0.7) ---
        "recruited_by":  None,
        "coach_loyalty": _rand_mental(3, 15),

        # --- POTENTIAL ---
        "potential_low":  potential["low"],
        "potential_high": potential["high"],
        "arc_type":       potential["arc_type"],

        # --- GAME STATE ---
        "fatigue":    0.0,
        "foul_count": 0,
        "in_game":    True,
    }

    # Derive natural position from completed profile
    player["natural_position"] = _derive_natural_position(player)

    return player


# -----------------------------------------
# ATTRIBUTE GENERATORS
# -----------------------------------------

def rand_attr(base, spread=50):
    val = int(random.gauss(base, spread))
    return max(1, min(1000, val))


def generate_shooting(position):
    if position == "PG":
        return {
            "catch_and_shoot": rand_attr(400),
            "off_dribble":     rand_attr(430),
            "mid_range":       rand_attr(390),
            "three_point":     rand_attr(390),
            "free_throw":      rand_attr(420),
            "finishing":       rand_attr(390),
            "post_scoring":    rand_attr(200),
        }
    elif position == "SG":
        return {
            "catch_and_shoot": rand_attr(460),
            "off_dribble":     rand_attr(440),
            "mid_range":       rand_attr(430),
            "three_point":     rand_attr(440),
            "free_throw":      rand_attr(440),
            "finishing":       rand_attr(390),
            "post_scoring":    rand_attr(210),
        }
    elif position == "SF":
        return {
            "catch_and_shoot": rand_attr(390),
            "off_dribble":     rand_attr(360),
            "mid_range":       rand_attr(380),
            "three_point":     rand_attr(360),
            "free_throw":      rand_attr(380),
            "finishing":       rand_attr(430),
            "post_scoring":    rand_attr(320),
        }
    elif position == "PF":
        return {
            "catch_and_shoot": rand_attr(290),
            "off_dribble":     rand_attr(260),
            "mid_range":       rand_attr(320),
            "three_point":     rand_attr(255),
            "free_throw":      rand_attr(320),
            "finishing":       rand_attr(460),
            "post_scoring":    rand_attr(420),
        }
    else:  # C
        return {
            "catch_and_shoot": rand_attr(190),
            "off_dribble":     rand_attr(160),
            "mid_range":       rand_attr(280),
            "three_point":     rand_attr(160),
            "free_throw":      rand_attr(300),
            "finishing":       rand_attr(470),
            "post_scoring":    rand_attr(450),
        }


def generate_defense(position):
    if position == "PG":
        return {
            "on_ball_defense": rand_attr(380),
            "help_defense":    rand_attr(350),
            "shot_blocking":   rand_attr(150),
            "steal_tendency":  rand_attr(400),
            "foul_tendency":   rand_attr(350),
        }
    elif position == "SG":
        return {
            "on_ball_defense": rand_attr(400),
            "help_defense":    rand_attr(360),
            "shot_blocking":   rand_attr(170),
            "steal_tendency":  rand_attr(380),
            "foul_tendency":   rand_attr(340),
        }
    elif position == "SF":
        return {
            "on_ball_defense": rand_attr(400),
            "help_defense":    rand_attr(400),
            "shot_blocking":   rand_attr(250),
            "steal_tendency":  rand_attr(360),
            "foul_tendency":   rand_attr(360),
        }
    elif position == "PF":
        return {
            "on_ball_defense": rand_attr(360),
            "help_defense":    rand_attr(430),
            "shot_blocking":   rand_attr(340),
            "steal_tendency":  rand_attr(290),
            "foul_tendency":   rand_attr(380),
        }
    else:  # C
        return {
            "on_ball_defense": rand_attr(300),
            "help_defense":    rand_attr(450),
            "shot_blocking":   rand_attr(400),
            "steal_tendency":  rand_attr(230),
            "foul_tendency":   rand_attr(400),
        }


def generate_rebounding(position):
    bases = {"PG": 250, "SG": 280, "SF": 380, "PF": 470, "C": 510}
    return rand_attr(bases.get(position, 350))


def generate_playmaking(position):
    if position == "PG":
        return {
            "passing":         rand_attr(450),
            "ball_handling":   rand_attr(480),
            "court_vision":    rand_attr(430),
            "decision_making": rand_attr(420),
        }
    elif position == "SG":
        return {
            "passing":         rand_attr(360),
            "ball_handling":   rand_attr(390),
            "court_vision":    rand_attr(350),
            "decision_making": rand_attr(360),
        }
    elif position == "SF":
        return {
            "passing":         rand_attr(320),
            "ball_handling":   rand_attr(330),
            "court_vision":    rand_attr(310),
            "decision_making": rand_attr(320),
        }
    elif position == "PF":
        return {
            "passing":         rand_attr(270),
            "ball_handling":   rand_attr(250),
            "court_vision":    rand_attr(260),
            "decision_making": rand_attr(280),
        }
    else:  # C
        return {
            "passing":         rand_attr(220),
            "ball_handling":   rand_attr(190),
            "court_vision":    rand_attr(210),
            "decision_making": rand_attr(240),
        }


def generate_athleticism(position, height=None):
    """
    v0.8: includes explosiveness and agility.
    Height-driven athleticism penalty applied when height is provided.

    Every inch above 78" (6'6") costs speed, lateral quickness,
    explosiveness and agility. Strength gets a small bonus.
    Vertical takes a partial penalty.

    This is what makes the 6'10" ultra-athlete so rare and impactful --
    he's rolling good numbers against a penalty that drags most bigs down.
    The typical 7'0" center has genuinely poor athleticism. He's there
    for his size, shot blocking, and rebounding window. Nothing else.

    Penalty per inch above 78":
      speed:             -10  (range: -0 to -90 for a 7'3" guy)
      lateral_quickness: -10
      explosiveness:     -12
      agility:           -10
      vertical:          -5   (partial -- bigs can still jump)
      strength:          +5   (bonus -- size builds strength)
    """
    if position in ("PG", "SG"):
        base = {
            "speed":             rand_attr(470),
            "lateral_quickness": rand_attr(450),
            "strength":          rand_attr(320),
            "vertical":          rand_attr(420),
            "endurance":         rand_attr(460),
            "explosiveness":     _generate_explosiveness(position),
            "agility":           _generate_agility(position),
        }
    elif position == "SF":
        base = {
            "speed":             rand_attr(430),
            "lateral_quickness": rand_attr(410),
            "strength":          rand_attr(380),
            "vertical":          rand_attr(430),
            "endurance":         rand_attr(450),
            "explosiveness":     _generate_explosiveness(position),
            "agility":           _generate_agility(position),
        }
    elif position == "PF":
        base = {
            "speed":             rand_attr(350),
            "lateral_quickness": rand_attr(340),
            "strength":          rand_attr(460),
            "vertical":          rand_attr(400),
            "endurance":         rand_attr(430),
            "explosiveness":     _generate_explosiveness(position),
            "agility":           _generate_agility(position),
        }
    else:  # C
        base = {
            "speed":             rand_attr(280),
            "lateral_quickness": rand_attr(270),
            "strength":          rand_attr(510),
            "vertical":          rand_attr(370),
            "endurance":         rand_attr(420),
            "explosiveness":     _generate_explosiveness(position),
            "agility":           _generate_agility(position),
        }

    # Apply height-driven penalty if height provided
    if height is not None:
        base = _apply_height_athleticism_penalty(base, height)

    return base


def _apply_height_athleticism_penalty(attrs, height):
    """
    Penalizes athleticism attributes for players taller than 6'6" (78").
    Called from generate_athleticism() and recruit generation.

    The penalty is the core reason why the athletic 6'10" guy is special.
    Most players his size are rolling heavily penalized numbers. He beat
    the penalty through the natural gaussian variance -- a legitimate freak.

    Per inch above 78":
      speed:             -10
      lateral_quickness: -10
      explosiveness:     -12
      agility:           -10
      vertical:           -5
      strength:           +5  (bonus)
    """
    HEIGHT_THRESHOLD = 78   # 6'6"
    inches_over = max(0, height - HEIGHT_THRESHOLD)

    if inches_over == 0:
        return attrs

    penalties = {
        "speed":             -10 * inches_over,
        "lateral_quickness": -10 * inches_over,
        "explosiveness":     -12 * inches_over,
        "agility":           -10 * inches_over,
        "vertical":           -5 * inches_over,
        "strength":           +5 * inches_over,   # bonus
    }

    result = dict(attrs)
    for attr, delta in penalties.items():
        if attr in result:
            result[attr] = max(1, min(950, result[attr] + delta))

    return result


def _rand_mental(low, high=None, spread=None):
    if spread is not None:
        val = int(random.gauss(low, spread))
        return max(1, min(20, val))
    else:
        return random.randint(low, high)


def generate_mental():
    return {
        "basketball_iq":    _rand_mental(5, 18),
        "clutch":           _rand_mental(4, 18),
        "composure":        _rand_mental(4, 18),
        "coachability":     _rand_mental(4, 20),
        "work_ethic":       _rand_mental(4, 20),
        "leadership":       _rand_mental(3, 16),
        # v0.8 new mental attributes
        "ball_dominance":   _rand_mental(3, 16),
        "usage_tendency":   _rand_mental(4, 15),
        "off_ball_movement": _rand_mental(3, 17),
    }


def generate_potential():
    low  = random.randint(10, 60)
    high = random.randint(low + 5, min(100, low + 45))
    return {
        "low":      low,
        "high":     high,
        "arc_type": random.choices(
            ARC_TYPES,
            weights=[0.08, 0.15, 0.45, 0.20, 0.12],
            k=1
        )[0],
    }


# -----------------------------------------
# PRESTIGE-SCALED TEAM GENERATOR
# -----------------------------------------

def apply_prestige_bonus(player, prestige):
    if prestige <= 20:
        bonus_pct = 0.0
    elif prestige <= 40:
        bonus_pct = 0.04 + (prestige - 20) / 20.0 * 0.06
    elif prestige <= 60:
        bonus_pct = 0.10 + (prestige - 40) / 20.0 * 0.08
    elif prestige <= 80:
        bonus_pct = 0.18 + (prestige - 60) / 20.0 * 0.10
    else:
        bonus_pct = 0.28 + (prestige - 80) / 20.0 * 0.10

    bonus_pct = min(bonus_pct, 0.40)

    for attr in DEVELOPABLE_ATTRIBUTES:
        if attr == "endurance":
            continue
        current = player.get(attr, 500)
        boost   = int(current * bonus_pct)
        player[attr] = min(950, current + boost)

    return player


def apply_freak_profile(player, position=None, true_talent=None):
    if random.random() > 0.08:
        return player

    pos = position if position is not None else player.get("position", "SF")

    from recruiting import POSITION_ARCHETYPES
    arch        = POSITION_ARCHETYPES.get(pos, {})
    floor_attrs = arch.get("floor", [])

    if not floor_attrs:
        return player

    attr    = random.choice(floor_attrs)
    current = player.get(attr, 300)

    if true_talent is not None:
        talent_factor = max(0.5, min(1.5, true_talent / 60.0))
        boost = int(random.randint(100, 250) * talent_factor)
    else:
        boost = random.randint(150, 300)

    player[attr] = min(850, current + boost)
    return player


def generate_team(program_name, prestige=50, roster_size=13):
    position_slots = {
        "PG": 2, "SG": 3, "SF": 3, "PF": 3, "C": 2,
    }

    roster = []
    years  = ["Freshman", "Sophomore", "Junior", "Senior"]
    year_dist = [0.30, 0.27, 0.23, 0.20]

    for pos, count in position_slots.items():
        for _ in range(count):
            year   = random.choices(years, weights=year_dist, k=1)[0]
            player = create_player("", pos, year)
            player = apply_prestige_bonus(player, prestige)
            player = apply_freak_profile(player, pos)
            roster.append(player)

    while len(roster) < roster_size:
        pos    = random.choice(POSITIONS)
        year   = random.choices(years, weights=year_dist, k=1)[0]
        player = create_player("", pos, year)
        player = apply_prestige_bonus(player, prestige)
        roster.append(player)

    return {
        "program":     program_name,
        "prestige":    prestige,
        "roster":      roster,
        "roster_size": len(roster),
    }


def get_team_ratings(program):
    roster = program.get("roster", [])
    if not roster:
        return {"shooting": 500, "defense": 500, "rebounding": 500,
                "playmaking": 500, "athleticism": 500}

    shooting      = []
    defense_r     = []
    rebounding_r  = []
    playmaking_r  = []
    athleticism_r = []

    for p in roster:
        shooting.append((
            p.get("catch_and_shoot", 500) +
            p.get("finishing", 500) +
            p.get("three_point", 500)
        ) / 3)
        defense_r.append((
            p.get("on_ball_defense", 500) +
            p.get("help_defense", 500)
        ) / 2)
        rebounding_r.append(p.get("rebounding", 500))
        playmaking_r.append((
            p.get("passing", 500) +
            p.get("ball_handling", 500)
        ) / 2)
        athleticism_r.append((
            p.get("speed", 500) +
            p.get("vertical", 500)
        ) / 2)

    def avg(lst):
        return int(sum(lst) / max(1, len(lst)))

    return {
        "shooting":    avg(shooting),
        "defense":     avg(defense_r),
        "rebounding":  avg(rebounding_r),
        "playmaking":  avg(playmaking_r),
        "athleticism": avg(athleticism_r),
        "name":        program.get("name", "Unknown"),
    }


# -----------------------------------------
# DISPLAY HELPERS (v0.8)
# -----------------------------------------

def display_height(inches):
    """Converts inches to feet'inches" string. E.g. 79 -> 6'7\""""
    feet   = inches // 12
    remain = inches % 12
    return str(feet) + "'" + str(remain) + '"'


def display_physical(player):
    """Returns a readable physical profile string for a player."""
    h  = player.get("height",   74)
    ws = player.get("wingspan", 74)
    w  = player.get("weight",   200)
    np = player.get("natural_position", "?")
    ws_diff = ws - h
    ws_note = ""
    if ws_diff >= 4:
        ws_note = " (long)"
    elif ws_diff <= -2:
        ws_note = " (short arms)"
    return (display_height(h) + "  " +
            display_height(ws) + ws_note + "  " +
            str(w) + "lbs  [" + np + "]")


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from display import display_attr

    print("=" * 65)
    print("  PLAYER SYSTEM v0.8 -- PHYSICAL ATTRIBUTES TEST")
    print("=" * 65)

    print("")
    print("=== Physical profile by position (10 players each) ===")
    print("{:<6} {:<10} {:<10} {:<8} {:<12} {:<14}".format(
        "Pos", "Height", "Wingspan", "Weight", "NatPos", "Explo/Agility"
    ))
    print("-" * 65)

    for pos in ["PG", "SG", "SF", "PF", "C"]:
        for _ in range(3):
            p = create_player("", pos, "Freshman")
            print("{:<6} {:<10} {:<10} {:<8} {:<14} {:<6}/{:<6}".format(
                pos,
                display_height(p["height"]),
                display_height(p["wingspan"]),
                str(p["weight"]) + "lbs",
                p["natural_position"],
                display_attr(p["explosiveness"], "1-20"),
                display_attr(p["agility"], "1-20"),
            ))
        print("")

    print("")
    print("=== Natural position distribution (500 players) ===")
    from collections import Counter
    nat_counts = Counter()
    for pos in POSITIONS:
        for _ in range(100):
            p = create_player("", pos, "Freshman")
            nat_counts[p["natural_position"]] += 1

    for label in NATURAL_POSITIONS:
        count = nat_counts.get(label, 0)
        bar   = "#" * (count // 5)
        print("  {:<12} {:>4}  {}".format(label, count, bar))

    print("")
    print("=== Ball dominance + usage tendency sample ===")
    print("{:<22} {:<5} {:<15} {:<14} {:<16}".format(
        "Name", "Pos", "NatPos", "BallDominance", "UsageTendency"
    ))
    print("-" * 75)
    for pos in ["PG", "SG", "SF", "PF", "C"]:
        p = create_player("", pos, "Junior")
        print("{:<22} {:<5} {:<15} {:<14} {:<16}".format(
            p["name"][:21], p["position"],
            p["natural_position"],
            str(p["ball_dominance"]) + "/20",
            str(p["usage_tendency"]) + "/20",
        ))

    print("")
    print("=== Physical development test (Freshman -> 3 seasons) ===")
    p = create_player("Test Player", "C", "Freshman")
    print("  Starting: " + display_physical(p))
    fake_coach = {"player_development": 12, "pace": 65}
    for yr in ["Freshman", "Sophomore", "Junior"]:
        p["year"] = yr
        p, _ = develop_player(p, fake_coach, 2025)
        print("  After " + yr + ": " + display_physical(p))

    print("")
    print("=== Migration test (old player gets v0.8 attrs) ===")
    old = {"name": "Old Timer", "position": "SF", "year": "Senior",
           "player_id": 9999, "finishing": 600, "ball_handling": 350,
           "post_scoring": 300, "passing": 310}
    ensure_player_physical_attrs(old)
    print("  " + display_physical(old))
    print("  explosiveness: " + display_attr(old["explosiveness"], "1-20") + "/20")
    print("  ball_dominance: " + str(old["ball_dominance"]) + "/20")
