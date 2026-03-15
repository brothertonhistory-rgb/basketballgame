import random
from names import generate_player_name

# -----------------------------------------
# COLLEGE HOOPS SIM -- Player System v0.2
# System 2 of the Design Bible
# All attributes on 1-20 scale. No overall rating.
# Now includes real names and heritage attribute.
# -----------------------------------------

POSITIONS = ["PG", "SG", "SF", "PF", "C"]
YEARS     = ["Freshman", "Sophomore", "Junior", "Senior"]
ARC_TYPES = ["bust", "plateau", "steady", "overachiever", "late_bloomer"]


def create_player(name, position, year, conference="",
                  shooting=None, defense=None, rebounding=None,
                  playmaking=None, athleticism=None, mental=None,
                  potential=None, heritage=None):

    if shooting    is None: shooting    = generate_shooting(position)
    if defense     is None: defense     = generate_defense(position)
    if rebounding  is None: rebounding  = generate_rebounding(position)
    if playmaking  is None: playmaking  = generate_playmaking(position)
    if athleticism is None: athleticism = generate_athleticism(position)
    if mental      is None: mental      = generate_mental()
    if potential   is None: potential   = generate_potential()

    # Generate real name if placeholder passed in or name is empty
    if not name or "Player" in name:
        generated_name, generated_heritage = generate_player_name(conference=conference)
        name = generated_name
        if heritage is None:
            heritage = generated_heritage
    elif heritage is None:
        _, heritage = generate_player_name(conference=conference)

    player = {
        # Identity
        "name":       name,
        "position":   position,
        "year":       year,
        "heritage":   heritage,    # Hidden -- drives name and eventually image gen

        # SHOOTING
        "catch_and_shoot": shooting["catch_and_shoot"],
        "off_dribble":     shooting["off_dribble"],
        "mid_range":       shooting["mid_range"],
        "three_point":     shooting["three_point"],
        "free_throw":      shooting["free_throw"],
        "finishing":       shooting["finishing"],
        "post_scoring":    shooting["post_scoring"],

        # PLAYMAKING
        "passing":         playmaking["passing"],
        "ball_handling":   playmaking["ball_handling"],
        "court_vision":    playmaking["court_vision"],
        "decision_making": playmaking["decision_making"],

        # DEFENSE
        "on_ball_defense": defense["on_ball_defense"],
        "help_defense":    defense["help_defense"],
        "rebounding":      rebounding,
        "shot_blocking":   defense["shot_blocking"],
        "steal_tendency":  defense["steal_tendency"],
        "foul_tendency":   defense["foul_tendency"],

        # PHYSICAL
        "speed":             athleticism["speed"],
        "lateral_quickness": athleticism["lateral_quickness"],
        "strength":          athleticism["strength"],
        "vertical":          athleticism["vertical"],

        # MENTAL -- Hidden
        "basketball_iq": mental["basketball_iq"],
        "clutch":        mental["clutch"],
        "composure":     mental["composure"],
        "coachability":  mental["coachability"],
        "work_ethic":    mental["work_ethic"],
        "leadership":    mental["leadership"],

        # DEVELOPMENT
        "potential_low":  potential["low"],
        "potential_high": potential["high"],
        "arc_type":       potential["arc_type"],

        # GAME STATE
        "fatigue":    0.0,
        "foul_count": 0,
        "in_game":    True,
    }

    return player


def rand_attr(base, spread=3):
    val = int(random.gauss(base, spread))
    return max(1, min(20, val))


def generate_shooting(position):
    if position == "PG":
        return {"catch_and_shoot": rand_attr(11), "off_dribble": rand_attr(12),
                "mid_range": rand_attr(11), "three_point": rand_attr(11),
                "free_throw": rand_attr(12), "finishing": rand_attr(11), "post_scoring": rand_attr(7)}
    elif position == "SG":
        return {"catch_and_shoot": rand_attr(13), "off_dribble": rand_attr(12),
                "mid_range": rand_attr(12), "three_point": rand_attr(12),
                "free_throw": rand_attr(12), "finishing": rand_attr(11), "post_scoring": rand_attr(8)}
    elif position == "SF":
        return {"catch_and_shoot": rand_attr(11), "off_dribble": rand_attr(10),
                "mid_range": rand_attr(11), "three_point": rand_attr(10),
                "free_throw": rand_attr(11), "finishing": rand_attr(12), "post_scoring": rand_attr(10)}
    elif position == "PF":
        return {"catch_and_shoot": rand_attr(9), "off_dribble": rand_attr(8),
                "mid_range": rand_attr(10), "three_point": rand_attr(8),
                "free_throw": rand_attr(10), "finishing": rand_attr(13), "post_scoring": rand_attr(12)}
    else:  # C
        return {"catch_and_shoot": rand_attr(7), "off_dribble": rand_attr(6),
                "mid_range": rand_attr(8), "three_point": rand_attr(6),
                "free_throw": rand_attr(9), "finishing": rand_attr(14), "post_scoring": rand_attr(13)}


def generate_defense(position):
    if position in ["PG", "SG"]:
        return {"on_ball_defense": rand_attr(10), "help_defense": rand_attr(10),
                "shot_blocking": rand_attr(5), "steal_tendency": rand_attr(11), "foul_tendency": rand_attr(10)}
    elif position == "SF":
        return {"on_ball_defense": rand_attr(11), "help_defense": rand_attr(11),
                "shot_blocking": rand_attr(8), "steal_tendency": rand_attr(10), "foul_tendency": rand_attr(10)}
    else:
        return {"on_ball_defense": rand_attr(10), "help_defense": rand_attr(12),
                "shot_blocking": rand_attr(12), "steal_tendency": rand_attr(8), "foul_tendency": rand_attr(11)}


def generate_rebounding(position):
    bases = {"PG": 7, "SG": 8, "SF": 10, "PF": 13, "C": 14}
    return rand_attr(bases.get(position, 10))


def generate_playmaking(position):
    if position == "PG":
        return {"passing": rand_attr(13), "ball_handling": rand_attr(13),
                "court_vision": rand_attr(12), "decision_making": rand_attr(12)}
    elif position == "SG":
        return {"passing": rand_attr(11), "ball_handling": rand_attr(12),
                "court_vision": rand_attr(10), "decision_making": rand_attr(11)}
    elif position == "SF":
        return {"passing": rand_attr(10), "ball_handling": rand_attr(10),
                "court_vision": rand_attr(10), "decision_making": rand_attr(10)}
    else:
        return {"passing": rand_attr(8), "ball_handling": rand_attr(7),
                "court_vision": rand_attr(8), "decision_making": rand_attr(9)}


def generate_athleticism(position):
    if position in ["PG", "SG"]:
        return {"speed": rand_attr(13), "lateral_quickness": rand_attr(13),
                "strength": rand_attr(9), "vertical": rand_attr(12)}
    elif position == "SF":
        return {"speed": rand_attr(11), "lateral_quickness": rand_attr(11),
                "strength": rand_attr(11), "vertical": rand_attr(11)}
    else:
        return {"speed": rand_attr(9), "lateral_quickness": rand_attr(9),
                "strength": rand_attr(13), "vertical": rand_attr(10)}


def generate_mental():
    return {
        "basketball_iq": rand_attr(10, 2), "clutch":       rand_attr(10, 2),
        "composure":     rand_attr(10, 2), "coachability": rand_attr(10, 2),
        "work_ethic":    rand_attr(10, 2), "leadership":   rand_attr(10, 2),
    }


def generate_potential():
    arc  = random.choice(ARC_TYPES)
    base = random.randint(8, 18)
    if arc == "bust":
        return {"low": max(1, base-4), "high": base,   "arc_type": arc}
    elif arc == "plateau":
        return {"low": base,           "high": base+1,  "arc_type": arc}
    elif arc == "steady":
        return {"low": base,           "high": base+3,  "arc_type": arc}
    elif arc == "overachiever":
        return {"low": base+2,         "high": base+5,  "arc_type": arc}
    else:  # late_bloomer
        return {"low": max(1, base-2), "high": base+6,  "arc_type": arc}


def generate_team(name, prestige=10, conference=""):
    """
    Generates a full 13-man roster.
    Now passes conference to name generator for realistic demographics.
    """
    roster = []
    positions_needed = ["PG","PG","SG","SG","SF","SF","SF","PF","PF","C","C","PG","SG"]
    years = ["Freshman","Sophomore","Junior","Senior"]

    for i, pos in enumerate(positions_needed):
        year = years[i % 4]
        prestige_bonus = (prestige - 10) * 0.3

        # Pass empty name so generator creates a real one
        player = create_player("", pos, year, conference=conference)

        for attr in ["catch_and_shoot","off_dribble","finishing","on_ball_defense",
                     "help_defense","rebounding","passing","ball_handling"]:
            player[attr] = max(1, min(20, int(player[attr] + prestige_bonus)))

        roster.append(player)

    return {"name": name, "prestige": prestige, "roster": roster}


def get_team_ratings(team):
    roster = team["roster"]
    if not roster:
        return {"shooting": 10, "defense": 10, "rebounding": 10, "foul_draw": 10}

    avg_shooting   = sum((p["catch_and_shoot"]+p["off_dribble"]+p["finishing"])/3 for p in roster) / len(roster)
    avg_defense    = sum((p["on_ball_defense"]+p["help_defense"])/2 for p in roster) / len(roster)
    avg_rebounding = sum(p["rebounding"] for p in roster) / len(roster)
    avg_foul_draw  = sum(p["finishing"] for p in roster) / len(roster)

    return {
        "name":       team["name"],
        "shooting":   round(avg_shooting, 1),
        "defense":    round(avg_defense, 1),
        "rebounding": round(avg_rebounding, 1),
        "foul_draw":  round(avg_foul_draw, 1),
    }


def print_roster(team):
    print("")
    print("=== " + team["name"] + " Roster (Prestige: " + str(team["prestige"]) + ") ===")
    print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
        "Name", "Pos", "Year", "Shoot", "Defense", "Reb", "Play"))
    print("-" * 80)
    for p in team["roster"]:
        avg_shoot = round((p["catch_and_shoot"]+p["finishing"]+p["three_point"])/3, 1)
        avg_def   = round((p["on_ball_defense"]+p["help_defense"])/2, 1)
        avg_play  = round((p["passing"]+p["ball_handling"])/2, 1)
        print("{:<25} {:<5} {:<12} {:<8} {:<8} {:<8} {:<8}".format(
            p["name"], p["position"], p["year"],
            avg_shoot, avg_def, p["rebounding"], avg_play))


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    kentucky    = generate_team("Kentucky",    prestige=17, conference="SEC")
    kansas_state = generate_team("Kansas State", prestige=13, conference="Big 12")
    montana     = generate_team("Montana",     prestige=10, conference="Big Sky")

    print_roster(kentucky)
    print_roster(kansas_state)
    print_roster(montana)

    print("")
    print("=== Team Rating Summaries ===")
    for team in [kentucky, kansas_state, montana]:
        r = get_team_ratings(team)
        print(team["name"] + " -- Shooting: " + str(r["shooting"]) +
              "  Defense: " + str(r["defense"]) +
              "  Rebounding: " + str(r["rebounding"]))
