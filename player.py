import random
from names import generate_player_name

# -----------------------------------------
# COLLEGE HOOPS SIM -- Player System v0.4
# System 2 of the Design Bible
#
# v0.4 CHANGES -- 1-1000 internal attribute scale.
#
#   ALL SKILL ATTRIBUTES now live on a 1-1000 internal scale.
#   Mental attributes (work_ethic, coachability, basketball_iq,
#   clutch, composure, leadership) remain on 1-20 -- they measure
#   character, not skill, same as coach competence ratings.
#
#   DISPLAY is handled entirely by display.py.
#   Never use raw attribute values in UI output.
#   Always pass them through display_attr().
#
#   SCALE ANCHORS (for reference):
#     1000  -- generational, Steph Curry level. Not present at world-build.
#      950  -- superstar, top 3 draft pick candidate. Rare outlier.
#      850  -- high-major star, all-conference level.
#      750  -- solid high-major starter.
#      650  -- mid-major starter, fringe high-major.
#      550  -- fringe D1, primary skill present. A coach said yes.
#      300  -- below average even for D1.
#      150  -- true floor. This player genuinely cannot do this thing.
#
#   DEVELOPMENT (develop_player):
#     Raw gain per attribute per season now calibrated to 1-1000.
#     A great coach + great player can move 10-20 points on a
#     natural attribute in a strong development year.
#     Breakthrough events jump 20-60 points.
#     A 1-point improvement is meaningful and invisible on display
#     until it crosses a grade boundary -- that's the point.
#
#   CEILING CONVERSION:
#     potential_high stays 1-100 (talent abstraction, not a skill).
#     _potential_to_attr_ceiling() maps it to 1-1000:
#       potential 100 -> ceiling 950
#       potential 85  -> ceiling 838
#       potential 65  -> ceiling 688
#       potential 40  -> ceiling 500
#       potential 20  -> ceiling 350
#     Formula: 200 + (potential_high / 100) * 750
#
# v0.3 CHANGES (preserved below):
#   - develop_player() added with arc types, coach multiplier,
#     ceiling dampening, breakthrough events.
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
    "endurance",   # physical stamina -- develops faster under high-pace coaches
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
    on the 1-1000 scale.

    Mapping:
      potential_high 20  -> ceiling ~350  (limited player)
      potential_high 40  -> ceiling ~500  (role player ceiling)
      potential_high 65  -> ceiling ~688  (solid contributor ceiling)
      potential_high 85  -> ceiling ~838  (star ceiling)
      potential_high 95  -> ceiling ~913  (elite ceiling)
      potential_high 100 -> ceiling  950  (superstar ceiling)

    Formula: 200 + (potential_high / 100) * 750
    Note: 1000 is not achievable through normal development.
    It would require potential_high > 100, which doesn't exist.
    A true 1000 is reserved for future special events only.
    """
    return min(950, int(200 + (potential_high / 100.0) * 750))


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

    All attribute gains are on the 1-1000 scale.
    A meaningful single-attribute improvement is 5-20 points.
    A breakthrough jumps 20-60 points.
    """

    year         = player.get("year", "Freshman")
    arc_type     = player.get("arc_type", "steady")
    work_ethic   = player.get("work_ethic", 10)      # 1-20 mental scale
    coachability = player.get("coachability", 10)     # 1-20 mental scale
    position     = player.get("position", "SF")
    potential_h  = player.get("potential_high", 50)   # 1-100 talent score

    # Seniors don't develop
    if year == "Senior":
        return player, {"improved": [], "breakthrough": False,
                        "breakthrough_attrs": [], "total_gain": 0,
                        "dev_score": 0}

    year_idx = YEAR_INDEX.get(year, 0)

    # --- COACH QUALITY ---
    dev_rating = 10
    if coach:
        dev_rating = coach.get("player_development", 10)  # 1-20 coach scale

    # --- BASE DEVELOPMENT SCORE ---
    # Self-improvement: always happens, driven by work_ethic (1-20)
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

    # --- ATTRIBUTE CEILING (1-1000 scale) ---
    global_ceiling = _potential_to_attr_ceiling(potential_h)

    # --- DETERMINE ATTRIBUTE IMPROVEMENTS ---
    natural_attrs = NATURAL_ATTRIBUTES.get(position, DEVELOPABLE_ATTRIBUTES)
    focus_attrs   = list(training_focus.keys()) if training_focus else []

    improved   = []
    total_gain = 0

    for attr in DEVELOPABLE_ATTRIBUTES:
        current = player.get(attr, 500)

        # Each attribute has the global ceiling as its max.
        # Ensure at least 30 points of room above current value so
        # ceiling dampening doesn't kill all growth for low-ceiling
        # players who start close to their potential_high.
        attr_ceiling = max(current + 30, global_ceiling)

        # Already at or above ceiling -- no growth
        if current >= attr_ceiling:
            continue

        # Ceiling proximity dampening
        # At 100% of ceiling: multiplier = 0.0
        # At 75% of ceiling: multiplier ~0.44
        # At 50% of ceiling: multiplier ~1.0
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

        # Raw gain on 1-1000 scale.
        # Max possible: ~15 points per attribute per season for great
        # coach + great player + natural attribute + no ceiling pressure.
        # This keeps internal movement meaningful but sub-threshold
        # relative to display grades -- a player can improve 8 points
        # internally without crossing a letter grade boundary.
        raw_gain = combined_dev * attr_weight * ceiling_dampen * 15.0

        # Noise -- scaled to 1-1000 (was 0.25, now 8.0)
        noise      = random.gauss(0, 8.0)
        final_gain = max(0.0, raw_gain + noise)

        # Apply only if meaningful on 1-1000 scale
        # (threshold was 0.50 on 1-20, now 3 on 1-1000)
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
    ethic_weight = work_ethic / 12.0   # 0.08 - 1.67

    # Ceiling gap weight: wide gap = more likely to break through.
    # Gaps are now 0-800 on 1-1000 scale. Dividing by 600 keeps
    # the weight in a sane 0.3-1.5 range, same behavior as v0.3.
    ceiling_gap  = global_ceiling - _avg_key_attrs(player, position)
    gap_weight   = max(0.3, min(1.5, ceiling_gap / 600.0))

    # Base breakthrough chance: ~1.0% per player per season
    breakthrough_chance = 0.06 * arc_weight * ethic_weight * gap_weight

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
            current = player.get(attr, 500)
            room    = max(0, global_ceiling - current)
            # Breakthrough minimum jump on 1-1000 scale: 20 points.
            # A real breakthrough is visible movement -- sub-20 is noise.
            if room < 20:
                continue
            # Jump: 20-60 points depending on room available
            jump = random.randint(20, max(20, min(60, room // 3)))
            temp_attrs.append({
                "attr": attr,
                "from": current,
                "to":   current + jump,
                "gain": jump,
            })
            bt_gain_this_event += jump

        # Only count as a breakthrough if total gain is at least 30 points
        if bt_gain_this_event >= 30 and temp_attrs:
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

    # --- ENDURANCE DEVELOPMENT ---
    # Endurance develops separately from skill attributes.
    # Primary driver: coach's pace system. Playing in a fast-paced
    # system is like conditioning training -- endurance improves faster.
    # Work ethic is a secondary driver.
    #
    # SEASON-LONG FATIGUE HOOK (future):
    #   When season-long fatigue is built, pass cumulative_minutes here.
    #   High-minute players develop endurance faster but wear down more.
    _develop_endurance(player, coach, combined_dev)

    return player, report


def _avg_key_attrs(player, position):
    """Average of the top natural attributes for this position."""
    natural = NATURAL_ATTRIBUTES.get(position, DEVELOPABLE_ATTRIBUTES[:5])
    vals    = [player.get(a, 500) for a in natural[:5]]
    return sum(vals) / max(1, len(vals))


def _develop_endurance(player, coach, combined_dev):
    """
    Develops endurance separately from skill attributes.

    Pace is the primary driver -- a fast-pace system is conditioning
    training by design. Every practice, every game is a cardio workout.
    Work ethic is a secondary driver.

    A player under a pace 85 coach for 3 years will have meaningfully
    better endurance than the same player under a pace 20 coach.

    Gains are modest -- 3-12 points per season typically.
    No ceiling dampening on endurance -- it can always improve.
    Cap at 950 (same as skill attributes).

    SEASON-LONG FATIGUE HOOK:
    When built, cumulative_minutes will be passed in and
    high-minute players will gain endurance faster but also
    accumulate fatigue that reduces performance late in the season.
    """
    year = player.get("year", "Freshman")
    if year == "Senior":
        return  # seniors don't develop

    current_endurance = player.get("endurance", 500)
    if current_endurance >= 950:
        return

    # Pace contribution -- fast pace systems train endurance harder
    pace = 50
    if coach:
        pace = coach.get("pace", 50)
    pace_factor = pace / 100.0   # 0.0-1.0

    # Work ethic contribution
    work_ethic   = player.get("work_ethic", 10)
    ethic_factor = work_ethic / 20.0   # 0.05-1.0

    # Base endurance gain: pace-weighted + work ethic
    # Max ~12 points/season for pace 85 + high work ethic
    base_gain = (pace_factor * 0.65 + ethic_factor * 0.35) * 12.0

    # Arc type modifier -- overachievers and steady types condition well
    arc_type = player.get("arc_type", "steady")
    arc_endurance_mods = {
        "late_bloomer":  0.8,
        "steady":        1.0,
        "overachiever":  1.2,
        "plateau":       0.7,
        "bust":          0.5,
    }
    arc_mod   = arc_endurance_mods.get(arc_type, 1.0)
    base_gain *= arc_mod

    # Add noise
    noise      = random.gauss(0, 3.0)
    final_gain = max(0.0, base_gain + noise)

    if final_gain >= 2.0:
        new_endurance = min(950, int(current_endurance + final_gain))
        player["endurance"] = new_endurance


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
        "name":       name,
        "position":   position,
        "year":       year,
        "heritage":   heritage,

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
#
# rand_attr() centers on a base with gaussian spread.
# Bases are chosen so the average generated player sits in the
# 480-560 range on primary attributes -- a typical D1 walkon or
# low-end scholarship player before prestige bonuses.
#
# Position-specific distributions reflect real basketball:
#   PG primary = ball handling, passing, vision
#   C  primary = rebounding, shot blocking, strength
#   etc.
# -----------------------------------------

def rand_attr(base, spread=50):
    """
    Generates a random attribute on 1-1000 scale.
    base   -- center of gaussian distribution
    spread -- standard deviation (default 50, about 1/20th of scale)
    """
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
            "mid_range":       rand_attr(240),
            "three_point":     rand_attr(160),
            "free_throw":      rand_attr(280),
            "finishing":       rand_attr(480),
            "post_scoring":    rand_attr(460),
        }


def generate_defense(position):
    if position in ["PG", "SG"]:
        return {
            "on_ball_defense": rand_attr(370),
            "help_defense":    rand_attr(350),
            "shot_blocking":   rand_attr(140),
            "steal_tendency":  rand_attr(390),
            "foul_tendency":   rand_attr(350),
        }
    elif position == "SF":
        return {
            "on_ball_defense": rand_attr(400),
            "help_defense":    rand_attr(385),
            "shot_blocking":   rand_attr(250),
            "steal_tendency":  rand_attr(360),
            "foul_tendency":   rand_attr(350),
        }
    else:  # PF / C
        return {
            "on_ball_defense": rand_attr(320),
            "help_defense":    rand_attr(420),
            "shot_blocking":   rand_attr(400),
            "steal_tendency":  rand_attr(240),
            "foul_tendency":   rand_attr(375),
        }


def generate_rebounding(position):
    bases = {"PG": 210, "SG": 240, "SF": 350, "PF": 470, "C": 520}
    return rand_attr(bases.get(position, 350))


def generate_playmaking(position):
    if position == "PG":
        return {
            "passing":         rand_attr(470),
            "ball_handling":   rand_attr(480),
            "court_vision":    rand_attr(455),
            "decision_making": rand_attr(445),
        }
    elif position == "SG":
        return {
            "passing":         rand_attr(390),
            "ball_handling":   rand_attr(420),
            "court_vision":    rand_attr(360),
            "decision_making": rand_attr(380),
        }
    elif position == "SF":
        return {
            "passing":         rand_attr(350),
            "ball_handling":   rand_attr(350),
            "court_vision":    rand_attr(345),
            "decision_making": rand_attr(345),
        }
    else:  # PF / C
        return {
            "passing":         rand_attr(240),
            "ball_handling":   rand_attr(200),
            "court_vision":    rand_attr(240),
            "decision_making": rand_attr(265),
        }


def generate_athleticism(position):
    if position in ["PG", "SG"]:
        return {
            "speed":             rand_attr(470),
            "lateral_quickness": rand_attr(460),
            "strength":          rand_attr(290),
            "vertical":          rand_attr(410),
            "endurance":         rand_attr(560, spread=80),  # PG highest baseline
        }
    elif position == "SF":
        return {
            "speed":             rand_attr(410),
            "lateral_quickness": rand_attr(395),
            "strength":          rand_attr(375),
            "vertical":          rand_attr(395),
            "endurance":         rand_attr(500, spread=80),  # wide variance position
        }
    else:  # PF / C
        return {
            "speed":             rand_attr(285),
            "lateral_quickness": rand_attr(275),
            "strength":          rand_attr(465),
            "vertical":          rand_attr(350),
            "endurance":         rand_attr(440, spread=80),  # lowest baseline, real outliers exist
        }


def generate_mental():
    """
    Mental attributes stay on 1-20 scale intentionally.
    They measure character and psychology, not physical skill.
    Same reasoning as coach competence ratings staying 1-20.
    """
    return {
        "basketball_iq": _rand_mental(10),
        "clutch":        _rand_mental(10),
        "composure":     _rand_mental(10),
        "coachability":  _rand_mental(10),
        "work_ethic":    _rand_mental(10),
        "leadership":    _rand_mental(10),
    }


def _rand_mental(base, spread=3):
    """Generates a mental attribute on 1-20 scale."""
    val = int(random.gauss(base, spread))
    return max(1, min(20, val))


def generate_potential():
    """
    Generates potential range and arc type.
    potential low/high remain 1-100 talent scores -- they are
    scouting abstractions, not attribute values.
    _potential_to_attr_ceiling() converts them to 1-1000 when needed.
    """
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
    else:  # late_bloomer
        return {"low": max(1, base-2), "high": base+6,  "arc_type": arc}


# -----------------------------------------
# FREAK PROFILE SYSTEM
#
# ~10% of all players get a cross-positional attribute cluster boost.
# The profile is internal only -- never shown to the human player.
# The player's numbers tell the story without a label.
#
# Physical plausibility rules:
#   - No short guard gets shot_blocking boost
#   - No slow big gets speed boost into guard range
#   - Boosts land in 520-720 range depending on talent level
#     (enough to be meaningful, not enough to break position identity)
#
# Each profile defines which attributes get boosted together
# so the result is a coherent player type, not a random anomaly.
# -----------------------------------------

FREAK_PROFILES = {
    "PG": [
        # Marcus Smart / Jrue Holiday -- defensive anchor guard
        ("defensive_anchor",   ["rebounding", "strength", "help_defense",
                                 "lateral_quickness", "on_ball_defense"]),
        # The scrappy rebounder -- times his jumps, crashes the glass
        ("scrappy_rebounder",  ["rebounding", "strength", "vertical"]),
        # Secondary playmaker -- reads the floor, finds cutters
        ("secondary_playmaker",["passing", "court_vision", "decision_making"]),
    ],
    "SG": [
        # The glass guard -- rebounds like a forward
        ("glass_guard",        ["rebounding", "strength", "vertical"]),
        # Defensive anchor -- switchable, guards 1-4
        ("defensive_anchor",   ["on_ball_defense", "help_defense", "lateral_quickness",
                                 "rebounding", "strength"]),
        # Playmaking two -- initiates offense, high vision
        ("playmaking_two",     ["passing", "court_vision", "ball_handling"]),
    ],
    "SF": [
        # Point forward -- handles, initiates, finds teammates
        ("point_forward",      ["ball_handling", "passing", "court_vision",
                                 "decision_making"]),
        # Big wing -- post scoring, overpowers smaller defenders
        ("big_wing",           ["post_scoring", "strength", "finishing"]),
        # Defensive stopper -- long, blocks shots, guards multiple positions
        ("defensive_stopper",  ["shot_blocking", "on_ball_defense", "lateral_quickness",
                                 "help_defense"]),
    ],
    "PF": [
        # Stretch initiator -- handles, shoots, runs the offense from the elbow
        ("stretch_initiator",  ["ball_handling", "passing", "catch_and_shoot",
                                 "three_point"]),
        # Switchable modern big -- guards guards on the perimeter
        ("switchable_modern",  ["lateral_quickness", "speed", "on_ball_defense"]),
        # Passing big -- finds cutters, runs two-man game
        ("passing_big",        ["passing", "court_vision", "decision_making"]),
    ],
    "C": [
        # The Jokic -- passes like a guard, runs the offense
        ("passing_big",        ["passing", "court_vision", "ball_handling",
                                 "decision_making"]),
        # Mobile center -- moves his feet, guards on the perimeter some
        ("mobile_center",      ["lateral_quickness", "speed", "on_ball_defense"]),
        # Face-up four -- shoots from the elbow, faces the basket
        ("face_up_four",       ["mid_range", "catch_and_shoot", "ball_handling"]),
    ],
}

# Probability any individual player gets a freak profile
FREAK_PROFILE_CHANCE = 0.10   # 10% of all generated players


def apply_freak_profile(player, true_talent=50):
    """
    Rolls for a cross-positional freak profile on a single player.
    If the roll hits, boosts 2-5 attributes from a different position's
    primary pool into a meaningful range for this player's talent level.

    true_talent  -- 1-100, used to scale how high the boost lands.
                    A fringe player's freak attribute lands at 520-600.
                    An elite player's freak attribute lands at 620-720.

    Modifies player dict in place. Returns player.
    """
    if random.random() > FREAK_PROFILE_CHANCE:
        return player

    position = player.get("position", "SF")
    profiles  = FREAK_PROFILES.get(position, [])
    if not profiles:
        return player

    profile_name, boost_attrs = random.choice(profiles)

    # Scale boost range to talent level
    # Fringe (talent ~20): boost lands 500-580
    # Mid (talent ~55):    boost lands 540-640
    # Elite (talent ~90):  boost lands 600-720
    talent_factor = (true_talent - 1) / 99.0
    boost_min = int(480 + talent_factor * 120)   # 480-600
    boost_max = int(560 + talent_factor * 160)   # 560-720

    for attr in boost_attrs:
        if attr in player:
            current    = player[attr]
            boosted    = random.randint(boost_min, boost_max)
            # Only boost if it's actually an improvement -- don't drag down
            # a player who already exceeds this range on that attribute
            if boosted > current:
                player[attr] = boosted

    return player


# -----------------------------------------
# TEAM GENERATOR
# Builds a full roster for a new program.
#
# Prestige bonus: scales attributes up from the baseline.
# A Kentucky (prestige 92) player starts significantly better
# than an Eastern Illinois (prestige 31) player on primary attributes.
#
# OUTLIER SYSTEM:
# Every program gets one roll for a superstar outlier on one player.
# Probability scales with prestige. If the roll hits, one player
# on the roster gets one primary attribute spiked to 900-950.
# Elite programs: ~15% chance. Low programs: ~1-2% chance.
# -----------------------------------------

# Prestige bonus scale:
# prestige 10 (floor) -> bonus = 0
# prestige 50 (mid)   -> bonus ~+80 on primary attrs
# prestige 92 (elite) -> bonus ~+164, capped at 180
#
# Formula: (prestige - 10) * 2.0 for primary, with hard cap.
# Baseline generators already center around 400-480 for primary
# attributes. Adding 80-180 lands elite programs at 580-660 average
# on primary attrs -- the right range for high-major starters.
# Eastern Illinois (31) gets +42, landing at ~520 average -- correct.

PRESTIGE_BONUS_PRIMARY   = 2.0   # points per prestige point above 10
PRESTIGE_BONUS_SECONDARY = 1.2
PRESTIGE_BONUS_TERTIARY  = 0.5
PRESTIGE_BONUS_CAP       = 180   # hard ceiling on any prestige bonus

# Outlier probability by prestige tier
OUTLIER_PROBABILITIES = {
    "elite":   0.15,   # 80+ prestige
    "good":    0.08,   # 60-79
    "average": 0.04,   # 40-59
    "low":     0.02,   # 20-39
    "bottom":  0.01,   # under 20
}


def _prestige_tier(prestige):
    if prestige >= 80: return "elite"
    if prestige >= 60: return "good"
    if prestige >= 40: return "average"
    if prestige >= 20: return "low"
    return "bottom"


def generate_team(name, prestige=50, conference=""):
    """
    Builds a full roster for a program.
    prestige 1-100 drives attribute quality and outlier probability.
    """
    roster = []
    positions_needed = ["PG", "PG", "SG", "SG", "SF", "SF", "SF", "PF", "PF", "C", "C", "PG", "SG"]
    years = ["Freshman", "Sophomore", "Junior", "Senior"]

    # Prestige bonus -- how much better than baseline each attribute is
    prestige_above_floor = max(0, prestige - 10)
    primary_bonus   = min(PRESTIGE_BONUS_CAP, int(prestige_above_floor * PRESTIGE_BONUS_PRIMARY))
    secondary_bonus = min(int(PRESTIGE_BONUS_CAP * 0.6), int(prestige_above_floor * PRESTIGE_BONUS_SECONDARY))
    tertiary_bonus  = min(int(PRESTIGE_BONUS_CAP * 0.25), int(prestige_above_floor * PRESTIGE_BONUS_TERTIARY))

    for i, pos in enumerate(positions_needed):
        year   = years[i % 4]
        player = create_player("", pos, year, conference=conference)

        # Apply prestige bonus to skill attributes by position role
        from recruiting import POSITION_ARCHETYPES, ALL_ATTRIBUTES
        arch = POSITION_ARCHETYPES.get(pos, {})

        for attr in ALL_ATTRIBUTES:
            if attr not in player:
                continue
            if attr in arch.get("primary", []):
                bonus = primary_bonus
            elif attr in arch.get("secondary", []):
                bonus = secondary_bonus
            elif attr in arch.get("tertiary", []):
                bonus = tertiary_bonus
            else:
                bonus = 0  # floor attributes get no prestige bonus

            if bonus > 0:
                # Add noise to prestige bonus so players aren't identical
                noisy_bonus = int(random.gauss(bonus, bonus * 0.15))
                player[attr] = max(1, min(950, player[attr] + noisy_bonus))

        roster.append(player)

    # --- FREAK PROFILE ROLL ---
    # Each player already on the roster gets an independent roll.
    # apply_freak_profile() handles the probability internally.
    # true_talent approximated from prestige for roster players.
    approx_talent = max(10, min(90, int(prestige * 0.9)))
    for player in roster:
        apply_freak_profile(player, true_talent=approx_talent)

    # --- OUTLIER ROLL ---
    # One chance per roster to produce an above-tier player
    tier              = _prestige_tier(prestige)
    outlier_prob      = OUTLIER_PROBABILITIES[tier]

    if random.random() < outlier_prob:
        # Pick a random player from the roster
        outlier_player = random.choice(roster)
        pos            = outlier_player["position"]
        arch           = POSITION_ARCHETYPES.get(pos, {})
        primary_attrs  = arch.get("primary", [])

        if primary_attrs:
            # Spike one primary attribute to superstar range
            spike_attr = random.choice(primary_attrs)
            if spike_attr in outlier_player:
                spike_value = random.randint(900, 950)
                outlier_player[spike_attr] = spike_value

    return {"name": name, "prestige": prestige, "roster": roster}


# -----------------------------------------
# TEAM RATINGS
# Converts roster to composite ratings used by game_engine.py.
# Returns values on 1-1000 scale.
# game_engine.py normalizes against 1000 (not 20).
# -----------------------------------------

def get_team_ratings(team):
    roster = team["roster"] if "roster" in team else []
    if not roster:
        return {
            "name":       team.get("name", "Unknown"),
            "shooting":   500,
            "defense":    500,
            "rebounding": 500,
            "foul_draw":  500,
        }

    avg_shooting   = sum(
        (p["catch_and_shoot"] + p["off_dribble"] + p["finishing"]) / 3
        for p in roster
    ) / len(roster)

    avg_defense    = sum(
        (p["on_ball_defense"] + p["help_defense"]) / 2
        for p in roster
    ) / len(roster)

    avg_rebounding = sum(p["rebounding"] for p in roster) / len(roster)
    avg_foul_draw  = sum(p["finishing"]  for p in roster) / len(roster)

    return {
        "name":       team.get("name", "Unknown"),
        "shooting":   round(avg_shooting,   1),
        "defense":    round(avg_defense,    1),
        "rebounding": round(avg_rebounding, 1),
        "foul_draw":  round(avg_foul_draw,  1),
    }


# -----------------------------------------
# DISPLAY HELPER
# Uses display.py -- never prints raw 1-1000 values
# -----------------------------------------

def print_roster(team, mode="letter"):
    from display import display_attr_raw
    print("")
    print("=== " + team["name"] + " Roster (Prestige: " + str(team["prestige"]) + ") ===")
    print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
        "Name", "Pos", "Year", "Shoot", "Defense", "Reb", "Play"))
    print("-" * 80)
    for p in team["roster"]:
        avg_shoot = (p["catch_and_shoot"] + p["finishing"] + p["three_point"]) / 3
        avg_def   = (p["on_ball_defense"] + p["help_defense"]) / 2
        avg_play  = (p["passing"] + p["ball_handling"]) / 2
        print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
            p["name"], p["position"], p["year"],
            display_attr_raw(avg_shoot, mode),
            display_attr_raw(avg_def,   mode),
            display_attr_raw(p["rebounding"], mode),
            display_attr_raw(avg_play,  mode),
        ))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from coach import generate_coach
    from display import display_attr
    from recruiting import POSITION_ARCHETYPES, ALL_ATTRIBUTES

    print("=" * 65)
    print("  PLAYER SYSTEM v0.4 -- 1-1000 SCALE TEST")
    print("=" * 65)

    # --- OVERALL QUALITY BY PRESTIGE TIER ---
    # Run 200 rosters per tier and measure average primary attribute quality.
    # This is the meaningful test -- not one player's one attribute.
    print("")
    print("=== Overall roster quality by prestige tier (200 rosters each) ===")
    print("  Showing avg of all primary attributes across all positions.")
    print("  Target: elite ~620-700, good ~570-640, average ~510-580,")
    print("          low ~460-530, bottom ~410-480")
    print("")
    print("  {:<14} {:<10} {:<10} {:<10} {:<8}".format(
        "Tier", "Avg Primary", "Min", "Max", "Grade"))
    print("  " + "-" * 52)

    tier_configs = [
        ("elite(92)",   92),
        ("good(70)",    70),
        ("average(50)", 50),
        ("low(30)",     30),
        ("bottom(15)",  15),
    ]

    for tier_name, prestige in tier_configs:
        all_primary_vals = []
        for _ in range(200):
            team   = generate_team("Test", prestige=prestige)
            roster = team["roster"]
            for p in roster:
                pos  = p["position"]
                arch = POSITION_ARCHETYPES.get(pos, {})
                primary_attrs = arch.get("primary", [])
                for attr in primary_attrs:
                    if attr in p:
                        all_primary_vals.append(p[attr])

        avg = sum(all_primary_vals) / max(1, len(all_primary_vals))
        mn  = min(all_primary_vals)
        mx  = max(all_primary_vals)
        print("  {:<14} {:<10} {:<10} {:<10} {:<8}".format(
            tier_name,
            str(round(avg)),
            str(mn),
            str(mx),
            display_attr(avg, "letter"),
        ))

    # --- OUTLIER CHECK ---
    # Checks if ANY attribute on ANY player hit 900+ (the outlier spike range).
    # This is what the outlier system actually produces.
    print("")
    print("=== Outlier roll frequency (500 rosters per tier) ===")
    print("  Target: elite ~15%, good ~8%, average ~4%, low ~2%, bottom ~1%")
    print("")
    for tier_name, prestige in tier_configs:
        outlier_count = 0
        for _ in range(500):
            team = generate_team("Test", prestige=prestige)
            found = False
            for p in team["roster"]:
                if found:
                    break
                for attr in ALL_ATTRIBUTES:
                    if p.get(attr, 0) >= 900:
                        found = True
                        break
            if found:
                outlier_count += 1
        print("  " + tier_name.ljust(14) +
              "  outliers: " + str(outlier_count) + "/500  (" +
              str(round(outlier_count / 500 * 100, 1)) + "%)" +
              "  target: " + {
                  "elite(92)": "~15%", "good(70)": "~8%",
                  "average(50)": "~4%", "low(30)": "~2%", "bottom(15)": "~1%"
              }.get(tier_name, "?"))

    # --- DEVELOPMENT TEST ---
    print("")
    print("=== Development test -- gains on 1-1000 scale ===")

    def make_test_player(name, arc, work_ethic_val, potential_high_val):
        p = create_player(name, "SF", "Freshman")
        p["arc_type"]       = arc
        p["work_ethic"]     = work_ethic_val
        p["coachability"]   = 12
        p["potential_high"] = potential_high_val
        p["finishing"]        = 520
        p["catch_and_shoot"]  = 490
        p["on_ball_defense"]  = 510
        p["speed"]            = 540
        p["rebounding"]       = 480
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
        ("Bust / Narrow Ceiling",        "bust",           7, 40),
    ]

    for case_name, arc, ethic, ceiling in test_cases:
        print("")
        print("  " + case_name +
              "  (ceiling=" + str(_potential_to_attr_ceiling(ceiling)) + " on 1000 scale)")
        p_great = make_test_player("A", arc, ethic, ceiling)
        p_poor  = make_test_player("B", arc, ethic, ceiling)

        for year in ["Freshman", "Sophomore", "Junior"]:
            p_great["year"] = year
            p_poor["year"]  = year
            key = ["finishing", "catch_and_shoot", "on_ball_defense", "speed", "rebounding"]

            before_g = sum(p_great.get(a, 500) for a in key)
            before_p = sum(p_poor.get(a,  500) for a in key)

            p_great, rg = develop_player(p_great, great_coach, 2025)
            p_poor,  rp = develop_player(p_poor,  poor_coach,  2025)

            gain_g = sum(p_great.get(a, 500) for a in key) - before_g
            gain_p = sum(p_poor.get(a,  500) for a in key) - before_p

            print("  {:<12}  great coach: +{:<6}  poor coach: +{:<6}{}{}".format(
                year, gain_g, gain_p,
                "  BREAKTHROUGH!" if rg["breakthrough"] else "",
                "  BREAKTHROUGH!" if rp["breakthrough"] else "",
            ))

    # --- BREAKTHROUGH FREQUENCY ---
    print("")
    print("=== Breakthrough frequency -- 326 programs x 10 players ===")
    print("  Expected: 2-4% of players = ~65-120 breakthroughs")
    total_bt = 0
    total_p  = 0
    coach    = generate_coach("Average", prestige=55, experience=10)
    for _ in range(326):
        for year in ["Freshman", "Sophomore", "Junior"]:
            p = make_test_player("Test", "steady", 11, 65)
            p["year"] = year
            _, report = develop_player(p, coach, 2025)
            if report["breakthrough"]:
                total_bt += 1
            total_p += 1
    print("  Total players: " + str(total_p))
    print("  Breakthroughs: " + str(total_bt))
    print("  Rate:          " + str(round(total_bt / total_p * 100, 2)) + "%")

    # --- FREAK PROFILE VERIFICATION ---
    # Generate 500 rosters and find players whose cross-positional
    # attributes are meaningfully above their position baseline.
    # Shows examples of what the freak system actually produces.
    print("")
    print("=== Freak profile verification -- 100 rosters, notable examples ===")
    print("  Looking for players with cross-positional attributes above 580...")
    print("")

    freak_examples = []
    for _ in range(100):
        team = generate_team("Test", prestige=55)
        for p in team["roster"]:
            pos  = p["position"]
            arch = POSITION_ARCHETYPES.get(pos, {})
            floor_attrs = arch.get("floor", [])
            # Find any floor attribute that's unusually high
            for attr in floor_attrs:
                val = p.get(attr, 0)
                if val >= 560:
                    freak_examples.append({
                        "pos":  pos,
                        "attr": attr,
                        "val":  val,
                        "name": p.get("name", "?"),
                    })

    # Show top 12 most interesting examples
    freak_examples.sort(key=lambda x: x["val"], reverse=True)
    shown = 0
    for ex in freak_examples[:12]:
        print("  {:<5} {:<22} floor attr: {:<20} value: {} ({})".format(
            ex["pos"],
            ex["name"][:21],
            ex["attr"],
            ex["val"],
            display_attr(ex["val"], "letter"),
        ))
        shown += 1

    if not freak_examples:
        print("  No notable cross-positional attributes found -- try more rosters.")
    else:
        print("")
        print("  Total cross-positional outliers found: " + str(len(freak_examples)) +
              " across 100 rosters (~" +
              str(round(len(freak_examples) / (100 * 13) * 100, 1)) + "% of players)")
