# -----------------------------------------
# COLLEGE HOOPS SIM -- Display Layer v1.0
# System 9 of the Design Bible
#
# THE ONLY FILE THAT KNOWS ABOUT DISPLAY FORMATS.
#
# All player attributes are stored internally on a 1-1000 scale.
# This module is the single translation point between internal values
# and whatever the human player sees on screen.
#
# SUPPORTED DISPLAY MODES:
#   "1-10"    --  1 through 10 (casual, simple)
#   "1-20"    --  1 through 20 (classic sim, FM style)
#   "1-100"   --  1 through 100 (granular, OOTP style)
#   "letter"  --  A+ through F  (scouting report style)
#   "stars"   --  1-5 stars     (recruiting service style)
#
# SCOUTING NOISE (future hook):
#   display_attr() accepts an optional noise parameter.
#   When the UI is built, pass in a noise value derived from
#   the scout's competence rating. The true internal value is
#   never modified -- only the displayed value is perturbed.
#   A great scout (noise=0) shows exactly what the player is.
#   A bad scout (noise=120) might show a 620 player as 510 or 730.
#
# USAGE:
#   from display import display_attr, display_attr_raw
#
#   # Get formatted string for UI
#   display_attr(player["finishing"], mode="letter")     --> "B+"
#   display_attr(player["finishing"], mode="1-20")       --> "14"
#   display_attr(player["finishing"], mode="stars")      --> "★★★☆☆"
#
#   # Get raw converted number (for math, not display)
#   display_attr_raw(player["finishing"], mode="1-20")   --> 14
#
# IMPORTANT: Never use display values for game calculations.
#   Always use the raw 1-1000 internal value in game_engine.py,
#   develop_player(), and all simulation logic.
# -----------------------------------------

import random

# Default mode -- change this when the settings screen is built
DEFAULT_MODE = "letter"

# -----------------------------------------
# LETTER GRADE BOUNDARIES
# On 1-1000 scale
# -----------------------------------------

LETTER_GRADES = [
    (970, "A+"),
    (920, "A"),
    (880, "A-"),
    (830, "B+"),
    (780, "B"),
    (730, "B-"),
    (670, "C+"),
    (610, "C"),
    (550, "C-"),
    (480, "D+"),
    (400, "D"),
    (300, "D-"),
    (  1, "F"),
]


# -----------------------------------------
# CORE CONVERSION FUNCTIONS
# -----------------------------------------

def display_attr(internal_value, mode=None, noise=0):
    """
    Converts a 1-1000 internal attribute value to a display string.

    internal_value  -- raw 1-1000 attribute (int or float)
    mode            -- display format string, or None to use DEFAULT_MODE
    noise           -- scouting uncertainty range (FUTURE HOOK).
                       Pass 0 for true value (staff view, debug).
                       Pass a positive int for scout uncertainty window.
                       Example: noise=80 means the displayed value could
                       be up to +/-80 from true value.

    Returns a string ready for display.
    """
    if mode is None:
        mode = DEFAULT_MODE

    value = _apply_noise(int(internal_value), noise)

    if mode == "1-10":
        converted = _to_1_10(value)
        return str(converted)

    elif mode == "1-20":
        converted = _to_1_20(value)
        return str(converted)

    elif mode == "1-100":
        converted = _to_1_100(value)
        return str(converted)

    elif mode == "letter":
        return _to_letter(value)

    elif mode == "stars":
        star_count = _to_stars(value)
        return "★" * star_count + "☆" * (5 - star_count)

    else:
        # Unknown mode -- fall back to raw internal value
        return str(int(internal_value))


def display_attr_raw(internal_value, mode=None, noise=0):
    """
    Returns the converted numeric value without formatting.
    Use this when you need a number for sorting, math, or comparison
    in the UI layer (never in simulation logic).

    Returns an int.
    """
    if mode is None:
        mode = DEFAULT_MODE

    value = _apply_noise(int(internal_value), noise)

    if mode == "1-10":
        return _to_1_10(value)
    elif mode == "1-20":
        return _to_1_20(value)
    elif mode == "1-100":
        return _to_1_100(value)
    elif mode == "stars":
        return _to_stars(value)
    else:
        # letter and unknown modes return internal value as int
        return int(internal_value)


def display_player_card(player, mode=None, scouted=False, scout_noise=0):
    """
    Returns a dict of all displayable attributes for a player.
    Used to build UI cards, roster screens, scouting reports.

    scouted     -- if True, applies scout_noise to all skill attributes
    scout_noise -- noise window (0 = perfect knowledge)

    Mental attributes (work_ethic, coachability, etc.) are on 1-20
    and displayed as-is -- they are not on the 1-1000 scale.
    """
    noise = scout_noise if scouted else 0

    skill_attrs = [
        "catch_and_shoot", "off_dribble", "mid_range", "three_point",
        "free_throw", "finishing", "post_scoring",
        "passing", "ball_handling", "court_vision", "decision_making",
        "on_ball_defense", "help_defense", "rebounding", "shot_blocking",
        "steal_tendency", "foul_tendency",
        "speed", "lateral_quickness", "strength", "vertical",
        "explosiveness", "agility",
    ]

    mental_attrs = [
        "basketball_iq", "clutch", "composure", "coachability",
        "work_ethic", "leadership",
        "ball_dominance", "usage_tendency", "off_ball_movement",
    ]

    card = {
        "name":             player.get("name", "Unknown"),
        "position":         player.get("position", "?"),
        "natural_position": player.get("natural_position", "?"),
        "year":             player.get("year", "?"),
        "heritage":         player.get("heritage", ""),
        "height":   display_height(player.get("height", 74)),
        "wingspan": display_wingspan(
                        player.get("wingspan", 74),
                        compare_to_height=player.get("height", 74)
                    ),
        "weight":   display_weight(player.get("weight", 200)),
    }

    for attr in skill_attrs:
        raw = player.get(attr, 500)
        card[attr] = display_attr(raw, mode=mode, noise=noise)

    # Mental attributes are 1-20, displayed directly (no conversion)
    for attr in mental_attrs:
        card[attr] = str(player.get(attr, 10)) + "/20"

    # Potential -- shown as letter range if scouted, hidden if not
    if not scouted:
        card["potential"] = "?"
    else:
        p_low  = player.get("potential_low",  30)
        p_high = player.get("potential_high", 60)
        card["potential"] = _to_letter_from_potential(p_low, p_high)

    return card


# -----------------------------------------
# CONVERSION HELPERS
# -----------------------------------------

def _to_1_10(value):
    """Maps 1-1000 to 1-10."""
    return max(1, min(10, round(value / 100)))


def _to_1_20(value):
    """Maps 1-1000 to 1-20."""
    return max(1, min(20, round(value / 50)))


def _to_1_100(value):
    """Maps 1-1000 to 1-100."""
    return max(1, min(100, round(value / 10)))


def _to_letter(value):
    """Maps 1-1000 to letter grade string."""
    for threshold, grade in LETTER_GRADES:
        if value >= threshold:
            return grade
    return "F"


def _to_stars(value):
    """Maps 1-1000 to 1-5 stars."""
    if value >= 850: return 5
    if value >= 700: return 4
    if value >= 550: return 3
    if value >= 380: return 2
    return 1


def _apply_noise(value, noise):
    """
    Applies scouting uncertainty to an internal value.
    FUTURE HOOK -- currently only called when noise > 0.

    The displayed value is perturbed by up to +/- noise,
    but clamped to 1-1000. The true internal value is never changed.
    """
    if noise <= 0:
        return value
    perturbation = random.randint(-noise, noise)
    return max(1, min(1000, value + perturbation))


def _to_letter_from_potential(potential_low, potential_high):
    """
    Converts a potential range (both on 1-100 talent scale) to a
    display string showing the ceiling letter grade.
    Example: potential_high=75 --> ceiling displayed as "B" range
    """
    # Convert 1-100 potential to approximate 1-1000 attr ceiling
    # using the same formula as _potential_to_attr_ceiling() in player.py
    ceiling_1000 = int(200 + (potential_high / 100.0) * 750)
    return _to_letter(ceiling_1000)


# -----------------------------------------
# PHYSICAL SIZE DISPLAY (v0.8)
# height and wingspan stored as inches.
# weight stored as lbs.
# These are NOT on the 1-1000 scale -- displayed as real units.
# -----------------------------------------

def display_height(inches):
    """
    Converts inches to feet'inches" string.
    Example: 79 -> "6'7\""
    """
    feet   = int(inches) // 12
    remain = int(inches) % 12
    return str(feet) + "'" + str(remain) + '"'


def display_wingspan(inches, compare_to_height=None):
    """
    Converts wingspan inches to display string.
    If compare_to_height is provided, appends a length note.

    Example:
      display_wingspan(82)              -> "6'10\""
      display_wingspan(82, 78)          -> "6'10\" (long)"
      display_wingspan(76, 78)          -> "6'4\" (short arms)"
    """
    base = display_height(inches)
    if compare_to_height is None:
        return base

    diff = inches - compare_to_height
    if diff >= 4:
        return base + " (long)"
    elif diff <= -2:
        return base + " (short arms)"
    else:
        return base


def display_weight(lbs):
    """Returns weight as a lbs string. Example: 215 -> '215 lbs'"""
    return str(int(lbs)) + " lbs"


def display_physical_line(player):
    """
    Returns a compact one-line physical summary for roster displays.
    Example: "6'4\"  6'6\" (long)  195 lbs  [guard/wing]"
    """
    h  = player.get("height",   74)
    ws = player.get("wingspan", 74)
    w  = player.get("weight",   200)
    np = player.get("natural_position", "?")
    return (display_height(h) + "  " +
            display_wingspan(ws, compare_to_height=h) + "  " +
            display_weight(w) + "  [" + np + "]")


# -----------------------------------------
# CONVENIENCE: DISPLAY A FULL ROSTER TABLE
# -----------------------------------------

def print_roster_display(program, mode=None):
    """
    Prints a human-readable roster in the chosen display mode.
    Uses display_attr() so it always reflects the current mode.
    """
    if mode is None:
        mode = DEFAULT_MODE

    roster = program.get("roster", [])
    name   = program.get("name", "Unknown")

    print("")
    print("=== " + name + " Roster (" + mode + " display) ===")
    print("{:<22} {:<5} {:<12} {:<6} {:<6} {:<6} {:<6} {:<6}".format(
        "Name", "Pos", "Year", "Shoot", "Pass", "Def", "Reb", "Ath"
    ))
    print("-" * 75)

    for p in roster:
        shoot = display_attr_raw(
            (p.get("catch_and_shoot", 500) + p.get("finishing", 500) +
             p.get("three_point", 500)) / 3, mode=mode)
        pass_ = display_attr_raw(
            (p.get("passing", 500) + p.get("ball_handling", 500)) / 2, mode=mode)
        def_  = display_attr_raw(
            (p.get("on_ball_defense", 500) + p.get("help_defense", 500)) / 2, mode=mode)
        reb   = display_attr_raw(p.get("rebounding", 500), mode=mode)
        ath   = display_attr_raw(
            (p.get("speed", 500) + p.get("vertical", 500)) / 2, mode=mode)

        print("{:<22} {:<5} {:<12} {:<6} {:<6} {:<6} {:<6} {:<6}".format(
            p.get("name", "?")[:21],
            p.get("position", "?"),
            p.get("year", "?"),
            str(shoot), str(pass_), str(def_), str(reb), str(ath)
        ))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("=" * 65)
    print("  DISPLAY LAYER v1.0 -- CONVERSION TEST")
    print("=" * 65)

    test_values = [
        (980, "All-time great"),
        (950, "Superstar / top draft pick"),
        (860, "High-major star"),
        (780, "High-major solid starter"),
        (700, "Mid-major star"),
        (620, "Solid D1 player"),
        (550, "Fringe D1 primary attribute"),
        (400, "Below average"),
        (280, "Floor attribute (can't do this)"),
        (150, "True floor"),
    ]

    print("")
    print("{:<10} {:<30} {:<8} {:<8} {:<8} {:<8} {:<8}".format(
        "Internal", "Description", "1-10", "1-20", "1-100", "Letter", "Stars"
    ))
    print("-" * 78)

    for val, desc in test_values:
        print("{:<10} {:<30} {:<8} {:<8} {:<8} {:<8} {:<8}".format(
            val,
            desc,
            display_attr(val, "1-10"),
            display_attr(val, "1-20"),
            display_attr(val, "1-100"),
            display_attr(val, "letter"),
            display_attr(val, "stars"),
        ))

    print("")
    print("=" * 65)
    print("  SCOUTING NOISE TEST -- same player, different scout quality")
    print("=" * 65)
    true_value = 720
    print("True internal value: " + str(true_value) + "  (" + display_attr(true_value, "letter") + ")")
    print("")
    print("{:<25} {:<15} {:<15}".format("Scout quality", "Displayed (letter)", "Displayed (1-20)"))
    print("-" * 55)
    for label, noise in [
        ("Elite scout (noise=0)",    0),
        ("Good scout (noise=40)",   40),
        ("Average scout (noise=80)", 80),
        ("Bad scout (noise=150)",  150),
    ]:
        random.seed(42)
        print("{:<25} {:<15} {:<15}".format(
            label,
            display_attr(true_value, "letter", noise=noise),
            display_attr(true_value, "1-20",   noise=noise),
        ))
