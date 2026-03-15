import random
from names import generate_player_name
from player import rand_attr, _rand_mental, apply_freak_profile

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting System v0.4
# System 3 of the Design Bible
#
# v0.4 CHANGES -- 1-1000 internal attribute scale.
#
#   _generate_attributes() now produces skill attributes on 1-1000.
#   Mental attributes (basketball_iq, work_ethic, coachability, etc.)
#   stay on 1-20 -- same reasoning as player.py and coach.py.
#   Personality attributes (ego, loyalty, maturity, social_influence)
#   stay on 1-20.
#
#   ATTRIBUTE RANGE ANCHORS by tier:
#     Elite (true_talent 88-100):
#       primary attrs ~820-900, floor attrs ~200-320
#     High (73-87):
#       primary attrs ~720-820, floor attrs ~180-280
#     Mid (52-72):
#       primary attrs ~600-720, floor attrs ~160-260
#     Low (33-51):
#       primary attrs ~500-620, floor attrs ~150-230
#     Fringe (10-32):
#       primary attrs ~550-650 spike, base ~420-540
#       (fringe players got in on their spike -- see below)
#
#   SPIKE SYSTEM:
#     Every recruit has one genuine strength that made D1 coaches
#     notice him. Spike values on 1-1000:
#       Fringe (true_talent < 35):  spike 700-820
#       Low (true_talent < 55):     spike 680-800
#       Mid+ (true_talent >= 55):   spike 720-870
#
#   FORMULA:
#     talent_factor = (true_talent - 1) / 99.0  --> 0.0 to 1.0
#     primary:   base = 400 + int(talent_factor * 500)  --> 400-900
#     secondary: base = 300 + int(talent_factor * 420)  --> 300-720
#     tertiary:  base = 200 + int(talent_factor * 330)  --> 200-530
#     floor:     base = 100 + int(talent_factor * 180)  --> 100-280
#     spread stays proportional: ~60-80 on 1-1000 (was 2-3 on 1-20)
#
# v0.3 CHANGES (preserved):
#   - Pool expanded to 1500 prospects.
#   - Every recruit gets one SPIKE ATTRIBUTE.
# -----------------------------------------


POSITIONS = ["PG", "SG", "SF", "PF", "C"]

# Recruit pool -- 1500 total
TALENT_TIERS = [
    # (tier_name, true_talent_range, count, star_likely)
    ("elite",      (88, 100),   25,   5),
    ("high",       (73,  87),   80,   4),
    ("mid",        (52,  72),  200,   3),
    ("low",        (33,  51),  545,   2),
    ("fringe",     (10,  32),  650,   1),
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
    Generates skill attributes on 1-1000 scale with one spike.

    talent_factor maps true_talent (1-100) to 0.0-1.0.

    Base ranges by tier:
      primary:   400 + talent_factor * 500  --> ~400 (fringe) to ~900 (elite)
      secondary: 300 + talent_factor * 420  --> ~300 to ~720
      tertiary:  200 + talent_factor * 330  --> ~200 to ~530
      floor:     100 + talent_factor * 180  --> ~100 to ~280

    Spread ~65 (gaussian), reflecting natural variation within a tier.

    Returns (attributes_dict, spike_label).
    """
    talent_factor = (true_talent - 1) / 99.0
    archetype     = POSITION_ARCHETYPES[position]
    attributes    = {}

    for attr in ALL_ATTRIBUTES:
        if attr in archetype["primary"]:
            base = int(400 + talent_factor * 500)
            val  = rand_attr(base, spread=65)
        elif attr in archetype["secondary"]:
            base = int(300 + talent_factor * 420)
            val  = rand_attr(base, spread=65)
        elif attr in archetype["tertiary"]:
            base = int(200 + talent_factor * 330)
            val  = rand_attr(base, spread=65)
        else:  # floor attributes
            base = int(100 + talent_factor * 180)
            val  = rand_attr(base, spread=55)
        attributes[attr] = max(1, min(950, val))

    # Mental attributes stay on 1-20 scale
    mental_base = 8 + int(talent_factor * 3)   # 8-11 range, same as before
    attributes["basketball_iq"] = _rand_mental(mental_base, spread=3)
    attributes["clutch"]        = _rand_mental(10, spread=3)
    attributes["composure"]     = _rand_mental(10, spread=3)
    attributes["coachability"]  = _rand_mental(10, spread=3)
    attributes["work_ethic"]    = _rand_mental(10, spread=3)
    attributes["leadership"]    = _rand_mental(10, spread=3)

    # --- SPIKE ATTRIBUTE ---
    # One genuine strength that made D1 coaches notice this player.
    # All recruits get one -- the fringe player's spike IS why he's here.
    specializations = SPIKE_SPECIALIZATIONS.get(position, [])
    spike_label     = "none"

    if specializations:
        spike_label, spike_attrs = random.choice(specializations)

        # Spike values on 1-1000 scale
        if true_talent < 35:
            spike_min, spike_max = 700, 820
        elif true_talent < 55:
            spike_min, spike_max = 680, 800
        else:
            spike_min, spike_max = 720, 870

        for attr in spike_attrs:
            # Only spike skill attributes, not mental ones
            if attr in attributes and attr not in [
                "basketball_iq", "clutch", "composure",
                "coachability", "work_ethic", "leadership"
            ]:
                current = attributes[attr]
                spiked  = random.randint(spike_min, spike_max)
                attributes[attr] = max(current, spiked)

    # --- FREAK PROFILE ROLL ---
    # ~10% of recruits get a cross-positional attribute cluster boost.
    # Physically plausible by position -- see FREAK_PROFILES in player.py.
    # The profile is internal only. The numbers tell the story.
    temp_player = {"position": position}
    temp_player.update(attributes)
    apply_freak_profile(temp_player, true_talent=true_talent)
    # Pull boosted values back into attributes dict
    for attr in ALL_ATTRIBUTES:
        if attr in temp_player:
            attributes[attr] = temp_player[attr]

    return attributes, spike_label


def _generate_potential(true_talent):
    """
    Potential floor and ceiling stay as 1-100 talent scores.
    They are scouting abstractions, not attribute values.
    _potential_to_attr_ceiling() in player.py converts to 1-1000 when needed.
    """
    talent_factor = (true_talent - 1) / 99.0
    floor_base = 30 + int(talent_factor * 45)
    floor = max(10, min(85, floor_base + random.randint(-10, 10)))
    ceiling_base = floor + 15 + int(talent_factor * 25)
    ceiling = max(floor + 5, min(100, ceiling_base + random.randint(-15, 20)))
    return floor, ceiling


def _generate_personality(true_talent):
    """Personality attributes stay on 1-20 scale."""
    talent_factor = (true_talent - 1) / 99.0
    ego_base = 8 + int(talent_factor * 5)
    ego = _rand_mental(ego_base, spread=3)
    return {
        "ego":              max(1, min(20, ego)),
        "loyalty":          _rand_mental(10, spread=3),
        "maturity":         _rand_mental(10, spread=3),
        "social_influence": _rand_mental(10, spread=3),
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
    1500 prospects. All skill attributes on 1-1000 scale.
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
    from display import display_attr
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
        # Show a sample attribute in both raw and letter grade
        primary_sample = {
            "PG": "ball_handling", "SG": "catch_and_shoot",
            "SF": "finishing", "PF": "rebounding", "C": "rebounding"
        }.get(recruit["position"], "finishing")
        raw_val = recruit.get(primary_sample, 0)
        print("  [HIDDEN] " + primary_sample + ": " + str(raw_val) +
              " (" + display_attr(raw_val, "letter") + ")")
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
    from display import display_attr
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
            primary_sample = {
                "PG": "ball_handling", "SG": "catch_and_shoot",
                "SF": "finishing", "PF": "rebounding", "C": "rebounding"
            }.get(r["position"], "finishing")
            raw_val = r.get(primary_sample, 0)
            print("       [true_talent: " + str(r["true_talent"]) +
                  "  potential: " + str(r["potential_floor"]) +
                  "-" + str(r["potential_ceiling"]) +
                  "  spike: " + r.get("spike_label", "none") +
                  "  " + primary_sample + ": " + str(raw_val) +
                  " (" + display_attr(raw_val, "letter") + ")]")


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("Generating 2025 recruiting class (v0.4 -- 1-1000 scale)...")
    recruits_2025 = generate_recruiting_class(season=2025)

    print_class_summary(recruits_2025, season=2025, show_hidden=True)

    print("")
    print("=" * 65)
    print("  ATTRIBUTE RANGE VERIFICATION by tier")
    print("  (primary attribute averages on 1-1000 scale)")
    print("=" * 65)

    from display import display_attr

    tier_buckets = {"elite": [], "high": [], "mid": [], "low": [], "fringe": []}
    for r in recruits_2025:
        tt = r["true_talent"]
        pos = r["position"]
        primary_attrs = POSITION_ARCHETYPES[pos]["primary"]
        avg_primary = sum(r.get(a, 500) for a in primary_attrs if a in r) / max(1, len(primary_attrs))

        if tt >= 88:   tier_buckets["elite"].append(avg_primary)
        elif tt >= 73: tier_buckets["high"].append(avg_primary)
        elif tt >= 52: tier_buckets["mid"].append(avg_primary)
        elif tt >= 33: tier_buckets["low"].append(avg_primary)
        else:          tier_buckets["fringe"].append(avg_primary)

    for tier, vals in tier_buckets.items():
        if vals:
            avg = sum(vals) / len(vals)
            mn  = min(vals)
            mx  = max(vals)
            print("  " + tier.ljust(8) +
                  "  avg primary: " + str(round(avg)).rjust(4) +
                  "  (" + display_attr(avg, "letter") + ")" +
                  "  range: " + str(round(mn)) + "-" + str(round(mx)))

    print("")
    print("=" * 65)
    print("  SPIKE VERIFICATION -- top spike values")
    print("=" * 65)
    fringe = [r for r in recruits_2025 if r["true_talent"] < 35]
    all_spike_vals = []
    for r in fringe[:50]:
        pos = r["position"]
        primary = POSITION_ARCHETYPES[pos]["primary"]
        top_attr = max(primary, key=lambda a: r.get(a, 0))
        top_val  = r.get(top_attr, 0)
        all_spike_vals.append(top_val)

    avg_spike = sum(all_spike_vals) / max(1, len(all_spike_vals))
    print("  Fringe recruits top attribute avg: " + str(round(avg_spike)) +
          " (" + display_attr(avg_spike, "letter") + ")")
    print("  Target: 700-820 range")
