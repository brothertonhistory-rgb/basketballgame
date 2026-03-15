import random
from names import generate_player_name
from player import rand_attr

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting System v0.3
# System 3 of the Design Bible
#
# v0.3 CHANGES:
#   - Recruit pool expanded from 1000 to 1500.
#     Extra 500 come entirely from fringe and low tiers.
#     328 programs × ~3 graduates/year = ~984 players needed.
#     1500 in the pool gives the commitment system enough supply
#     to fill rosters even with a 50% sign rate.
#
# v0.2 CHANGES:
#   - Every recruit gets one SPIKE ATTRIBUTE -- one genuine strength
#     that makes them recruitable regardless of overall talent level.
# -----------------------------------------


POSITIONS = ["PG", "SG", "SF", "PF", "C"]

# Recruit pool -- 1500 total
# Extra 500 added to fringe and low tiers only.
# Elite/high/mid counts unchanged -- the talent pyramid stays realistic.
TALENT_TIERS = [
    # (tier_name, true_talent_range, count, star_likely)
    ("elite",      (88, 100),   25,   5),
    ("high",       (73,  87),   80,   4),
    ("mid",        (52,  72),  200,   3),
    ("low",        (33,  51),  545,   2),   # was 350, +195
    ("fringe",     (10,  32),  650,   1),   # was 345, +305
]

# Position distribution targets per class
POSITION_WEIGHTS = {
    "PG": 0.18,
    "SG": 0.22,
    "SF": 0.22,
    "PF": 0.20,
    "C":  0.18,
}

# Geographic hotbeds
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

POSITION_SIZE = {
    "PG": {"height": (70, 77),  "weight": (165, 195)},
    "SG": {"height": (74, 79),  "weight": (175, 210)},
    "SF": {"height": (77, 82),  "weight": (200, 230)},
    "PF": {"height": (79, 84),  "weight": (215, 250)},
    "C":  {"height": (81, 87),  "weight": (230, 270)},
}

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

ALL_ATTRIBUTES = [
    "catch_and_shoot", "off_dribble", "mid_range", "three_point", "free_throw",
    "finishing", "post_scoring",
    "passing", "ball_handling", "court_vision", "decision_making",
    "on_ball_defense", "help_defense", "rebounding", "shot_blocking",
    "steal_tendency", "foul_tendency",
    "speed", "lateral_quickness", "strength", "vertical",
]

# Spike specializations by position -- one genuine strength per recruit
SPIKE_SPECIALIZATIONS = {
    "PG": [
        ("floor_general",    ["passing", "court_vision", "decision_making"]),
        ("catch_and_shoot",  ["catch_and_shoot", "three_point", "free_throw"]),
        ("on_ball_defender", ["on_ball_defense", "lateral_quickness", "steal_tendency"]),
        ("speedster",        ["speed", "lateral_quickness", "ball_handling"]),
        ("high_iq",          ["basketball_iq", "decision_making", "court_vision"]),
    ],
    "SG": [
        ("spot_up_shooter",  ["catch_and_shoot", "three_point", "free_throw"]),
        ("off_dribble",      ["off_dribble", "ball_handling", "finishing"]),
        ("lockdown",         ["on_ball_defense", "lateral_quickness", "steal_tendency"]),
        ("athlete",          ["speed", "vertical", "lateral_quickness"]),
        ("mid_range",        ["mid_range", "catch_and_shoot", "free_throw"]),
    ],
    "SF": [
        ("three_and_d",      ["catch_and_shoot", "three_point", "on_ball_defense"]),
        ("slasher",          ["finishing", "speed", "vertical"]),
        ("rebounder",        ["rebounding", "strength", "help_defense"]),
        ("switchable",       ["lateral_quickness", "on_ball_defense", "help_defense"]),
        ("tough_wing",       ["strength", "rebounding", "help_defense"]),
    ],
    "PF": [
        ("glass_eater",      ["rebounding", "strength", "vertical"]),
        ("post_scorer",      ["post_scoring", "strength", "finishing"]),
        ("shot_blocker",     ["shot_blocking", "vertical", "help_defense"]),
        ("stretch_four",     ["catch_and_shoot", "three_point", "mid_range"]),
        ("energy_big",       ["rebounding", "help_defense", "strength"]),
    ],
    "C": [
        ("rim_protector",    ["shot_blocking", "vertical", "help_defense"]),
        ("rebounder",        ["rebounding", "strength", "finishing"]),
        ("post_scorer",      ["post_scoring", "strength", "finishing"]),
        ("energy_big",       ["rebounding", "help_defense", "on_ball_defense"]),
        ("physical_presence",["strength", "rebounding", "foul_tendency"]),
    ],
}

SERVICE_NAMES = ["247Sports", "Rivals", "ESPN"]
SERVICE_NOISE = {
    "247Sports": (-8,   8),
    "Rivals":    (-10, 10),
    "ESPN":      (-14, 14),
}

def talent_to_stars(talent_score):
    if talent_score >= 90: return 5
    if talent_score >= 75: return 4
    if talent_score >= 55: return 3
    if talent_score >= 35: return 2
    return 1


# -----------------------------------------
# CORE RECRUIT GENERATOR
# -----------------------------------------

def generate_recruit(position, true_talent, season, conference_region=None):
    region_conf = conference_region or random.choice(list(STATE_TO_CONFERENCE_REGION.values()))
    name, heritage = generate_player_name(conference=region_conf)
    name_parts = name.split(" ", 1)
    first_name = name_parts[0]
    last_name  = name_parts[1] if len(name_parts) > 1 else "Smith"

    home_state = _pick_home_state()

    size_range = POSITION_SIZE[position]
    height = random.randint(*size_range["height"])
    weight = random.randint(*size_range["weight"])

    service_ratings = {}
    service_ranks   = {}
    for service, (noise_low, noise_high) in SERVICE_NOISE.items():
        noise        = random.randint(noise_low, noise_high)
        service_read = max(1, min(100, true_talent + noise))
        service_ratings[service] = talent_to_stars(service_read)
        rank_noise = random.randint(0, max(1, 500 - true_talent * 4))
        service_ranks[service] = max(1, int((100 - true_talent) * 5 + rank_noise))

    attributes, spike_label = _generate_attributes(position, true_talent)
    potential_floor, potential_ceiling = _generate_potential(true_talent)
    personality = _generate_personality(true_talent)
    priorities  = _generate_priorities()

    recruit = {
        "name":           name,
        "first_name":     first_name,
        "last_name":      last_name,
        "position":       position,
        "heritage":       heritage,
        "home_state":     home_state,
        "height_inches":  height,
        "weight_lbs":     weight,
        "season":         season,
        "true_talent":       true_talent,
        "potential_floor":   potential_floor,
        "potential_ceiling": potential_ceiling,
        "spike_label":       spike_label,
        "stars_247":    service_ratings["247Sports"],
        "stars_rivals": service_ratings["Rivals"],
        "stars_espn":   service_ratings["ESPN"],
        "rank_247":     service_ranks["247Sports"],
        "rank_rivals":  service_ranks["Rivals"],
        "rank_espn":    service_ranks["ESPN"],
        "stars_consensus": _consensus_stars(service_ratings),
        "status":          "available",
        "committed_to":    None,
        "offer_list":      [],
        "interest_levels": {},
        "visit_history":   [],
        **attributes,
        "ego":              personality["ego"],
        "loyalty":          personality["loyalty"],
        "maturity":         personality["maturity"],
        "social_influence": personality["social_influence"],
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
    states  = list(STATE_WEIGHTS.keys())
    weights = list(STATE_WEIGHTS.values())
    return random.choices(states, weights=weights, k=1)[0]


def _consensus_stars(service_ratings):
    ratings = sorted(service_ratings.values())
    return ratings[1]


def _generate_attributes(position, true_talent):
    """
    Generates attributes with one spike -- a genuine strength.
    Returns (attributes_dict, spike_label).
    """
    talent_factor = (true_talent - 1) / 99.0
    archetype     = POSITION_ARCHETYPES[position]
    attributes    = {}

    for attr in ALL_ATTRIBUTES:
        if attr in archetype["primary"]:
            base = 10 + int(talent_factor * 8)
            val  = rand_attr(base, spread=2)
        elif attr in archetype["secondary"]:
            base = 8 + int(talent_factor * 8)
            val  = rand_attr(base, spread=3)
        elif attr in archetype["tertiary"]:
            base = 7 + int(talent_factor * 7)
            val  = rand_attr(base, spread=3)
        else:
            base = 4 + int(talent_factor * 3)
            val  = rand_attr(base, spread=2)
        attributes[attr] = max(1, min(20, val))

    mental_base = 8 + int(talent_factor * 3)
    attributes["basketball_iq"] = rand_attr(mental_base, spread=3)
    attributes["clutch"]        = rand_attr(10, spread=3)
    attributes["composure"]     = rand_attr(10, spread=3)
    attributes["coachability"]  = rand_attr(10, spread=3)
    attributes["work_ethic"]    = rand_attr(10, spread=3)
    attributes["leadership"]    = rand_attr(10, spread=3)

    # Spike attribute
    specializations = SPIKE_SPECIALIZATIONS.get(position, [])
    spike_label     = "none"

    if specializations:
        spike_label, spike_attrs = random.choice(specializations)

        if true_talent < 35:
            spike_min, spike_max = 14, 17
        elif true_talent < 55:
            spike_min, spike_max = 13, 16
        else:
            spike_min, spike_max = 14, 18

        for attr in spike_attrs:
            if attr in attributes:
                current = attributes[attr]
                spiked  = random.randint(spike_min, spike_max)
                attributes[attr] = max(current, spiked)

    return attributes, spike_label


def _generate_potential(true_talent):
    talent_factor = (true_talent - 1) / 99.0
    floor_base = 30 + int(talent_factor * 45)
    floor = max(10, min(85, floor_base + random.randint(-10, 10)))
    ceiling_base = floor + 15 + int(talent_factor * 25)
    ceiling = max(floor + 5, min(100, ceiling_base + random.randint(-15, 20)))
    return floor, ceiling


def _generate_personality(true_talent):
    talent_factor = (true_talent - 1) / 99.0
    ego_base = 8 + int(talent_factor * 5)
    ego = rand_attr(ego_base, spread=3)
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
    v0.3: 1500 prospects (was 1000). Extra 500 in fringe/low tiers.
    """
    recruits = []

    for tier_name, talent_range, count, _ in TALENT_TIERS:
        position_counts = _distribute_positions(count)

        for position, pos_count in position_counts.items():
            for _ in range(pos_count):
                true_talent = random.randint(*talent_range)
                home_state  = _pick_home_state()
                conf_region = STATE_TO_CONFERENCE_REGION.get(home_state)

                recruit = generate_recruit(
                    position=position,
                    true_talent=true_talent,
                    season=season,
                    conference_region=conf_region,
                )
                recruit["home_state"] = home_state
                recruits.append(recruit)

    recruits.sort(key=lambda r: (r["stars_consensus"], r["true_talent"]), reverse=True)

    for i, r in enumerate(recruits):
        r["composite_rank"] = i + 1

    return recruits


def _distribute_positions(total_count):
    counts    = {}
    remaining = total_count
    positions = list(POSITION_WEIGHTS.keys())
    for i, pos in enumerate(positions):
        if i == len(positions) - 1:
            counts[pos] = remaining
        else:
            counts[pos] = round(POSITION_WEIGHTS[pos] * total_count)
            remaining  -= counts[pos]
    return counts


# -----------------------------------------
# DISPLAY HELPERS
# -----------------------------------------

def format_height(inches):
    feet = inches // 12
    inch = inches % 12
    return str(feet) + "'" + str(inch) + '"'


def stars_display(n):
    return "★" * n + "☆" * (5 - n)


def print_recruit(recruit, show_hidden=False):
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
              "-" + str(recruit["potential_ceiling"]) +
              "  Spike: " + recruit.get("spike_label", "none"))
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
    print("")
    print("=" * 65)
    print("  " + str(season) + " RECRUITING CLASS  --  " +
          str(len(recruits)) + " prospects")
    print("=" * 65)

    star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in recruits:
        star_counts[r["stars_consensus"]] += 1

    print("  Star distribution:")
    for stars in [5, 4, 3, 2, 1]:
        bar = "█" * min(star_counts[stars], 40)
        print("  " + stars_display(stars) + "  " +
              str(star_counts[stars]).rjust(3) + "  " + bar)

    pos_counts = {p: 0 for p in POSITIONS}
    for r in recruits:
        pos_counts[r["position"]] += 1
    print("")
    print("  Position distribution: " +
          "  ".join(pos + ": " + str(pos_counts[pos]) for pos in POSITIONS))

    state_counts = {}
    for r in recruits:
        state_counts[r["home_state"]] = state_counts.get(r["home_state"], 0) + 1
    top_states = sorted(state_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print("  Top states: " +
          "  ".join(s + ": " + str(c) for s, c in top_states))

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
                  "-" + str(r["potential_ceiling"]) +
                  "  spike: " + r.get("spike_label", "none") + "]")


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("Generating 2025 recruiting class (v0.3 -- 1500 prospects)...")
    recruits_2025 = generate_recruiting_class(season=2025)

    print_class_summary(recruits_2025, season=2025, show_hidden=True)

    print("")
    print("=" * 65)
    print("  POOL SIZE VERIFICATION")
    print("=" * 65)
    total = len(recruits_2025)
    by_stars = {s: sum(1 for r in recruits_2025 if r["stars_consensus"] == s)
                for s in [5, 4, 3, 2, 1]}
    print("  Total recruits: " + str(total) + "  (target: 1500)")
    for s in [5, 4, 3, 2, 1]:
        print("    " + str(s) + "-star: " + str(by_stars[s]))
    print("")
    print("  328 programs × 3 graduates avg = ~984 players needed per year")
    print("  At 65% sign rate: " + str(int(total * 0.65)) + " commits -- should cover demand")
