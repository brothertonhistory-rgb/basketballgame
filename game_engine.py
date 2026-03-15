import random
from player import generate_team, get_team_ratings

# -----------------------------------------
# COLLEGE HOOPS SIM -- Game Engine v0.4
#
# v0.4 CHANGES -- Recalibrated for 1-1000 attribute scale.
#
# Player attributes now live on 1-1000 internally. get_team_ratings()
# returns composite values on 1-1000. All formulas in resolve_shot()
# and resolve_rebound() normalize against 1000 instead of 20.
#
# Game outcome probabilities are IDENTICAL to v0.3 -- only the
# denominators changed. The mid-range team average on the old scale
# was ~10/20 = 0.50. On the new scale it's ~500/1000 = 0.50.
# All shot probabilities, contest penalties, and rebound chances
# produce the same distributions as before.
#
# v0.3 CHANGES (preserved):
#   Coaching philosophy now drives game outcomes.
#   pace, shot_profile, pressure, off_rebounding, shot_selection
#   all shape each possession.
# -----------------------------------------


# -----------------------------------------
# COACHING GAME PROFILE
# -----------------------------------------

def build_game_profile(team):
    """
    Reads the team's coach sliders and builds a game profile dict
    that shapes how this team plays each possession.

    If no coach is present (legacy dict or test team), returns
    neutral defaults so the engine is backward compatible.
    """
    coach = team.get("coach", {})

    if not coach:
        return _neutral_profile()

    # --- PACE → POSSESSIONS ---
    pace = coach.get("pace", 50)
    possessions_modifier = int((pace - 50) / 5)   # range roughly -10 to +10

    # --- SHOT PROFILE → SHOT TYPE WEIGHTS ---
    shot_profile = coach.get("shot_profile", 50)
    personnel    = coach.get("personnel", 50)

    rim_weight     = 15 + int((shot_profile / 100) * 20)
    three_weight   = 10 + int((shot_profile / 100) * 25)
    mid_weight     = 20 - int((shot_profile / 100) * 15)
    post_weight    = 20 - int((shot_profile / 100) * 15)
    dribble_weight = 10 + int((personnel / 100) * 10)

    shot_weights = {
        "at_rim":          max(5, rim_weight),
        "catch_and_shoot": max(5, three_weight),
        "mid_range":       max(5, mid_weight),
        "post_up":         max(3, post_weight),
        "off_dribble":     max(5, dribble_weight),
        "floater":         8,
    }

    # --- PRESSURE / PHILOSOPHY → TURNOVER RATE ---
    pressure   = coach.get("pressure", 50)
    philosophy = coach.get("philosophy", 50)
    turnover_rate = 0.16 + (pressure / 100) * 0.08 + (philosophy / 100) * 0.04

    # --- REBOUNDING SLIDERS ---
    off_rebounding    = coach.get("off_rebounding", 50)
    off_rebound_bonus = (off_rebounding - 50) / 100 * 0.06   # -0.03 to +0.03

    # --- SHOT SELECTION → SHOT QUALITY ---
    shot_selection     = coach.get("shot_selection", 50)
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

    v0.4: Normalized against 1000 instead of 20.
    All probability outputs are identical to v0.3 at the mean.
    shooter["shooting"] and defender["defense"] are now ~500 at average
    instead of ~10, but dividing by 1000 instead of 20 gives same result.
    """
    # Base probability: 0.38 to 0.63 depending on shooting (same range as v0.3)
    base_prob = 0.38 + (shooter["shooting"] / 1000) * 0.25

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

    # Contest penalty: 0.0 to 0.14 depending on defender (same range as v0.3)
    contest_penalty = (defender["defense"] / 1000) * 0.14
    base_prob -= contest_penalty

    base_prob -= fatigue * 0.04
    base_prob += momentum * 0.03

    base_prob = max(0.05, min(0.95, base_prob))

    # Foul chance: 0.03 to 0.08 depending on foul_draw (same range as v0.3)
    foul_chance = 0.03 + (shooter.get("foul_draw", 500) / 1000) * 0.05
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

    v0.4: Normalized against 1000.
    offense_rating/1000 * 0.08 gives same range as offense_rating/20 * 0.08
    when ratings are proportionally equivalent.
    """
    off_chance = 0.27 + (offense_rating / 1000) * 0.08 + off_rebound_bonus
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

    v0.4: No structural changes. Uses offense/defense composite ratings
    from get_team_ratings() which now return 1-1000 values.
    resolve_shot() and resolve_rebound() normalize against 1000.
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
        points = 3 if shot_type == "catch_and_shoot" and random.random() < 0.55 else 2
        return {"outcome": "score", "points": points, "shot_type": shot_type}

    elif result == "foul":
        ft_made = sum(1 for _ in range(2) if random.random() < 0.72)
        return {"outcome": "foul", "points": ft_made, "shot_type": shot_type}

    else:
        rebound = resolve_rebound(
            offense.get("rebounding", 500),
            defense.get("rebounding", 500),
            off_rebound_bonus=offense_profile["off_rebound_bonus"]
        )
        if rebound == "offensive":
            result2 = resolve_shot(
                offense, defense, "putback", fatigue + 0.1, momentum,
                shot_quality_bonus=0.0
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
    Unchanged from v0.3 structurally -- passes game profiles through.
    """
    for i in range(possessions):
        fatigue = fatigue_base + (i / (possessions * 2))

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

    v0.4: get_team_ratings() now returns 1-1000 values.
    All internal formulas recalibrated. Game outcomes are equivalent.

    Accepts either a full program dict (with roster and coach) or a
    simple ratings dict (for backward compatibility).
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
    print("  GAME ENGINE v0.4 -- 1-1000 SCALE VERIFICATION")
    print("=" * 65)

    grinder_prog = create_program(
        "Grinder U", "Grinders", "Detroit", "MI", "D1", "Big Ten",
        "Grinder Arena", 75, 72, 70, "Coach Izzo Type"
    )
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

    print("")
    print("Game profiles:")
    for prog in [grinder_prog, pace_prog, press_prog]:
        profile = build_game_profile(prog)
        coach   = prog["coach"]
        print("  " + prog["name"].ljust(22) +
              "  archetype: " + coach["archetype"].ljust(18) +
              "  poss modifier: " + str(profile["possessions_modifier"]).rjust(3) +
              "  TO rate: " + str(profile["turnover_rate"]))

    print("")
    print("=== Score Profile -- 50 games each matchup ===")
    matchups = [
        ("Grinder vs Grinder", grinder_prog, grinder_prog),
        ("Pace vs Pace",       pace_prog,    pace_prog),
        ("Grinder vs Pace",    grinder_prog, pace_prog),
    ]

    for label, home, away in matchups:
        scores         = []
        possessions_list = []
        for _ in range(50):
            result = simulate_game(home, away, verbose=False)
            scores.append(result)
            possessions_list.append(result["possessions"])

        avg_total = sum(r["home"] + r["away"] for r in scores) / 50
        avg_poss  = sum(possessions_list) / 50
        avg_home  = sum(r["home"] for r in scores) / 50
        avg_away  = sum(r["away"] for r in scores) / 50
        home_wins = sum(1 for r in scores if r["home"] > r["away"])

        print("")
        print("  " + label)
        print("    Home wins:       " + str(home_wins) + "/50")
        print("    Avg score:       " + str(round(avg_home, 1)) +
              " - " + str(round(avg_away, 1)) +
              "  (combined: " + str(round(avg_total, 1)) + ")")
        print("    Avg possessions: " + str(round(avg_poss, 1)))
        print("    (grinder target: ~62-66 poss, pace target: ~72-76 poss)")
