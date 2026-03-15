import random
from player import generate_team, get_team_ratings

# -----------------------------------------
# COLLEGE HOOPS SIM -- Game Engine v0.6
# System 1 of the Design Bible
#
# v0.6 CHANGES -- Individual players now on the floor.
#
#   CORE CHANGE:
#     Each possession uses specific players from the active lineup.
#     A catch-and-shoot specialist uses his catch_and_shoot attribute.
#     A post scorer uses post_scoring vs the defender's strength.
#     The best rebounder gets the ball most often.
#
#   NEW SYSTEMS:
#     build_lineup()            -- 5 players on floor from minutes allocation
#     _select_shooter()         -- who takes each shot type
#     _select_defender()        -- automatic positional matchup
#     _select_rebounder()       -- weighted by rebounding attribute
#     accumulate_game_stats()   -- writes to player game_stats
#     initialize_season_stats() -- called once per season per program
#     finalize_season_stats()   -- calculates per-game averages at season end
#     commit_game_to_season()   -- adds game totals to season totals
#     get_box_score()           -- formats game stats
#     print_box_score()         -- prints readable box score
#
#   STAT STRUCTURE:
#     player["game_stats"]      -- current game accumulator, reset each game
#     player["career_stats"]    -- list of completed season stat dicts
#     program["season_stats"]   -- {player_name: season totals dict}
#
#   ASSISTS: not tracked until play-by-play exists.
#     Field present as 0. Never estimate what can't be measured.
#
#   FOUL-OUTS: tracked but not enforced until depth charts exist.
#     foul_count increments per player. Players with 5 fouls draw
#     fewer fouls (they play more carefully) but stay on the floor.
#
# v0.5: Cohesion modifiers. v0.4: 1-1000 scale.
# -----------------------------------------


# Positional matchup fallback order
POSITION_MATCHUP_ORDER = {
    "PG": ["PG", "SG", "SF"],
    "SG": ["SG", "PG", "SF"],
    "SF": ["SF", "SG", "PF"],
    "PF": ["PF", "SF", "C"],
    "C":  ["C",  "PF", "SF"],
}

# Which player attribute drives each shot type
SHOT_ATTR_MAP = {
    "catch_and_shoot": "catch_and_shoot",
    "off_dribble":     "off_dribble",
    "mid_range":       "mid_range",
    "post_up":         "post_scoring",
    "at_rim":          "finishing",
    "floater":         "finishing",
    "putback":         "finishing",
    "free_throw":      "free_throw",
}

# Which defender attribute contests each shot type
DEFEND_ATTR_MAP = {
    "catch_and_shoot": "on_ball_defense",
    "off_dribble":     "lateral_quickness",
    "mid_range":       "on_ball_defense",
    "post_up":         "strength",
    "at_rim":          "shot_blocking",
    "floater":         "help_defense",
    "putback":         "rebounding",
    "free_throw":      None,
}

# Positional shot-taking tendencies
SHOT_POSITION_WEIGHTS = {
    "catch_and_shoot": {"PG": 15, "SG": 30, "SF": 25, "PF": 20, "C": 10},
    "off_dribble":     {"PG": 35, "SG": 30, "SF": 20, "PF": 10, "C":  5},
    "mid_range":       {"PG": 20, "SG": 25, "SF": 20, "PF": 20, "C": 15},
    "post_up":         {"PG":  5, "SG":  5, "SF": 15, "PF": 35, "C": 40},
    "at_rim":          {"PG": 15, "SG": 15, "SF": 20, "PF": 25, "C": 25},
    "floater":         {"PG": 35, "SG": 25, "SF": 20, "PF": 15, "C":  5},
}


# -----------------------------------------
# STAT MANAGEMENT
# -----------------------------------------

def initialize_season_stats(program, season_year):
    """
    Called once per season per program before games begin.
    Resets game_stats on all players.
    Initializes season_stats dict on program.
    Does NOT reset career_stats -- those persist forever.
    """
    roster = program.get("roster", [])
    if "season_stats" not in program:
        program["season_stats"] = {}

    for player in roster:
        name = player["name"]
        player["game_stats"] = _empty_game_stats()
        if name not in program["season_stats"]:
            program["season_stats"][name] = _empty_season_stats(season_year)
        if "career_stats" not in player:
            player["career_stats"] = []

    return program


def finalize_season_stats(program, season_year):
    """
    Called at season end. Appends completed season to career_stats.
    Calculates per-game averages from season totals.
    """
    roster      = program.get("roster", [])
    season_data = program.get("season_stats", {})

    for player in roster:
        name   = player["name"]
        season = season_data.get(name)
        if not season:
            continue

        games = max(1, season["games"])

        season["ppg"]  = round(season["points"]    / games, 1)
        season["rpg"]  = round(season["rebounds"]  / games, 1)
        season["apg"]  = round(season["assists"]   / games, 1)
        season["spg"]  = round(season["steals"]    / games, 1)
        season["bpg"]  = round(season["blocks"]    / games, 1)
        season["topg"] = round(season["turnovers"] / games, 1)
        season["fpg"]  = round(season["fouls"]     / games, 1)
        season["mpg"]  = round(season["minutes"]   / games, 1)

        season["fg_pct"]    = round(season["fg_made"]    / max(1, season["fg_att"])    * 100, 1)
        season["three_pct"] = round(season["three_made"] / max(1, season["three_att"]) * 100, 1)
        season["ft_pct"]    = round(season["ft_made"]    / max(1, season["ft_att"])    * 100, 1)

        if "career_stats" not in player:
            player["career_stats"] = []
        player["career_stats"].append(dict(season))

    return program


def _empty_game_stats():
    return {
        "points": 0, "rebounds": 0, "assists": 0,
        "steals": 0, "blocks": 0, "turnovers": 0,
        "fouls": 0, "minutes": 0.0,
        "fg_made": 0, "fg_att": 0,
        "three_made": 0, "three_att": 0,
        "ft_made": 0, "ft_att": 0,
    }


def _empty_season_stats(season_year):
    return {
        "season": season_year, "games": 0,
        "points": 0, "rebounds": 0, "assists": 0,
        "steals": 0, "blocks": 0, "turnovers": 0,
        "fouls": 0, "minutes": 0.0,
        "fg_made": 0, "fg_att": 0,
        "three_made": 0, "three_att": 0,
        "ft_made": 0, "ft_att": 0,
        "ppg": 0.0, "rpg": 0.0, "apg": 0.0,
        "spg": 0.0, "bpg": 0.0, "topg": 0.0,
        "fpg": 0.0, "mpg": 0.0,
        "fg_pct": 0.0, "three_pct": 0.0, "ft_pct": 0.0,
    }


def accumulate_game_stats(player, stat_key, value=1):
    """Adds value to a player's current game stats."""
    if "game_stats" not in player:
        player["game_stats"] = _empty_game_stats()
    player["game_stats"][stat_key] = player["game_stats"].get(stat_key, 0) + value


def commit_game_to_season(program):
    """
    Called after each game. Adds game stats to season totals.
    Resets game_stats for the next game.
    """
    roster      = program.get("roster", [])
    season_data = program.get("season_stats", {})

    for player in roster:
        name       = player["name"]
        game_stats = player.get("game_stats", {})

        if not game_stats or game_stats.get("minutes", 0) <= 0:
            player["game_stats"] = _empty_game_stats()
            continue

        if name not in season_data:
            season_data[name] = _empty_season_stats(0)

        season_data[name]["games"] += 1
        for key in ["points", "rebounds", "assists", "steals", "blocks",
                    "turnovers", "fouls", "minutes",
                    "fg_made", "fg_att", "three_made", "three_att",
                    "ft_made", "ft_att"]:
            season_data[name][key] = (
                season_data[name].get(key, 0) + game_stats.get(key, 0)
            )

        player["game_stats"] = _empty_game_stats()

    program["season_stats"] = season_data
    return program


# -----------------------------------------
# LINEUP MANAGEMENT
# -----------------------------------------

def build_lineup(program):
    """
    Builds active lineup from minutes allocation.
    Returns (starters list of 5, bench list).
    """
    roster     = program.get("roster", [])
    allocation = program.get("minutes_allocation", {})

    if not roster:
        return [], []

    sorted_roster = sorted(
        roster,
        key=lambda p: allocation.get(p["name"], 0),
        reverse=True
    )

    starters = sorted_roster[:5]
    bench    = sorted_roster[5:]
    return starters, bench


def _get_rotation_segment(possession_num, total_possessions,
                           starters, bench, rotation_size, rotation_flex):
    """
    Returns active 5-player lineup for this point in the game.
    Starters open and close. Bench rotates in the middle.
    """
    progress = possession_num / max(1, total_possessions)

    if progress > 0.85:
        return list(starters)

    if 0.20 < progress <= 0.85 and bench:
        bench_slots = min(rotation_flex // 3, len(bench), 2)
        if bench_slots > 0:
            active = list(starters)
            for i in range(bench_slots):
                if i < len(bench) and (4 - i) >= 0:
                    active[4 - i] = bench[i]
            return active

    return list(starters)


# -----------------------------------------
# PLAYER SELECTION
# -----------------------------------------

def _select_shooter(lineup, shot_type):
    """Picks which player takes this shot type. Weighted by position and attribute."""
    if not lineup:
        return lineup[0] if lineup else None

    position_weights = SHOT_POSITION_WEIGHTS.get(shot_type, {})
    attr_key         = SHOT_ATTR_MAP.get(shot_type, "finishing")

    scores = []
    for player in lineup:
        pos_w    = position_weights.get(player.get("position", "SF"), 10)
        attr_val = player.get(attr_key, 400)
        scores.append(pos_w * (attr_val / 500.0))

    total = sum(scores)
    if total <= 0:
        return random.choice(lineup)
    return random.choices(lineup, weights=scores, k=1)[0]


def _select_defender(shooter, defending_lineup):
    """Automatic positional matchup. Falls back to closest position."""
    if not defending_lineup:
        return defending_lineup[0] if defending_lineup else None

    shooter_pos   = shooter.get("position", "SF")
    matchup_order = POSITION_MATCHUP_ORDER.get(shooter_pos, ["SF", "SG", "PF"])

    for target_pos in matchup_order:
        for player in defending_lineup:
            if player.get("position") == target_pos:
                return player

    return random.choice(defending_lineup)


def _select_rebounder(lineup, is_offensive):
    """Picks rebounder weighted by rebounding attribute and position."""
    if not lineup:
        return None

    pos_bonus = {"C": 1.3, "PF": 1.2, "SF": 1.0, "SG": 0.85, "PG": 0.75}
    scores    = [
        player.get("rebounding", 400) * pos_bonus.get(player.get("position", "SF"), 1.0)
        for player in lineup
    ]
    total = sum(scores)
    if total <= 0:
        return random.choice(lineup)
    return random.choices(lineup, weights=scores, k=1)[0]


def _select_steal_player(defending_lineup):
    """Picks who gets a steal. Weighted by steal_tendency."""
    if not defending_lineup:
        return None
    scores = [max(1, p.get("steal_tendency", 300)) for p in defending_lineup]
    return random.choices(defending_lineup, weights=scores, k=1)[0]


def _select_block_player(defending_lineup):
    """Picks who gets a block. Weighted by shot_blocking."""
    if not defending_lineup:
        return None
    scores = [max(1, p.get("shot_blocking", 200)) for p in defending_lineup]
    return random.choices(defending_lineup, weights=scores, k=1)[0]


# -----------------------------------------
# COACHING GAME PROFILE (unchanged from v0.5)
# -----------------------------------------

def build_game_profile(team):
    coach = team.get("coach", {})
    if not coach:
        return _neutral_profile()

    pace                 = coach.get("pace", 50)
    possessions_modifier = int((pace - 50) / 5)
    shot_profile         = coach.get("shot_profile", 50)
    personnel            = coach.get("personnel", 50)

    shot_weights = {
        "at_rim":          max(5, 15 + int((shot_profile / 100) * 20)),
        "catch_and_shoot": max(5, 10 + int((shot_profile / 100) * 25)),
        "mid_range":       max(5, 20 - int((shot_profile / 100) * 15)),
        "post_up":         max(3, 20 - int((shot_profile / 100) * 15)),
        "off_dribble":     max(5, 10 + int((personnel / 100) * 10)),
        "floater":         8,
    }

    pressure      = coach.get("pressure", 50)
    philosophy    = coach.get("philosophy", 50)
    # Turnover rate per possession. Real D1 averages ~18% of possessions.
    # The old formula (0.16 + pressure*0.08 + philosophy*0.04) was too high
    # when both teams apply it simultaneously. Reduced base to 0.10.
    turnover_rate = 0.10 + (pressure / 100) * 0.05 + (philosophy / 100) * 0.025

    off_rebounding     = coach.get("off_rebounding", 50)
    off_rebound_bonus  = (off_rebounding - 50) / 100 * 0.06
    shot_selection     = coach.get("shot_selection", 50)
    shot_quality_bonus = (shot_selection - 50) / 100 * 0.04

    return {
        "possessions_modifier": possessions_modifier,
        "shot_weights":         shot_weights,
        "turnover_rate":        round(turnover_rate, 3),
        "off_rebound_bonus":    round(off_rebound_bonus, 3),
        "shot_quality_bonus":   round(shot_quality_bonus, 3),
        "rebounding_mod":       0.0,
    }


def _neutral_profile():
    return {
        "possessions_modifier": 0,
        "shot_weights": {
            "at_rim": 20, "catch_and_shoot": 20, "mid_range": 15,
            "post_up": 15, "off_dribble": 15, "floater": 8,
        },
        "turnover_rate": 0.12, "off_rebound_bonus": 0.0,
        "shot_quality_bonus": 0.0, "rebounding_mod": 0.0,
    }


# -----------------------------------------
# SHOT RESOLUTION (individual player)
# -----------------------------------------

def resolve_shot(shooter, defender, shot_type, fatigue=0, momentum=0,
                 shot_quality_bonus=0.0):
    """
    Resolves a shot between two specific players.
    Returns (result, points, is_three).
    result is "make", "miss", or "foul".
    """
    shoot_attr = SHOT_ATTR_MAP.get(shot_type, "finishing")
    shoot_val  = shooter.get(shoot_attr, 400)

    base_prob = 0.32 + (shoot_val / 1000) * 0.35

    shot_type_mods = {
        "catch_and_shoot": 0.05, "off_dribble": -0.04,
        "post_up": -0.02, "putback": 0.03, "floater": -0.03,
        "at_rim": 0.07, "mid_range": -0.01,
    }
    base_prob += shot_type_mods.get(shot_type, 0)
    base_prob += shot_quality_bonus

    defend_attr = DEFEND_ATTR_MAP.get(shot_type)
    if defender and defend_attr:
        defend_val      = defender.get(defend_attr, 400)
        contest_penalty = (defend_val / 1000) * 0.16
        base_prob      -= contest_penalty

    endurance    = shooter.get("endurance", 500)
    fatigue_mult = max(0.5, endurance / 500.0)
    base_prob   -= fatigue * 0.04 * (1.0 / fatigue_mult)
    base_prob   += momentum * 0.03

    iq        = shooter.get("basketball_iq", 10)
    base_prob += (iq - 10) / 10.0 * 0.02

    base_prob = max(0.05, min(0.92, base_prob))

    foul_draw     = shooter.get("finishing", 400)
    foul_count    = shooter.get("foul_count", 0)
    foul_modifier = max(0.5, 1.0 - (foul_count * 0.08))
    foul_chance   = (0.025 + (foul_draw / 1000) * 0.055) * foul_modifier

    if random.random() < foul_chance:
        return "foul", 0, False

    if random.random() < base_prob:
        is_three = (shot_type == "catch_and_shoot" and random.random() < 0.58)
        return "make", (3 if is_three else 2), is_three
    else:
        return "miss", 0, False


# -----------------------------------------
# REBOUND RESOLUTION (individual player)
# -----------------------------------------

def resolve_rebound(offense_lineup, defense_lineup,
                    off_rebound_bonus=0.0, rebounding_mod=0.0):
    """
    Resolves who gets the rebound and which specific player.
    Returns (type, player_dict).
    """
    avg_off_reb = (sum(p.get("rebounding", 400) for p in offense_lineup) /
                   max(1, len(offense_lineup))) if offense_lineup else 400

    off_chance = 0.27 + (avg_off_reb / 1000) * 0.08 + off_rebound_bonus + rebounding_mod
    off_chance = max(0.05, min(0.50, off_chance))

    if random.random() < off_chance:
        return "offensive", _select_rebounder(offense_lineup, True)
    else:
        return "defensive", _select_rebounder(defense_lineup, False)


# -----------------------------------------
# POSSESSION RESOLUTION (individual player)
# -----------------------------------------

def simulate_possession(offense_lineup, defense_lineup,
                        offense_profile, defense_profile,
                        momentum=0, fatigue=0,
                        possession_num=0, total_possessions=68):
    """
    Simulates one offensive possession with specific players.
    Returns outcome dict with player attribution for stat tracking.
    """
    empty = {"outcome": "turnover", "points": 0, "shot_type": "none",
             "shooter": None, "defender": None, "rebounder": None,
             "steal_by": None, "block_by": None,
             "is_three": False, "ft_made": 0, "ft_att": 0}

    if not offense_lineup or not defense_lineup:
        return empty

    # --- TURNOVER ---
    if random.random() < defense_profile["turnover_rate"]:
        # Distribute turnovers weighted by inverse ball handling
        # Poor ball handlers turn it over more
        to_scores = []
        for player in offense_lineup:
            bh = player.get("ball_handling", 400)
            # Higher ball handling = LESS likely to turn it over
            # Weight = inverse: 1000 - bh, so bad handlers get more TOs
            to_scores.append(max(50, 1000 - bh))
        ball_handler = random.choices(offense_lineup, weights=to_scores, k=1)[0]

        steal_player = None
        if random.random() < 0.45:
            steal_player = _select_steal_player(defense_lineup)
            if steal_player:
                accumulate_game_stats(steal_player, "steals")
        accumulate_game_stats(ball_handler, "turnovers")
        return {**empty, "shooter": ball_handler, "steal_by": steal_player}

    # --- SHOT SELECTION ---
    shot_types = list(offense_profile["shot_weights"].keys())
    shot_wts   = list(offense_profile["shot_weights"].values())
    shot_type  = random.choices(shot_types, weights=shot_wts, k=1)[0]

    shooter  = _select_shooter(offense_lineup, shot_type)
    defender = _select_defender(shooter, defense_lineup)

    result, points, is_three = resolve_shot(
        shooter, defender, shot_type, fatigue, momentum,
        shot_quality_bonus=offense_profile["shot_quality_bonus"]
    )

    if result == "make":
        accumulate_game_stats(shooter, "points", points)
        accumulate_game_stats(shooter, "fg_made")
        accumulate_game_stats(shooter, "fg_att")
        if is_three:
            accumulate_game_stats(shooter, "three_made")
            accumulate_game_stats(shooter, "three_att")
        return {"outcome": "score", "points": points, "shot_type": shot_type,
                "shooter": shooter, "defender": defender, "rebounder": None,
                "steal_by": None, "block_by": None,
                "is_three": is_three, "ft_made": 0, "ft_att": 0}

    elif result == "foul":
        ft_att         = 2
        ft_make_chance = shooter.get("free_throw", 400) / 1000 * 0.6 + 0.4
        ft_made        = sum(1 for _ in range(ft_att)
                             if random.random() < ft_make_chance)
        if defender:
            defender["foul_count"] = defender.get("foul_count", 0) + 1
            accumulate_game_stats(defender, "fouls")
        accumulate_game_stats(shooter, "points", ft_made)
        accumulate_game_stats(shooter, "ft_made", ft_made)
        accumulate_game_stats(shooter, "ft_att",  ft_att)
        return {"outcome": "foul", "points": ft_made, "shot_type": shot_type,
                "shooter": shooter, "defender": defender, "rebounder": None,
                "steal_by": None, "block_by": None,
                "is_three": False, "ft_made": ft_made, "ft_att": ft_att}

    else:  # miss
        accumulate_game_stats(shooter, "fg_att")
        if shot_type == "catch_and_shoot":
            accumulate_game_stats(shooter, "three_att")

        # Block check
        block_player = None
        if shot_type in ("at_rim", "floater", "post_up") and defender:
            block_chance = (defender.get("shot_blocking", 200) / 1000) * 0.12
            if random.random() < block_chance:
                block_player = _select_block_player(defense_lineup)
                if block_player:
                    accumulate_game_stats(block_player, "blocks")

        # Rebound
        reb_type, rebounder = resolve_rebound(
            offense_lineup, defense_lineup,
            off_rebound_bonus=offense_profile["off_rebound_bonus"],
            rebounding_mod=offense_profile.get("rebounding_mod", 0.0)
        )
        if rebounder:
            accumulate_game_stats(rebounder, "rebounds")

        if reb_type == "offensive" and rebounder:
            pb_defender        = _select_defender(rebounder, defense_lineup)
            result2, pts2, _   = resolve_shot(rebounder, pb_defender, "putback",
                                               fatigue + 0.1, momentum)
            if result2 == "make":
                accumulate_game_stats(rebounder, "points", pts2)
                accumulate_game_stats(rebounder, "fg_made")
                accumulate_game_stats(rebounder, "fg_att")
                return {"outcome": "score", "points": pts2, "shot_type": "putback",
                        "shooter": rebounder, "defender": pb_defender,
                        "rebounder": rebounder, "steal_by": None,
                        "block_by": block_player, "is_three": False,
                        "ft_made": 0, "ft_att": 0}
            else:
                accumulate_game_stats(rebounder, "fg_att")

        return {"outcome": "miss", "points": 0, "shot_type": shot_type,
                "shooter": shooter, "defender": defender,
                "rebounder": rebounder, "steal_by": None,
                "block_by": block_player, "is_three": False,
                "ft_made": 0, "ft_att": 0}


# -----------------------------------------
# PERIOD SIMULATION
# -----------------------------------------

def simulate_period(home_lineup, away_lineup, home_bench, away_bench,
                    possessions, home_score, away_score,
                    home_momentum, away_momentum,
                    home_profile, away_profile,
                    home_coach, away_coach,
                    fatigue_base=0):
    """Simulates one period with individual players and rotation."""
    home_rot_size = home_coach.get("rotation_size", 8) if home_coach else 8
    away_rot_size = away_coach.get("rotation_size", 8) if away_coach else 8
    home_rot_flex = home_coach.get("rotation_flexibility", 5) if home_coach else 5
    away_rot_flex = away_coach.get("rotation_flexibility", 5) if away_coach else 5

    mins_per_possession = 40.0 / max(1, possessions)

    for i in range(possessions):
        fatigue = fatigue_base + (i / (possessions * 2))

        home_active = _get_rotation_segment(
            i, possessions, home_lineup, home_bench,
            home_rot_size, home_rot_flex)
        away_active = _get_rotation_segment(
            i, possessions, away_lineup, away_bench,
            away_rot_size, away_rot_flex)

        home_mom_mod = min(0.3, max(-0.3, home_momentum * 0.3))
        away_mom_mod = min(0.3, max(-0.3, away_momentum * 0.3))

        for p in home_active:
            accumulate_game_stats(p, "minutes", mins_per_possession)
        for p in away_active:
            accumulate_game_stats(p, "minutes", mins_per_possession)

        # Home offense
        home_result = simulate_possession(
            home_active, away_active,
            home_profile, away_profile,
            home_mom_mod, fatigue, i, possessions)
        home_score += home_result["points"]

        if home_result["outcome"] == "score":
            home_momentum = min(1.0, home_momentum + 0.2)
            away_momentum = max(-1.0, away_momentum - 0.1)
        else:
            home_momentum = max(-1.0, home_momentum - 0.1)

        # Away offense
        away_result = simulate_possession(
            away_active, home_active,
            away_profile, home_profile,
            away_mom_mod, fatigue, i, possessions)
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

def simulate_game(home_team, away_team, possessions=None, verbose=True,
                  season_year=2024):
    """
    Simulates a full game. Individual players on the floor.
    Stats accumulate per player. Box score generated.

    Returns game result dict.
    """
    from cohesion import get_cohesion_modifiers

    # Legacy fallback for simple rating dicts
    if "roster" not in home_team or "roster" not in away_team:
        return _simulate_game_legacy(home_team, away_team, possessions, verbose)

    home_lineup, home_bench = build_lineup(home_team)
    away_lineup, away_bench = build_lineup(away_team)

    if not home_lineup or not away_lineup:
        return _simulate_game_legacy(home_team, away_team, possessions, verbose)

    home_coach = home_team.get("coach", {})
    away_coach = away_team.get("coach", {})

    home_cohesion = get_cohesion_modifiers(home_team)
    away_cohesion = get_cohesion_modifiers(away_team)

    home_profile = build_game_profile(home_team)
    away_profile = build_game_profile(away_team)
    home_profile = _apply_cohesion_to_profile(home_profile, home_cohesion)
    away_profile = _apply_cohesion_to_profile(away_profile, away_cohesion)

    if possessions is None:
        base_possessions = 68
        pace_adjustment  = (home_profile["possessions_modifier"] +
                            away_profile["possessions_modifier"]) // 2
        possessions = max(55, min(82, base_possessions + pace_adjustment))

    home_momentum = 0
    away_momentum = 0
    home_name     = home_team.get("name", "Home")
    away_name     = away_team.get("name", "Away")

    if verbose:
        print("")
        print(home_name + " vs " + away_name)
        home_coh = home_team.get("cohesion_tier", "?")
        away_coh = away_team.get("cohesion_tier", "?")
        print("  " + home_coach.get("archetype", "?").replace("_", " ") +
              " vs " + away_coach.get("archetype", "?").replace("_", " ") +
              "  |  " + str(possessions) + " poss" +
              "  |  cohesion: " + home_coh + " / " + away_coh)
        print("  Starters: " +
              ", ".join(p["name"].split()[0] + "(" + p["position"] + ")"
                        for p in home_lineup) + "  vs  " +
              ", ".join(p["name"].split()[0] + "(" + p["position"] + ")"
                        for p in away_lineup))
        print("----------------------------------------")

    home_score, away_score, home_momentum, away_momentum = simulate_period(
        home_lineup, away_lineup, home_bench, away_bench,
        possessions, 0, 0, home_momentum, away_momentum,
        home_profile, away_profile, home_coach, away_coach, fatigue_base=0)

    ot_periods = 0
    while home_score == away_score:
        ot_periods += 1
        if ot_periods > 4:
            home_score += 1
            break
        if verbose:
            print("  -- Overtime " + str(ot_periods) + " --")
        home_score, away_score, home_momentum, away_momentum = simulate_period(
            home_lineup, away_lineup, home_bench, away_bench,
            6, home_score, away_score, home_momentum, away_momentum,
            home_profile, away_profile, home_coach, away_coach, fatigue_base=0.7)

    ot_label = ""
    if ot_periods == 1: ot_label = " (OT)"
    elif ot_periods > 1: ot_label = " (" + str(ot_periods) + "OT)"

    if verbose:
        print("Final" + ot_label + ": " + home_name + " " +
              str(home_score) + ", " + away_name + " " + str(away_score))

    # Print box scores BEFORE commit clears game_stats
    if verbose:
        print_box_score(home_team)
        print_box_score(away_team)

    commit_game_to_season(home_team)
    commit_game_to_season(away_team)

    return {
        "home": home_score, "away": away_score, "ot": ot_periods,
        "home_name": home_name, "away_name": away_name,
        "possessions": possessions,
    }


def _simulate_game_legacy(home_team, away_team, possessions=None, verbose=False):
    """Fallback for simple rating dicts without rosters."""
    home_ratings = get_team_ratings(home_team) if "roster" in home_team else home_team
    away_ratings = get_team_ratings(away_team) if "roster" in away_team else away_team
    home_profile = build_game_profile(home_team)
    away_profile = build_game_profile(away_team)

    if possessions is None:
        pace_adj    = (home_profile["possessions_modifier"] +
                       away_profile["possessions_modifier"]) // 2
        possessions = max(55, min(82, 68 + pace_adj))

    home_score = away_score = 0
    for _ in range(possessions):
        for ratings, profile, score_list in [
            (home_ratings, home_profile, "home"),
            (away_ratings, away_profile, "away")
        ]:
            opp = away_ratings if score_list == "home" else home_ratings
            if random.random() >= profile["turnover_rate"]:
                shot_types = list(profile["shot_weights"].keys())
                shot_type  = random.choices(shot_types,
                                            weights=list(profile["shot_weights"].values()),
                                            k=1)[0]
                prob = max(0.05, min(0.92,
                    0.38 + (ratings.get("shooting",500)/1000)*0.25
                         - (opp.get("defense",500)/1000)*0.14))
                if random.random() < prob:
                    pts = 3 if shot_type == "catch_and_shoot" and random.random() < 0.55 else 2
                    if score_list == "home": home_score += pts
                    else:                   away_score += pts

    if home_score == away_score:
        home_score += 1

    return {
        "home": home_score, "away": away_score, "ot": 0,
        "home_name": home_ratings.get("name", "Home"),
        "away_name": away_ratings.get("name", "Away"),
        "possessions": possessions,
    }


def _apply_cohesion_to_profile(profile, cohesion_mods):
    if not cohesion_mods:
        profile["rebounding_mod"] = 0.0
        return profile
    profile["turnover_rate"] = max(0.08, min(0.35,
        profile["turnover_rate"] + cohesion_mods.get("turnover_rate_mod", 0.0)))
    profile["shot_quality_bonus"] = round(
        profile.get("shot_quality_bonus", 0.0) +
        cohesion_mods.get("shot_quality_mod", 0.0), 4)
    profile["rebounding_mod"] = cohesion_mods.get("rebounding_mod", 0.0)
    return profile


# -----------------------------------------
# BOX SCORE
# -----------------------------------------

def get_box_score(program):
    """Returns formatted box score dict from current game_stats."""
    roster = program.get("roster", [])
    lines  = []
    for player in roster:
        gs = player.get("game_stats", {})
        if gs.get("minutes", 0) < 0.5:
            continue
        lines.append({
            "name":     player["name"],
            "position": player["position"],
            "year":     player["year"],
            "min":      round(gs.get("minutes", 0), 1),
            "pts":      gs.get("points", 0),
            "reb":      gs.get("rebounds", 0),
            "stl":      gs.get("steals", 0),
            "blk":      gs.get("blocks", 0),
            "to":       gs.get("turnovers", 0),
            "foul":     gs.get("fouls", 0),
            "fg":       str(gs.get("fg_made",0)) + "/" + str(gs.get("fg_att",0)),
            "3pt":      str(gs.get("three_made",0)) + "/" + str(gs.get("three_att",0)),
            "ft":       str(gs.get("ft_made",0)) + "/" + str(gs.get("ft_att",0)),
        })
    lines.sort(key=lambda x: x["pts"], reverse=True)
    return {"team": program.get("name", "Unknown"), "players": lines}


def print_box_score(program):
    """Prints a readable box score."""
    box = get_box_score(program)
    print("")
    print("  " + box["team"] + " Box Score")
    print("  {:<22} {:<4} {:<5} {:<4} {:<4} {:<4} {:<4} {:<4} {:<8} {:<7} {:<7}".format(
        "Player", "Pos", "Min", "Pts", "Reb", "Stl", "Blk", "TO", "FG", "3PT", "FT"))
    print("  " + "-" * 80)
    total_pts = 0
    for p in box["players"]:
        print("  {:<22} {:<4} {:<5} {:<4} {:<4} {:<4} {:<4} {:<4} {:<8} {:<7} {:<7}".format(
            p["name"][:21], p["position"], str(p["min"]),
            str(p["pts"]), str(p["reb"]), str(p["stl"]),
            str(p["blk"]), str(p["to"]), p["fg"], p["3pt"], p["ft"]))
        total_pts += p["pts"]
    print("  " + "-" * 80)
    print("  Team total: " + str(total_pts) + " points")


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from roster_minutes import allocate_minutes
    from cohesion import update_cohesion

    print("=" * 65)
    print("  GAME ENGINE v0.6 -- INDIVIDUAL PLAYER TEST")
    print("=" * 65)

    print("Loading programs...")
    all_programs = build_all_d1_programs()

    print("Setting up rosters, minutes, cohesion, stats...")
    for program in all_programs:
        allocate_minutes(program)
        update_cohesion(program, previous_minutes=None)
        initialize_season_stats(program, season_year=2024)

    kentucky = next(p for p in all_programs if p["name"] == "Kentucky")
    duke     = next(p for p in all_programs if p["name"] == "Duke")
    wagner   = next(p for p in all_programs if p["name"] == "Wagner")
    gonzaga  = next(p for p in all_programs if p["name"] == "Gonzaga")

    print("")
    print("=== GAME 1: Kentucky vs Duke ===")
    result = simulate_game(kentucky, duke, verbose=True, season_year=2024)

    print("")
    print("=== GAME 2: Wagner vs Gonzaga ===")
    result2 = simulate_game(wagner, gonzaga, verbose=True, season_year=2024)

    print("")
    print("=== SCORE PROFILE -- 50 games Kentucky vs Duke ===")
    for program in [kentucky, duke]:
        initialize_season_stats(program, season_year=2024)

    scores = []
    for _ in range(50):
        r = simulate_game(kentucky, duke, verbose=False, season_year=2024)
        scores.append(r)

    home_wins = sum(1 for r in scores if r["home"] > r["away"])
    avg_home  = sum(r["home"] for r in scores) / 50
    avg_away  = sum(r["away"] for r in scores) / 50
    avg_poss  = sum(r["possessions"] for r in scores) / 50

    print("  Home wins:       " + str(home_wins) + "/50")
    print("  Avg score:       " + str(round(avg_home,1)) +
          " - " + str(round(avg_away,1)))
    print("  Avg possessions: " + str(round(avg_poss,1)))

    print("")
    print("=== SEASON STATS after 50 games (Kentucky top players) ===")
    finalize_season_stats(kentucky, season_year=2024)
    season = kentucky.get("season_stats", {})
    sorted_players = sorted(
        [(name, stats) for name, stats in season.items()
         if stats.get("games", 0) > 0],
        key=lambda x: x[1].get("points", 0),
        reverse=True
    )
    print("  {:<22} {:<5} {:<5} {:<5} {:<5} {:<5} {:<5} {:<8} {:<8}".format(
        "Player", "G", "PPG", "RPG", "SPG", "BPG", "TOPG", "FG%", "3PT%"))
    print("  " + "-" * 72)
    for name, stats in sorted_players[:8]:
        games = max(1, stats.get("games", 1))
        print("  {:<22} {:<5} {:<5} {:<5} {:<5} {:<5} {:<5} {:<8} {:<8}".format(
            name[:21],
            stats.get("games", 0),
            round(stats.get("points",0)/games, 1),
            round(stats.get("rebounds",0)/games, 1),
            round(stats.get("steals",0)/games, 1),
            round(stats.get("blocks",0)/games, 1),
            round(stats.get("turnovers",0)/games, 1),
            str(round(stats.get("fg_pct", 0), 1)) + "%",
            str(round(stats.get("three_pct", 0), 1)) + "%",
        ))
