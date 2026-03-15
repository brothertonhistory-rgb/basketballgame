import random
import uuid
from names import generate_player_name

# -----------------------------------------
# COLLEGE HOOPS SIM -- Player System v0.5
# System 2 of the Design Bible
#
# v0.5 CHANGES -- Unique Player ID:
#
#   Every player now receives a unique integer ID at creation.
#   Stored as player["player_id"] -- a monotonically incrementing
#   integer from _PLAYER_ID_COUNTER.
#
#   WHY THIS MATTERS:
#     - Almanac queries: find every season a specific player appeared
#       in, across any program, even after transferring.
#     - Transfer portal: player identity persists when he moves schools.
#     - Career stat continuity: stats follow the player, not the name.
#     - Future database migration: integer IDs index cleanly into SQLite.
#     - Two players with the same name are unambiguous.
#
#   The ID is immutable -- it never changes after creation.
#   It is the single source of truth for player identity.
#
# v0.4 CHANGES -- 1-1000 internal attribute scale.
#   All skill attributes on 1-1000 scale.
#   Mental attributes (work_ethic, coachability, basketball_iq,
#   clutch, composure, leadership) remain on 1-20.
#   Display handled entirely by display.py.
#
# SCALE ANCHORS:
#   1000 -- generational. Not present at world-build.
#    950 -- superstar, top 3 draft pick. Rare outlier.
#    850 -- high-major star, all-conference level.
#    750 -- solid high-major starter.
#    650 -- mid-major starter, fringe high-major.
#    550 -- fringe D1. A coach said yes.
#    300 -- below average even for D1.
#    150 -- true floor. Cannot do this thing.
# -----------------------------------------

POSITIONS = ["PG", "SG", "SF", "PF", "C"]
YEARS     = ["Freshman", "Sophomore", "Junior", "Senior"]
ARC_TYPES = ["bust", "plateau", "steady", "overachiever", "late_bloomer"]

# -----------------------------------------
# PLAYER ID COUNTER
# Simple monotonic integer. Starts at 1.
# In a future SQLite migration this becomes the primary key.
# -----------------------------------------

_PLAYER_ID_COUNTER = [0]   # mutable list so it persists across calls

def _next_player_id():
    _PLAYER_ID_COUNTER[0] += 1
    return _PLAYER_ID_COUNTER[0]


# All developable skill attributes -- mental attributes never change
DEVELOPABLE_ATTRIBUTES = [
    "catch_and_shoot", "off_dribble", "mid_range", "three_point", "free_throw",
    "finishing", "post_scoring",
    "passing", "ball_handling", "court_vision", "decision_making",
    "on_ball_defense", "help_defense", "rebounding", "shot_blocking",
    "steal_tendency",
    "speed", "lateral_quickness", "strength", "vertical",
    "endurance",
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


# -----------------------------------------
# CEILING CONVERSION
# -----------------------------------------

def _potential_to_attr_ceiling(potential_high):
    """
    Converts potential_high (1-100) to attribute ceiling on 1-1000 scale.
    Formula: 200 + (potential_high / 100) * 750
    Cap at 950 -- 1000 reserved for future special events only.
    """
    return min(950, int(200 + (potential_high / 100.0) * 750))


# -----------------------------------------
# MAIN DEVELOPMENT FUNCTION
# -----------------------------------------

def develop_player(player, coach, season_year,
                   training_focus=None, morale_modifier=1.0):
    """
    Develops a player through one offseason.
    Returns (player, development_report).
    All attribute gains on the 1-1000 scale.
    """
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

    return player, report


def _avg_key_attrs(player, position):
    natural = NATURAL_ATTRIBUTES.get(position, DEVELOPABLE_ATTRIBUTES[:5])
    vals    = [player.get(a, 500) for a in natural[:5]]
    return sum(vals) / max(1, len(vals))


def _develop_endurance(player, coach, combined_dev):
    """Develops endurance separately. Pace is primary driver."""
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


# -----------------------------------------
# PLAYER GENERATOR
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
        # --- IDENTITY ---
        "player_id": _next_player_id(),   # v0.5: unique immutable integer ID
        "name":      name,
        "position":  position,
        "year":      year,
        "heritage":  heritage,

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

        "speed":             athleticism["speed"],
        "lateral_quickness": athleticism["lateral_quickness"],
        "strength":          athleticism["strength"],
        "vertical":          athleticism["vertical"],
        "endurance":         athleticism["endurance"],

        # --- MENTAL ATTRIBUTES (1-20, intentionally separate scale) ---
        "basketball_iq": mental["basketball_iq"],
        "clutch":        mental["clutch"],
        "composure":     mental["composure"],
        "coachability":  mental["coachability"],
        "work_ethic":    mental["work_ethic"],
        "leadership":    mental["leadership"],

        # --- POTENTIAL (1-100 talent abstraction) ---
        "potential_low":  potential["low"],
        "potential_high": potential["high"],
        "arc_type":       potential["arc_type"],

        # --- GAME STATE ---
        "fatigue":    0.0,
        "foul_count": 0,
        "in_game":    True,
    }

    return player


# -----------------------------------------
# ATTRIBUTE GENERATORS
# All values on 1-1000 scale.
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


def generate_athleticism(position):
    if position in ("PG", "SG"):
        return {
            "speed":             rand_attr(470),
            "lateral_quickness": rand_attr(450),
            "strength":          rand_attr(320),
            "vertical":          rand_attr(420),
            "endurance":         rand_attr(460),
        }
    elif position == "SF":
        return {
            "speed":             rand_attr(430),
            "lateral_quickness": rand_attr(410),
            "strength":          rand_attr(380),
            "vertical":          rand_attr(430),
            "endurance":         rand_attr(450),
        }
    elif position == "PF":
        return {
            "speed":             rand_attr(350),
            "lateral_quickness": rand_attr(340),
            "strength":          rand_attr(460),
            "vertical":          rand_attr(400),
            "endurance":         rand_attr(430),
        }
    else:  # C
        return {
            "speed":             rand_attr(280),
            "lateral_quickness": rand_attr(270),
            "strength":          rand_attr(510),
            "vertical":          rand_attr(370),
            "endurance":         rand_attr(420),
        }


def _rand_mental(low, high=None, spread=None):
    """
    Flexible mental attribute generator.
    Supports two calling styles:
      _rand_mental(low, high)          -- original style, random int in range
      _rand_mental(base, spread=n)     -- recruiting.py style, gaussian around base
    """
    if spread is not None:
        # Called as _rand_mental(base, spread=n) -- gaussian around base
        val = int(random.gauss(low, spread))
        return max(1, min(20, val))
    else:
        # Called as _rand_mental(low, high) -- uniform range
        return random.randint(low, high)


def generate_mental():
    return {
        "basketball_iq": _rand_mental(5, 18),
        "clutch":        _rand_mental(4, 18),
        "composure":     _rand_mental(4, 18),
        "coachability":  _rand_mental(4, 20),
        "work_ethic":    _rand_mental(4, 20),
        "leadership":    _rand_mental(3, 16),
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
    """
    Scales player attributes up based on program prestige.
    Elite programs recruit better players -- this reflects that
    at world-build without running a full recruiting cycle.
    """
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
    """
    Occasionally gives a player an unusually high cross-positional attribute.
    Creates the PG who can rebound, the C who can shoot, etc.

    Supports two calling styles:
      apply_freak_profile(player, position)              -- original style
      apply_freak_profile(player, true_talent=n)         -- recruiting.py style
        When called with true_talent only, position is read from the player dict.
        true_talent modulates the boost magnitude -- higher talent = bigger freak spike.
    """
    if random.random() > 0.08:
        return player

    # Resolve position -- either passed directly or read from player dict
    pos = position if position is not None else player.get("position", "SF")

    from recruiting import POSITION_ARCHETYPES
    arch        = POSITION_ARCHETYPES.get(pos, {})
    floor_attrs = arch.get("floor", [])

    if not floor_attrs:
        return player

    attr    = random.choice(floor_attrs)
    current = player.get(attr, 300)

    # Higher true_talent = larger potential freak boost
    if true_talent is not None:
        talent_factor = max(0.5, min(1.5, true_talent / 60.0))
        boost = int(random.randint(100, 250) * talent_factor)
    else:
        boost = random.randint(150, 300)

    player[attr] = min(850, current + boost)
    return player


def generate_team(program_name, prestige=50, roster_size=13):
    """
    Generates a full roster for a program at world-build.
    Each player gets a unique player_id via create_player().
    """
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

    # Fill to roster_size with random positions
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
    """
    Returns aggregate team ratings for a program.
    Used by the game engine for team-level calculations.
    """
    roster = program.get("roster", [])
    if not roster:
        return {"shooting": 500, "defense": 500, "rebounding": 500,
                "playmaking": 500, "athleticism": 500}

    shooting    = []
    defense_r   = []
    rebounding_r = []
    playmaking_r = []
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
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from display import display_attr
    from recruiting import POSITION_ARCHETYPES, ALL_ATTRIBUTES

    print("=" * 65)
    print("  PLAYER SYSTEM v0.5 -- UNIQUE ID + 1-1000 SCALE TEST")
    print("=" * 65)

    print("")
    print("=== Player ID verification ===")
    p1 = create_player("Marcus Dillard", "PG", "Junior")
    p2 = create_player("Tyrese Holloway", "SG", "Senior")
    p3 = create_player("DeShawn Price", "C", "Junior")
    print("  " + p1["name"] + "  player_id: " + str(p1["player_id"]))
    print("  " + p2["name"] + "  player_id: " + str(p2["player_id"]))
    print("  " + p3["name"] + "  player_id: " + str(p3["player_id"]))
    print("  IDs are unique and monotonically increasing: " +
          str(p1["player_id"] < p2["player_id"] < p3["player_id"]))

    print("")
    print("=== Roster generation -- IDs persist across full team ===")
    team = generate_team("Oklahoma State", prestige=62)
    print("  Generated " + str(len(team["roster"])) + " players")
    ids  = [p["player_id"] for p in team["roster"]]
    print("  All IDs unique: " + str(len(ids) == len(set(ids))))
    print("  ID range: " + str(min(ids)) + " to " + str(max(ids)))
    print("")
    for p in team["roster"][:5]:
        print("  ID:{:<6} {:<22} {:<5} {:<12}".format(
            p["player_id"], p["name"][:21], p["position"], p["year"]))

    print("")
    print("=== Overall roster quality by prestige tier (200 rosters each) ===")
    tier_configs = [
        ("elite(92)",   92),
        ("good(70)",    70),
        ("average(50)", 50),
        ("low(30)",     30),
        ("bottom(15)",  15),
    ]
    print("  {:<14} {:<12} {:<8}".format("Tier", "Avg Primary", "Grade"))
    print("  " + "-" * 34)
    for tier_name, prestige in tier_configs:
        all_primary_vals = []
        for _ in range(200):
            t      = generate_team("Test", prestige=prestige)
            roster = t["roster"]
            for p in roster:
                pos          = p["position"]
                arch         = POSITION_ARCHETYPES.get(pos, {})
                primary_attrs = arch.get("primary", [])
                for attr in primary_attrs:
                    if attr in p:
                        all_primary_vals.append(p[attr])
        avg = sum(all_primary_vals) / max(1, len(all_primary_vals))
        print("  {:<14} {:<12} {:<8}".format(
            tier_name, str(round(avg)), display_attr(avg, "letter")))
