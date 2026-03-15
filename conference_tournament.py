# -----------------------------------------
# COLLEGE HOOPS SIM -- Conference Tournament v1.0
#
# 4-team single-elimination bracket for every conference.
# Called after the regular season, before universe gravity and recruiting.
#
# BRACKET STRUCTURE:
#   Seeds 1-4 by conference win pct (tiebreak: overall win pct)
#   Semis:  1 vs 4,  2 vs 3
#   Final:  semi winners
#   All games neutral site -- no home court advantage
#
# OUTPUT:
#   Returns a dict: {conference_name: winning_program}
#   31 auto-bid winners flow into the NCAA tournament selector.
#
# PRESTIGE:
#   apply_conf_tournament_prestige() fires after each conference bracket.
#   Separate from update_prestige_for_results() -- keeps both clean.
#   Semifinal appearance: +0.2
#   Runner-up:            +0.35
#   Champion:             +0.50
#   Floor_conf and low_major teams get a 0.7x multiplier --
#   identity pull handles keeping them grounded, not the tourney cap.
#
# RECORD:
#   Tournament wins/losses added to program wins/losses via
#   record_game_result(). These count toward the final season record
#   that feeds update_prestige_for_results().
#
# ARCHITECTURE NOTE:
#   conf_tournament_result stored on each program dict after the bracket:
#     "conf_tournament_result": {
#         "seed":        int,         -- 1-4 seed entering the bracket
#         "result":      str,         -- "champion", "runner_up", "semifinal", "none"
#         "wins":        int,         -- tournament wins (0, 1, or 2)
#         "auto_bid":    bool,        -- True if this program won the auto-bid
#     }
#   NCAA tournament selector reads this dict to determine auto-bid winners.
# -----------------------------------------

import random
from game_engine import simulate_game
from program import record_game_result, prestige_grade

# -----------------------------------------
# PRESTIGE WEIGHTS
# -----------------------------------------

CONF_TOURNEY_PRESTIGE = {
    "semifinal": 0.20,
    "runner_up":  0.35,
    "champion":   0.50,
}

# Tier multiplier -- floor/low programs get reduced tourney prestige boost
# Their identity pull handles the ceiling, not this multiplier
CONF_TOURNEY_TIER_MULTIPLIER = {
    "power":      1.0,
    "high_major": 1.0,
    "mid_major":  1.0,
    "low_major":  0.7,
    "floor_conf": 0.7,
}


# -----------------------------------------
# NEUTRAL SITE GAME
# -----------------------------------------

def _simulate_neutral_site_game(team_a, team_b):
    """
    Simulates a game with no home court advantage.
    Temporarily sets venue_rating to 50 (neutral) on both teams,
    restores after the game resolves.

    Returns result dict from simulate_game().
    """
    orig_a = team_a.get("venue_rating", 70)
    orig_b = team_b.get("venue_rating", 70)

    team_a["venue_rating"] = 50
    team_b["venue_rating"] = 50

    result = simulate_game(team_a, team_b, verbose=False)

    team_a["venue_rating"] = orig_a
    team_b["venue_rating"] = orig_b

    return result


# -----------------------------------------
# SEEDING
# -----------------------------------------

def _seed_conference(conference_programs):
    """
    Returns top 4 programs seeded by conference win pct.
    Tiebreak: overall win pct.
    Returns list of 4 program dicts, index 0 = seed 1.
    If fewer than 4 programs, fills with None.
    """
    eligible = [p for p in conference_programs if p.get("conf_wins", 0) + p.get("conf_losses", 0) > 0]

    def seed_key(p):
        conf_games   = p["conf_wins"] + p["conf_losses"]
        overall_games = p["wins"] + p["losses"]
        conf_pct     = p["conf_wins"] / max(1, conf_games)
        overall_pct  = p["wins"] / max(1, overall_games)
        return (conf_pct, overall_pct)

    ranked = sorted(eligible, key=seed_key, reverse=True)

    # Pad to 4 if conference has fewer teams (shouldn't happen but safety net)
    while len(ranked) < 4:
        ranked.append(None)

    return ranked[:4]


# -----------------------------------------
# PRESTIGE APPLICATION
# -----------------------------------------

def apply_conf_tournament_prestige(program):
    """
    Applies a small prestige boost based on conference tournament result.
    Called after the bracket resolves for each participating program.
    Only fires for semifinal appearance or better -- first round losers get nothing.

    Tier-aware: floor_conf and low_major get 0.7x multiplier.
    Does NOT touch prestige_gravity -- current only.
    """
    from programs_data import get_conference_tier

    result = program.get("conf_tournament_result", {})
    finish = result.get("result", "none")

    if finish == "none" or finish not in ("semifinal", "runner_up", "champion"):
        return program

    base_boost = CONF_TOURNEY_PRESTIGE.get(finish, 0.0)
    if base_boost == 0.0:
        return program

    tier_obj    = get_conference_tier(program["conference"])
    tier        = tier_obj["tier"]
    multiplier  = CONF_TOURNEY_TIER_MULTIPLIER.get(tier, 1.0)

    boost       = round(base_boost * multiplier, 3)
    new_prestige = min(100, program["prestige_current"] + boost)
    program["prestige_current"] = round(new_prestige, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    return program


# -----------------------------------------
# BRACKET RUNNER
# -----------------------------------------

def _init_conf_tournament_result(program, seed):
    """Sets baseline conf_tournament_result on a program entering the bracket."""
    program["conf_tournament_result"] = {
        "seed":     seed,
        "result":   "none",
        "wins":     0,
        "auto_bid": False,
    }
    return program


def simulate_conference_tournament(conference_name, conference_programs, verbose=False):
    """
    Runs the full 4-team single-elimination bracket for one conference.

    Bracket:
      Semifinal A: seed 1 vs seed 4
      Semifinal B: seed 2 vs seed 3
      Final:       semi A winner vs semi B winner

    Returns:
      winner       -- the winning program dict (auto-bid recipient)
      participants -- list of all 4 program dicts with conf_tournament_result set
    """
    seeds = _seed_conference(conference_programs)

    # Filter out None placeholders (undersized conferences)
    valid_seeds = [s for s in seeds if s is not None]
    if len(valid_seeds) < 2:
        # Not enough teams -- award auto-bid to best team with no tournament
        if valid_seeds:
            winner = valid_seeds[0]
            _init_conf_tournament_result(winner, 1)
            winner["conf_tournament_result"]["result"]   = "champion"
            winner["conf_tournament_result"]["auto_bid"] = True
            apply_conf_tournament_prestige(winner)
            return winner, valid_seeds
        return None, []

    # Initialize tournament results on all participants
    for i, program in enumerate(valid_seeds):
        _init_conf_tournament_result(program, i + 1)

    seed1, seed4 = valid_seeds[0], valid_seeds[3] if len(valid_seeds) > 3 else valid_seeds[-1]
    seed2, seed3 = valid_seeds[1], valid_seeds[2] if len(valid_seeds) > 2 else valid_seeds[1]

    if verbose:
        print("")
        print("  [" + conference_name + " Tournament]")
        print("  Bracket: (" + seed1["name"] + ") vs (" + seed4["name"] + ")"
              + "   |   (" + seed2["name"] + ") vs (" + seed3["name"] + ")")

    # -----------------------------------------
    # SEMIFINALS
    # -----------------------------------------

    # Semifinal A: 1 vs 4
    result_a = _simulate_neutral_site_game(seed1, seed4)
    if result_a["home"] > result_a["away"]:
        semi_a_winner, semi_a_loser = seed1, seed4
    else:
        semi_a_winner, semi_a_loser = seed4, seed1

    record_game_result(seed1,  seed4["name"], result_a["home"], result_a["away"],
                       is_home=False, is_conference=False)
    record_game_result(seed4,  seed1["name"], result_a["away"], result_a["home"],
                       is_home=False, is_conference=False)

    semi_a_winner["conf_tournament_result"]["wins"] += 1
    semi_a_loser["conf_tournament_result"]["result"]  = "semifinal"

    if verbose:
        print("  Semi A: " + seed1["name"] + " " + str(result_a["home"]) +
              "  " + seed4["name"] + " " + str(result_a["away"]) +
              "  --> " + semi_a_winner["name"] + " advances")

    # Semifinal B: 2 vs 3
    result_b = _simulate_neutral_site_game(seed2, seed3)
    if result_b["home"] > result_b["away"]:
        semi_b_winner, semi_b_loser = seed2, seed3
    else:
        semi_b_winner, semi_b_loser = seed3, seed2

    record_game_result(seed2, seed3["name"], result_b["home"], result_b["away"],
                       is_home=False, is_conference=False)
    record_game_result(seed3, seed2["name"], result_b["away"], result_b["home"],
                       is_home=False, is_conference=False)

    semi_b_winner["conf_tournament_result"]["wins"] += 1
    semi_b_loser["conf_tournament_result"]["result"]  = "semifinal"

    if verbose:
        print("  Semi B: " + seed2["name"] + " " + str(result_b["home"]) +
              "  " + seed3["name"] + " " + str(result_b["away"]) +
              "  --> " + semi_b_winner["name"] + " advances")

    # -----------------------------------------
    # FINAL
    # -----------------------------------------

    result_f = _simulate_neutral_site_game(semi_a_winner, semi_b_winner)
    if result_f["home"] > result_f["away"]:
        champion, runner_up = semi_a_winner, semi_b_winner
    else:
        champion, runner_up = semi_b_winner, semi_a_winner

    record_game_result(semi_a_winner, semi_b_winner["name"],
                       result_f["home"], result_f["away"],
                       is_home=False, is_conference=False)
    record_game_result(semi_b_winner, semi_a_winner["name"],
                       result_f["away"], result_f["home"],
                       is_home=False, is_conference=False)

    champion["conf_tournament_result"]["wins"]     += 1
    champion["conf_tournament_result"]["result"]    = "champion"
    champion["conf_tournament_result"]["auto_bid"]  = True
    runner_up["conf_tournament_result"]["result"]   = "runner_up"

    if verbose:
        print("  Final:  " + semi_a_winner["name"] + " " + str(result_f["home"]) +
              "  " + semi_b_winner["name"] + " " + str(result_f["away"]) +
              "  --> " + champion["name"] + " wins the " + conference_name + " Tournament")

    # Apply prestige to all 4 participants
    for program in valid_seeds:
        apply_conf_tournament_prestige(program)

    return champion, valid_seeds


# -----------------------------------------
# WORLD RUNNER
# Called from simulate_world_season() in season.py
# -----------------------------------------

def simulate_all_conference_tournaments(all_programs, verbose=True):
    """
    Runs the conference tournament for every conference.

    Called after regular season simulation, before universe gravity.

    Returns:
      auto_bids  -- dict of {conference_name: winning_program}
                   31 entries (one per conference), consumed by NCAA tournament
      results    -- list of result summary dicts for reporting
    """
    # Group programs by conference
    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)

    auto_bids = {}
    results   = []

    if verbose:
        print("")
        print("--- Conference Tournaments ---")

    for conf_name, conf_programs in sorted(conferences.items()):
        if len(conf_programs) < 2:
            # Single-program conference (shouldn't exist but guard it)
            if conf_programs:
                winner = conf_programs[0]
                _init_conf_tournament_result(winner, 1)
                winner["conf_tournament_result"]["result"]   = "champion"
                winner["conf_tournament_result"]["auto_bid"] = True
                auto_bids[conf_name] = winner
            continue

        winner, participants = simulate_conference_tournament(
            conf_name, conf_programs, verbose=False
        )

        if winner:
            auto_bids[conf_name] = winner

            results.append({
                "conference": conf_name,
                "champion":   winner["name"],
                "champion_seed": winner["conf_tournament_result"]["seed"],
                "participants": [
                    {
                        "name":   p["name"],
                        "seed":   p["conf_tournament_result"]["seed"],
                        "result": p["conf_tournament_result"]["result"],
                        "wins":   p["conf_tournament_result"]["wins"],
                    }
                    for p in participants
                ],
            })

    if verbose:
        print("  " + str(len(auto_bids)) + " conference tournament champions determined")
        # Show any upsets: lower seed beat higher seed in the final
        upsets = [r for r in results if r["champion_seed"] > 1]
        if upsets:
            print("  Upsets (non-1-seed champions): " + str(len(upsets)))
            for u in upsets[:5]:
                print("    " + u["conference"] + ": " + u["champion"] +
                      " (seed " + str(u["champion_seed"]) + ")")

    return auto_bids, results


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_conference_tournament_summary(results, auto_bids):
    """Prints a readable summary of all conference tournament results."""
    print("")
    print("=== Conference Tournament Results ===")
    print("{:<22} {:<24} {:<6} {}".format(
        "Conference", "Champion", "Seed", "Path"))
    print("-" * 70)

    for r in sorted(results, key=lambda x: x["conference"]):
        participants = {p["name"]: p for p in r["participants"]}
        champion     = participants.get(r["champion"], {})
        seed         = r["champion_seed"]

        # Reconstruct path from participant results
        finalist     = next((p["name"] for p in r["participants"]
                             if p["result"] == "runner_up"), "?")

        print("{:<22} {:<24} {:<6} def. {}".format(
            r["conference"][:21],
            r["champion"][:23],
            "#" + str(seed),
            finalist[:20]
        ))


# -----------------------------------------
# INTEGRATION PATCH FOR season.py
# -----------------------------------------
#
# In simulate_world_season(), add this block AFTER the conference
# regular season loop and BEFORE apply_universe_gravity():
#
#   from conference_tournament import simulate_all_conference_tournaments
#   auto_bids, conf_tourney_results = simulate_all_conference_tournaments(
#       all_programs, verbose=verbose
#   )
#
# Pass auto_bids forward to the NCAA tournament when that module is built.
# Store conf_tourney_results on the season summary if you want reporting.
#
# Also update simulate_world_season()'s return signature to include auto_bids:
#   return all_programs, recruiting_class, cycle_summary, lifecycle_summary, auto_bids
# -----------------------------------------


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from roster_minutes import allocate_minutes
    from game_engine import initialize_season_stats
    from season import simulate_conference_season

    print("Loading programs...")
    all_programs = build_all_d1_programs()

    print("Allocating minutes and initializing stats...")
    for p in all_programs:
        allocate_minutes(p)
        initialize_season_stats(p, season_year=2024)

    print("Simulating regular season (Big 12 only for speed)...")
    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)

    # Run one conference regular season so standings exist
    big12 = conferences.get("Big 12", [])
    if big12:
        simulate_conference_season(big12, all_programs, 2024, verbose=False)
        print("Big 12 regular season done. Standings:")
        ranked = sorted(big12, key=lambda p: (p["conf_wins"], p["wins"]), reverse=True)
        for i, p in enumerate(ranked[:8]):
            games = p["conf_wins"] + p["conf_losses"]
            print("  " + str(i+1) + ". " + p["name"].ljust(22) +
                  "  conf: " + str(p["conf_wins"]) + "-" + str(p["conf_losses"]) +
                  "  overall: " + str(p["wins"]) + "-" + str(p["losses"]))

        print("")
        print("Running Big 12 Conference Tournament...")
        winner, participants = simulate_conference_tournament("Big 12", big12, verbose=True)

        print("")
        print("Results:")
        for p in participants:
            r = p.get("conf_tournament_result", {})
            print("  " + p["name"].ljust(22) +
                  "  seed: " + str(r.get("seed", "?")) +
                  "  result: " + r.get("result", "none") +
                  "  tourney wins: " + str(r.get("wins", 0)) +
                  "  auto_bid: " + str(r.get("auto_bid", False)))

        print("")
        print("Auto-bid winner: " + (winner["name"] if winner else "NONE"))

    print("")
    print("Running ALL conference tournaments...")
    auto_bids, results = simulate_all_conference_tournaments(all_programs, verbose=True)

    print_conference_tournament_summary(results, auto_bids)

    print("")
    print("Total auto-bids awarded: " + str(len(auto_bids)))
    seed_dist = {}
    for r in results:
        s = r["champion_seed"]
        seed_dist[s] = seed_dist.get(s, 0) + 1
    print("Champion seed distribution:")
    for seed in sorted(seed_dist):
        print("  Seed " + str(seed) + ": " + str(seed_dist[seed]) + " conferences")
