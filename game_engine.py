import random
from player import generate_team, get_team_ratings

# -----------------------------------------
# COLLEGE HOOPS SIM -- Game Engine v0.3
#
# v0.3 CHANGES -- Coaching philosophy now drives game outcomes.
#
# Previously every game used identical logic regardless of coaches:
#   - Fixed 70 possessions per game
#   - Random shot type selection
#   - Flat 18% turnover rate
#   - Flat rebound rates
#
# Now the coach's philosophy sliders shape every possession:
#
#   PACE (slider 1-100)
#     Controls possessions per game. A grinder (pace=20) plays ~62
#     possessions. A 40-minutes-of-hell system (pace=85) plays ~76.
#     Range: 58-78 possessions per game.
#
#   SHOT PROFILE (slider 1-100)
#     Controls shot type distribution. High shot_profile = rim and 3
#     (analytics modern). Low = mid-range and post heavy. Affects
#     which shot types get selected each possession.
#
#   PRESSURE / PHILOSOPHY (sliders 1-100)
#     Controls opponent turnover rate. A full-court press (pressure=90)
#     forces turnovers on ~24% of possessions. A set defense (pressure=20)
#     forces turnovers on ~13%.
#
#   OFF_REBOUNDING / DEF_REBOUNDING (sliders 1-100)
#     Shifts the offensive rebound probability up or down from baseline.
#     A crash-the-glass team gets more second chances.
#
#   SHOT_SELECTION (slider 1-100)
#     Patient offense (high) takes fewer bad shots -- raises base
#     shot probability slightly. ISO-heavy (low) takes quick looks.
#
# The coaching effect is real but not overwhelming. Talent still
# dominates. A great coach running a great system with bad players
# still loses to a mediocre coach with great players. But two evenly
# matched rosters will produce meaningfully different outcomes
# depending on the coaching matchup.
# -----------------------------------------


# -----------------------------------------
# COACHING GAME PROFILE
# Translates coach philosophy sliders into game parameters.
# Called once per game per team.
# -----------------------------------------

def build_game_profile(team):
    """
    Reads the team's coach sliders and builds a game profile dict
    that shapes how this team plays each possession.

    If no coach is present (legacy dict or test team), returns
    neutral defaults so the engine is backward compatible.

    Returns a dict with keys:
      possessions_modifier  -- added to base 68 possessions
      shot_weights          -- {shot_type: weight} for random.choices()
      turnover_rate         -- fraction of possessions ending in TO
      off_rebound_bonus     -- added to base offensive rebound chance
      shot_quality_bonus    -- added to base shot probability
    """
    coach = team.get("coach", {})

    if not coach:
        return _neutral_profile()

    # --- PACE → POSSESSIONS ---
    # pace slider 1-100 maps to -10 to +10 possessions from base 68
    pace = coach.get("pace", 50)
    possessions_modifier = int((pace - 50) / 5)   # range roughly -10 to +10

    # --- SHOT PROFILE → SHOT TYPE WEIGHTS ---
    # shot_profile: 1=post/mid heavy, 100=rim and 3 only
    # personnel: 1=traditional, 100=positionless (affects spacing shots)
    shot_profile = coach.get("shot_profile", 50)
    personnel    = coach.get("personnel", 50)

    # Base weights for each shot type
    # at_rim and catch_and_shoot scale up with shot_profile
    # post_up and floater scale down with shot_profile
    rim_weight = 15 + int((shot_profile / 100) * 20)        # 15-35
    three_weight = 10 + int((shot_profile / 100) * 25)      # 10-35
    mid_weight = 20 - int((shot_profile / 100) * 15)        # 5-20
    post_weight = 20 - int((shot_profile / 100) * 15)       # 5-20
    # Positionless systems create more off-dribble opportunities
    dribble_weight = 10 + int((personnel / 100) * 10)       # 10-20

    shot_weights = {
        "at_rim":          max(5, rim_weight),
        "catch_and_shoot": max(5, three_weight),
        "mid_range":       max(5, mid_weight),
        "post_up":         max(3, post_weight),
        "off_dribble":     max(5, dribble_weight),
        "floater":         8,   # relatively stable across systems
    }

    # --- PRESSURE / PHILOSOPHY → TURNOVER RATE ---
    # pressure: 1=set defense, 100=full court press
    # philosophy: 1=contain, 100=gamble/trap
    pressure    = coach.get("pressure", 50)
    philosophy  = coach.get("philosophy", 50)

    # Base turnover rate 0.16, press adds up to +0.08, gambling adds up to +0.04
    # This is the rate this team's DEFENSE forces on the opponent
    turnover_rate = 0.16 + (pressure / 100) * 0.08 + (philosophy / 100) * 0.04

    # --- REBOUNDING SLIDERS → OFFENSIVE REBOUND BONUS ---
    off_rebounding = coach.get("off_rebounding", 50)
    # Baseline off_rebound chance is 0.27. Crash-the-glass adds up to +0.06.
    off_rebound_bonus = (off_rebounding - 50) / 100 * 0.06   # -0.03 to +0.03

    # --- SHOT SELECTION → SHOT QUALITY ---
    # Patient offense works for better shots -- small boost to base probability
    shot_selection = coach.get("shot_selection", 50)
    shot_quality_bonus = (shot_selection - 50) / 100 * 0.04  # -0.02 to +0.02

    return {
        "possessions_modifier": possessions_modifier,
        "shot_weights":         shot_weights,
        "turnover_rate":        round(turnover_rate, 3),
        "off_rebound_bonus":    round(off_rebound_bonus, 3),
        "shot_quality_bonus":   round(shot_quality_bonus, 3),
    }


def _neutral_profile():
    """Default game profile when no coach data is available."""
    return {
        "possessions_modifier": 0,
        "shot_weights": {
            "at_rim": 20, "catch_and_shoot": 20, "mid_range": 15,
            "post_up": 15, "off_dribble": 15, "floater": 8,
        },
        "turnover_rate":     0.18,
        "off_rebound_bonus": 0.0,
        "shot_quality_bonus": 0.0,
    }


# -----------------------------------------
# SHOT RESOLUTION
# -----------------------------------------

def resolve_shot(shooter, defender, shot_type, fatigue=0, momentum=0,
                 shot_quality_bonus=0.0):
    """
    Resolves a single shot attempt.
    Returns "make", "miss", or "foul".

    v0.3: shot_quality_bonus from coach's shot_selection slider
    slightly adjusts the base probability.
    """
    base_prob = 0.38 + (shooter["shooting"] / 20) * 0.25

    shot_type_mods = {
        "catch_and_shoot":  0.04,
        "off_dribble":     -0.04,
        "post_up":         -0.02,
        "putback":          0.02,
        "floater":         -0.03,
        "at_rim":           0.06,
        "mid_range":       -0.01,
    }
    base_prob += shot_type_mods.get(shot_type, 0)
    base_prob += shot_quality_bonus

    contest_penalty = (defender["defense"] / 20) * 0.14
    base_prob -= contest_penalty

    base_prob -= fatigue * 0.04
    base_prob += momentum * 0.03

    base_prob = max(0.05, min(0.95, base_prob))

    foul_chance = 0.03 + (shooter.get("foul_draw", 10) / 20) * 0.05
    if random.random() < foul_chance:
        return "foul"

    if random.random() < base_prob:
        return "make"
    else:
        return "miss"


# -----------------------------------------
# REBOUND RESOLUTION
# -----------------------------------------

def resolve_rebound(offense_rating, defense_rating, off_rebound_bonus=0.0):
    """
    Resolves a rebound after a missed shot.

    v0.3: off_rebound_bonus from offense team's rebounding philosophy
    shifts the probability toward offensive boards.
    """
    off_chance = 0.27 + (offense_rating / 20) * 0.08 + off_rebound_bonus
    off_chance = max(0.05, min(0.50, off_chance))

    if random.random() < off_chance:
        return "offensive"
    else:
        return "defensive"


# -----------------------------------------
# POSSESSION RESOLUTION
# -----------------------------------------

def simulate_possession(offense, defense, offense_profile, defense_profile,
                        momentum=0, fatigue=0):
    """
    Simulates one offensive possession.

    v0.3: Uses offense and defense game profiles to determine:
      - Turnover rate (driven by defense's pressure/philosophy)
      - Shot type selection (driven by offense's shot profile/personnel)
      - Shot quality (driven by offense's shot selection patience)
      - Offensive rebound chance (driven by offense's off_rebounding)

    Returns dict with outcome, points, shot_type.
    """

    # Turnover -- driven by DEFENSE's pressure system
    if random.random() < defense_profile["turnover_rate"]:
        return {"outcome": "turnover", "points": 0, "shot_type": "none"}

    # Shot type selection -- driven by OFFENSE's system
    shot_types  = list(offense_profile["shot_weights"].keys())
    shot_wts    = list(offense_profile["shot_weights"].values())
    shot_type   = random.choices(shot_types, weights=shot_wts, k=1)[0]

    result = resolve_shot(
        offense, defense, shot_type, fatigue, momentum,
        shot_quality_bonus=offense_profile["shot_quality_bonus"]
    )

    if result == "make":
        # Three-point attempt from catch_and_shoot
        points = 3 if shot_type == "catch_and_shoot" and random.random() < 0.55 else 2
        return {"outcome": "score", "points": points, "shot_type": shot_type}

    elif result == "foul":
        ft_made = sum(1 for _ in range(2) if random.random() < 0.72)
        return {"outcome": "foul", "points": ft_made, "shot_type": shot_type}

    else:
        rebound = resolve_rebound(
            offense.get("rebounding", 10),
            defense.get("rebounding", 10),
            off_rebound_bonus=offense_profile["off_rebound_bonus"]
        )
        if rebound == "offensive":
            result2 = resolve_shot(
                offense, defense, "putback", fatigue + 0.1, momentum,
                shot_quality_bonus=0.0   # putbacks are pure athleticism
            )
            if result2 == "make":
                return {"outcome": "score", "points": 2, "shot_type": "putback"}
            else:
                return {"outcome": "miss", "points": 0, "shot_type": shot_type}
        else:
            return {"outcome": "miss", "points": 0, "shot_type": shot_type}


# -----------------------------------------
# PERIOD SIMULATION
# -----------------------------------------

def simulate_period(home_team, away_team, possessions, home_score, away_score,
                    home_momentum, away_momentum,
                    home_profile, away_profile,
                    fatigue_base=0):
    """
    Simulates one period (half or OT).

    v0.3: Passes game profiles to each possession so coach philosophy
    shapes every shot selection and turnover decision.
    """
    for i in range(possessions):
        fatigue = fatigue_base + (i / (possessions * 2))

        # Home team on offense -- defense profile drives turnover rate
        home_result = simulate_possession(
            home_team, away_team,
            home_profile, away_profile,
            home_momentum, fatigue
        )
        home_score += home_result["points"]

        if home_result["outcome"] == "score":
            home_momentum = min(1.0, home_momentum + 0.2)
            away_momentum = max(-1.0, away_momentum - 0.1)
        else:
            home_momentum = max(-1.0, home_momentum - 0.1)

        # Away team on offense
        away_result = simulate_possession(
            away_team, home_team,
            away_profile, home_profile,
            away_momentum, fatigue
        )
        away_score += away_result["points"]

        if away_result["outcome"] == "score":
            away_momentum = min(1.0, away_momentum + 0.2)
            home_momentum = max(-1.0, home_momentum - 0.1)
        else:
            away_momentum = max(-1.0, away_momentum - 0.1)

    return home_score, away_score, home_momentum, away_momentum


# -----------------------------------------
# MAIN GAME SIMULATOR
# -----------------------------------------

def simulate_game(home_team, away_team, possessions=None, verbose=True):
    """
    Simulates a full game between two programs.

    v0.3: Coaching philosophy now shapes every game.
      - Pace sliders determine total possessions
      - Shot profile determines shot type distribution
      - Pressure/philosophy determines turnover rates
      - Rebounding philosophy determines second chance opportunities
      - Shot selection patience affects shot quality

    Accepts either a full program dict (with roster and coach) or a
    simple ratings dict (for backward compatibility with old tests).

    Returns final score and OT info.
    """

    # --- BUILD RATINGS ---
    if "roster" in home_team:
        home_ratings = get_team_ratings(home_team)
    else:
        home_ratings = home_team

    if "roster" in away_team:
        away_ratings = get_team_ratings(away_team)
    else:
        away_ratings = away_team

    # --- BUILD GAME PROFILES FROM COACH SLIDERS ---
    home_profile = build_game_profile(home_team)
    away_profile = build_game_profile(away_team)

    # --- DETERMINE POSSESSIONS ---
    # Base 68. Each team's pace modifier pushes it up or down.
    # Average the two teams' pace preferences -- both teams influence tempo.
    # A grinder vs a run-and-gun results in a contested pace game.
    if possessions is None:
        base_possessions = 68
        pace_adjustment  = (home_profile["possessions_modifier"] +
                            away_profile["possessions_modifier"]) // 2
        possessions = max(55, min(82, base_possessions + pace_adjustment))

    home_momentum = 0
    away_momentum = 0

    if verbose:
        print("")
        print(home_ratings["name"] + " vs " + away_ratings["name"])
        home_coach = home_team.get("coach", {})
        away_coach = away_team.get("coach", {})
        if home_coach and away_coach:
            print("  " + home_coach.get("archetype", "?").replace("_", " ") +
                  " vs " + away_coach.get("archetype", "?").replace("_", " ") +
                  "  |  " + str(possessions) + " possessions")
        print("----------------------------------------")

    # --- SIMULATE GAME ---
    home_score, away_score, home_momentum, away_momentum = simulate_period(
        home_ratings, away_ratings, possessions, 0, 0,
        home_momentum, away_momentum,
        home_profile, away_profile,
        fatigue_base=0
    )

    # --- OVERTIME ---
    ot_periods = 0
    while home_score == away_score:
        ot_periods += 1
        if ot_periods > 4:
            home_score += 1
            break
        if verbose:
            print("  -- Overtime " + str(ot_periods) + " --")
        home_score, away_score, home_momentum, away_momentum = simulate_period(
            home_ratings, away_ratings, 6, home_score, away_score,
            home_momentum, away_momentum,
            home_profile, away_profile,
            fatigue_base=0.7
        )

    ot_label = ""
    if ot_periods == 1:
        ot_label = " (OT)"
    elif ot_periods > 1:
        ot_label = " (" + str(ot_periods) + "OT)"

    if verbose:
        print("Final" + ot_label + ": " + home_ratings["name"] + " " +
              str(home_score) + ", " + away_ratings["name"] + " " + str(away_score))

    return {
        "home":      home_score,
        "away":      away_score,
        "ot":        ot_periods,
        "home_name": home_ratings["name"],
        "away_name": away_ratings["name"],
        "possessions": possessions,
    }


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from coach import generate_coach
    from program import create_program

    print("=" * 65)
    print("  GAME ENGINE v0.3 -- COACHING PHILOSOPHY TEST")
    print("=" * 65)

    # Build four programs with distinct coaching philosophies
    grinder_prog = create_program(
        "Grinder U", "Grinders", "Detroit", "MI", "D1", "Big Ten",
        "Grinder Arena", 75, 72, 70, "Coach Izzo Type"
    )
    # Force the archetype for testing
    from coach import generate_coach
    grinder_prog["coach"] = generate_coach("Coach Izzo Type", prestige=72,
                                            archetype="grinder", experience=20)

    pace_prog = create_program(
        "Pace U", "Racers", "Lexington", "KY", "D1", "SEC",
        "Pace Arena", 90, 88, 85, "Coach Cal Type"
    )
    pace_prog["coach"] = generate_coach("Coach Cal Type", prestige=88,
                                         archetype="pace_and_space", experience=18)

    press_prog = create_program(
        "Press U", "Pressers", "Louisville", "KY", "D1", "ACC",
        "Press Arena", 82, 78, 75, "Coach Pitino Type"
    )
    press_prog["coach"] = generate_coach("Coach Pitino Type", prestige=78,
                                          archetype="pressure_defense", experience=25)

    princeton_prog = create_program(
        "Princeton Style U", "Thinkers", "Princeton", "NJ", "D1", "Ivy League",
        "Think Arena", 60, 58, 55, "Coach Carril Type"
    )
    princeton_prog["coach"] = generate_coach("Coach Carril Type", prestige=58,
                                              archetype="princeton_style", experience=22)

    print("")
    print("Game profiles (what each coach's system produces):")
    for prog in [grinder_prog, pace_prog, press_prog, princeton_prog]:
        profile = build_game_profile(prog)
        coach   = prog["coach"]
        print("  " + prog["name"].ljust(22) +
              "  archetype: " + coach["archetype"].ljust(18) +
              "  possessions modifier: " + str(profile["possessions_modifier"]).rjust(3) +
              "  TO rate: " + str(profile["turnover_rate"]) +
              "  off_reb bonus: " + str(profile["off_rebound_bonus"]))

    # --- HEAD TO HEAD TESTS ---
    print("")
    print("=" * 65)
    print("  HEAD TO HEAD -- 20 GAMES EACH MATCHUP")
    print("=" * 65)

    matchups = [
        ("Grinder vs Pace",    grinder_prog,   pace_prog),
        ("Grinder vs Press",   grinder_prog,   press_prog),
        ("Pace vs Princeton",  pace_prog,      princeton_prog),
        ("Press vs Grinder",   press_prog,     grinder_prog),
    ]

    for label, home, away in matchups:
        scores = []
        possessions_list = []
        for _ in range(20):
            result = simulate_game(home, away, verbose=False)
            scores.append(result)
            possessions_list.append(result["possessions"])

        home_wins   = sum(1 for r in scores if r["home"] > r["away"])
        avg_total   = sum(r["home"] + r["away"] for r in scores) / 20
        avg_poss    = sum(possessions_list) / 20
        avg_home    = sum(r["home"] for r in scores) / 20
        avg_away    = sum(r["away"] for r in scores) / 20

        print("")
        print("  " + label)
        print("    Home wins: " + str(home_wins) + "/20")
        print("    Avg score: " + str(round(avg_home, 1)) + " - " + str(round(avg_away, 1)) +
              "  (total: " + str(round(avg_total, 1)) + " pts)")
        print("    Avg possessions: " + str(round(avg_poss, 1)))

    # --- PACE VERIFICATION ---
    print("")
    print("=" * 65)
    print("  PACE VERIFICATION -- grinder vs pace-and-space")
    print("  Grinder games should have ~60-65 possessions")
    print("  Pace games should have ~72-78 possessions")
    print("=" * 65)

    grinder_poss = []
    for _ in range(50):
        r = simulate_game(grinder_prog, grinder_prog, verbose=False)
        grinder_poss.append(r["possessions"])

    pace_poss = []
    for _ in range(50):
        r = simulate_game(pace_prog, pace_prog, verbose=False)
        pace_poss.append(r["possessions"])

    print("  Grinder vs Grinder avg possessions: " +
          str(round(sum(grinder_poss) / 50, 1)))
    print("  Pace vs Pace avg possessions:       " +
          str(round(sum(pace_poss) / 50, 1)))

    # --- SCORE PROFILE VERIFICATION ---
    print("")
    print("=" * 65)
    print("  SCORE PROFILE -- grinder games should be lower scoring")
    print("=" * 65)

    grinder_totals = []
    for _ in range(50):
        r = simulate_game(grinder_prog, grinder_prog, verbose=False)
        grinder_totals.append(r["home"] + r["away"])

    pace_totals = []
    for _ in range(50):
        r = simulate_game(pace_prog, pace_prog, verbose=False)
        pace_totals.append(r["home"] + r["away"])

    print("  Grinder avg combined score: " +
          str(round(sum(grinder_totals) / 50, 1)))
    print("  Pace avg combined score:    " +
          str(round(sum(pace_totals) / 50, 1)))
    print("  (Grinder should be 10-20 points lower than Pace)")
