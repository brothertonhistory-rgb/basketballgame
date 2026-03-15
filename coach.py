# -----------------------------------------
# COLLEGE HOOPS SIM -- Coaching Philosophy v0.3
#
# A coach has five layers:
#
#   1. IDENTITY
#      name, archetype, experience, legacy
#
#   2. PHILOSOPHY SLIDERS (1-100 each)
#      Where on each spectrum this coach lives.
#      These never change much -- they are who he is.
#
#      OFFENSIVE:
#        pace            1=grind              100=40 min of hell
#        shot_profile    1=exploit mid-range  100=rim and 3 only
#        ball_movement   1=ISO heavy          100=ball movement
#        shot_selection  1=first decent look  100=work for best shot
#        personnel       1=traditional 5 pos  100=positionless
#        off_rebounding  1=get back on D      100=crash every miss
#
#      DEFENSIVE:
#        pressure        1=set defense        100=full court pressure
#        philosophy      1=contain/pack line  100=gamble/trap/steals
#        def_rebounding  1=leak out           100=crash defensive glass
#        screen_defense  1=switch everything  100=fight through screens
#        zone_tendency   1=pure man           100=zone heavy
#
#      LATE GAME:
#        late_game       1=draw set play      100=star iso
#
#   3. COMPETENCE RATINGS (1-20 each)
#      How GOOD he is at what he does.
#      Two coaches can run the same system -- one runs it well,
#      one runs it into the ground.
#
#        offensive_skill       -- executes his offensive system
#        defensive_skill       -- executes his defensive system
#        player_development    -- players improve under him
#        tactics               -- game prep, situational execution,
#                                 set plays, adjustments
#        in_game_adaptability  -- adjusts when things aren't working
#                                 mid-game. Low = sticks to gameplan
#                                 regardless. High = reads and reacts.
#        scheme_adaptability   -- reshapes system for his personnel
#                                 over seasons. Low = forces players
#                                 into his system. High = builds around
#                                 what walked in the door.
#        recruiting_attraction -- pulling power. Gets in the door with
#                                 elite recruits. Sells the vision.
#        roster_fit            -- identifies which recruit fills which
#                                 role. Not finding gems, finding the
#                                 right piece for the right slot.
#
#   4. ROSTER CONSTRUCTION
#      How he thinks about building a complete roster.
#
#        rotation_size         -- how many players he trusts (6-11)
#                                 influenced by pace, with variance
#        slot_strictness       -- how specific he is about depth roles
#                                 1=just give me athletes
#                                 10=my 12th man MUST be an energy big
#        talent_vs_fit         -- already in values_role_players
#
#   5. ROSTER VALUES (1-10 each)
#      What he looks for when evaluating recruits.
#      Derived from his sliders with noise.
#
#        values_athleticism, values_iq, values_size,
#        values_shooting, values_defense, values_toughness,
#        values_role_players
#
# v0.4 CHANGES:
#   - calculate_style_fit() updated to normalize player skill attributes
#     against 1000 instead of 20. All style fit scores (0-100) are
#     equivalent to v0.3 at the mean. Only the denominator changed.
#   - _scale_attr() helper added for 1-1000 player attribute scaling.
#   - Coach competence ratings STAY 1-20. Intentional.
#
# v0.3 CHANGES:
#   - _generate_competence() bonus now capped at 3 (was uncapped, causing
#     multiple coaches to max out at 20/20 at elite programs)
# -----------------------------------------

import random

# -----------------------------------------
# ARCHETYPE TEMPLATES
# Internal only -- never shown to human player.
# Each generated coach gets gaussian noise applied
# so no two coaches are identical.
# -----------------------------------------

COACH_ARCHETYPES = {

    "grinder": {
        # Izzo, Mick Cronin, Tony Bennett
        "pace": 20, "shot_profile": 35, "ball_movement": 40,
        "shot_selection": 75, "personnel": 30, "off_rebounding": 70,
        "pressure": 30, "philosophy": 25, "def_rebounding": 80,
        "screen_defense": 70, "zone_tendency": 20, "late_game": 35,
        # Competence tendencies
        "offensive_skill": 13, "defensive_skill": 16,
        "player_development": 14, "tactics": 15,
        "in_game_adaptability": 9, "scheme_adaptability": 7,
        "recruiting_attraction": 12, "roster_fit": 15,
        # Roster construction
        "rotation_size_bias": -1,   # tends to play fewer
        "slot_strictness_bias": 3,  # pretty specific about roles
        "rotation_flexibility_bias": 2,  # fairly rigid rotation
    },

    "pace_and_space": {
        # Calipari, Nate Oats, Fred Hoiberg
        "pace": 85, "shot_profile": 80, "ball_movement": 55,
        "shot_selection": 35, "personnel": 80, "off_rebounding": 35,
        "pressure": 55, "philosophy": 60, "def_rebounding": 40,
        "screen_defense": 30, "zone_tendency": 25, "late_game": 70,
        "offensive_skill": 16, "defensive_skill": 12,
        "player_development": 13, "tactics": 13,
        "in_game_adaptability": 12, "scheme_adaptability": 11,
        "recruiting_attraction": 17, "roster_fit": 10,
        "rotation_size_bias": 2,    # tends to go deeper
        "slot_strictness_bias": -2, # talent over role
        "rotation_flexibility_bias": 7,  # rides hot hands
    },

    "princeton_style": {
        # Pete Carril disciples, patient, high IQ
        "pace": 15, "shot_profile": 30, "ball_movement": 85,
        "shot_selection": 90, "personnel": 45, "off_rebounding": 40,
        "pressure": 20, "philosophy": 20, "def_rebounding": 55,
        "screen_defense": 65, "zone_tendency": 30, "late_game": 25,
        "offensive_skill": 15, "defensive_skill": 13,
        "player_development": 16, "tactics": 17,
        "in_game_adaptability": 11, "scheme_adaptability": 8,
        "recruiting_attraction": 10, "roster_fit": 17,
        "rotation_size_bias": -2,   # plays tight rotation
        "slot_strictness_bias": 4,  # very specific roles
        "rotation_flexibility_bias": 2,  # rigid, system is everything
    },

    "motion_offense": {
        # Dean Smith tradition, ball movement, team first
        "pace": 55, "shot_profile": 45, "ball_movement": 80,
        "shot_selection": 70, "personnel": 50, "off_rebounding": 50,
        "pressure": 40, "philosophy": 35, "def_rebounding": 60,
        "screen_defense": 60, "zone_tendency": 25, "late_game": 30,
        "offensive_skill": 15, "defensive_skill": 14,
        "player_development": 15, "tactics": 14,
        "in_game_adaptability": 13, "scheme_adaptability": 13,
        "recruiting_attraction": 13, "roster_fit": 14,
        "rotation_size_bias": 0,
        "slot_strictness_bias": 1,
        "rotation_flexibility_bias": 5,  # balanced
    },

    "dribble_drive": {
        # Calipari Memphis era, attack the paint
        "pace": 75, "shot_profile": 70, "ball_movement": 35,
        "shot_selection": 30, "personnel": 70, "off_rebounding": 45,
        "pressure": 60, "philosophy": 55, "def_rebounding": 45,
        "screen_defense": 35, "zone_tendency": 20, "late_game": 80,
        "offensive_skill": 15, "defensive_skill": 13,
        "player_development": 12, "tactics": 12,
        "in_game_adaptability": 11, "scheme_adaptability": 10,
        "recruiting_attraction": 14, "roster_fit": 11,
        "rotation_size_bias": 1,
        "slot_strictness_bias": -1,
        "rotation_flexibility_bias": 7,  # rides hot hands, star driven
    },

    "post_centric": {
        # Matt Painter, traditional big man offense
        "pace": 35, "shot_profile": 25, "ball_movement": 50,
        "shot_selection": 65, "personnel": 20, "off_rebounding": 65,
        "pressure": 35, "philosophy": 30, "def_rebounding": 75,
        "screen_defense": 65, "zone_tendency": 30, "late_game": 40,
        "offensive_skill": 14, "defensive_skill": 14,
        "player_development": 15, "tactics": 14,
        "in_game_adaptability": 10, "scheme_adaptability": 8,
        "recruiting_attraction": 12, "roster_fit": 15,
        "rotation_size_bias": -1,
        "slot_strictness_bias": 3,
        "rotation_flexibility_bias": 3,  # fairly rigid, knows his guys
    },

    "pressure_defense": {
        # Rick Pitino, Billy Donovan, press and gamble
        "pace": 70, "shot_profile": 60, "ball_movement": 50,
        "shot_selection": 40, "personnel": 60, "off_rebounding": 35,
        "pressure": 90, "philosophy": 85, "def_rebounding": 40,
        "screen_defense": 25, "zone_tendency": 45, "late_game": 55,
        "offensive_skill": 14, "defensive_skill": 17,
        "player_development": 13, "tactics": 15,
        "in_game_adaptability": 14, "scheme_adaptability": 12,
        "recruiting_attraction": 15, "roster_fit": 12,
        "rotation_size_bias": 2,    # needs depth for press
        "slot_strictness_bias": 1,
        "rotation_flexibility_bias": 7,  # must rotate fresh legs for press
    },

    "zone_specialist": {
        # Jim Boeheim, 2-3 zone identity
        "pace": 40, "shot_profile": 40, "ball_movement": 55,
        "shot_selection": 60, "personnel": 35, "off_rebounding": 55,
        "pressure": 35, "philosophy": 40, "def_rebounding": 65,
        "screen_defense": 50, "zone_tendency": 90, "late_game": 40,
        "offensive_skill": 14, "defensive_skill": 16,
        "player_development": 14, "tactics": 15,
        "in_game_adaptability": 9, "scheme_adaptability": 7,
        "recruiting_attraction": 13, "roster_fit": 14,
        "rotation_size_bias": -1,
        "slot_strictness_bias": 2,
        "rotation_flexibility_bias": 2,  # rigid, zone is the system
    },

    "analytics_modern": {
        # Modern analytics coaches, rim or 3, switch everything
        "pace": 65, "shot_profile": 90, "ball_movement": 65,
        "shot_selection": 55, "personnel": 85, "off_rebounding": 30,
        "pressure": 45, "philosophy": 50, "def_rebounding": 35,
        "screen_defense": 20, "zone_tendency": 20, "late_game": 50,
        "offensive_skill": 15, "defensive_skill": 14,
        "player_development": 13, "tactics": 14,
        "in_game_adaptability": 14, "scheme_adaptability": 15,
        "recruiting_attraction": 13, "roster_fit": 16,
        "rotation_size_bias": 1,
        "slot_strictness_bias": 0,
        "rotation_flexibility_bias": 6,  # data driven, reacts to matchups
    },

    "wildcard": {
        # Unpredictable, hard to scout
        "pace": 50, "shot_profile": 50, "ball_movement": 50,
        "shot_selection": 50, "personnel": 50, "off_rebounding": 50,
        "pressure": 50, "philosophy": 50, "def_rebounding": 50,
        "screen_defense": 50, "zone_tendency": 50, "late_game": 50,
        "offensive_skill": 11, "defensive_skill": 11,
        "player_development": 11, "tactics": 11,
        "in_game_adaptability": 11, "scheme_adaptability": 11,
        "recruiting_attraction": 11, "roster_fit": 11,
        "rotation_size_bias": 0,
        "slot_strictness_bias": 0,
        "rotation_flexibility_bias": 5,
    },
}

ARCHETYPE_WEIGHTS = {
    "grinder":          18,
    "pace_and_space":   14,
    "princeton_style":   6,
    "motion_offense":   16,
    "dribble_drive":    12,
    "post_centric":      8,
    "pressure_defense":  8,
    "zone_specialist":   6,
    "analytics_modern": 10,
    "wildcard":          2,
}

SLIDER_NOISE      = 12
COMPETENCE_NOISE  = 2


# -----------------------------------------
# HELPERS
# -----------------------------------------

def _pick_archetype():
    """Weighted random archetype selection."""
    archetypes = list(ARCHETYPE_WEIGHTS.keys())
    weights    = list(ARCHETYPE_WEIGHTS.values())
    return random.choices(archetypes, weights=weights, k=1)[0]


def _slider(base, noise=SLIDER_NOISE):
    """Applies gaussian noise to a base slider value. Clamps 1-100."""
    val = int(random.gauss(base, noise))
    return max(1, min(100, val))


def _scale(val, lo, hi):
    """Scales a value to 0.0-1.0 range."""
    if hi == lo:
        return 0.0
    return (val - lo) / (hi - lo)


def _scale_attr(val):
    """
    Scales a player skill attribute (1-1000) to 0.0-1.0.
    Used by calculate_style_fit() which reads raw player attributes.
    Replaces the old _scale(val, 1, 20) calls.
    """
    return _scale(val, 1, 1000)


# -----------------------------------------
# MAIN GENERATOR
# -----------------------------------------

def generate_coach(name, prestige=50, archetype=None, experience=None):
    """
    Generates a full coach object.

    name       -- coach name string
    prestige   -- program prestige 1-100, raises competence ceiling
    archetype  -- optional, forces archetype. None = weighted random.
    experience -- optional 0-30 years. None = random.
    """

    if archetype is None:
        archetype = _pick_archetype()
    t = COACH_ARCHETYPES[archetype]

    if experience is None:
        experience = random.randint(0, 25)

    # --- PHILOSOPHY SLIDERS ---
    philosophy = {
        "pace":           _slider(t["pace"]),
        "shot_profile":   _slider(t["shot_profile"]),
        "ball_movement":  _slider(t["ball_movement"]),
        "shot_selection": _slider(t["shot_selection"]),
        "personnel":      _slider(t["personnel"]),
        "off_rebounding": _slider(t["off_rebounding"]),
        "pressure":       _slider(t["pressure"]),
        "philosophy":     _slider(t["philosophy"]),
        "def_rebounding": _slider(t["def_rebounding"]),
        "screen_defense": _slider(t["screen_defense"]),
        "zone_tendency":  _slider(t["zone_tendency"]),
        "late_game":      _slider(t["late_game"]),
    }

    # --- COMPETENCE RATINGS ---
    # Experience adds to ceiling. Prestige programs attract more competent coaches.
    exp_bonus      = min(4, experience // 6)
    prestige_bonus = min(3, prestige // 35)
    competence     = _generate_competence(t, exp_bonus, prestige_bonus)

    # --- ROTATION SIZE ---
    # Base: driven by pace. Fast pace = more players needed.
    pace_driven   = 7 + int((philosophy["pace"] / 100) * 3)   # 7-10 range from pace
    bias          = t["rotation_size_bias"]
    rotation_size = max(6, min(11,
        pace_driven + bias + random.randint(-1, 1)
    ))

    # --- SLOT STRICTNESS ---
    slot_base       = 5 + t["slot_strictness_bias"]
    slot_strictness = max(1, min(10, slot_base + random.randint(-2, 2)))

    # --- ROTATION FLEXIBILITY ---
    # 1 = rigid, plays his 8, strict minute blocks
    # 10 = reactive, rides hot hands, goes deep when trailing
    flex_base            = t.get("rotation_flexibility_bias", 5)
    rotation_flexibility = max(1, min(10, flex_base + random.randint(-2, 2)))

    # --- ROSTER VALUES ---
    roster_values = _generate_roster_values(archetype, philosophy)

    coach = {
        # --- IDENTITY ---
        "name":       name,
        "archetype":  archetype,
        "experience": experience,
        "legacy":     0,

        # --- PHILOSOPHY SLIDERS ---
        "pace":           philosophy["pace"],
        "shot_profile":   philosophy["shot_profile"],
        "ball_movement":  philosophy["ball_movement"],
        "shot_selection": philosophy["shot_selection"],
        "personnel":      philosophy["personnel"],
        "off_rebounding": philosophy["off_rebounding"],
        "pressure":       philosophy["pressure"],
        "philosophy":     philosophy["philosophy"],
        "def_rebounding": philosophy["def_rebounding"],
        "screen_defense": philosophy["screen_defense"],
        "zone_tendency":  philosophy["zone_tendency"],
        "late_game":      philosophy["late_game"],

        # --- COMPETENCE RATINGS (1-20) ---
        "offensive_skill":       competence["offensive_skill"],
        "defensive_skill":       competence["defensive_skill"],
        "player_development":    competence["player_development"],
        "tactics":               competence["tactics"],
        "in_game_adaptability":  competence["in_game_adaptability"],
        "scheme_adaptability":   competence["scheme_adaptability"],
        "recruiting_attraction": competence["recruiting_attraction"],
        "roster_fit":            competence["roster_fit"],

        # --- ROSTER CONSTRUCTION ---
        "rotation_size":        rotation_size,
        "slot_strictness":      slot_strictness,
        "rotation_flexibility": rotation_flexibility,

        # --- ROSTER VALUES (1-10) ---
        "values_athleticism":  roster_values["athleticism"],
        "values_iq":           roster_values["iq"],
        "values_size":         roster_values["size"],
        "values_shooting":     roster_values["shooting"],
        "values_defense":      roster_values["defense"],
        "values_toughness":    roster_values["toughness"],
        "values_role_players": roster_values["role_players"],

        # --- SEASON STATE ---
        "seasons_at_program": 0,
        "career_wins":        0,
        "career_losses":      0,
    }

    return coach


# -----------------------------------------
# COMPETENCE GENERATOR
# -----------------------------------------

def _generate_competence(template, exp_bonus, prestige_bonus):
    """
    Generates competence ratings 1-20.
    Each archetype has baseline tendencies.
    Experience and prestige raise the ceiling slightly.
    Noise ensures no two coaches are identical.

    v0.3: Total bonus capped at 3 to prevent elite-program coaches
    from systematically maxing out multiple ratings at 20/20.
    Archetype bases for elite archetypes are already 15-17; adding
    a full 7-point bonus was causing most power-conference coaches
    to hit the ceiling on their primary competencies.
    """
    # Cap total bonus at 3 -- prestige attracts better coaches but
    # doesn't guarantee a roster full of maxed-out ratings
    bonus = min(3, exp_bonus + prestige_bonus)

    ratings = {}
    competence_keys = [
        "offensive_skill", "defensive_skill", "player_development",
        "tactics", "in_game_adaptability", "scheme_adaptability",
        "recruiting_attraction", "roster_fit",
    ]

    for key in competence_keys:
        base = template.get(key, 11)
        val  = int(random.gauss(base + bonus, COMPETENCE_NOISE))
        ratings[key] = max(1, min(20, val))

    return ratings


# -----------------------------------------
# ROSTER VALUES GENERATOR
# -----------------------------------------

def _generate_roster_values(archetype, philosophy):
    """
    What this coach values in recruits.
    Derived from his philosophy sliders.
    """
    def clamp(val):
        return max(1, min(10, val + random.randint(-1, 2)))

    athleticism  = clamp(int((philosophy["pace"] + philosophy["personnel"]) / 20))
    iq           = clamp(int((philosophy["shot_selection"] + philosophy["ball_movement"]) / 20))
    size         = clamp(10 - int(philosophy["personnel"] / 14))
    shooting     = clamp(int(philosophy["shot_profile"] / 11))
    defense      = clamp(int((philosophy["pressure"] + philosophy["philosophy"]) / 20))
    toughness    = clamp(int((philosophy["off_rebounding"] + philosophy["def_rebounding"]) / 20))

    role_archetypes = [
        "grinder", "princeton_style", "motion_offense",
        "post_centric", "zone_specialist"
    ]
    role_base    = 7 if archetype in role_archetypes else 4
    role_players = max(1, min(10, role_base + random.randint(-2, 2)))

    return {
        "athleticism":  athleticism,
        "iq":           iq,
        "size":         size,
        "shooting":     shooting,
        "defense":      defense,
        "toughness":    toughness,
        "role_players": role_players,
    }


# -----------------------------------------
# STYLE FIT
# How well a player's attributes fit this coach's system
# Returns 0-100. Used in recruiting interest calculation.
# -----------------------------------------

def calculate_style_fit(player, coach):
    """
    Calculates how well a player fits a coach's system.
    A player who fits gets a significant interest boost in recruiting.
    Returns a fit score 0-100.
    """
    fit_points = 0
    checks     = 0

    def contrib(player_val, weight):
        return _scale_attr(player_val) * weight

    # Pace fit -- fast systems need speed
    if coach["pace"] >= 60:
        fit_points += contrib(player.get("speed", 10), coach["pace"] / 100)
        checks += 1

    # Shot profile -- rim and 3 needs finishing and three point
    if coach["shot_profile"] >= 55:
        avg = (player.get("three_point", 10) + player.get("finishing", 10)) / 2
        fit_points += contrib(avg, coach["shot_profile"] / 100)
        checks += 1

    # Ball movement -- motion needs passing and vision
    if coach["ball_movement"] >= 60:
        avg = (player.get("passing", 10) + player.get("court_vision", 10)) / 2
        fit_points += contrib(avg, coach["ball_movement"] / 100)
        checks += 1

    # Personnel -- positionless needs versatility
    if coach["personnel"] >= 65:
        avg = (player.get("ball_handling", 10) + player.get("speed", 10)) / 2
        fit_points += contrib(avg, coach["personnel"] / 100)
        checks += 1

    # Pressure defense -- needs athleticism and steals
    if coach["philosophy"] >= 65:
        avg = (player.get("steal_tendency", 10) + player.get("lateral_quickness", 10)) / 2
        fit_points += contrib(avg, coach["philosophy"] / 100)
        checks += 1

    # Rebounding systems need boards and strength
    if coach["off_rebounding"] >= 65 or coach["def_rebounding"] >= 65:
        avg = (player.get("rebounding", 10) + player.get("strength", 10)) / 2
        fit_points += contrib(avg, 1.0)
        checks += 1

    # Post centric -- needs post scoring and size
    if coach["shot_profile"] <= 35 and coach["personnel"] <= 35:
        avg = (player.get("post_scoring", 10) + player.get("strength", 10)) / 2
        fit_points += contrib(avg, 1.0)
        checks += 1

    if checks == 0:
        return 50

    raw = (fit_points / checks) * 100
    return max(0, min(100, int(raw)))


# -----------------------------------------
# DISPLAY
# -----------------------------------------

def print_coach_profile(coach, show_archetype=False):
    """Prints a full readable coaching profile."""

    def bar(val, width=20):
        filled = int((val / 100) * width)
        return "█" * filled + "░" * (width - filled) + "  " + str(val)

    def stars(val, max_val=20):
        filled = round((val / max_val) * 10)
        return "●" * filled + "○" * (10 - filled) + "  " + str(val) + "/20"

    print("")
    print("=" * 65)
    print("  " + coach["name"])
    if show_archetype:
        print("  Archetype:      " + coach["archetype"])
    print("  Experience:     " + str(coach["experience"]) + " years")
    print("  Rotation size:  " + str(coach["rotation_size"]) + " players")
    print("  Rot flexibility:" + str(coach["rotation_flexibility"]) + "/10  " +
          ("(rides hot hand)" if coach["rotation_flexibility"] >= 7
           else "(rigid blocks)"  if coach["rotation_flexibility"] <= 3
           else "(balanced)"))
    print("  Slot strictness:" + str(coach["slot_strictness"]) + "/10  " +
          ("(builds by role)" if coach["slot_strictness"] >= 7
           else "(stacks talent)" if coach["slot_strictness"] <= 3
           else "(balanced)"))

    print("")
    print("  -- OFFENSE --")
    print("  Pace            slow  " + bar(coach["pace"]) + "  fast")
    print("  Shot Profile    mid   " + bar(coach["shot_profile"]) + "  rim&3")
    print("  Ball Movement   iso   " + bar(coach["ball_movement"]) + "  motion")
    print("  Shot Selection  quick " + bar(coach["shot_selection"]) + "  patient")
    print("  Personnel       trad  " + bar(coach["personnel"]) + "  positionless")
    print("  Off Rebounding  get back " + bar(coach["off_rebounding"]) + "  crash")

    print("")
    print("  -- DEFENSE --")
    print("  Pressure        set   " + bar(coach["pressure"]) + "  press")
    print("  Philosophy      contain " + bar(coach["philosophy"]) + "  gamble")
    print("  Def Rebounding  leak  " + bar(coach["def_rebounding"]) + "  crash")
    print("  Screen Defense  switch " + bar(coach["screen_defense"]) + "  fight thru")
    print("  Zone Tendency   man   " + bar(coach["zone_tendency"]) + "  zone")

    print("")
    print("  -- LATE GAME --")
    print("  Late Game       sets  " + bar(coach["late_game"]) + "  star iso")

    print("")
    print("  -- COMPETENCE --")
    print("  Offensive Skill:       " + stars(coach["offensive_skill"]))
    print("  Defensive Skill:       " + stars(coach["defensive_skill"]))
    print("  Player Development:    " + stars(coach["player_development"]))
    print("  Tactics:               " + stars(coach["tactics"]))
    print("  In-Game Adaptability:  " + stars(coach["in_game_adaptability"]))
    print("  Scheme Adaptability:   " + stars(coach["scheme_adaptability"]))
    print("  Recruiting Attraction: " + stars(coach["recruiting_attraction"]))
    print("  Roster Fit:            " + stars(coach["roster_fit"]))

    print("")
    print("  -- ROSTER VALUES --")
    print("  What he recruits for:")
    print("  Athleticism: " + str(coach["values_athleticism"]) +
          "  IQ: "          + str(coach["values_iq"]) +
          "  Size: "        + str(coach["values_size"]) +
          "  Shooting: "    + str(coach["values_shooting"]))
    print("  Defense: "     + str(coach["values_defense"]) +
          "  Toughness: "   + str(coach["values_toughness"]) +
          "  Role Players: "+ str(coach["values_role_players"]))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from player import create_player

    print("=" * 65)
    print("  COACH GENERATION TEST -- v0.3")
    print("=" * 65)

    coaches = [
        generate_coach("Tom Izzo Type",     prestige=85, archetype="grinder",          experience=25),
        generate_coach("Cal Type",          prestige=90, archetype="pace_and_space",    experience=20),
        generate_coach("Bennett Type",      prestige=70, archetype="grinder",           experience=15),
        generate_coach("Pitino Type",       prestige=75, archetype="pressure_defense",  experience=30),
        generate_coach("Boeheim Type",      prestige=80, archetype="zone_specialist",   experience=28),
        generate_coach("Analytics Coach",   prestige=60, archetype="analytics_modern",  experience=8),
        generate_coach("Princeton Coach",   prestige=55, archetype="princeton_style",   experience=18),
        generate_coach("Post Coach",        prestige=65, archetype="post_centric",      experience=20),
    ]

    for coach in coaches:
        print_coach_profile(coach, show_archetype=True)

    # --- COMPETENCE CEILING VERIFICATION ---
    # After the v0.3 fix, elite coaches should NOT routinely hit 20/20
    print("")
    print("=" * 65)
    print("  COMPETENCE CEILING VERIFICATION -- 50 elite program coaches")
    print("  (should see very few 20/20 ratings after v0.3 fix)")
    print("=" * 65)
    maxed_count = 0
    total_ratings = 0
    for i in range(50):
        c = generate_coach("Coach " + str(i+1), prestige=90, experience=25)
        for key in ["offensive_skill", "defensive_skill", "recruiting_attraction", "roster_fit"]:
            total_ratings += 1
            if c[key] == 20:
                maxed_count += 1
    print("  Ratings at 20/20: " + str(maxed_count) + " of " + str(total_ratings) +
          " (" + str(round(maxed_count / total_ratings * 100, 1)) + "%)")
    print("  (healthy range: under 5%)")

    # --- ROTATION SIZE vs PACE ---
    print("")
    print("=" * 65)
    print("  ROTATION SIZE vs PACE VERIFICATION")
    print("=" * 65)
    print("  {:<22} {:<8} {:<10}".format("Coach", "Pace", "Rotation"))
    print("  " + "-" * 40)
    for coach in coaches:
        print("  {:<22} {:<8} {:<10}".format(
            coach["name"], str(coach["pace"]), str(coach["rotation_size"]) + " players"
        ))

    # --- STYLE FIT TEST ---
    print("")
    print("=" * 65)
    print("  STYLE FIT TEST")
    print("=" * 65)

    fast_wing = create_player("Fast Wing", "SF", "Freshman")
    fast_wing["speed"] = 18
    fast_wing["three_point"] = 16
    fast_wing["finishing"] = 15
    fast_wing["ball_handling"] = 14
    fast_wing["lateral_quickness"] = 16

    slow_big = create_player("Slow Big", "C", "Freshman")
    slow_big["speed"] = 6
    slow_big["strength"] = 17
    slow_big["rebounding"] = 17
    slow_big["finishing"] = 15
    slow_big["post_scoring"] = 16

    smart_pg = create_player("Smart PG", "PG", "Freshman")
    smart_pg["court_vision"] = 17
    smart_pg["passing"] = 17
    smart_pg["decision_making"] = 16
    smart_pg["ball_handling"] = 15
    smart_pg["speed"] = 12

    print("")
    print("  {:<22} {:<12} {:<12} {:<12}".format(
        "Coach", "Fast Wing", "Slow Big", "Smart PG"))
    print("  " + "-" * 58)
    for coach in coaches:
        wing_fit  = calculate_style_fit(fast_wing, coach)
        big_fit   = calculate_style_fit(slow_big,  coach)
        pg_fit    = calculate_style_fit(smart_pg,  coach)
        print("  {:<22} {:<12} {:<12} {:<12}".format(
            coach["name"],
            str(wing_fit) + "/100",
            str(big_fit)  + "/100",
            str(pg_fit)   + "/100",
        ))
