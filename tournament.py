# -----------------------------------------
# COLLEGE HOOPS SIM -- NCAA Tournament v1.1
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
# CONFERENCE SEPARATION RULES:
#   <= 4 bids: all teams in DIFFERENT regions (Final Four earliest meeting)
#   5-8 bids:  no same-half pairing in same region (Sweet 16 earliest)
#   9+ bids:   best-effort separation (R32 possible)
#
# PRESTIGE -- BUZZ SYSTEM (v1.1):
#   tournament.py NO LONGER touches prestige_current directly.
#   All tournament prestige flows through tournament_buzz (program.py).
#   Buzz is gravity-relative -- low-gravity deep runs get big multipliers.
#   Gravity drift feeds existing drift_state freight-train momentum.
# -----------------------------------------

import random
from game_engine import simulate_game
from program import prestige_grade, apply_tournament_buzz, ensure_tournament_buzz

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

TOURNAMENT_FIELD_SIZE = 64
NUM_AUTO_BIDS         = 31
NUM_AT_LARGE          = TOURNAMENT_FIELD_SIZE - NUM_AUTO_BIDS
REGIONS               = ["East", "West", "South", "Midwest"]

TIER_WEIGHT = {
    "power":      1.4,
    "high_major": 1.2,
    "mid_major":  1.0,
    "low_major":  0.7,
    "floor_conf": 0.7,
}

SEPARATION_HARD = 4
SEPARATION_SOFT = 8


# -----------------------------------------
# SELECTION SCORE
# -----------------------------------------

def _selection_score(program):
    from programs_data import get_conference_tier
    from program import get_effective_prestige
    games   = program["wins"] + program["losses"]
    win_pct = program["wins"] / max(1, games)
    tier    = get_conference_tier(program["conference"])["tier"]
    weight  = TIER_WEIGHT.get(tier, 1.0)
    ep_tb   = get_effective_prestige(program) / 10000.0
    return (win_pct * weight) + ep_tb


# -----------------------------------------
# FIELD SELECTION
# -----------------------------------------

def select_field(all_programs, auto_bids):
    auto_bid_names = {p["name"] for p in auto_bids.values()}
    field = [(p, False) for p in auto_bids.values()]
    at_large_pool = [
        p for p in all_programs
        if p["name"] not in auto_bid_names and (p["wins"] + p["losses"]) > 0
    ]
    at_large_pool.sort(key=_selection_score, reverse=True)
    field += [(p, True) for p in at_large_pool[:NUM_AT_LARGE]]
    return field


# -----------------------------------------
# SEEDING AND CONFERENCE SEPARATION
# -----------------------------------------

def _assign_seeds_and_regions(field):
    conf_bid_counts = {}
    for p, _ in field:
        conf = p["conference"]
        conf_bid_counts[conf] = conf_bid_counts.get(conf, 0) + 1

    sorted_field = sorted(field, key=lambda x: _selection_score(x[0]), reverse=True)
    ranked = [
        {"program": p, "at_large": al, "rank": i+1, "seed": None, "region": None}
        for i, (p, al) in enumerate(sorted_field)
    ]

    seed_groups = []
    for s in range(16):
        group = ranked[s*4:(s+1)*4]
        for entry in group:
            entry["seed"] = s + 1
        seed_groups.append(group)

    region_conf_map = {r: [] for r in REGIONS}
    region_slots    = {r: [] for r in REGIONS}

    for group in seed_groups:
        _assign_group_with_separation(group, region_conf_map, region_slots, conf_bid_counts)

    result = []
    for region in REGIONS:
        result.extend(region_slots[region])
    return result


def _assign_group_with_separation(group, region_conf_map, region_slots, conf_bid_counts):
    available_regions = list(REGIONS)

    for entry in group:
        conf      = entry["program"]["conference"]
        bid_count = conf_bid_counts.get(conf, 1)
        seed      = entry["seed"]
        upper     = seed <= 8

        def region_score(r):
            size = len(region_slots[r])
            if bid_count <= SEPARATION_HARD:
                conflict = 1 if conf in region_conf_map[r] else 0
                return (conflict * 1000, size)
            elif bid_count <= SEPARATION_SOFT:
                same_half = sum(
                    1 for e in region_slots[r]
                    if e["program"]["conference"] == conf
                    and (e["seed"] <= 8) == upper
                )
                return (same_half * 100, size)
            else:
                conf_count = sum(
                    1 for e in region_slots[r]
                    if e["program"]["conference"] == conf
                )
                return (conf_count, size)

        best = min(available_regions, key=region_score)
        entry["region"] = best
        region_conf_map[best].append(conf)
        region_slots[best].append(entry)
        available_regions.remove(best)


# -----------------------------------------
# NEUTRAL SITE GAME
# -----------------------------------------

def _simulate_neutral_site_game(team_a, team_b):
    orig_a = team_a.get("venue_rating", 70)
    orig_b = team_b.get("venue_rating", 70)
    team_a["venue_rating"] = 50
    team_b["venue_rating"] = 50
    result = simulate_game(team_a, team_b, verbose=False)
    team_a["venue_rating"] = orig_a
    team_b["venue_rating"] = orig_b
    return result


# -----------------------------------------
# ROUND SIMULATION
# -----------------------------------------

def _simulate_game_from_entries(entry_a, entry_b, loser_result, verbose=False):
    """
    Simulates one game between two bracket entries.
    Returns the winner entry. Marks loser with loser_result.
    """
    result = _simulate_neutral_site_game(entry_a["program"], entry_b["program"])

    if result["home"] > result["away"]:
        winner, loser = entry_a, entry_b
        w_score, l_score = result["home"], result["away"]
    else:
        winner, loser = entry_b, entry_a
        w_score, l_score = result["away"], result["home"]

    winner["program"]["ncaa_tournament_result"]["wins"] += 1
    loser["program"]["ncaa_tournament_result"]["result"] = loser_result

    if verbose:
        print("    " +
              winner["program"]["name"] + " (" + str(winner["seed"]) + ") def. " +
              loser["program"]["name"]  + " (" + str(loser["seed"])  + ")  " +
              str(w_score) + "-" + str(l_score))

    return winner


def _simulate_region(region_name, region_entries, verbose=False):
    """
    Simulates all rounds in one region using the correct fixed NCAA bracket path.

    R64 game order (index 0-7):
      0: 1 vs 16
      1: 8 vs 9
      2: 5 vs 12
      3: 4 vs 13
      4: 6 vs 11
      5: 3 vs 14
      6: 7 vs 10
      7: 2 vs 15

    R32 bracket paths (winner of game X plays winner of game Y):
      Game 0 winner vs Game 1 winner  (1/16 side vs 8/9 side)
      Game 2 winner vs Game 3 winner  (5/12 side vs 4/13 side)
      Game 4 winner vs Game 5 winner  (6/11 side vs 3/14 side)
      Game 6 winner vs Game 7 winner  (7/10 side vs 2/15 side)

    Sweet 16:
      R32 Game A winner vs R32 Game B winner  (1-seed half)
      R32 Game C winner vs R32 Game D winner  (2-seed half)

    Elite 8:
      Sweet 16 Game 1 winner vs Sweet 16 Game 2 winner
    """
    if verbose:
        print("")
        print("  [" + region_name + " Region]")

    by_seed = {e["seed"]: e for e in region_entries}

    # Build R64 in the correct order
    r64_pairs = [(1,16), (8,9), (5,12), (4,13), (6,11), (3,14), (7,10), (2,15)]

    if verbose: print("  -- Round of 64 --")
    r64_winners = []
    for high, low in r64_pairs:
        if high in by_seed and low in by_seed:
            w = _simulate_game_from_entries(by_seed[high], by_seed[low], "r64", verbose)
            r64_winners.append(w)

    if len(r64_winners) < 8:
        return r64_winners[0] if r64_winners else None

    # R32 -- fixed bracket paths
    if verbose: print("  -- Round of 32 --")
    r32_w0 = _simulate_game_from_entries(r64_winners[0], r64_winners[1], "r32", verbose)
    r32_w1 = _simulate_game_from_entries(r64_winners[2], r64_winners[3], "r32", verbose)
    r32_w2 = _simulate_game_from_entries(r64_winners[4], r64_winners[5], "r32", verbose)
    r32_w3 = _simulate_game_from_entries(r64_winners[6], r64_winners[7], "r32", verbose)

    # Sweet 16 -- top half vs bottom half
    if verbose: print("  -- Sweet 16 --")
    s16_w0 = _simulate_game_from_entries(r32_w0, r32_w1, "sweet_16", verbose)
    s16_w1 = _simulate_game_from_entries(r32_w2, r32_w3, "sweet_16", verbose)

    # Elite 8
    if verbose: print("  -- Elite 8 --")
    ff_entry = _simulate_game_from_entries(s16_w0, s16_w1, "elite_8", verbose)

    # Mark Elite 8 winner -- will be updated to final_four/champion by caller
    ff_entry["program"]["ncaa_tournament_result"]["result"] = "elite_8"
    return ff_entry


# -----------------------------------------
# GRAVITY DRIFT FROM TOURNAMENT SUCCESS
# -----------------------------------------

def _apply_tournament_gravity_drift(program, result):
    from programs_data import get_conference_tier

    if "drift_state" not in program:
        program["drift_state"] = {
            "consecutive_above": 0, "consecutive_below": 0,
            "last_direction": "none", "seasons_bottom_half": 0,
        }

    gravity = program["prestige_gravity"]
    state   = program["drift_state"]

    # Expected result based on gravity
    if gravity >= 85:    expected = 4
    elif gravity >= 70:  expected = 3
    elif gravity >= 55:  expected = 2
    elif gravity >= 35:  expected = 1
    else:                expected = 0

    result_ranks = {
        "none": 0, "r64": 1, "r32": 2, "sweet_16": 3,
        "elite_8": 4, "final_four": 5, "champion": 6
    }
    actual = result_ranks.get(result, 0)

    if actual <= expected:
        return program

    above_margin = actual - expected
    contribution = {1: 0.3, 2: 0.7, 3: 1.2, 4: 2.0, 5: 3.0, 6: 4.0}.get(
        min(above_margin, 6), 0.3)

    if state["last_direction"] == "up":
        state["consecutive_above"] = round(state["consecutive_above"] + contribution, 1)
    else:
        state["consecutive_above"] = contribution
        state["consecutive_below"] = 0
        state["last_direction"]    = "up"

    return program


# -----------------------------------------
# BUZZ APPLICATION
# -----------------------------------------

def _apply_buzz_for_result(program, result, season_year):
    ensure_tournament_buzz(program)
    if result and result != "none":
        apply_tournament_buzz(program, result, season_year)
        _apply_tournament_gravity_drift(program, result)
    return program


# -----------------------------------------
# MAIN TOURNAMENT RUNNER
# -----------------------------------------

def simulate_ncaa_tournament(all_programs, auto_bids, season_year=2024, verbose=True):
    for p in all_programs:
        ensure_tournament_buzz(p)
        p["ncaa_tournament_result"] = {
            "seed": None, "region": None,
            "result": "none", "wins": 0, "at_large": False,
        }

    field        = select_field(all_programs, auto_bids)
    seeded_field = _assign_seeds_and_regions(field)

    for entry in seeded_field:
        p = entry["program"]
        p["ncaa_tournament_result"]["seed"]     = entry["seed"]
        p["ncaa_tournament_result"]["region"]   = entry["region"]
        p["ncaa_tournament_result"]["at_large"] = entry["at_large"]

    region_groups = {r: [] for r in REGIONS}
    for entry in seeded_field:
        region_groups[entry["region"]].append(entry)

    if verbose:
        print("")
        print("--- NCAA Tournament ---")
        print("  Field: " + str(len(seeded_field)) + " teams")

    final_four = []
    for region_name in REGIONS:
        ff_entry = _simulate_region(region_name, region_groups[region_name], verbose)
        if ff_entry:
            ff_entry["program"]["ncaa_tournament_result"]["result"] = "final_four"
            final_four.append(ff_entry)

    if verbose:
        print("")
        print("  -- Final Four --")

    if len(final_four) < 2:
        champion_entry = final_four[0] if final_four else None
    else:
        sf1 = _simulate_neutral_site_game(final_four[0]["program"], final_four[1]["program"])
        sf1_w, sf1_l = (final_four[0], final_four[1]) if sf1["home"] > sf1["away"] \
                        else (final_four[1], final_four[0])
        sf1_l["program"]["ncaa_tournament_result"]["result"] = "final_four"
        sf1_w["program"]["ncaa_tournament_result"]["wins"]  += 1
        if verbose: print("    " + sf1_w["program"]["name"] + " def. " + sf1_l["program"]["name"])

        sf2 = _simulate_neutral_site_game(final_four[2]["program"], final_four[3]["program"])
        sf2_w, sf2_l = (final_four[2], final_four[3]) if sf2["home"] > sf2["away"] \
                        else (final_four[3], final_four[2])
        sf2_l["program"]["ncaa_tournament_result"]["result"] = "final_four"
        sf2_w["program"]["ncaa_tournament_result"]["wins"]  += 1
        if verbose: print("    " + sf2_w["program"]["name"] + " def. " + sf2_l["program"]["name"])

        if verbose:
            print("")
            print("  -- Championship --")

        cr = _simulate_neutral_site_game(sf1_w["program"], sf2_w["program"])
        champion_entry, runner = (sf1_w, sf2_w) if cr["home"] > cr["away"] else (sf2_w, sf1_w)
        runner["program"]["ncaa_tournament_result"]["result"]         = "final_four"
        champion_entry["program"]["ncaa_tournament_result"]["wins"]  += 1
        champion_entry["program"]["ncaa_tournament_result"]["result"] = "champion"

        if verbose:
            print("    CHAMPION: " + champion_entry["program"]["name"] +
                  " (" + champion_entry["region"] + " " +
                  str(champion_entry["seed"]) + " seed)")

    # Apply buzz to all participants
    participant_names = {entry["program"]["name"] for entry in seeded_field}
    for p in all_programs:
        if p["name"] in participant_names:
            result = p["ncaa_tournament_result"]["result"]
            _apply_buzz_for_result(p, result, season_year)

    final_four_names = [e["program"]["name"] for e in final_four]
    champion_name    = champion_entry["program"]["name"] if champion_entry else "Unknown"
    champion_seed    = champion_entry["seed"] if champion_entry else None
    champion_conf    = champion_entry["program"]["conference"] if champion_entry else "Unknown"

    cinderellas = [
        p for p in all_programs
        if p["ncaa_tournament_result"]["seed"] is not None
        and p["ncaa_tournament_result"]["seed"] >= 10
        and p["ncaa_tournament_result"]["result"] in (
            "sweet_16", "elite_8", "final_four", "champion")
    ]

    return all_programs, {
        "champion":      champion_name,
        "champion_seed": champion_seed,
        "champion_conf": champion_conf,
        "final_four":    final_four_names,
        "cinderellas":   [(p["name"],
                           p["ncaa_tournament_result"]["seed"],
                           p["ncaa_tournament_result"]["result"])
                          for p in cinderellas],
        "field_size":    len(seeded_field),
    }


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_tournament_summary(tournament_results, season_year):
    print("")
    print("=== " + str(season_year) + " NCAA Tournament ===")
    print("  Champion:    " + tournament_results["champion"] +
          "  (" + tournament_results["champion_conf"] + ", " +
          str(tournament_results["champion_seed"]) + " seed)")
    print("  Final Four:  " + "  |  ".join(tournament_results["final_four"]))
    if tournament_results["cinderellas"]:
        print("  Cinderellas:")
        for name, seed, result in tournament_results["cinderellas"]:
            print("    " + name + " (seed " + str(seed) + ") -- " +
                  result.replace("_", " ").title())


def print_buzz_report(all_programs):
    from program import get_effective_prestige
    buzzed = sorted(
        [p for p in all_programs if p.get("tournament_buzz", {}).get("current", 0) > 0.5],
        key=lambda p: p["tournament_buzz"]["current"], reverse=True
    )
    if not buzzed:
        return
    print("")
    print("=== Tournament Buzz Report ===")
    print("{:<24} {:<8} {:<8} {:<8} {:<10} {}".format(
        "Program", "Gravity", "Base", "Buzz", "Effective", "Last Run"))
    print("-" * 72)
    for p in buzzed[:20]:
        b = p["tournament_buzz"]
        print("{:<24} {:<8} {:<8} {:<8} {:<10} {}".format(
            p["name"][:23],
            str(p["prestige_gravity"]),
            str(p["prestige_current"]),
            str(round(b["current"], 1)),
            str(round(get_effective_prestige(p), 1)),
            b.get("last_result", "none")
        ))


def print_bracket_seedings(all_programs, season_year):
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
                str(r["seed"]), p["name"][:23], p["conference"][:19], record, result))
