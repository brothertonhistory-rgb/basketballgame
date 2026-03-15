import random
from player import generate_team, get_team_ratings

# -----------------------------------------
# COLLEGE HOOPS SIM -- Game Engine v0.2
# Now uses real player rosters from player.py
# -----------------------------------------

def resolve_shot(shooter, defender, shot_type, fatigue=0, momentum=0):
    base_prob = 0.38 + (shooter["shooting"] / 20) * 0.25

    shot_type_mods = {
        "catch_and_shoot": 0.04,
        "off_dribble":    -0.04,
        "post_up":        -0.02,
        "putback":         0.02,
        "floater":        -0.03,
        "at_rim":          0.06,
    }
    base_prob += shot_type_mods.get(shot_type, 0)

    contest_penalty = (defender["defense"] / 20) * 0.14
    base_prob -= contest_penalty

    base_prob -= fatigue * 0.04
    base_prob += momentum * 0.03

    if base_prob < 0.05:
        base_prob = 0.05
    if base_prob > 0.95:
        base_prob = 0.95

    foul_chance = 0.03 + (shooter.get("foul_draw", 10) / 20) * 0.05
    if random.random() < foul_chance:
        return "foul"

    if random.random() < base_prob:
        return "make"
    else:
        return "miss"


def resolve_rebound(offense_rating, defense_rating):
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
    if random.random() < 0.18:
        return {"outcome": "turnover", "points": 0, "shot_type": "none"}

    shot_types = ["catch_and_shoot", "off_dribble", "post_up", "floater", "at_rim"]
    shot_type = random.choice(shot_types)

    result = resolve_shot(offense, defense, shot_type, fatigue, momentum)

    if result == "make":
        return {"outcome": "score", "points": 2, "shot_type": shot_type}

    elif result == "foul":
        ft_made = sum(1 for _ in range(2) if random.random() < 0.72)
        return {"outcome": "foul", "points": ft_made, "shot_type": shot_type}

    else:
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


def simulate_period(home_team, away_team, possessions, home_score, away_score,
                    home_momentum, away_momentum, fatigue_base=0):
    for i in range(possessions):
        fatigue = fatigue_base + (i / (possessions * 2))

        home_result = simulate_possession(home_team, away_team, home_momentum, fatigue)
        home_score += home_result["points"]

        if home_result["outcome"] == "score":
            home_momentum = min(1.0, home_momentum + 0.2)
            away_momentum = max(-1.0, away_momentum - 0.1)
        else:
            home_momentum = max(-1.0, home_momentum - 0.1)

        away_result = simulate_possession(away_team, home_team, away_momentum, fatigue)
        away_score += away_result["points"]

        if away_result["outcome"] == "score":
            away_momentum = min(1.0, away_momentum + 0.2)
            home_momentum = max(-1.0, home_momentum - 0.1)
        else:
            away_momentum = max(-1.0, away_momentum - 0.1)

    return home_score, away_score, home_momentum, away_momentum


def simulate_game(home_team, away_team, possessions=70, verbose=True):
    """
    Simulates a full game.
    Accepts either a simple ratings dict OR a full team with roster.
    Returns final score and OT info.
    """

    if "roster" in home_team:
        home_ratings = get_team_ratings(home_team)
    else:
        home_ratings = home_team

    if "roster" in away_team:
        away_ratings = get_team_ratings(away_team)
    else:
        away_ratings = away_team

    home_momentum = 0
    away_momentum = 0

    if verbose:
        print("")
        print(home_ratings["name"] + " vs " + away_ratings["name"])
        print("----------------------------------------")

    home_score, away_score, home_momentum, away_momentum = simulate_period(
        home_ratings, away_ratings, possessions, 0, 0,
        home_momentum, away_momentum, fatigue_base=0
    )

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
            home_momentum, away_momentum, fatigue_base=0.7
        )

    ot_label = ""
    if ot_periods == 1:
        ot_label = " (OT)"
    elif ot_periods > 1:
        ot_label = " (" + str(ot_periods) + "OT)"

    if verbose:
        print("Final" + ot_label + ": " + home_ratings["name"] + " " +
              str(home_score) + ", " + away_ratings["name"] + " " + str(away_score))

    return {"home": home_score, "away": away_score, "ot": ot_periods,
            "home_name": home_ratings["name"], "away_name": away_ratings["name"]}


# -----------------------------------------
# TEST -- Using real generated rosters
# -----------------------------------------

if __name__ == "__main__":

    print("Generating rosters...")
    kentucky     = generate_team("Kentucky", prestige=17)
    kansas_state = generate_team("Kansas State", prestige=13)
    average_d1   = generate_team("Average D1", prestige=10)

    print("")
    print("=== MATCHUP 1: Kentucky vs Kansas State (10 games) ===")
    results1 = []
    for _ in range(10):
        result = simulate_game(kentucky, kansas_state)
        results1.append(result)
    wins1 = sum(1 for r in results1 if r["home"] > r["away"])
    avg_h1 = sum(r["home"] for r in results1) // 10
    avg_a1 = sum(r["away"] for r in results1) // 10
    print("")
    print("Kentucky wins: " + str(wins1) + "/10")
    print("Average: Kentucky " + str(avg_h1) + " -- Kansas State " + str(avg_a1))

    print("")
    print("=== MATCHUP 2: Kentucky vs Average D1 (10 games) ===")
    results2 = []
    for _ in range(10):
        result = simulate_game(kentucky, average_d1)
        results2.append(result)
    wins2 = sum(1 for r in results2 if r["home"] > r["away"])
    avg_h2 = sum(r["home"] for r in results2) // 10
    avg_a2 = sum(r["away"] for r in results2) // 10
    print("")
    print("Kentucky wins: " + str(wins2) + "/10")
    print("Average: Kentucky " + str(avg_h2) + " -- Average D1 " + str(avg_a2))

    print("")
    print("=== MATCHUP 3: Average D1 vs Average D1 (10 games) ===")
    results3 = []
    for _ in range(10):
        result = simulate_game(average_d1, average_d1)
        results3.append(result)
    wins3 = sum(1 for r in results3 if r["home"] > r["away"])
    avg_h3 = sum(r["home"] for r in results3) // 10
    avg_a3 = sum(r["away"] for r in results3) // 10
    print("")
    print("Home wins: " + str(wins3) + "/10")
    print("Average: Team A " + str(avg_h3) + " -- Team B " + str(avg_a3))
