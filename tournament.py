# -----------------------------------------
# COLLEGE HOOPS SIM -- NCAA Tournament v1.0
#
# 64-team single-elimination bracket.
# Called after conference tournaments, before universe gravity.
#
# FIELD SIZE:
#   TOURNAMENT_FIELD_SIZE = 64  <-- change this one constant for 32/68/etc.
#   Auto-bids:   31 (one per conference tournament winner)
#   At-large:    TOURNAMENT_FIELD_SIZE - 31
#
# FIELD SELECTION:
#   Auto-bid winners are in automatically.
#   At-large pool: all remaining teams ranked by selection score.
#   Selection score = win_pct * conference_tier_weight
#   Tier weights: power=1.4, high_major=1.2, mid_major=1.0,
#                 low_major=0.7, floor_conf=0.7
#
# SEEDING:
#   All 64 teams ranked by selection score.
#   4 regions of 16. Snake-seeded across regions.
#   Seeds 1-4 are the top 4 teams (one per region).
#   Standard matchups: 1v16, 2v15, 3v14, 4v13, 5v12, 6v11, 7v10, 8v9.
#
# CONFERENCE SEPARATION:
#   Conference mates placed in opposite regions wherever possible.
#   They can only meet in the Final Four at the earliest if spread correctly.
#   If a conference floods the field, separation is best-effort.
#
# PRESTIGE -- TWO EFFECTS:
#
#   1. prestige_current spike (tier-inverted):
#      Base values:
#        Appearance:  +0.5
#        Each win:    +1.0
#        Sweet 16:    +2.0 bonus
#        Elite 8:     +3.5 bonus
#        Final Four:  +6.0 bonus
#        Champion:    +10.0 bonus
#      Tier multipliers (applied to total base):
#        Poor (1-20):         x4.0
#        Below avg (21-38):   x3.0
#        Average (39-58):     x2.0
#        Strong (59-78):      x1.2
#        Elite (79-94):       x0.7
#        Blue blood (95+):    x0.3
#      A Coppin State championship: ~+40 prestige_current.
#      A Memphis Final Four: ~+10 prestige_current.
#
#   2. prestige_gravity drift from consecutive tournament runs:
#      Feeds directly into drift_state["consecutive_above"] --
#      tournament success is treated as sustained overperformance,
#      building anchor momentum the same way regular season does.
#      Single deep run: small nudge.
#      Back-to-back Final Fours: meaningful drift.
#      Dynasty runs: anchor moves -- this is how mid-majors climb.
#
# STORED ON EACH PROGRAM:
#   program["ncaa_tournament_result"] = {
#       "seed":    int,
#       "region":  str,
#       "result":  str,  -- "champion"/"final_four"/"elite_8"/
#                           "sweet_16"/"r32"/"r64"/"none"
#       "wins":    int,
#       "at_large": bool,
#   }
#
# INTEGRATION (season.py):
#   Called after simulate_all_conference_tournaments(), before
#   apply_universe_gravity(). Returns (all_programs, tournament_results).
#   simulate_world_season() passes auto_bids in and gets
#   tournament_results back.
# -----------------------------------------

import random
from game_engine import simulate_game
from program import prestige_grade

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

# Change this one constant to resize the tournament (32, 64, 68, etc.)
TOURNAMENT_FIELD_SIZE = 64

# Number of automatic bids (one per conference)
NUM_AUTO_BIDS = 31

# At-large bids = field size minus auto bids
NUM_AT_LARGE = TOURNAMENT_FIELD_SIZE - NUM_AUTO_BIDS

# Region names
REGIONS = ["East", "West", "South", "Midwest"]

# Conference tier weights for at-large selection score
TIER_WEIGHT = {
    "power":      1.4,
    "high_major": 1.2,
    "mid_major":  1.0,
    "low_major":  0.7,
    "floor_conf": 0.7,
}

# -----------------------------------------
# PRESTIGE CONSTANTS
# -----------------------------------------

# Base prestige values before tier multiplier
TOURNEY_BASE = {
    "appearance": 0.5,
    "win":        1.0,
    "sweet_16":   2.0,   # bonus on top of win value
    "elite_8":    3.5,   # bonus on top of sweet_16 bonus
    "final_four": 6.0,   # bonus on top of elite_8 bonus
    "champion":   10.0,  # bonus on top of final_four bonus
}

# Tier multipliers -- inverted so low-prestige programs get bigger spikes
def _get_prestige_multiplier(prestige_current):
    if prestige_current >= 95:  return 0.3
    if prestige_current >= 79:  return 0.7
    if prestige_current >= 59:  return 1.2
    if prestige_current >= 39:  return 2.0
    if prestige_current >= 21:  return 3.0
    return 4.0


# -----------------------------------------
# SELECTION SCORE
# -----------------------------------------

def _selection_score(program):
    """
    Composite score used for at-large selection and seeding.
    win_pct * conference tier weight.
    """
    from programs_data import get_conference_tier

    games   = program["wins"] + program["losses"]
    win_pct = program["wins"] / max(1, games)
    tier    = get_conference_tier(program["conference"])["tier"]
    weight  = TIER_WEIGHT.get(tier, 1.0)

    # Small prestige tiebreaker so equal win-pct teams resolve deterministically
    prestige_tiebreak = program["prestige_current"] / 10000.0

    return (win_pct * weight) + prestige_tiebreak


# -----------------------------------------
# FIELD SELECTION
# -----------------------------------------

def select_field(all_programs, auto_bids):
    """
    Selects the full tournament field.

    auto_bids: dict of {conference_name: program} from conference tournaments.

    Returns list of (program, is_at_large) tuples, length = TOURNAMENT_FIELD_SIZE.
    """
    auto_bid_names = {p["name"] for p in auto_bids.values()}
    field = [(p, False) for p in auto_bids.values()]

    # At-large pool: everyone not already in on an auto-bid
    # Must have played games
    at_large_pool = [
        p for p in all_programs
        if p["name"] not in auto_bid_names
        and (p["wins"] + p["losses"]) > 0
    ]

    # Sort by selection score descending
    at_large_pool.sort(key=_selection_score, reverse=True)

    # Take top N
    at_large_picks = at_large_pool[:NUM_AT_LARGE]
    field += [(p, True) for p in at_large_picks]

    return field


# -----------------------------------------
# SEEDING AND BRACKETING
# -----------------------------------------

def _assign_seeds_and_regions(field):
    """
    Seeds all teams 1-16 across 4 regions.

    Snake-seeding across regions:
      Rank 1  -> seed 1, region assigned by conference separation
      Rank 2  -> seed 1, different region
      Rank 3  -> seed 1, different region
      Rank 4  -> seed 1, remaining region
      Rank 5  -> seed 2, region re-assigned by separation logic
      ... and so on

    Conference separation: conference mates placed in different regions
    wherever possible so they can only meet in the Final Four at earliest.

    Returns list of dicts:
      {"program": p, "seed": int, "region": str, "at_large": bool}
    """
    # Sort field by selection score descending
    sorted_field = sorted(field, key=lambda x: _selection_score(x[0]), reverse=True)

    # Assign global rank
    ranked = [
        {"program": p, "at_large": al, "rank": i + 1, "seed": None, "region": None}
        for i, (p, al) in enumerate(sorted_field)
    ]

    # Build seed groups of 4 (one per region per seed line)
    # seed_groups[0] = ranks 1-4 (seed 1s), seed_groups[1] = ranks 5-8 (seed 2s), etc.
    seed_groups = []
    for s in range(16):
        start = s * 4
        end   = start + 4
        seed_groups.append(ranked[start:end])

    # Assign seed number to each team in group
    for seed_num, group in enumerate(seed_groups, start=1):
        for entry in group:
            entry["seed"] = seed_num

    # Assign regions with conference separation
    # Process seed groups in order, tracking which conferences are in which regions
    region_conf_occupancy = {r: set() for r in REGIONS}
    region_slots          = {r: [] for r in REGIONS}  # entries assigned to this region

    for group in seed_groups:
        _assign_group_to_regions(group, region_conf_occupancy, region_slots)

    # Flatten back to list
    result = []
    for region in REGIONS:
        result.extend(region_slots[region])

    return result


def _assign_group_to_regions(group, region_conf_occupancy, region_slots):
    """
    Assigns one seed-line group (4 teams) to the 4 regions,
    minimizing conference mates in the same region.

    Greedy approach: for each team in the group, assign to the region
    that has the fewest conference mates already, breaking ties by
    total occupancy.
    """
    available_regions = list(REGIONS)

    for entry in group:
        conf = entry["program"]["conference"]

        # Score each available region: lower = better (fewer conf mates)
        def region_score(r):
            conf_conflicts = 1 if conf in region_conf_occupancy[r] else 0
            total_size     = len(region_slots[r])
            return (conf_conflicts, total_size)

        best_region = min(available_regions, key=region_score)

        entry["region"] = best_region
        region_conf_occupancy[best_region].add(conf)
        region_slots[best_region].append(entry)
        available_regions.remove(best_region)


# -----------------------------------------
# BRACKET BUILDER
# -----------------------------------------

def _build_region_bracket(region_entries):
    """
    Builds the 8-game first-round bracket for one region (16 teams).
    Standard NCAA matchups: 1v16, 2v15, 3v14, 4v13, 5v12, 6v11, 7v10, 8v9.

    Returns list of matchup dicts:
      {"high_seed": entry, "low_seed": entry}
    """
    by_seed = {e["seed"]: e for e in region_entries}
    matchups = []
    pairs = [(1,16),(2,15),(3,14),(4,13),(5,12),(6,11),(7,10),(8,9)]
    for high, low in pairs:
        if high in by_seed and low in by_seed:
            matchups.append({"high_seed": by_seed[high], "low_seed": by_seed[low]})
    return matchups


# -----------------------------------------
# NEUTRAL SITE GAME
# -----------------------------------------

def _simulate_neutral_site_game(team_a, team_b):
    """Simulates a game with venue_rating neutralized to 50 for both teams."""
    orig_a = team_a.get("venue_rating", 70)
    orig_b = team_b.get("venue_rating", 70)
    team_a["venue_rating"] = 50
    team_b["venue_rating"] = 50
    result = simulate_game(team_a, team_b, verbose=False)
    team_a["venue_rating"] = orig_a
    team_b["venue_rating"] = orig_b
    return result


# -----------------------------------------
# BRACKET SIMULATION
# -----------------------------------------

def _simulate_round(matchups, round_name, verbose=False):
    """
    Simulates one round of the bracket.

    matchups: list of {"high_seed": entry, "low_seed": entry}
              OR after R1: {"team_a": entry, "team_b": entry}

    Returns list of winner entries (advancing to next round).
    Also updates ncaa_tournament_result on each loser.
    """
    winners = []

    for matchup in matchups:
        # Support both first-round format and subsequent rounds
        if "high_seed" in matchup:
            entry_a = matchup["high_seed"]
            entry_b = matchup["low_seed"]
        else:
            entry_a = matchup["team_a"]
            entry_b = matchup["team_b"]

        prog_a = entry_a["program"]
        prog_b = entry_b["program"]

        result = _simulate_neutral_site_game(prog_a, prog_b)

        if result["home"] > result["away"]:
            winner, loser = entry_a, entry_b
            w_score, l_score = result["home"], result["away"]
        else:
            winner, loser = entry_b, entry_a
            w_score, l_score = result["away"], result["home"]

        # Update winner wins
        winner["program"]["ncaa_tournament_result"]["wins"] += 1

        # Update loser result
        loser["program"]["ncaa_tournament_result"]["result"] = round_name

        if verbose:
            print("    " +
                  winner["program"]["name"] + " (" + str(winner["seed"]) + ") def. " +
                  loser["program"]["name"] + " (" + str(loser["seed"]) + ")  " +
                  str(w_score) + "-" + str(l_score))

        winners.append(winner)

    return winners


def _pair_winners(winners):
    """
    Pairs winners for the next round.
    Maintains bracket integrity: winner of game 1 plays winner of game 2, etc.
    """
    matchups = []
    for i in range(0, len(winners), 2):
        if i + 1 < len(winners):
            matchups.append({"team_a": winners[i], "team_b": winners[i+1]})
    return matchups


def _simulate_region(region_name, region_entries, verbose=False):
    """
    Simulates all rounds within one region (R64 through Elite 8).
    Returns the Elite 8 winner entry.
    """
    if verbose:
        print("")
        print("  [" + region_name + " Region]")

    # First round (R64)
    r64_matchups = _build_region_bracket(region_entries)
    if verbose:
        print("  -- Round of 64 --")
    r32_teams = _simulate_round(r64_matchups, "r64", verbose=verbose)

    # Round of 32
    r32_matchups = _pair_winners(r32_teams)
    if verbose:
        print("  -- Round of 32 --")
    s16_teams = _simulate_round(r32_matchups, "r32", verbose=verbose)

    # Sweet 16
    s16_matchups = _pair_winners(s16_teams)
    if verbose:
        print("  -- Sweet 16 --")
    e8_teams = _simulate_round(s16_matchups, "sweet_16", verbose=verbose)

    # Elite 8
    e8_matchups = _pair_winners(e8_teams)
    if verbose:
        print("  -- Elite 8 --")
    ff_teams = _simulate_round(e8_matchups, "elite_8", verbose=verbose)

    # Mark Elite 8 winner result (updated to final_four after Final Four)
    if ff_teams:
        ff_teams[0]["program"]["ncaa_tournament_result"]["result"] = "elite_8"

    return ff_teams[0] if ff_teams else None


# -----------------------------------------
# PRESTIGE APPLICATION
# -----------------------------------------

def _apply_tournament_prestige(program):
    """
    Applies prestige effects after the tournament resolves.

    Two effects:
      1. prestige_current spike -- tier-inverted, dramatic for low programs
      2. prestige_gravity drift -- feeds consecutive_above in drift_state,
         building anchor momentum from sustained tournament success
    """
    result = program.get("ncaa_tournament_result", {})
    finish = result.get("result", "none")
    wins   = result.get("wins", 0)

    if finish == "none":
        return program

    # --- CURRENT PRESTIGE SPIKE ---
    base = TOURNEY_BASE["appearance"]
    base += wins * TOURNEY_BASE["win"]

    if finish in ("sweet_16", "elite_8", "final_four", "champion"):
        base += TOURNEY_BASE["sweet_16"]
    if finish in ("elite_8", "final_four", "champion"):
        base += TOURNEY_BASE["elite_8"]
    if finish in ("final_four", "champion"):
        base += TOURNEY_BASE["final_four"]
    if finish == "champion":
        base += TOURNEY_BASE["champion"]

    multiplier   = _get_prestige_multiplier(program["prestige_current"])
    spike        = round(base * multiplier, 2)
    new_prestige = min(100, program["prestige_current"] + spike)
    program["prestige_current"] = round(new_prestige, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    # --- GRAVITY DRIFT FROM TOURNAMENT SUCCESS ---
    # Treat tournament success as sustained overperformance --
    # feeds into drift_state to build anchor momentum.
    # Deep runs push consecutive_above harder than first-round exits.
    if "drift_state" not in program:
        program["drift_state"] = {
            "consecutive_above":   0,
            "consecutive_below":   0,
            "last_direction":      "none",
            "seasons_bottom_half": 0,
        }

    state = program["drift_state"]

    # Tournament contribution to consecutive_above:
    # appearance/r64:  +0 (just showing up doesn't move the anchor)
    # r32:             +0.5
    # sweet_16:        +1
    # elite_8:         +2
    # final_four:      +3
    # champion:        +4
    tourney_momentum = {
        "r64":        0.0,
        "r32":        0.5,
        "sweet_16":   1.0,
        "elite_8":    2.0,
        "final_four": 3.0,
        "champion":   4.0,
    }
    momentum_add = tourney_momentum.get(finish, 0.0)

    if momentum_add > 0:
        if state["last_direction"] == "up":
            state["consecutive_above"] += momentum_add
        else:
            state["consecutive_above"] = momentum_add
            state["consecutive_below"] = 0
        state["last_direction"] = "up"

    return program


# -----------------------------------------
# MAIN TOURNAMENT RUNNER
# -----------------------------------------

def simulate_ncaa_tournament(all_programs, auto_bids, verbose=True):
    """
    Simulates the full NCAA Tournament.

    Parameters:
      all_programs  -- full list of all program dicts
      auto_bids     -- dict {conference_name: program} from conference tournaments

    Returns:
      all_programs       -- modified in place with ncaa_tournament_result set
      tournament_results -- summary dict with champion, Final Four, bracket info
    """
    # --- INITIALIZE RESULT ON ALL PROGRAMS ---
    for p in all_programs:
        p["ncaa_tournament_result"] = {
            "seed":     None,
            "region":   None,
            "result":   "none",
            "wins":     0,
            "at_large": False,
        }

    # --- SELECT FIELD ---
    field = select_field(all_programs, auto_bids)

    if len(field) < TOURNAMENT_FIELD_SIZE:
        if verbose:
            print("  WARNING: Only " + str(len(field)) + " teams available for " +
                  str(TOURNAMENT_FIELD_SIZE) + "-team field.")

    # --- SEED AND BRACKET ---
    seeded_field = _assign_seeds_and_regions(field)

    # Write seed/region/at_large onto each program's result dict
    for entry in seeded_field:
        p = entry["program"]
        p["ncaa_tournament_result"]["seed"]     = entry["seed"]
        p["ncaa_tournament_result"]["region"]   = entry["region"]
        p["ncaa_tournament_result"]["at_large"] = entry["at_large"]

    # --- SIMULATE REGIONS ---
    region_groups = {r: [] for r in REGIONS}
    for entry in seeded_field:
        region_groups[entry["region"]].append(entry)

    if verbose:
        print("")
        print("--- NCAA Tournament ---")
        print("  Field: " + str(len(seeded_field)) + " teams")

    final_four_entries = []
    for region_name in REGIONS:
        region_entries = region_groups[region_name]
        ff_entry = _simulate_region(region_name, region_entries, verbose=verbose)
        if ff_entry:
            ff_entry["program"]["ncaa_tournament_result"]["result"] = "final_four"
            final_four_entries.append(ff_entry)

    # --- FINAL FOUR ---
    if verbose:
        print("")
        print("  -- Final Four --")

    if len(final_four_entries) < 2:
        champion_entry = final_four_entries[0] if final_four_entries else None
    else:
        # Semifinal 1: region 0 vs region 1
        # Semifinal 2: region 2 vs region 3
        sf1_result = _simulate_neutral_site_game(
            final_four_entries[0]["program"],
            final_four_entries[1]["program"]
        )
        if sf1_result["home"] > sf1_result["away"]:
            sf1_winner, sf1_loser = final_four_entries[0], final_four_entries[1]
        else:
            sf1_winner, sf1_loser = final_four_entries[1], final_four_entries[0]

        sf1_loser["program"]["ncaa_tournament_result"]["result"] = "final_four"
        sf1_winner["program"]["ncaa_tournament_result"]["wins"] += 1

        if verbose:
            print("    " + sf1_winner["program"]["name"] +
                  " def. " + sf1_loser["program"]["name"])

        sf2_result = _simulate_neutral_site_game(
            final_four_entries[2]["program"],
            final_four_entries[3]["program"]
        )
        if sf2_result["home"] > sf2_result["away"]:
            sf2_winner, sf2_loser = final_four_entries[2], final_four_entries[3]
        else:
            sf2_winner, sf2_loser = final_four_entries[3], final_four_entries[2]

        sf2_loser["program"]["ncaa_tournament_result"]["result"] = "final_four"
        sf2_winner["program"]["ncaa_tournament_result"]["wins"] += 1

        if verbose:
            print("    " + sf2_winner["program"]["name"] +
                  " def. " + sf2_loser["program"]["name"])

        # --- CHAMPIONSHIP ---
        if verbose:
            print("")
            print("  -- Championship --")

        championship_result = _simulate_neutral_site_game(
            sf1_winner["program"],
            sf2_winner["program"]
        )
        if championship_result["home"] > championship_result["away"]:
            champion_entry, runner_up_entry = sf1_winner, sf2_winner
        else:
            champion_entry, runner_up_entry = sf2_winner, sf1_winner

        runner_up_entry["program"]["ncaa_tournament_result"]["result"] = "final_four"
        champion_entry["program"]["ncaa_tournament_result"]["wins"]   += 1
        champion_entry["program"]["ncaa_tournament_result"]["result"]  = "champion"

        if verbose:
            print("    CHAMPION: " + champion_entry["program"]["name"] +
                  " (" + champion_entry["region"] + " " +
                  str(champion_entry["seed"]) + " seed)")

    # --- APPLY PRESTIGE TO ALL TOURNAMENT PARTICIPANTS ---
    participant_names = {entry["program"]["name"] for entry in seeded_field}
    for p in all_programs:
        if p["name"] in participant_names:
            _apply_tournament_prestige(p)

    # --- BUILD RESULTS SUMMARY ---
    final_four_names = [
        e["program"]["name"] for e in final_four_entries
    ] if final_four_entries else []

    champion_name = champion_entry["program"]["name"] if champion_entry else "Unknown"
    champion_seed = champion_entry["seed"] if champion_entry else None
    champion_conf = champion_entry["program"]["conference"] if champion_entry else "Unknown"

    # Collect notable results for reporting
    cinderellas = [
        p for p in all_programs
        if p["ncaa_tournament_result"]["result"] not in ("none",)
        and p["ncaa_tournament_result"]["seed"] is not None
        and p["ncaa_tournament_result"]["seed"] >= 10
        and p["ncaa_tournament_result"]["result"] in ("sweet_16", "elite_8", "final_four", "champion")
    ]

    tournament_results = {
        "champion":       champion_name,
        "champion_seed":  champion_seed,
        "champion_conf":  champion_conf,
        "final_four":     final_four_names,
        "cinderellas":    [(p["name"], p["ncaa_tournament_result"]["seed"],
                            p["ncaa_tournament_result"]["result"])
                           for p in cinderellas],
        "field_size":     len(seeded_field),
        "auto_bids_used": len(auto_bids),
    }

    return all_programs, tournament_results


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_tournament_summary(tournament_results, season_year):
    """Prints a readable tournament summary."""
    print("")
    print("=== " + str(season_year) + " NCAA Tournament ===")
    print("  Champion:    " + tournament_results["champion"] +
          "  (" + tournament_results["champion_conf"] + ", " +
          str(tournament_results["champion_seed"]) + " seed)")
    print("  Final Four:  " + "  |  ".join(tournament_results["final_four"]))

    if tournament_results["cinderellas"]:
        print("  Cinderellas:")
        for name, seed, result in tournament_results["cinderellas"]:
            print("    " + name + " (seed " + str(seed) + ") -- " + result.replace("_", " ").title())


def print_bracket_seedings(all_programs, season_year):
    """Prints the full bracket seedings by region."""
    print("")
    print("=== " + str(season_year) + " NCAA Tournament Bracket ===")

    for region in REGIONS:
        print("")
        print("  [" + region + " Region]")
        print("  {:<4} {:<24} {:<20} {:<10} {}".format(
            "Seed", "Team", "Conference", "Record", "Result"))
        print("  " + "-" * 72)

        region_teams = sorted(
            [p for p in all_programs
             if p["ncaa_tournament_result"].get("region") == region
             and p["ncaa_tournament_result"]["seed"] is not None],
            key=lambda p: p["ncaa_tournament_result"]["seed"]
        )

        for p in region_teams:
            r      = p["ncaa_tournament_result"]
            record = str(p["wins"]) + "-" + str(p["losses"])
            result = r["result"].replace("_", " ").title() if r["result"] != "none" else "-"
            print("  {:<4} {:<24} {:<20} {:<10} {}".format(
                str(r["seed"]),
                p["name"][:23],
                p["conference"][:19],
                record,
                result
            ))


# -----------------------------------------
# INTEGRATION NOTE FOR season.py
# -----------------------------------------
#
# In simulate_world_season(), add after simulate_all_conference_tournaments()
# and BEFORE apply_universe_gravity():
#
#   from tournament import simulate_ncaa_tournament, print_tournament_summary
#   all_programs, tournament_results = simulate_ncaa_tournament(
#       all_programs, auto_bids, verbose=verbose
#   )
#   if verbose:
#       print_tournament_summary(tournament_results, season_year)
#
# Update the return signature:
#   return all_programs, recruiting_class, cycle_summary, lifecycle_summary,
#          auto_bids, tournament_results
#
# Update __main__ unpack accordingly.
# -----------------------------------------


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    from programs_data import build_all_d1_programs
    from roster_minutes import allocate_minutes
    from game_engine import initialize_season_stats
    from season import simulate_conference_season
    from conference_tournament import simulate_all_conference_tournaments

    print("Loading programs...")
    all_programs = build_all_d1_programs()

    print("Allocating minutes and initializing stats...")
    for p in all_programs:
        allocate_minutes(p)
        initialize_season_stats(p, season_year=2024)

    print("Simulating regular season...")
    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)

    for conf_name, conf_programs in conferences.items():
        if len(conf_programs) >= 2:
            simulate_conference_season(conf_programs, all_programs, 2024, verbose=False)

    print("Simulating conference tournaments...")
    auto_bids, conf_results = simulate_all_conference_tournaments(all_programs, verbose=False)
    print("  " + str(len(auto_bids)) + " auto-bids awarded")

    print("Simulating NCAA Tournament...")
    all_programs, tournament_results = simulate_ncaa_tournament(
        all_programs, auto_bids, verbose=True
    )

    print_tournament_summary(tournament_results, 2024)
    print_bracket_seedings(all_programs, 2024)

    print("")
    print("=== Prestige Impact Check ===")
    participants = sorted(
        [p for p in all_programs
         if p["ncaa_tournament_result"]["result"] != "none"],
        key=lambda p: p["ncaa_tournament_result"]["wins"],
        reverse=True
    )
    print("{:<24} {:<6} {:<12} {:<10} {:<10} {}".format(
        "Team", "Seed", "Result", "Pre-T", "Post-T", "Spike"))
    print("-" * 75)
    for p in participants[:20]:
        r = p["ncaa_tournament_result"]
        # We don't have pre-tourney prestige stored yet -- just show current
        print("{:<24} {:<6} {:<12} {:<10} {:<10}".format(
            p["name"][:23],
            str(r["seed"]),
            r["result"].replace("_", " "),
            "-",
            str(p["prestige_current"]) + " (" + p["prestige_grade"] + ")"
        ))
