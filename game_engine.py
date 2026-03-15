import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Game Engine v0.1
# Core unit: the shot attempt
# Calibration target: ~70-75 points per team per game
# -----------------------------------------

def resolve_shot(shooter, defender, shot_type, fatigue=0, momentum=0):
    """
    Resolves a single shot attempt.
    Returns: 'make', 'miss', or 'foul'
    """

    # Base make probability from shooter rating (1-20 scale)
    # Rating 10 (average) = ~47%. Rating 16 (elite) = ~55%. Rating 13 = ~51%.
    base_prob = 0.38 + (shooter["shooting"] / 20) * 0.25

    # Shot type modifier
    shot_type_mods = {
        "catch_and_shoot": 0.04,
        "off_dribble":    -0.04,
        "post_up":        -0.02,
        "putback":         0.02,
        "floater":        -0.03,
        "at_rim":          0.06,
    }
    base_prob += shot_type_mods.get(shot_type, 0)

    # Defender contest modifier
    contest_penalty = (defender["defense"] / 20) * 0.14
    base_prob -= contest_penalty

    # Fatigue modifier (0-1 scale, higher = more tired)
    base_prob -= fatigue * 0.04

    # Momentum modifier (-1 to +1 scale)
    base_prob += momentum * 0.03

    # Hard floor and ceiling -- per the Bible
    if base_prob < 0.05:
        base_prob = 0.05
    if base_prob > 0.95:
        base_prob = 0.95

    # Foul check
    foul_chance = 0.03 + (shooter.get("foul_draw", 10) / 20) * 0.05
    if random.random() < foul_chance:
        return "foul"

    # Resolve the shot
    if random.random() < base_prob:
        return "make"
    else:
        return "miss"


def resolve_rebound(offense_rating, defense_rating):
    """
    Resolves a rebound after a miss.
    Returns: 'offensive' or 'defensive'
    """
    off_chance = 0.25 + (offense_rating / 20) * 0.08
    if off_chance < 0.05:
        off_chance = 0.05
    if off_chance > 0.45:
        off_chance = 0.45

    if random.random() < off_chance:
        return "offensive"
    else:
        return "defensive"


def simulate_possession(offense, defense, momentum=0, fatigue=0):
    """
    Simulates one possession.
    Returns a dict describing what happened.
    """
    # Turnovers -- real D1 turnover rate roughly 18% of possessions
    if random.random() < 0.18:
        return {"outcome": "turnover", "points": 0, "shot_type": "none"}

    shot_types = ["catch_and_shoot", "off_dribble", "post_up", "floater", "at_rim"]
    shot_type = random.choice(shot_types)

    result = resolve_shot(offense, defense, shot_type, fatigue, momentum)

    if result == "make":
        return {"outcome": "score", "points": 2, "shot_type": shot_type}

    elif result == "foul":
        # 2 free throws at 72% each
        ft_made = sum(1 for _ in range(2) if random.random() < 0.72)
        return {"outcome": "foul", "points": ft_made, "shot_type": shot_type}

    else:  # miss
        rebound = resolve_rebound(
            offense.get("rebounding", 10),
            defense.get("rebounding", 10)
        )
        if rebound == "offensive":
            result2 = resolve_shot(offense, defense, "putback", fatigue + 0.1, momentum)
            if result2 == "make":
                return {"outcome": "score", "points": 2, "shot_type": "putback"}
            else:
                return {"outcome": "miss", "points": 0, "shot_type": shot_type}
        else:
            return {"outcome": "miss", "points": 0, "shot_type": shot_type}


def simulate_period(home_team, away_team, possessions, home_score, away_score, home_momentum, away_momentum, fatigue_base=0):
    """
    Simulates a period (half or overtime) of possessions.
    Returns updated scores and momentum.
    """
    for i in range(possessions):
        fatigue = fatigue_base + (i / (possessions * 2))

        # Home possession
        home_result = simulate_possession(home_team, away_team, home_momentum, fatigue)
        home_score += home_result["points"]

        if home_result["outcome"] == "score":
            home_momentum = min(1.0, home_momentum + 0.2)
            away_momentum = max(-1.0, away_momentum - 0.1)
        else:
            home_momentum = max(-1.0, home_momentum - 0.1)

        # Away possession
        away_result = simulate_possession(away_team, home_team, away_momentum, fatigue)
        away_score += away_result["points"]

        if away_result["outcome"] == "score":
            away_momentum = min(1.0, away_momentum + 0.2)
            home_momentum = max(-1.0, home_momentum - 0.1)
        else:
            away_momentum = max(-1.0, away_momentum - 0.1)

    return home_score, away_score, home_momentum, away_momentum


def simulate_game(home_team, away_team, possessions=72):
    """
    Simulates a full game with overtime support.
    possessions = per team per regulation (real D1 average 68-74)
    Returns final score and OT info.
    """
    home_momentum = 0
    away_momentum = 0

    print("")
    print(home_team["name"] + " vs " + away_team["name"])
    print("----------------------------------------")

    # Regulation -- two halves
    home_score, away_score, home_momentum, away_momentum = simulate_period(
        home_team, away_team, possessions, 0, 0, home_momentum, away_momentum, fatigue_base=0
    )

    # Overtime -- college basketball uses 5-minute OT periods (~6 possessions per team)
    ot_periods = 0
    while home_score == away_score:
        ot_periods += 1
        if ot_periods > 4:
            # Extremely rare -- force a winner after 4 OTs
            home_score += 1
            break
        print("  -- Overtime " + str(ot_periods) + " --")
        home_score, away_score, home_momentum, away_momentum = simulate_period(
            home_team, away_team, 6, home_score, away_score, home_momentum, away_momentum, fatigue_base=0.7
        )

    ot_label = ""
    if ot_periods == 1:
        ot_label = " (OT)"
    elif ot_periods > 1:
        ot_label = " (" + str(ot_periods) + "OT)"

    print("Final" + ot_label + ": " + home_team["name"] + " " + str(home_score) + ", " + away_team["name"] + " " + str(away_score))
    return {"home": home_score, "away": away_score, "ot": ot_periods}


# -----------------------------------------
# TEST -- Three matchups
# -----------------------------------------

if __name__ == "__main__":

    kentucky = {
        "name": "Kentucky",
        "shooting": 16,
        "defense": 15,
        "rebounding": 15,
        "foul_draw": 14,
    }

    kansas_state = {
        "name": "Kansas State",
        "shooting": 13,
        "defense": 14,
        "rebounding": 13,
        "foul_draw": 11,
    }

    average_d1 = {
        "name": "Average D1",
        "shooting": 10,
        "defense": 10,
        "rebounding": 10,
        "foul_draw": 10,
    }

    print("=== MATCHUP 1: Kentucky vs Kansas State ===")
    results1 = []
    for _ in range(10):
        result = simulate_game(kentucky, kansas_state)
        results1.append(result)
    wins1 = sum(1 for r in results1 if r["home"] > r["away"])
    avg_h1 = sum(r["home"] for r in results1) // 10
    avg_a1 = sum(r["away"] for r in results1) // 10
    ot1 = sum(r["ot"] for r in results1)
    print("")
    print("Kentucky wins: " + str(wins1) + "/10")
    print("Average: Kentucky " + str(avg_h1) + " -- Kansas State " + str(avg_a1))
    print("Overtime games: " + str(ot1))

    print("")
    print("=== MATCHUP 2: Kentucky vs Average D1 ===")
    results2 = []
    for _ in range(10):
        result = simulate_game(kentucky, average_d1)
        results2.append(result)
    wins2 = sum(1 for r in results2 if r["home"] > r["away"])
    avg_h2 = sum(r["home"] for r in results2) // 10
    avg_a2 = sum(r["away"] for r in results2) // 10
    ot2 = sum(r["ot"] for r in results2)
    print("")
    print("Kentucky wins: " + str(wins2) + "/10")
    print("Average: Kentucky " + str(avg_h2) + " -- Average D1 " + str(avg_a2))
    print("Overtime games: " + str(ot2))

    print("")
    print("=== MATCHUP 3: Average D1 vs Average D1 ===")
    results3 = []
    for _ in range(10):
        result = simulate_game(average_d1, average_d1)
        results3.append(result)
    wins3 = sum(1 for r in results3 if r["home"] > r["away"])
    avg_h3 = sum(r["home"] for r in results3) // 10
    avg_a3 = sum(r["away"] for r in results3) // 10
    ot3 = sum(r["ot"] for r in results3)
    print("")
    print("Home wins: " + str(wins3) + "/10")
    print("Average: Team A " + str(avg_h3) + " -- Team B " + str(avg_a3))
    print("Overtime games: " + str(ot3))
