import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Player System v0.1
# System 2 of the Design Bible
# All attributes on 1-20 scale. No overall rating.
# -----------------------------------------

# Position definitions
POSITIONS = ["PG", "SG", "SF", "PF", "C"]

# Year definitions
YEARS = ["Freshman", "Sophomore", "Junior", "Senior"]

# Development arc types -- from the Bible
ARC_TYPES = ["bust", "plateau", "steady", "overachiever", "late_bloomer"]


def create_player(name, position, year, shooting=None, defense=None,
                  rebounding=None, playmaking=None, athleticism=None,
                  mental=None, potential=None):
    """
    Creates a player object with all attributes from System 2.
    If attributes are not provided, generates them based on position and year.
    All ratings on 1-20 scale.
    """

    # If no ratings provided, generate them
    if shooting is None:
        shooting = generate_shooting(position)
    if defense is None:
        defense = generate_defense(position)
    if rebounding is None:
        rebounding = generate_rebounding(position)
    if playmaking is None:
        playmaking = generate_playmaking(position)
    if athleticism is None:
        athleticism = generate_athleticism(position)
    if mental is None:
        mental = generate_mental()
    if potential is None:
        potential = generate_potential()

    player = {
        # Identity
        "name": name,
        "position": position,
        "year": year,

        # --- SHOOTING (System 2) ---
        "catch_and_shoot":  shooting["catch_and_shoot"],
        "off_dribble":      shooting["off_dribble"],
        "mid_range":        shooting["mid_range"],
        "three_point":      shooting["three_point"],
        "free_throw":       shooting["free_throw"],
        "finishing":        shooting["finishing"],
        "post_scoring":     shooting["post_scoring"],

        # --- PLAYMAKING (System 2) ---
        "passing":          playmaking["passing"],
        "ball_handling":    playmaking["ball_handling"],
        "court_vision":     playmaking["court_vision"],
        "decision_making":  playmaking["decision_making"],

        # --- DEFENSE (System 2) ---
        "on_ball_defense":  defense["on_ball_defense"],
        "help_defense":     defense["help_defense"],
        "rebounding":       rebounding,
        "shot_blocking":    defense["shot_blocking"],
        "steal_tendency":   defense["steal_tendency"],
        "foul_tendency":    defense["foul_tendency"],

        # --- PHYSICAL (System 2) ---
        "speed":            athleticism["speed"],
        "lateral_quickness":athleticism["lateral_quickness"],
        "strength":         athleticism["strength"],
        "vertical":         athleticism["vertical"],

        # --- MENTAL -- Hidden (System 2) ---
        "basketball_iq":    mental["basketball_iq"],
        "clutch":           mental["clutch"],
        "composure":        mental["composure"],
        "coachability":     mental["coachability"],
        "work_ethic":       mental["work_ethic"],
        "leadership":       mental["leadership"],

        # --- DEVELOPMENT ---
        "potential_low":    potential["low"],
        "potential_high":   potential["high"],
        "arc_type":         potential["arc_type"],

        # --- GAME STATE ---
        "fatigue":          0.0,    # 0 = fresh, 1 = exhausted
        "foul_count":       0,      # fouls in current game
        "in_game":          True,   # on the floor or not
    }

    return player


# -----------------------------------------
# ATTRIBUTE GENERATORS BY POSITION
# Each position has realistic tendencies
# Average D1 player is roughly 9-11 in most categories
# -----------------------------------------

def rand_attr(base, spread=3):
    """Generates a rating centered on base with some spread. Clamped 1-20."""
    val = int(random.gauss(base, spread))
    return max(1, min(20, val))


def generate_shooting(position):
    """Shooting ratings vary heavily by position."""
    if position == "PG":
        return {
            "catch_and_shoot": rand_attr(11),
            "off_dribble":     rand_attr(12),
            "mid_range":       rand_attr(11),
            "three_point":     rand_attr(11),
            "free_throw":      rand_attr(12),
            "finishing":       rand_attr(11),
            "post_scoring":    rand_attr(7),
        }
    elif position == "SG":
        return {
            "catch_and_shoot": rand_attr(13),
            "off_dribble":     rand_attr(12),
            "mid_range":       rand_attr(12),
            "three_point":     rand_attr(12),
            "free_throw":      rand_attr(12),
            "finishing":       rand_attr(11),
            "post_scoring":    rand_attr(8),
        }
    elif position == "SF":
        return {
            "catch_and_shoot": rand_attr(11),
            "off_dribble":     rand_attr(10),
            "mid_range":       rand_attr(11),
            "three_point":     rand_attr(10),
            "free_throw":      rand_attr(11),
            "finishing":       rand_attr(12),
            "post_scoring":    rand_attr(10),
        }
    elif position == "PF":
        return {
            "catch_and_shoot": rand_attr(9),
            "off_dribble":     rand_attr(8),
            "mid_range":       rand_attr(10),
            "three_point":     rand_attr(8),
            "free_throw":      rand_attr(10),
            "finishing":       rand_attr(13),
            "post_scoring":    rand_attr(12),
        }
    else:  # C
        return {
            "catch_and_shoot": rand_attr(7),
            "off_dribble":     rand_attr(6),
            "mid_range":       rand_attr(8),
            "three_point":     rand_attr(6),
            "free_throw":      rand_attr(9),
            "finishing":       rand_attr(14),
            "post_scoring":    rand_attr(13),
        }


def generate_defense(position):
    """Defense ratings vary by position."""
    if position in ["PG", "SG"]:
        return {
            "on_ball_defense": rand_attr(10),
            "help_defense":    rand_attr(10),
            "shot_blocking":   rand_attr(5),
            "steal_tendency":  rand_attr(11),
            "foul_tendency":   rand_attr(10),
        }
    elif position == "SF":
        return {
            "on_ball_defense": rand_attr(11),
            "help_defense":    rand_attr(11),
            "shot_blocking":   rand_attr(8),
            "steal_tendency":  rand_attr(10),
            "foul_tendency":   rand_attr(10),
        }
    else:  # PF, C
        return {
            "on_ball_defense": rand_attr(10),
            "help_defense":    rand_attr(12),
            "shot_blocking":   rand_attr(12),
            "steal_tendency":  rand_attr(8),
            "foul_tendency":   rand_attr(11),
        }


def generate_rebounding(position):
    """Rebounding is a single rating -- bigs rebound more."""
    bases = {"PG": 7, "SG": 8, "SF": 10, "PF": 13, "C": 14}
    return rand_attr(bases.get(position, 10))


def generate_playmaking(position):
    """Playmaking varies heavily -- guards lead, bigs are limited."""
    if position == "PG":
        return {
            "passing":         rand_attr(13),
            "ball_handling":   rand_attr(13),
            "court_vision":    rand_attr(12),
            "decision_making": rand_attr(12),
        }
    elif position == "SG":
        return {
            "passing":         rand_attr(11),
            "ball_handling":   rand_attr(12),
            "court_vision":    rand_attr(10),
            "decision_making": rand_attr(11),
        }
    elif position == "SF":
        return {
            "passing":         rand_attr(10),
            "ball_handling":   rand_attr(10),
            "court_vision":    rand_attr(10),
            "decision_making": rand_attr(10),
        }
    else:  # PF, C
        return {
            "passing":         rand_attr(8),
            "ball_handling":   rand_attr(7),
            "court_vision":    rand_attr(8),
            "decision_making": rand_attr(9),
        }


def generate_athleticism(position):
    """Physical attributes -- guards are faster, bigs are stronger."""
    if position in ["PG", "SG"]:
        return {
            "speed":            rand_attr(13),
            "lateral_quickness":rand_attr(13),
            "strength":         rand_attr(9),
            "vertical":         rand_attr(12),
        }
    elif position == "SF":
        return {
            "speed":            rand_attr(11),
            "lateral_quickness":rand_attr(11),
            "strength":         rand_attr(11),
            "vertical":         rand_attr(11),
        }
    else:  # PF, C
        return {
            "speed":            rand_attr(9),
            "lateral_quickness":rand_attr(9),
            "strength":         rand_attr(13),
            "vertical":         rand_attr(10),
        }


def generate_mental():
    """Mental attributes -- hidden, narrow band effects."""
    return {
        "basketball_iq": rand_attr(10, 2),
        "clutch":        rand_attr(10, 2),
        "composure":     rand_attr(10, 2),
        "coachability":  rand_attr(10, 2),
        "work_ethic":    rand_attr(10, 2),
        "leadership":    rand_attr(10, 2),
    }


def generate_potential():
    """
    Potential is a range, not a single number -- per the Bible.
    Arc type determines how the player develops over their career.
    """
    arc = random.choice(ARC_TYPES)
    base = random.randint(8, 18)

    if arc == "bust":
        return {"low": max(1, base - 4), "high": base, "arc_type": arc}
    elif arc == "plateau":
        return {"low": base, "high": base + 1, "arc_type": arc}
    elif arc == "steady":
        return {"low": base, "high": base + 3, "arc_type": arc}
    elif arc == "overachiever":
        return {"low": base + 2, "high": base + 5, "arc_type": arc}
    else:  # late_bloomer
        return {"low": base - 2, "high": base + 6, "arc_type": arc}


# -----------------------------------------
# TEAM GENERATOR
# Creates a full roster of 13 players
# -----------------------------------------

def generate_team(name, prestige=10):
    """
    Generates a full college basketball roster.
    Prestige (1-20) shifts the quality of generated players up or down.
    """
    roster = []

    # Positional needs -- a real roster
    positions_needed = ["PG", "PG", "SG", "SG", "SF", "SF", "SF", "PF", "PF", "C", "C", "PG", "SG"]
    years = ["Freshman", "Sophomore", "Junior", "Senior"]

    for i, pos in enumerate(positions_needed):
        year = years[i % 4]
        player_name = name + " Player " + str(i + 1)

        # Prestige shifts base ratings up or down
        # Average D1 player is ~10. Elite program players average ~13-14.
        prestige_bonus = (prestige - 10) * 0.3

        player = create_player(player_name, pos, year)

        # Apply prestige bonus to key ratings
        for attr in ["catch_and_shoot", "off_dribble", "finishing", "on_ball_defense",
                     "help_defense", "rebounding", "passing", "ball_handling"]:
            player[attr] = max(1, min(20, int(player[attr] + prestige_bonus)))

        roster.append(player)

    return {"name": name, "prestige": prestige, "roster": roster}


def get_team_ratings(team):
    """
    Calculates average team ratings from the roster.
    Used by the game engine for team-level resolution.
    """
    roster = team["roster"]
    if not roster:
        return {"shooting": 10, "defense": 10, "rebounding": 10, "foul_draw": 10}

    avg_shooting = sum(
        (p["catch_and_shoot"] + p["off_dribble"] + p["finishing"]) / 3
        for p in roster
    ) / len(roster)

    avg_defense = sum(
        (p["on_ball_defense"] + p["help_defense"]) / 2
        for p in roster
    ) / len(roster)

    avg_rebounding = sum(p["rebounding"] for p in roster) / len(roster)

    avg_foul_draw = sum(p["finishing"] for p in roster) / len(roster)

    return {
        "name": team["name"],
        "shooting":   round(avg_shooting, 1),
        "defense":    round(avg_defense, 1),
        "rebounding": round(avg_rebounding, 1),
        "foul_draw":  round(avg_foul_draw, 1),
    }


def print_roster(team):
    """Prints a readable roster summary."""
    print("")
    print("=== " + team["name"] + " Roster (Prestige: " + str(team["prestige"]) + ") ===")
    print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
        "Name", "Pos", "Year", "Shoot", "Defense", "Reb", "Play"))
    print("-" * 80)
    for p in team["roster"]:
        avg_shoot = round((p["catch_and_shoot"] + p["finishing"] + p["three_point"]) / 3, 1)
        avg_def = round((p["on_ball_defense"] + p["help_defense"]) / 2, 1)
        avg_play = round((p["passing"] + p["ball_handling"]) / 2, 1)
        print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
            p["name"], p["position"], p["year"],
            avg_shoot, avg_def, p["rebounding"], avg_play))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    # Generate two teams at different prestige levels
    kentucky = generate_team("Kentucky", prestige=17)
    kansas_state = generate_team("Kansas State", prestige=13)
    average_d1 = generate_team("Average D1", prestige=10)

    # Print rosters
    print_roster(kentucky)
    print_roster(kansas_state)
    print_roster(average_d1)

    # Show team ratings summary
    print("")
    print("=== Team Rating Summaries ===")
    for team in [kentucky, kansas_state, average_d1]:
        ratings = get_team_ratings(team)
        print(team["name"] + " -- Shooting: " + str(ratings["shooting"]) +
              "  Defense: " + str(ratings["defense"]) +
              "  Rebounding: " + str(ratings["rebounding"]))
