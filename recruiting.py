import random
from names import generate_player_name
from player import (rand_attr, _rand_mental, apply_freak_profile,
                    _generate_height, _generate_wingspan, _generate_weight,
                    _generate_explosiveness, _generate_agility,
                    _apply_height_athleticism_penalty, _derive_natural_position)

# -----------------------------------------
# COLLEGE HOOPS SIM -- Recruiting System v0.6
# System 3 of the Design Bible
#
# v0.6 CHANGES -- Outliers, Generational Talents, Height-Driven Athleticism
#
#   PHYSICAL OUTLIERS:
#     Short outlier (5'4"-5'8" PG): 1 in 800 recruits.
#       Generates with guard skills but severe size disadvantage.
#       The engine treats him exactly as his attributes say.
#       At a low major he might still start. At a power program he's
#       a 10-minute spark plug who gets cooked in the post.
#
#     Tall outlier, no skills (7'3"-7'5" C): 1 in 600 recruits.
#       Poor skills across the board. Low true_talent (10-25).
#       Still affects games at low majors via sheer length_rating
#       and rebound window. Gets destroyed by real post players.
#       Most programs that sign him regret it by year two.
#
#     Tall outlier, real skills (7'3"-7'5" C): 1 in 15,000 recruits.
#       A real player who happens to be enormous.
#       true_talent 60-85. Skills seeded elite at one or two things.
#       Still takes the full height athleticism penalty -- he's not
#       athletic. But skill and size together at 7'4" is an event.
#
#   GENERATIONAL TALENTS:
#     Two subtypes. Both extremely rare. Different discovery patterns.
#
#     "phenom":
#       1 in 33,000 recruits. ~1 every 10 seasons.
#       Everyone knows. Arrives elite. True talent 95-100.
#       2-3 primary attributes seeded 800-900 as a freshman.
#       Arc type: overachiever or steady.
#       Physical profile skewed toward exceptional but not guaranteed.
#       Recruiting services go insane. Every blue blood goes all-in.
#       The existing recruiting engine handles the frenzy naturally
#       because his true_talent is so high every top program targets him.
#
#     "late_bloomer_generational":
#       1 in 50,000 recruits. ~1 every 15 seasons.
#       Nobody saw it. Looks like a 3-star. Lands at a mid-major.
#       True talent visible to scouts: 35-55 range.
#       Attributes at arrival: solid but not elite.
#       Arc type: always late_bloomer. Breakthrough multiplier 3x.
#       Junior year he becomes the best player in the country.
#       The flag itself is hidden -- no program knows what they have.
#
#   HEIGHT-DRIVEN ATHLETICISM:
#     Recruit generation now passes height into athleticism generation.
#     Every inch above 6'6" applies speed/explosiveness/agility penalties.
#     The 7'0" space filler really is plodding. The 6'10" freak who
#     beats the penalty is genuinely rare. This is what makes him special.
#
# v0.5 CHANGES (preserved):
#   Pool size 4500, tier 6-7 depth pool, weighted spike selection,
#   paired attribute guarantee, stretch big talent restriction.
# -----------------------------------------


POSITIONS = ["PG", "SG", "SF", "PF", "C"]

# -----------------------------------------
# TALENT TIERS
# Tier 1-5: traditional D1 scholarship pool (1500 total)
# Tier 6-7: developmental/depth pool (3000 total)
# -----------------------------------------

TALENT_TIERS = [
    # (tier_name, true_talent_range, count, ranked)
    ("elite",       (88, 100),   25,  True),
    ("high",        (73,  87),   80,  True),
    ("mid",         (52,  72),  200,  True),
    ("low",         (33,  51),  545,  True),
    ("fringe",      (10,  32),  650,  True),
    ("developmental",(5,  15), 1000,  False),
    ("depth",        (1,   8), 2000,  False),
]

# Ranks shown to human -- top 300 get composite rank displayed
RANKED_CUTOFF     = 300
PARTIAL_RANKED_CUTOFF = 500   # 301-500 get stars but limited service coverage

POSITION_WEIGHTS = {
    "PG": 0.18,
    "SG": 0.22,
    "SF": 0.22,
    "PF": 0.20,
    "C":  0.18,
}

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

# -----------------------------------------
# SPIKE SPECIALIZATIONS
#
# Structure: (label, [attr1, attr2, attr3, ...])
# First two attrs are the QUALIFYING PAIR -- both guaranteed to clear
# spike threshold. Third+ are bonus attrs that also get boosted.
#
# Weighted selection per position reflects real basketball distributions.
# -----------------------------------------

SPIKE_SPECIALIZATIONS = {
    "PG": [
        # (label, qualifying_pair + bonus attrs)
        ("floor_general",    ["passing", "court_vision", "decision_making"]),
        ("spot_up_shooter",  ["catch_and_shoot", "three_point", "free_throw"]),
        ("on_ball_defender", ["on_ball_defense", "lateral_quickness", "steal_tendency"]),
        ("speedster",        ["speed", "lateral_quickness", "ball_handling"]),
        ("high_iq",          ["court_vision", "decision_making", "passing"]),
    ],
    "SG": [
        ("spot_up_shooter",  ["catch_and_shoot", "three_point", "free_throw"]),
        ("off_dribble",      ["off_dribble", "finishing", "ball_handling"]),
        ("lockdown",         ["on_ball_defense", "lateral_quickness", "steal_tendency"]),
        ("athlete",          ["speed", "vertical", "lateral_quickness"]),
        ("mid_range",        ["mid_range", "catch_and_shoot", "free_throw"]),
    ],
    "SF": [
        ("slasher",          ["finishing", "speed", "vertical"]),
        ("three_and_d",      ["catch_and_shoot", "three_point", "on_ball_defense"]),
        ("switchable",       ["on_ball_defense", "lateral_quickness", "help_defense"]),
        ("rebounder",        ["rebounding", "strength", "help_defense"]),
        ("tough_wing",       ["strength", "rebounding", "help_defense"]),
    ],
    "PF": [
        ("glass_eater",      ["rebounding", "strength", "vertical"]),
        ("post_scorer",      ["post_scoring", "finishing", "strength"]),
        ("energy_big",       ["rebounding", "help_defense", "strength"]),
        ("shot_blocker",     ["shot_blocking", "vertical", "help_defense"]),
        ("stretch_four",     ["catch_and_shoot", "three_point", "mid_range"]),
    ],
    "C": [
        ("rebounder",        ["rebounding", "strength", "finishing"]),
        ("post_scorer",      ["post_scoring", "finishing", "strength"]),
        ("rim_protector",    ["shot_blocking", "vertical", "help_defense"]),
        ("energy_big",       ["rebounding", "help_defense", "on_ball_defense"]),
        ("physical_presence",["strength", "rebounding", "finishing"]),
    ],
}

# Weighted spike selection by position
# Weights correspond to specializations list order above
SPIKE_WEIGHTS = {
    "PG": [20, 25, 20, 15, 20],   # shooters most common
    "SG": [30, 20, 20, 15, 15],   # spot-up shooter most common
    "SF": [25, 25, 20, 15, 15],   # slasher and three-and-d tied
    "PF": [25, 25, 25, 15, 10],   # rebounders, post scorers, energy bigs
    "C":  [30, 25, 20, 20,  5],   # rebounders most common, post scorers strong
}

# Talent threshold for stretch big spikes (stretch_four, stretch_five)
# Below this true_talent, bigs cannot roll shooting spikes
STRETCH_MIN_TALENT = 45

SERVICE_NAMES = ["247Sports", "Rivals", "ESPN"]
SERVICE_NOISE = {
    "247Sports": (-8,   8),
    "Rivals":    (-10, 10),
    "ESPN":      (-14, 14),
}

# -----------------------------------------
# OUTLIER AND GENERATIONAL TALENT RATES
#
# PER-RECRUIT (scales with pool size -- realistic):
#   Physical accidents of nature. More recruits = more of them.
#   A 15,000-recruit pool should produce more 5'6" kids trying to
#   play ball than a 4,500 pool. These stay per-recruit.
#
# PER-SEASON (fixed regardless of pool size -- by design):
#   Generational talents and skilled giants are once-in-a-generation
#   anomalies. They don't become more common because you added D2.
#   The roll happens once per class generation. One recruit in the
#   pool gets the flag. Scaling to 15,000 does NOT produce 3x LeBrons.
# -----------------------------------------

# Per-recruit rates (scale naturally with pool size)
OUTLIER_SHORT_RATE        = 1 / 800    # 5'4"-5'8" PG/SG
OUTLIER_TALL_NOSKILL_RATE = 1 / 600    # 7'3"-7'5" C, poor skills

# Per-season rates (fixed regardless of pool size)
# generate_recruiting_class() rolls these once and stamps one recruit
SEASON_TALL_SKILL_CHANCE   = 1 / 5     # ~1 skilled giant every 5 seasons
SEASON_PHENOM_CHANCE       = 1 / 10    # ~1 phenom every 10 seasons
SEASON_LATE_BLOOMER_CHANCE = 1 / 15    # ~1 late bloomer every 15 seasons


def talent_to_stars(talent_score):
    if talent_score >= 90: return 5
    if talent_score >= 75: return 4
    if talent_score >= 55: return 3
    if talent_score >= 35: return 2
    return 1


# -----------------------------------------
# OUTLIER AND GENERATIONAL TALENT GENERATORS
# -----------------------------------------

def _check_outlier_per_recruit(position):
    """
    Rolls for per-recruit physical outlier flags only.
    Generational talents and skilled giants are handled at the class
    level in generate_recruiting_class() -- they are per-season events,
    not per-recruit rolls. Pool size does not affect their frequency.

    Returns outlier_type: "short", "tall_noskill", or None.
    """
    # Short outliers only for guard positions
    if position in ("PG", "SG"):
        if random.random() < OUTLIER_SHORT_RATE:
            return "short"

    # Tall no-skill only for C (occasionally PF)
    if position == "C" or (position == "PF" and random.random() < 0.2):
        if random.random() < OUTLIER_TALL_NOSKILL_RATE:
            return "tall_noskill"

    return None


def _apply_outlier_physical(recruit, outlier_type, position):
    """
    Overrides height/wingspan/weight for physical outlier recruits.
    Called after normal physical generation.
    """
    if outlier_type == "short":
        # 5'4" to 5'8" -- true undersized guard
        height  = random.randint(64, 68)
        wingspan = max(63, height + random.randint(-2, 3))
        weight  = random.randint(150, 175)
        recruit["height_inches"] = height
        recruit["weight_lbs"]    = weight
        recruit["wingspan"]      = wingspan

    elif outlier_type in ("tall_noskill", "tall_skill"):
        # 7'3" to 7'5"
        height   = random.randint(87, 89)
        wingspan = min(96, height + random.randint(0, 6))
        weight   = random.randint(230, 270)
        recruit["height_inches"] = height
        recruit["weight_lbs"]    = weight
        recruit["wingspan"]      = wingspan

    return recruit


def _apply_outlier_attributes(attributes, outlier_type, position,
                               true_talent, talent_factor):
    """
    Modifies skill attributes for physical outliers.

    Short outlier: normal guard skill profile, no modifications needed.
      The engine will punish him physically but his skills are real.

    Tall no-skill: deliberately poor skills everywhere.
      true_talent forced to 10-25 range.
      He's on a D1 roster because he's 7'4", full stop.
      Rebounds, blocks shots by existing, fouls out in 18 minutes
      against anyone who can actually post up.

    Tall skilled: real skills at one or two things.
      true_talent 60-85. Primary attrs seeded elite.
      Still takes full height athleticism penalty.
      Different from generational -- skilled but not transcendent.
    """
    if outlier_type == "short":
        # No attribute modification -- short guy with normal guard skills.
        # Height penalty handled at engine time (Phase B).
        pass

    elif outlier_type == "tall_noskill":
        # Deliberately poor everything except the things size gives you
        for attr in ALL_ATTRIBUTES:
            if attr in ("rebounding", "shot_blocking", "strength", "help_defense"):
                # These are decent -- size helps here
                attributes[attr] = rand_attr(380, spread=60)
            elif attr in ("finishing",):
                # Can catch and finish near the rim
                attributes[attr] = rand_attr(300, spread=60)
            else:
                # Everything else is genuinely bad
                attributes[attr] = rand_attr(150, spread=50)

    elif outlier_type == "tall_skill":
        # Start with normal generation (already done), then spike
        # 1-2 primary attrs to elite level
        primary_for_c = ["rebounding", "shot_blocking", "post_scoring",
                         "finishing", "strength"]
        num_elite = random.randint(1, 2)
        chosen    = random.sample(primary_for_c, num_elite)
        for attr in chosen:
            attributes[attr] = rand_attr(720, spread=60)

    return attributes


def _apply_generational_attributes(recruit, generational_type, position,
                                    attributes):
    """
    Stamps generational talent flag and modifies attributes/potential.

    Phenom:
      Arrives visibly special. true_talent 95-100.
      2-3 primary attrs seeded 800-900.
      Arc: overachiever or steady. Never busts.
      Physical profile skewed exceptional but not required.

    Late bloomer generational:
      Arrives looking like a 3-star. true_talent to scouts: 35-55.
      Attributes at arrival: solid but not elite.
      Arc: always late_bloomer. Breakthrough multiplier 3x normal.
      The flag is hidden -- no program knows what they have.
      The generational_talent key exists on the player dict but
      is not surfaced in any scouting report until he breaks out.
    """
    recruit["generational_talent"] = generational_type

    if generational_type == "phenom":
        # Force true talent to elite range
        recruit["true_talent"]       = random.randint(95, 100)
        recruit["potential_floor"]   = random.randint(85, 92)
        recruit["potential_ceiling"] = random.randint(95, 100)
        recruit["arc_type"]          = random.choice(["overachiever", "steady"])

        # Seed 2-3 primary attributes elite
        arch    = POSITION_ARCHETYPES.get(position, {})
        primary = arch.get("primary", [])
        num_elite = random.randint(2, 3)
        chosen    = random.sample(primary, min(num_elite, len(primary)))
        for attr in chosen:
            if attr in ALL_ATTRIBUTES:
                attributes[attr] = rand_attr(840, spread=40)

        # Service ratings reflect the true talent
        recruit["stars_consensus"] = 5
        recruit["stars_247"]  = 5
        recruit["stars_rivals"] = 5
        recruit["stars_espn"] = 5

    elif generational_type == "late_bloomer_generational":
        # Looks ordinary to scouts
        recruit["true_talent"]       = random.randint(35, 55)
        recruit["potential_floor"]   = random.randint(40, 55)
        recruit["potential_ceiling"] = random.randint(92, 100)
        recruit["arc_type"]          = "late_bloomer"
        # No attribute modification -- he looks like a normal 3-star.
        # The breakthrough system will handle his explosion in year 3.
        # The 3x breakthrough multiplier is applied in develop_player
        # when the generational_talent flag is read. (Phase C hook)

    return recruit, attributes


# -----------------------------------------
# CORE RECRUIT GENERATOR
# -----------------------------------------

def generate_recruit(position, true_talent, season,
                     conference_region=None, is_ranked=True):
    """
    Generates a single recruit.
    is_ranked=False for developmental/depth pool players --
    no service ratings, no composite rank, coaches find by scouting.

    v0.6: physical attributes now fully generated here and carried
    through to _recruit_to_player() in lifecycle.py.
    Outlier and generational checks happen at generation, not enrollment.
    """
    region_conf = conference_region or random.choice(
        list(STATE_TO_CONFERENCE_REGION.values())
    )
    name, heritage = generate_player_name(conference=region_conf)
    name_parts = name.split(" ", 1)
    first_name = name_parts[0]
    last_name  = name_parts[1] if len(name_parts) > 1 else "Smith"

    home_state = _pick_home_state()

    # --- CHECK FOR PER-RECRUIT PHYSICAL OUTLIER ---
    # Generational talents and skilled giants are injected by the caller
    # (generate_recruiting_class) as per-season events. This only rolls
    # the per-recruit physical outliers (short guard, tall no-skill).
    outlier_type     = _check_outlier_per_recruit(position)
    generational_type = None   # stamped by generate_recruiting_class if applicable

    # --- GENERATE PHYSICAL SIZE ---
    # Outlier height overridden after normal generation
    height   = _generate_height(position)
    wingspan = _generate_wingspan(height, position)
    weight   = _generate_weight(position, "Freshman")

    attributes, spike_label = _generate_attributes(
        position, true_talent, is_ranked=is_ranked
    )

    # Apply height-driven athleticism penalty to recruit attributes
    ath_attrs = {k: attributes[k] for k in
                 ["speed", "lateral_quickness", "strength", "vertical",
                  "explosiveness", "agility"]
                 if k in attributes}
    if ath_attrs:
        penalized = _apply_height_athleticism_penalty(ath_attrs, height)
        attributes.update(penalized)

    potential_floor, potential_ceiling = _generate_potential(true_talent)
    personality = _generate_personality(true_talent)
    priorities  = _generate_priorities()

    # Service ratings -- only for ranked/partially-ranked players
    if is_ranked:
        service_ratings = {}
        service_ranks   = {}
        for service, (noise_low, noise_high) in SERVICE_NOISE.items():
            noise        = random.randint(noise_low, noise_high)
            service_read = max(1, min(100, true_talent + noise))
            service_ratings[service] = talent_to_stars(service_read)
            rank_noise = random.randint(0, max(1, 500 - true_talent * 4))
            service_ranks[service] = max(1, int((100 - true_talent) * 5 + rank_noise))
        stars_consensus = _consensus_stars(service_ratings)
    else:
        service_ratings = {"247Sports": 0, "Rivals": 0, "ESPN": 0}
        service_ranks   = {"247Sports": 0, "Rivals": 0, "ESPN": 0}
        stars_consensus = 1

    # Add new v0.8 athleticism to attributes if not already there
    if "explosiveness" not in attributes:
        attributes["explosiveness"] = _generate_explosiveness(position)
        attributes["explosiveness"] = max(1, min(950,
            attributes["explosiveness"] +
            _apply_height_athleticism_penalty(
                {"explosiveness": attributes["explosiveness"]}, height
            ).get("explosiveness", attributes["explosiveness"]) -
            attributes["explosiveness"]
        ))
    if "agility" not in attributes:
        attributes["agility"] = _generate_agility(position)

    # New mental attributes
    attributes["ball_dominance"]    = _rand_mental(3, 16)
    attributes["usage_tendency"]    = _rand_mental(4, 15)
    attributes["off_ball_movement"] = _rand_mental(3, 17)

    recruit = {
        "name":           name,
        "first_name":     first_name,
        "last_name":      last_name,
        "position":       position,
        "heritage":       heritage,
        "home_state":     home_state,
        "height_inches":  height,
        "weight_lbs":     weight,
        "wingspan":       wingspan,
        "season":         season,
        "true_talent":       true_talent,
        "potential_floor":   potential_floor,
        "potential_ceiling": potential_ceiling,
        "arc_type":          "steady",       # default; overridden below
        "spike_label":       spike_label,
        "is_ranked":         is_ranked,
        "composite_rank":    None,
        "generational_talent": None,         # overridden if applicable
        "outlier_type":      outlier_type,   # "short"/"tall_noskill"/"tall_skill"/None
        "stars_247":    service_ratings["247Sports"],
        "stars_rivals": service_ratings["Rivals"],
        "stars_espn":   service_ratings["ESPN"],
        "rank_247":     service_ranks["247Sports"],
        "rank_rivals":  service_ranks["Rivals"],
        "rank_espn":    service_ranks["ESPN"],
        "stars_consensus": stars_consensus,
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

    # --- APPLY OUTLIER PHYSICAL OVERRIDES ---
    if outlier_type:
        recruit = _apply_outlier_physical(recruit, outlier_type, position)
        attributes = _apply_outlier_attributes(
            attributes, outlier_type, position, true_talent,
            (true_talent - 1) / 99.0
        )
        # Re-stamp modified attributes
        for k, v in attributes.items():
            recruit[k] = v

        # Adjust true_talent for no-skill tall outlier
        if outlier_type == "tall_noskill":
            recruit["true_talent"] = random.randint(10, 25)
            recruit["stars_consensus"] = random.randint(1, 2)
            recruit["is_ranked"] = recruit["true_talent"] >= 15

    # --- APPLY GENERATIONAL TALENT ---
    if generational_type:
        recruit, attributes = _apply_generational_attributes(
            recruit, generational_type, position, attributes
        )
        for k, v in attributes.items():
            recruit[k] = v

    # --- DERIVE NATURAL POSITION ---
    # Build minimal player dict for natural position derivation
    temp = {"height": recruit["height_inches"], "position": position}
    temp.update(attributes)
    recruit["natural_position"] = _derive_natural_position(temp)

    return recruit


def _pick_home_state():
    states  = list(STATE_WEIGHTS.keys())
    weights = list(STATE_WEIGHTS.values())
    return random.choices(states, weights=weights, k=1)[0]


def _consensus_stars(service_ratings):
    ratings = sorted(service_ratings.values())
    return ratings[1]


# -----------------------------------------
# ATTRIBUTE GENERATION
# -----------------------------------------

def _generate_attributes(position, true_talent, is_ranked=True):
    """
    Generates skill attributes on 1-1000 scale.

    For ranked players: standard distribution by talent tier.
    For developmental/depth pool: compressed range centered lower,
    but with one mandatory identifiable spike.

    Spike selection is WEIGHTED by position to reflect real basketball.
    First two spike attributes are guaranteed to clear threshold (paired).
    Talent-tier restrictions prevent fringe/low bigs from rolling
    shooting spikes -- they go to rebounding/post/rim protection instead.

    Returns (attributes_dict, spike_label).
    """
    talent_factor = (true_talent - 1) / 99.0
    archetype     = POSITION_ARCHETYPES[position]
    attributes    = {}

    if is_ranked:
        # Standard distribution
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
            else:
                base = int(100 + talent_factor * 180)
                val  = rand_attr(base, spread=55)
            attributes[attr] = max(1, min(950, val))
    else:
        # Developmental/depth pool -- compressed, lower baseline
        # These players are roughly D2/D3 talent in a D1 pool.
        # Primary attrs sit around 300-420, floor attrs 80-150.
        dev_talent_factor = max(0.0, (true_talent - 1) / 15.0)  # 0.0-1.0 over 1-15
        for attr in ALL_ATTRIBUTES:
            if attr in archetype["primary"]:
                base = int(280 + dev_talent_factor * 140)  # 280-420
                val  = rand_attr(base, spread=50)
            elif attr in archetype["secondary"]:
                base = int(200 + dev_talent_factor * 110)  # 200-310
                val  = rand_attr(base, spread=50)
            elif attr in archetype["tertiary"]:
                base = int(140 + dev_talent_factor * 90)   # 140-230
                val  = rand_attr(base, spread=45)
            else:
                base = int(70  + dev_talent_factor * 70)   # 70-140
                val  = rand_attr(base, spread=40)
            attributes[attr] = max(1, min(700, val))   # depth pool cap at 700

        # Depth pool endurance -- lower baseline, wide variance
        endurance_bases = {"PG": 460, "SG": 440, "SF": 400, "PF": 370, "C": 340}
        attributes["endurance"] = max(1, min(700, rand_attr(
            endurance_bases.get(position, 400), spread=80
        )))

    # Endurance for ranked players -- added after ranked attr loop
    if is_ranked:
        endurance_bases = {"PG": 560, "SG": 540, "SF": 500, "PF": 460, "C": 420}
        endurance_base  = endurance_bases.get(position, 500)
        endurance_bonus = int(talent_factor * 80)
        attributes["endurance"] = rand_attr(endurance_base + endurance_bonus, spread=80)

    # v0.6: explosiveness and agility -- generated here, height penalty applied in caller
    attributes["explosiveness"] = _generate_explosiveness(position)
    attributes["agility"]       = _generate_agility(position)

    # Mental attributes -- same scale regardless of tier
    mental_base = 8 + int(talent_factor * 3) if is_ranked else 8
    attributes["basketball_iq"] = _rand_mental(mental_base, spread=3)
    attributes["clutch"]        = _rand_mental(10, spread=3)
    attributes["composure"]     = _rand_mental(10, spread=3)
    attributes["coachability"]  = _rand_mental(10, spread=3)
    attributes["work_ethic"]    = _rand_mental(10, spread=3)
    attributes["leadership"]    = _rand_mental(10, spread=3)
    # v0.6 new mentals
    attributes["ball_dominance"]    = _rand_mental(3, 16)
    attributes["usage_tendency"]    = _rand_mental(4, 15)
    attributes["off_ball_movement"] = _rand_mental(3, 17)

    # --- SPIKE SELECTION ---
    spike_label, spike_attrs = _pick_spike(position, true_talent, is_ranked)

    # Spike values -- both qualifying pair attrs guaranteed to clear threshold
    if is_ranked:
        if true_talent < 35:
            spike_min, spike_max = 700, 820
        elif true_talent < 55:
            spike_min, spike_max = 680, 800
        else:
            spike_min, spike_max = 720, 870
    else:
        # Depth pool spike -- lower ceiling, but still identifiable
        spike_min, spike_max = 560, 680

    mental_skip = {
        "basketball_iq", "clutch", "composure",
        "coachability", "work_ethic", "leadership"
    }

    for i, attr in enumerate(spike_attrs):
        if attr in attributes and attr not in mental_skip:
            current = attributes[attr]
            if i < 2:
                # Qualifying pair -- guaranteed to clear spike_min
                spiked = random.randint(spike_min, spike_max)
                attributes[attr] = max(current, spiked)
            else:
                # Bonus attr -- boosted but not guaranteed to clear threshold
                bonus_min = int(spike_min * 0.85)
                bonus_max = int(spike_max * 0.90)
                spiked = random.randint(bonus_min, bonus_max)
                attributes[attr] = max(current, spiked)

    # Freak profile -- 10% of players get cross-positional boost
    # Only for ranked players -- depth pool players are too limited
    if is_ranked:
        temp_player = {"position": position}
        temp_player.update(attributes)
        apply_freak_profile(temp_player, true_talent=true_talent)
        for attr in ALL_ATTRIBUTES:
            if attr in temp_player:
                attributes[attr] = temp_player[attr]

    return attributes, spike_label


def _pick_spike(position, true_talent, is_ranked):
    """
    Weighted spike selection with talent-tier restrictions for bigs.

    PF and C below STRETCH_MIN_TALENT cannot roll stretch_four.
    The weight for that option is redistributed to rebounding/post.

    Returns (spike_label, spike_attrs).
    """
    specializations = SPIKE_SPECIALIZATIONS.get(position, [])
    weights         = list(SPIKE_WEIGHTS.get(position, []))

    if not specializations:
        return "none", []

    # Talent restriction for stretch bigs
    if position in ("PF", "C") and true_talent < STRETCH_MIN_TALENT:
        # Find stretch_four index and zero it out, redistribute to rebounders
        for i, (label, _) in enumerate(specializations):
            if label == "stretch_four":
                redistributed = weights[i]
                weights[i] = 0
                # Give the weight to glass_eater/rebounder (index 0)
                weights[0] += redistributed
                break

    # Depth pool restriction -- no complex athletic spikes
    # Depth pool bigs only get rebounding, post scoring, rim protection
    if not is_ranked and position in ("PF", "C"):
        allowed = {"glass_eater", "post_scorer", "rebounder",
                   "energy_big", "rim_protector", "physical_presence"}
        for i, (label, _) in enumerate(specializations):
            if label not in allowed:
                weights[0] += weights[i]
                weights[i] = 0

    chosen_label, chosen_attrs = random.choices(
        specializations, weights=weights, k=1
    )[0]

    return chosen_label, chosen_attrs


# -----------------------------------------
# POTENTIAL, PERSONALITY, PRIORITIES
# -----------------------------------------

def _generate_potential(true_talent):
    """Potential stays 1-100 talent abstraction."""
    talent_factor = (true_talent - 1) / 99.0
    floor_base    = 30 + int(talent_factor * 45)
    floor         = max(10, min(85, floor_base + random.randint(-10, 10)))
    ceiling_base  = floor + 15 + int(talent_factor * 25)
    ceiling       = max(floor + 5, min(100, ceiling_base + random.randint(-15, 20)))
    return floor, ceiling


def _generate_personality(true_talent):
    """Personality attributes stay on 1-20 scale."""
    talent_factor = (true_talent - 1) / 99.0
    ego_base      = 8 + int(talent_factor * 5)
    return {
        "ego":              max(1, min(20, _rand_mental(ego_base, spread=3))),
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
    Generates the full prospect pool for a season.

    4500 total:
      Tiers 1-5 (ranked): 1500 players, full service coverage for top 300,
                           partial for 301-500, unranked for 501-1500.
      Tier 6 (developmental): 1000 players, no service coverage.
      Tier 7 (depth): 2000 players, no service coverage.

    Ranked players get composite_rank 1-N.
    Developmental/depth players get composite_rank = None.

    v0.6: Per-season special events rolled here, not per-recruit.
    Pool size does not affect frequency of generational talents or
    skilled giants. One recruit in the pool gets the flag stamped.
    """
    # --- PER-SEASON SPECIAL EVENT ROLLS ---
    # These happen regardless of pool size. Adding D2/JUCO later
    # will not make generational talents more common.
    phenom_this_season      = random.random() < SEASON_PHENOM_CHANCE
    late_bloomer_this_season = random.random() < SEASON_LATE_BLOOMER_CHANCE
    tall_skill_this_season   = random.random() < SEASON_TALL_SKILL_CHANCE

    ranked_recruits = []
    depth_recruits  = []

    for tier_name, talent_range, count, is_ranked in TALENT_TIERS:
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
                    is_ranked=is_ranked,
                )
                recruit["home_state"] = home_state

                if is_ranked:
                    ranked_recruits.append(recruit)
                else:
                    depth_recruits.append(recruit)

    # --- STAMP PER-SEASON SPECIAL EVENTS ---
    # Pick one eligible recruit from the full pool and apply the flag.
    # Phenoms must be in ranked pool (they'd be found by scouts).
    # Late bloomers and skilled giants can be anywhere.
    all_recruits = ranked_recruits + depth_recruits

    if tall_skill_this_season:
        eligible = [r for r in all_recruits
                    if r["position"] in ("C", "PF")
                    and not r.get("outlier_type")]
        if eligible:
            chosen = random.choice(eligible)
            chosen["outlier_type"] = "tall_skill"

            # Enforce true_talent floor -- a skilled 7'4" guy is a real
            # player. Programs need to be able to find and recruit him.
            # Floor of 40 means he shows up as a 2-star with real upside.
            # Without this, his true_talent could be 1 and no program's
            # recruiting logic would ever surface him.
            TT_FLOOR = 40
            if chosen["true_talent"] < TT_FLOOR:
                chosen["true_talent"] = random.randint(TT_FLOOR, 60)
                # Recalculate potential to match
                pf, pc = _generate_potential(chosen["true_talent"])
                chosen["potential_floor"]   = pf
                chosen["potential_ceiling"] = pc
                # Recalculate service ratings to match new true_talent
                for service, (nl, nh) in SERVICE_NOISE.items():
                    noise = random.randint(nl, nh)
                    sr    = max(1, min(100, chosen["true_talent"] + noise))
                    key   = {"247Sports": "stars_247",
                             "Rivals": "stars_rivals",
                             "ESPN": "stars_espn"}[service]
                    chosen[key] = talent_to_stars(sr)
                chosen["stars_consensus"] = _consensus_stars({
                    "247Sports": chosen["stars_247"],
                    "Rivals":    chosen["stars_rivals"],
                    "ESPN":      chosen["stars_espn"],
                })
                chosen["is_ranked"] = True

            _apply_outlier_physical(chosen, "tall_skill", chosen["position"])
            attrs = {k: chosen[k] for k in ALL_ATTRIBUTES if k in chosen}
            attrs = _apply_outlier_attributes(
                attrs, "tall_skill", chosen["position"],
                chosen["true_talent"], (chosen["true_talent"]-1)/99.0
            )
            for k, v in attrs.items():
                chosen[k] = v

    if phenom_this_season:
        eligible = [r for r in ranked_recruits
                    if not r.get("generational_talent")
                    and not r.get("outlier_type")]
        if eligible:
            chosen = random.choice(eligible)
            attrs  = {k: chosen[k] for k in ALL_ATTRIBUTES if k in chosen}
            chosen, attrs = _apply_generational_attributes(
                chosen, "phenom", chosen["position"], attrs
            )
            for k, v in attrs.items():
                chosen[k] = v

    if late_bloomer_this_season:
        eligible = [r for r in all_recruits
                    if not r.get("generational_talent")
                    and not r.get("outlier_type")]
        if eligible:
            chosen = random.choice(eligible)
            attrs  = {k: chosen[k] for k in ALL_ATTRIBUTES if k in chosen}
            chosen, attrs = _apply_generational_attributes(
                chosen, "late_bloomer_generational",
                chosen["position"], attrs
            )
            for k, v in attrs.items():
                chosen[k] = v

    # Sort ranked players by stars then true_talent
    ranked_recruits.sort(
        key=lambda r: (r["stars_consensus"], r["true_talent"]),
        reverse=True
    )

    # Assign composite ranks
    # Top 300: full rank displayed
    # 301-500: rank shown but partial service coverage
    # 501+: NR (no rank)
    for i, r in enumerate(ranked_recruits):
        rank = i + 1
        if rank <= PARTIAL_RANKED_CUTOFF:
            r["composite_rank"] = rank
        else:
            r["composite_rank"] = None   # displayed as "NR"

        # Partial coverage: 301-500 only get one service rating
        if RANKED_CUTOFF < rank <= PARTIAL_RANKED_CUTOFF:
            # Keep only 247Sports, zero out others
            r["stars_rivals"] = 0
            r["stars_espn"]   = 0

    # Depth pool has no ranks
    for r in depth_recruits:
        r["composite_rank"] = None

    # Full pool: ranked first, then depth
    return ranked_recruits + depth_recruits


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
    if n == 0:
        return "     "   # unranked depth pool -- no stars shown
    return "★" * n + "☆" * (5 - n)


def print_recruit(recruit, show_hidden=False):
    from display import display_attr

    rank_str = ("#" + str(recruit["composite_rank"])
                if recruit["composite_rank"]
                else "NR")

    print("")
    print("  " + recruit["name"] + "  |  " + recruit["position"] +
          "  |  " + format_height(recruit["height_inches"]) +
          "  " + str(recruit["weight_lbs"]) + "lbs" +
          "  |  " + recruit["home_state"] +
          "  |  " + rank_str)

    if recruit["is_ranked"]:
        print("  247: " + stars_display(recruit["stars_247"]) +
              "  Rivals: " + stars_display(recruit["stars_rivals"]) +
              "  ESPN: " + stars_display(recruit["stars_espn"]) +
              "  (Consensus: " + stars_display(recruit["stars_consensus"]) + ")")
    else:
        print("  [Unranked -- no service coverage]")

    print("  Status: " + recruit["status"])

    if show_hidden:
        print("  [HIDDEN] True talent: " + str(recruit["true_talent"]) +
              "  Potential: " + str(recruit["potential_floor"]) +
              "-" + str(recruit["potential_ceiling"]) +
              "  Spike: " + recruit.get("spike_label", "none"))
        primary_sample = {
            "PG": "ball_handling", "SG": "catch_and_shoot",
            "SF": "finishing",     "PF": "rebounding", "C": "rebounding"
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

    ranked = [r for r in recruits if r["is_ranked"]]
    depth  = [r for r in recruits if not r["is_ranked"]]

    print("")
    print("=" * 65)
    print("  " + str(season) + " RECRUITING CLASS  --  " +
          str(len(recruits)) + " prospects")
    print("  Ranked pool: " + str(len(ranked)) +
          "  |  Depth pool: " + str(len(depth)))
    print("=" * 65)

    print("  Star distribution (ranked pool):")
    star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for r in ranked:
        star_counts[r["stars_consensus"]] += 1
    for stars in [5, 4, 3, 2, 1]:
        bar = "█" * min(star_counts[stars], 40)
        print("  " + stars_display(stars) + "  " +
              str(star_counts[stars]).rjust(4) + "  " + bar)

    pos_counts = {p: 0 for p in POSITIONS}
    for r in recruits:
        pos_counts[r["position"]] += 1
    print("")
    print("  Position distribution (full pool): " +
          "  ".join(pos + ": " + str(pos_counts[pos]) for pos in POSITIONS))

    # Spike distribution
    spike_counts = {}
    for r in recruits:
        label = r.get("spike_label", "none")
        spike_counts[label] = spike_counts.get(label, 0) + 1
    top_spikes = sorted(spike_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    print("")
    print("  Top spike types: " +
          "  ".join(label + ": " + str(count) for label, count in top_spikes))

    print("")
    print("  TOP 10 PROSPECTS (ranked pool)")
    print("  " + "-" * 65)
    print("  {:<4} {:<22} {:<5} {:<8} {:<6} {}".format(
        "Rank", "Name", "Pos", "Ht", "State", "Stars"))
    print("  " + "-" * 65)
    for r in ranked[:10]:
        rank_str = str(r["composite_rank"]) if r["composite_rank"] else "NR"
        print("  {:<4} {:<22} {:<5} {:<8} {:<6} {}".format(
            rank_str, r["name"], r["position"],
            format_height(r["height_inches"]),
            r["home_state"],
            stars_display(r["stars_consensus"]),
        ))
        if show_hidden:
            primary_sample = {
                "PG": "ball_handling", "SG": "catch_and_shoot",
                "SF": "finishing",     "PF": "rebounding", "C": "rebounding"
            }.get(r["position"], "finishing")
            raw_val = r.get(primary_sample, 0)
            print("       [true_talent: " + str(r["true_talent"]) +
                  "  potential: " + str(r["potential_floor"]) +
                  "-" + str(r["potential_ceiling"]) +
                  "  spike: " + r.get("spike_label", "none") +
                  "  " + primary_sample + ": " + str(raw_val) +
                  " (" + display_attr(raw_val, "letter") + ")]")

    print("")
    print("  SAMPLE DEPTH POOL PLAYERS (what low-major coaches see)")
    print("  " + "-" * 65)
    sample_depth = random.sample(depth, min(5, len(depth)))
    for r in sample_depth:
        primary_sample = {
            "PG": "ball_handling", "SG": "catch_and_shoot",
            "SF": "finishing",     "PF": "rebounding", "C": "rebounding"
        }.get(r["position"], "finishing")
        raw_val = r.get(primary_sample, 0)
        print("  NR   {:<22} {:<5} {:<8} {:<6} spike: {:<20} {}={}({})".format(
            r["name"], r["position"],
            format_height(r["height_inches"]),
            r["home_state"],
            r.get("spike_label", "none"),
            primary_sample, raw_val,
            display_attr(raw_val, "letter"),
        ))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("Generating 2025 recruiting class (v0.6 -- 4500 prospects)...")
    recruits_2025 = generate_recruiting_class(season=2025)

    print_class_summary(recruits_2025, season=2025, show_hidden=True)

    print("")
    print("=" * 65)
    print("  POOL COMPOSITION VERIFICATION")
    print("=" * 65)
    ranked = [r for r in recruits_2025 if r["is_ranked"]]
    depth  = [r for r in recruits_2025 if not r["is_ranked"]]
    print("  Total pool:    " + str(len(recruits_2025)))
    print("  Ranked pool:   " + str(len(ranked)) + "  (target: 1500)")
    print("  Depth pool:    " + str(len(depth))  + "  (target: 3000)")
    print("  With rank #:   " + str(sum(1 for r in recruits_2025
                                        if r["composite_rank"] is not None)))
    print("  NR (unranked): " + str(sum(1 for r in recruits_2025
                                        if r["composite_rank"] is None)))

    print("")
    print("=" * 65)
    print("  HEIGHT-DRIVEN ATHLETICISM CHECK")
    print("  Taller players should have lower speed/explosiveness")
    print("=" * 65)
    from display import display_attr
    print("  {:<8} {:<10} {:<8} {:<8} {:<8}".format(
        "Height", "Position", "Speed", "Explo", "Strength"))
    print("  " + "-" * 50)
    height_sample = sorted(
        [r for r in recruits_2025 if r["is_ranked"]][:200],
        key=lambda r: r["height_inches"]
    )
    # Show bottom 5 (shortest) and top 5 (tallest)
    for r in height_sample[:5] + height_sample[-5:]:
        print("  {:<8} {:<10} {:<8} {:<8} {:<8}".format(
            format_height(r["height_inches"]),
            r["position"],
            display_attr(r.get("speed", 400), "1-20"),
            display_attr(r.get("explosiveness", 400), "1-20"),
            display_attr(r.get("strength", 400), "1-20"),
        ))

    print("")
    print("=" * 65)
    print("  OUTLIER AND GENERATIONAL TALENT CHECK")
    print("  Running 50 seasons to surface rare events...")
    print("=" * 65)

    short_outliers  = []
    tall_noskill    = []
    tall_skilled    = []
    phenoms         = []
    late_bloomers   = []

    for season_n in range(2025, 2075):
        class_n = generate_recruiting_class(season=season_n)
        for r in class_n:
            ot = r.get("outlier_type")
            gt = r.get("generational_talent")
            if ot == "short":         short_outliers.append((season_n, r))
            elif ot == "tall_noskill": tall_noskill.append((season_n, r))
            elif ot == "tall_skill":   tall_skilled.append((season_n, r))
            if gt == "phenom":                    phenoms.append((season_n, r))
            elif gt == "late_bloomer_generational": late_bloomers.append((season_n, r))

    print("")
    print("  Over 50 seasons (~{} recruits):".format(50 * 4500))
    print("  Short outliers (5'4\"-5'8\"):     " + str(len(short_outliers)))
    print("  Tall no-skill  (7'3\"-7'5\"):     " + str(len(tall_noskill)))
    print("  Tall skilled   (7'3\"-7'5\"):     " + str(len(tall_skilled)))
    print("  Phenoms:                         " + str(len(phenoms)))
    print("  Late bloomer generationals:      " + str(len(late_bloomers)))

    if short_outliers:
        print("")
        print("  SHORT OUTLIERS:")
        for yr, r in short_outliers[:4]:
            print("  " + str(yr) + "  " + r["name"].ljust(22) +
                  r["position"] + "  " + format_height(r["height_inches"]) +
                  "  tt:" + str(r["true_talent"]) +
                  "  nat:" + r.get("natural_position", "?"))

    if tall_noskill:
        print("")
        print("  TALL NO-SKILL (space fillers):")
        for yr, r in tall_noskill[:4]:
            print("  " + str(yr) + "  " + r["name"].ljust(22) +
                  r["position"] + "  " + format_height(r["height_inches"]) +
                  "  tt:" + str(r["true_talent"]) +
                  "  reb:" + str(r.get("rebounding", 0)) +
                  "  spd:" + str(r.get("speed", 0)))

    if tall_skilled:
        print("")
        print("  TALL SKILLED (rare events):")
        for yr, r in tall_skilled:
            print("  " + str(yr) + "  " + r["name"].ljust(22) +
                  r["position"] + "  " + format_height(r["height_inches"]) +
                  "  tt:" + str(r["true_talent"]) +
                  "  reb:" + str(r.get("rebounding", 0)) +
                  "  post:" + str(r.get("post_scoring", 0)) +
                  "  spd:" + str(r.get("speed", 0)) + " (penalized)")

    if phenoms:
        print("")
        print("  PHENOMS (generational):")
        for yr, r in phenoms:
            print("  " + str(yr) + "  " + r["name"].ljust(22) +
                  r["position"] + "  " + format_height(r["height_inches"]) +
                  "  " + stars_display(r["stars_consensus"]) +
                  "  tt:" + str(r["true_talent"]) +
                  "  ceil:" + str(r["potential_ceiling"]) +
                  "  nat:" + r.get("natural_position", "?"))

    if late_bloomers:
        print("")
        print("  LATE BLOOMER GENERATIONALS (hidden talent):")
        for yr, r in late_bloomers:
            print("  " + str(yr) + "  " + r["name"].ljust(22) +
                  r["position"] + "  " + stars_display(r["stars_consensus"]) +
                  "  visible tt:" + str(r["true_talent"]) +
                  "  true ceil:" + str(r["potential_ceiling"]) +
                  "  arc:" + r.get("arc_type", "?"))

    if not phenoms and not late_bloomers:
        print("")
        print("  No generational talents this run -- expected at these rates.")
        print("  Expand to 200+ seasons to reliably surface them.")

    print_class_summary(recruits_2025, season=2025, show_hidden=True)

    print("")
    print("=" * 65)
    print("  POOL COMPOSITION VERIFICATION")
    print("=" * 65)
    ranked = [r for r in recruits_2025 if r["is_ranked"]]
    depth  = [r for r in recruits_2025 if not r["is_ranked"]]
    print("  Total pool:    " + str(len(recruits_2025)))
    print("  Ranked pool:   " + str(len(ranked)) + "  (target: 1500)")
    print("  Depth pool:    " + str(len(depth))  + "  (target: 3000)")
    print("  With rank #:   " + str(sum(1 for r in recruits_2025
                                        if r["composite_rank"] is not None)))
    print("  NR (unranked): " + str(sum(1 for r in recruits_2025
                                        if r["composite_rank"] is None)))

    print("")
    print("=" * 65)
    print("  SPIKE DISTRIBUTION VERIFICATION")
    print("  Verifying weighted selection and paired attribute guarantee")
    print("=" * 65)

    from display import display_attr

    # Check spike type distribution by position
    for pos in POSITIONS:
        pos_recruits = [r for r in recruits_2025 if r["position"] == pos]
        spike_counts = {}
        for r in pos_recruits:
            label = r.get("spike_label", "none")
            spike_counts[label] = spike_counts.get(label, 0) + 1
        total = len(pos_recruits)
        print("")
        print("  " + pos + " spike distribution (" + str(total) + " players):")
        for label, count in sorted(spike_counts.items(),
                                   key=lambda x: x[1], reverse=True):
            pct = round(count / total * 100, 1)
            bar = "█" * int(pct / 2)
            print("    {:<22} {:>4}  ({:>5}%)  {}".format(
                label, count, pct, bar))

    # Verify paired attribute guarantee
    print("")
    print("=" * 65)
    print("  PAIRED ATTRIBUTE GUARANTEE CHECK")
    print("  Both qualifying attrs should clear spike_min for ranked players")
    print("=" * 65)

    failures = 0
    checked  = 0
    for r in [x for x in recruits_2025 if x["is_ranked"]]:
        label    = r.get("spike_label", "none")
        position = r["position"]
        specs    = SPIKE_SPECIALIZATIONS.get(position, [])
        spec     = next((s for s in specs if s[0] == label), None)
        if not spec:
            continue
        spike_attrs = spec[1]
        if len(spike_attrs) < 2:
            continue
        # Determine expected spike_min for this player
        tt = r["true_talent"]
        if tt < 35:
            spike_min = 700
        elif tt < 55:
            spike_min = 680
        else:
            spike_min = 720
        # Check both qualifying attrs
        attr1, attr2 = spike_attrs[0], spike_attrs[1]
        if attr1 in ALL_ATTRIBUTES and attr2 in ALL_ATTRIBUTES:
            val1 = r.get(attr1, 0)
            val2 = r.get(attr2, 0)
            checked += 1
            if val1 < spike_min or val2 < spike_min:
                failures += 1

    print("  Checked: " + str(checked) + " ranked recruits")
    print("  Failures (qualifying pair below threshold): " + str(failures))
    if checked > 0:
        print("  Pass rate: " + str(round((checked - failures) / checked * 100, 1)) + "%")
    print("  (Target: 100% -- both qualifying attrs guaranteed above threshold)")

    # Verify stretch restriction for low-talent bigs
    print("")
    print("=" * 65)
    print("  STRETCH BIG RESTRICTION CHECK")
    print("  Bigs below talent " + str(STRETCH_MIN_TALENT) +
          " should have 0% stretch_four")
    print("=" * 65)
    low_pf = [r for r in recruits_2025
              if r["position"] in ("PF", "C")
              and r["true_talent"] < STRETCH_MIN_TALENT
              and r["is_ranked"]]
    stretch_count = sum(1 for r in low_pf
                        if r.get("spike_label") == "stretch_four")
    print("  Low-talent PF/C checked: " + str(len(low_pf)))
    print("  stretch_four spikes found: " + str(stretch_count) +
          "  (target: 0)")
