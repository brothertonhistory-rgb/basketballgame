import random
from names import generate_player_name
from player import rand_attr

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting System v0.1
# System 3 of the Design Bible
# Recruit generation -- builds the annual prospect pool
#
# Key concepts:
#   true_talent   -- hidden 1-100 value, the ground truth
#   star ratings  -- three services each read true_talent with noise
#   potential     -- a range (floor/ceiling), not a single number
#   priorities    -- eight hidden weights driving the decision model (Phase 3b)
#   personality   -- four hidden traits driving behavior and cohesion
# -----------------------------------------


POSITIONS = ["PG", "SG", "SF", "PF", "C"]

# How many D1-relevant recruits to generate per class
# Power law distribution -- very few elite, many average
TALENT_TIERS = [
    # (tier_name, true_talent_range, count, star_likely)
    ("elite",      (88, 100), 25,   5),
    ("high",       (73,  87), 80,   4),
    ("mid",        (52,  72), 200,  3),
    ("low",        (33,  51), 250,  2),
    ("fringe",     (10,  32), 200,  1),
]

# Position distribution targets per class -- mirrors real D1 recruiting
POSITION_WEIGHTS = {
    "PG": 0.18,
    "SG": 0.22,
    "SF": 0.22,
    "PF": 0.20,
    "C":  0.18,
}

# Geographic hotbeds -- weighted by basketball culture + population
# Mirrors real recruiting patterns
STATE_WEIGHTS = {
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

# Map states to nearby conferences -- used for proximity recruiting later
STATE_TO_CONFERENCE_REGION = {
    "AL": "SEC",  "AR": "SEC",  "FL": "SEC",  "GA": "SEC",
    "KY": "SEC",  "LA": "SEC",  "MS": "SEC",  "MO": "SEC",
    "SC": "SEC",  "TN": "SEC",
    "TX": "Big 12", "OK": "Big 12", "KS": "Big 12", "IA": "Big 12",
    "WV": "Big 12",
    "CA": "Pac-10", "WA": "Pac-10", "OR": "Pac-10", "AZ": "Pac-10",
    "UT": "Pac-10", "CO": "Pac-10",
    "NC": "ACC",  "VA": "ACC",  "MD": "ACC",  "DC": "ACC",
    "IL": "Big Ten", "IN": "Big Ten", "MI": "Big Ten", "OH": "Big Ten",
    "MN": "Big Ten", "WI": "Big Ten", "NE": "Big Ten", "PA": "Big Ten",
    "NJ": "Big East", "CT": "Big East", "NY": "Big East",
    "MA": "Big East", "RI": "Big East",
}

# Physical size ranges by position -- height in inches
POSITION_SIZE = {
    "PG": {"height": (70, 77),  "weight": (165, 195)},   # 5'10" - 6'5"
    "SG": {"height": (74, 79),  "weight": (175, 210)},   # 6'2"  - 6'7"
    "SF": {"height": (77, 82),  "weight": (200, 230)},   # 6'5"  - 6'10"
    "PF": {"height": (79, 84),  "weight": (215, 250)},   # 6'7"  - 7'0"
    "C":  {"height": (81, 87),  "weight": (230, 270)},   # 6'9"  - 7'3"
}

# Attribute archetypes by position
# Each entry: (attribute_name, base_for_elite, base_for_fringe)
# Linear interpolation between them based on true_talent
POSITION_ARCHETYPES = {
    "PG": {
        "primary":   ["ball_handling", "court_vision", "passing", "decision_making", "speed"],
        "secondary": ["catch_and_shoot", "three_point", "lateral_quickness", "on_ball_defense"],
        "tertiary":  ["finishing", "mid_range", "help_defense", "rebounding", "vertical"],
        "floor":     ["post_scoring", "shot_blocking", "strength"],
    },
    "SG": {
        "primary":   ["catch_and_shoot", "three_point", "off_dribble", "speed", "lateral_quickness"],
        "secondary": ["mid_range", "ball_handling", "on_ball_defense", "free_throw"],
        "tertiary":  ["finishing", "passing", "court_vision", "vertical"],
        "floor":     ["post_scoring", "shot_blocking", "strength", "rebounding"],
    },
    "SF": {
        "primary":   ["speed", "vertical", "finishing", "catch_and_shoot", "on_ball_defense"],
        "secondary": ["mid_range", "rebounding", "help_defense", "strength", "lateral_quickness"],
        "tertiary":  ["three_point", "off_dribble", "passing", "ball_handling"],
        "floor":     ["post_scoring", "shot_blocking", "court_vision"],
    },
    "PF": {
        "primary":   ["rebounding", "strength", "post_scoring", "finishing", "help_defense"],
        "secondary": ["shot_blocking", "vertical", "on_ball_defense", "mid_range"],
        "tertiary":  ["free_throw", "catch_and_shoot", "passing"],
        "floor":     ["ball_handling", "three_point", "speed", "court_vision"],
    },
    "C": {
        "primary":   ["rebounding", "shot_blocking", "strength", "post_scoring", "finishing"],
        "secondary": ["vertical", "help_defense", "on_ball_defense", "mid_range"],
        "tertiary":  ["free_throw", "foul_tendency"],
        "floor":     ["speed", "ball_handling", "three_point", "passing", "court_vision"],
    },
}

# All attributes -- must match player.py exactly
ALL_ATTRIBUTES = [
    "catch_and_shoot", "off_dribble", "mid_range", "three_point", "free_throw",
    "finishing", "post_scoring",
    "passing", "ball_handling", "court_vision", "decision_making",
    "on_ball_defense", "help_defense", "rebounding", "shot_blocking",
    "steal_tendency", "foul_tendency",
    "speed", "lateral_quickness", "strength", "vertical",
]

# Recruiting service names -- three services that disagree
SERVICE_NAMES = ["247Sports", "Rivals", "ESPN"]

# How much noise each service adds to true_talent when assigning stars
# 247 is most accurate, ESPN most volatile
SERVICE_NOISE = {
    "247Sports": (-8,   8),
    "Rivals":    (-10, 10),
    "ESPN":      (-14, 14),
}

# Star thresholds -- applied to the service's noisy read of true_talent
def talent_to_stars(talent_score):
    """Converts a talent score (1-100) to a star rating (1-5)."""
    if talent_score >= 90: return 5
    if talent_score >= 75: return 4
    if talent_score >= 55: return 3
    if talent_score >= 35: return 2
    return 1


# -----------------------------------------
# CORE RECRUIT GENERATOR
# -----------------------------------------

def generate_recruit(position, true_talent, season, conference_region=None):
    """
    Generates a single recruit dict.

    position        -- PG/SG/SF/PF/C
    true_talent     -- 1-100 hidden ground truth
    season          -- recruiting class year
    conference_region -- optional home conference region (for proximity later)

    Returns a recruit dict that mirrors the player dict structure from player.py
    but adds recruiting-specific fields.
    """

    # --- NAME AND HERITAGE ---
    # Use the existing name generator -- pass conference region as a proxy for geography
    # This gives us realistic demographic distribution by region
    region_conf = conference_region or random.choice(list(STATE_TO_CONFERENCE_REGION.values()))
    name, heritage = generate_player_name(conference=region_conf)
    name_parts = name.split(" ", 1)
    first_name = name_parts[0]
    last_name  = name_parts[1] if len(name_parts) > 1 else "Smith"

    # --- GEOGRAPHY ---
    home_state = _pick_home_state()

    # --- PHYSICAL SIZE ---
    size_range = POSITION_SIZE[position]
    height = random.randint(*size_range["height"])
    weight = random.randint(*size_range["weight"])

    # --- STAR RATINGS -- three services, each with noise ---
    service_ratings = {}
    service_ranks   = {}
    for service, (noise_low, noise_high) in SERVICE_NOISE.items():
        noise           = random.randint(noise_low, noise_high)
        service_read    = max(1, min(100, true_talent + noise))
        service_ratings[service] = talent_to_stars(service_read)
        # National rank is rough -- elite prospects ranked tighter
        rank_noise = random.randint(0, max(1, 500 - true_talent * 4))
        service_ranks[service] = max(1, int((100 - true_talent) * 5 + rank_noise))

    # --- ATTRIBUTES ---
    attributes = _generate_attributes(position, true_talent)

    # --- POTENTIAL ---
    potential_floor, potential_ceiling = _generate_potential(true_talent)

    # --- PERSONALITY TRAITS -- hidden ---
    personality = _generate_personality(true_talent)

    # --- PRIORITY WEIGHTS -- hidden, drive decision model ---
    priorities = _generate_priorities()

    # --- BUILD RECRUIT DICT ---
    recruit = {
        # Identity
        "name":           name,
        "first_name":     first_name,
        "last_name":      last_name,
        "position":       position,
        "heritage":       heritage,
        "home_state":     home_state,
        "height_inches":  height,
        "weight_lbs":     weight,
        "season":         season,

        # Hidden ground truth
        "true_talent":       true_talent,
        "potential_floor":   potential_floor,
        "potential_ceiling": potential_ceiling,

        # Service ratings -- what coaches see
        "stars_247":    service_ratings["247Sports"],
        "stars_rivals": service_ratings["Rivals"],
        "stars_espn":   service_ratings["ESPN"],
        "rank_247":     service_ranks["247Sports"],
        "rank_rivals":  service_ranks["Rivals"],
        "rank_espn":    service_ranks["ESPN"],

        # Consensus star -- most common rating across services, or middle value
        "stars_consensus": _consensus_stars(service_ratings),

        # Commitment state
        "status":              "available",   # available, committed, signed, enrolled
        "committed_to":        None,
        "offer_list":          [],            # list of program names that have offered
        "interest_levels":     {},            # program_name -> 1-10 interest score
        "visit_history":       [],            # list of visit dicts

        # Attributes -- same keys as player.py so generate_team can absorb a recruit
        **attributes,

        # Hidden personality traits
        "ego":              personality["ego"],
        "loyalty":          personality["loyalty"],
        "maturity":         personality["maturity"],
        "social_influence": personality["social_influence"],

        # Hidden decision priorities
        "priority_playing_time":       priorities["playing_time"],
        "priority_prestige":           priorities["prestige"],
        "priority_location":           priorities["location"],
        "priority_coach_relationship": priorities["coach_relationship"],
        "priority_playing_style":      priorities["playing_style"],
        "priority_academics":          priorities["academics"],
        "priority_nil":                priorities["nil"],
        "priority_family_proximity":   priorities["family_proximity"],
    }

    return recruit


def _pick_home_state():
    """Weighted random state selection based on basketball hotbed data."""
    states  = list(STATE_WEIGHTS.keys())
    weights = list(STATE_WEIGHTS.values())
    return random.choices(states, weights=weights, k=1)[0]


def _consensus_stars(service_ratings):
    """
    Returns the median star rating across the three services.
    When all three disagree, middle value wins.
    """
    ratings = sorted(service_ratings.values())
    return ratings[1]   # median of three


def _generate_attributes(position, true_talent):
    """
    Generates a full attribute set for a recruit.

    Uses the position archetype to determine which attributes get
    the talent bonus. Primary attributes scale strongly with true_talent.
    Secondary attributes scale moderately. Tertiary get a small lift.
    Floor attributes are low regardless of talent.

    Mirrors the rand_attr() pattern from player.py exactly.
    """

    # Talent factor -- 0.0 (fringe) to 1.0 (elite)
    talent_factor = (true_talent - 1) / 99.0

    archetype = POSITION_ARCHETYPES[position]
    attributes = {}

    for attr in ALL_ATTRIBUTES:
        if attr in archetype["primary"]:
            # Primary: 10-18 range, scales strongly with talent
            base = 10 + int(talent_factor * 8)
            val  = rand_attr(base, spread=2)

        elif attr in archetype["secondary"]:
            # Secondary: 8-16 range, scales moderately
            base = 8 + int(talent_factor * 8)
            val  = rand_attr(base, spread=3)

        elif attr in archetype["tertiary"]:
            # Tertiary: 7-14 range, small lift from talent
            base = 7 + int(talent_factor * 7)
            val  = rand_attr(base, spread=3)

        else:
            # Floor: stays low regardless of talent -- position mis-fit
            base = 4 + int(talent_factor * 3)
            val  = rand_attr(base, spread=2)

        attributes[attr] = max(1, min(20, val))

    # Mental attributes -- hidden, same as player.py generate_mental()
    # Slight positive correlation with true_talent (better players often have
    # better IQ) but high variance -- diamonds and busts at all levels
    mental_base = 8 + int(talent_factor * 3)
    attributes["basketball_iq"] = rand_attr(mental_base, spread=3)
    attributes["clutch"]        = rand_attr(10, spread=3)   # pure variance
    attributes["composure"]     = rand_attr(10, spread=3)
    attributes["coachability"]  = rand_attr(10, spread=3)
    attributes["work_ethic"]    = rand_attr(10, spread=3)
    attributes["leadership"]    = rand_attr(10, spread=3)

    return attributes


def _generate_potential(true_talent):
    """
    Generates a potential floor and ceiling.
    High talent recruits have higher floors. Ceiling variance is wider for all.
    A 3-star with a high ceiling is your late bloomer.
    A 5-star with a low ceiling is your bust.
    """
    talent_factor = (true_talent - 1) / 99.0

    # Floor scales with talent -- elite recruits don't collapse completely
    floor_base = 30 + int(talent_factor * 45)
    floor = max(10, min(85, floor_base + random.randint(-10, 10)))

    # Ceiling: talent gives a base, but variance is wide
    ceiling_base = floor + 15 + int(talent_factor * 25)
    ceiling = max(floor + 5, min(100, ceiling_base + random.randint(-15, 20)))

    return floor, ceiling


def _generate_personality(true_talent):
    """
    Generates the four hidden personality traits.
    Ego has mild positive correlation with star rating -- top recruits
    know they're top recruits. All others are largely random.
    """
    talent_factor = (true_talent - 1) / 99.0

    # Ego: higher for highly rated players -- mild correlation
    ego_base = 8 + int(talent_factor * 5)
    ego = rand_attr(ego_base, spread=3)

    # Loyalty, maturity, social influence -- independent of talent
    loyalty          = rand_attr(10, spread=3)
    maturity         = rand_attr(10, spread=3)
    social_influence = rand_attr(10, spread=3)

    return {
        "ego":              max(1, min(20, ego)),
        "loyalty":          max(1, min(20, loyalty)),
        "maturity":         max(1, min(20, maturity)),
        "social_influence": max(1, min(20, social_influence)),
    }


def _generate_priorities(player_weights=None):
    """
    Generates the eight hidden priority weights (1-10 each).
    These drive the decision model -- which factors does this recruit
    actually care about? Sum doesn't need to equal anything.
    Pure random with mild constraints (no weight can be zero).
    Optionally accepts a dict of overrides for testing.
    """
    base = {
        "playing_time":       random.randint(3, 10),
        "prestige":           random.randint(2, 10),
        "location":           random.randint(1, 10),
        "coach_relationship": random.randint(2, 10),
        "playing_style":      random.randint(1, 8),
        "academics":          random.randint(1, 7),
        "nil":                random.randint(1, 8),
        "family_proximity":   random.randint(1, 9),
    }
    if player_weights:
        base.update(player_weights)
    return base


# -----------------------------------------
# RECRUITING CLASS GENERATOR
# -----------------------------------------

def generate_recruiting_class(season):
    """
    Generates the full D1 recruiting prospect pool for a given season.

    Returns a list of recruit dicts sorted by consensus star rating (desc).
    This is the pool all D1 programs draw from.
    Total size: ~755 prospects (mirrors real D1 class volume)
    """

    recruits = []

    for tier_name, talent_range, count, _ in TALENT_TIERS:
        # Distribute positions across this tier
        position_counts = _distribute_positions(count)

        for position, pos_count in position_counts.items():
            for _ in range(pos_count):
                # True talent: random within tier range, gaussian-ish via clamp
                true_talent = random.randint(*talent_range)

                # Home state drives conference region for name generation
                home_state = _pick_home_state()
                conf_region = STATE_TO_CONFERENCE_REGION.get(home_state)

                recruit = generate_recruit(
                    position=position,
                    true_talent=true_talent,
                    season=season,
                    conference_region=conf_region,
                )

                # Set home state consistently (generate_recruit also picks one,
                # but we want it tied to the conference region we used)
                recruit["home_state"] = home_state

                recruits.append(recruit)

    # Sort by consensus stars desc, then by true_talent desc within same star level
    recruits.sort(key=lambda r: (r["stars_consensus"], r["true_talent"]), reverse=True)

    # Assign composite national rank (1 = best)
    for i, r in enumerate(recruits):
        r["composite_rank"] = i + 1

    return recruits


def _distribute_positions(total_count):
    """
    Distributes a total recruit count across positions using POSITION_WEIGHTS.
    Returns a dict of {position: count}.
    """
    counts = {}
    remaining = total_count

    positions = list(POSITION_WEIGHTS.keys())
    for i, pos in enumerate(positions):
        if i == len(positions) - 1:
            counts[pos] = remaining   # last position gets the remainder
        else:
            counts[pos] = round(POSITION_WEIGHTS[pos] * total_count)
            remaining -= counts[pos]

    return counts


# -----------------------------------------
# DISPLAY HELPERS
# -----------------------------------------

def format_height(inches):
    """Converts height in inches to readable format like 6'4\"."""
    feet = inches // 12
    inch = inches % 12
    return str(feet) + "'" + str(inch) + '"'


def stars_display(n):
    """Returns a star string like ★★★☆☆ for display."""
    return "★" * n + "☆" * (5 - n)


def print_recruit(recruit, show_hidden=False):
    """Prints a single recruit's scouting card."""
    print("")
    print("  " + recruit["name"] + "  |  " + recruit["position"] +
          "  |  " + format_height(recruit["height_inches"]) +
          "  " + str(recruit["weight_lbs"]) + "lbs" +
          "  |  " + recruit["home_state"])
    print("  247: " + stars_display(recruit["stars_247"]) +
          "  Rivals: " + stars_display(recruit["stars_rivals"]) +
          "  ESPN: " + stars_display(recruit["stars_espn"]) +
          "  (Consensus: " + stars_display(recruit["stars_consensus"]) + ")")
    print("  Composite rank: #" + str(recruit.get("composite_rank", "?")))
    print("  Status: " + recruit["status"])

    if show_hidden:
        print("  [HIDDEN] True talent: " + str(recruit["true_talent"]) +
              "  Potential: " + str(recruit["potential_floor"]) +
              "-" + str(recruit["potential_ceiling"]))
        print("  [HIDDEN] Ego: " + str(recruit["ego"]) +
              "  Loyalty: " + str(recruit["loyalty"]) +
              "  Maturity: " + str(recruit["maturity"]))
        top_priority = max(
            ["playing_time", "prestige", "location", "coach_relationship",
             "playing_style", "academics", "nil", "family_proximity"],
            key=lambda k: recruit["priority_" + k]
        )
        print("  [HIDDEN] Top priority: " + top_priority.replace("_", " "))


def print_class_summary(recruits, season, show_hidden=False):
    """Prints a summary of the full recruiting class."""
    print("")
    print("=" * 65)
    print("  " + str(season) + " RECRUITING CLASS  --  " +
          str(len(recruits)) + " prospects")
    print("=" * 65)

    # Star distribution
    star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in recruits:
        star_counts[r["stars_consensus"]] += 1

    print("  Star distribution:")
    for stars in [5, 4, 3, 2, 1]:
        bar = "█" * min(star_counts[stars], 40)
        print("  " + stars_display(stars) + "  " +
              str(star_counts[stars]).rjust(3) + "  " + bar)

    # Position distribution
    pos_counts = {p: 0 for p in POSITIONS}
    for r in recruits:
        pos_counts[r["position"]] += 1
    print("")
    print("  Position distribution: " +
          "  ".join(pos + ": " + str(pos_counts[pos]) for pos in POSITIONS))

    # State distribution -- top 10
    state_counts = {}
    for r in recruits:
        state_counts[r["home_state"]] = state_counts.get(r["home_state"], 0) + 1
    top_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print("  Top states: " +
          "  ".join(s + ": " + str(c) for s, c in top_states))

    # Top 10 recruits
    print("")
    print("  TOP 10 PROSPECTS")
    print("  " + "-" * 60)
    print("  {:<4} {:<22} {:<5} {:<8} {:<6} {}".format(
        "Rank", "Name", "Pos", "Ht", "State", "Stars"))
    print("  " + "-" * 60)
    for r in recruits[:10]:
        print("  {:<4} {:<22} {:<5} {:<8} {:<6} {}".format(
            r.get("composite_rank", "?"),
            r["name"],
            r["position"],
            format_height(r["height_inches"]),
            r["home_state"],
            stars_display(r["stars_consensus"]),
        ))
        if show_hidden:
            print("       [true_talent: " + str(r["true_talent"]) +
                  "  potential: " + str(r["potential_floor"]) +
                  "-" + str(r["potential_ceiling"]) + "]")

    print("")
    print("  FIVE-STAR CLASS")
    print("  " + "-" * 60)
    five_stars = [r for r in recruits if r["stars_consensus"] == 5]
    if five_stars:
        for r in five_stars:
            print_recruit(r, show_hidden=show_hidden)
    else:
        print("  (no consensus five-stars this cycle)")


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("Generating 2025 recruiting class...")
    recruits_2025 = generate_recruiting_class(season=2025)

    # Full class summary with hidden data visible for testing
    print_class_summary(recruits_2025, season=2025, show_hidden=True)

    # Verify: services disagree on mid-tier prospects
    print("")
    print("=" * 65)
    print("  SERVICE DISAGREEMENT TEST -- 10 mid-tier recruits")
    print("=" * 65)
    mid_tier = [r for r in recruits_2025 if r["stars_consensus"] == 3][:10]
    for r in mid_tier:
        print("  " + r["name"].ljust(22) +
              " 247:" + str(r["stars_247"]) +
              " Rivals:" + str(r["stars_rivals"]) +
              " ESPN:" + str(r["stars_espn"]) +
              " [true: " + str(r["true_talent"]) + "]")

    # Verify: late bloomer exists -- 3-star with elite ceiling
    print("")
    print("=" * 65)
    print("  HIDDEN GEM TEST -- 3-stars with 80+ potential ceiling")
    print("=" * 65)
    hidden_gems = [r for r in recruits_2025
                   if r["stars_consensus"] == 3 and r["potential_ceiling"] >= 80]
    print("  Found " + str(len(hidden_gems)) + " hidden gems in this class")
    for r in hidden_gems[:5]:
        print("  " + r["name"].ljust(22) + r["position"] +
              "  true_talent: " + str(r["true_talent"]) +
              "  potential: " + str(r["potential_floor"]) +
              "-" + str(r["potential_ceiling"]))

    # Verify: service bust -- 5-star by one service, 3-star by another
    print("")
    print("=" * 65)
    print("  SERVICE BUST TEST -- 5-star somewhere, 3-star somewhere else")
    print("=" * 65)
    busts = [r for r in recruits_2025
             if max(r["stars_247"], r["stars_rivals"], r["stars_espn"]) -
                min(r["stars_247"], r["stars_rivals"], r["stars_espn"]) >= 2]
    print("  Found " + str(len(busts)) + " contested ratings in this class")
    for r in busts[:5]:
        print("  " + r["name"].ljust(22) +
              " 247:" + str(r["stars_247"]) +
              " Rivals:" + str(r["stars_rivals"]) +
              " ESPN:" + str(r["stars_espn"]) +
              " [true: " + str(r["true_talent"]) + "]")
