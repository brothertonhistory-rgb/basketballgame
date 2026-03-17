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
from tournament_sites import draw_tournament_sites, name_regionals, assign_seed_to_site

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

TOURNAMENT_FIELD_SIZE = 64
NUM_AUTO_BIDS         = 31
NUM_AT_LARGE          = TOURNAMENT_FIELD_SIZE - NUM_AUTO_BIDS
# REGIONS is set dynamically each year by draw_and_name_tournament_sites().
# Default fallback only — overridden before any tournament runs.
REGIONS = ["East", "West", "South", "Midwest"]

TIER_WEIGHT = {
    "power":      1.4,
    "high_major": 1.2,
    "mid_major":  1.0,
    "low_major":  0.7,
    "floor_conf": 0.7,
}

SEPARATION_HARD = 4
SEPARATION_SOFT = 8

# Holds this year's tournament geography — set by draw_and_name_tournament_sites()
_TOURNAMENT_DRAW = None


# -----------------------------------------
# TOURNAMENT GEOGRAPHY
# -----------------------------------------

def draw_and_name_tournament_sites(exclude_recent_cities=None):
    """
    Run the pre-season site draw.
    Sets the global REGIONS list to this year's dynamic directional names.
    Stores the full draw in _TOURNAMENT_DRAW for site assignment.
    Call once before simulate_ncaa_tournament() each season.
    """
    global REGIONS, _TOURNAMENT_DRAW

    draw = draw_tournament_sites(exclude_recent_cities=exclude_recent_cities)
    named_regionals = name_regionals(draw['sweet16_elite8'])
    draw['sweet16_elite8'] = named_regionals

    # Update REGIONS to this year's dynamic names
    REGIONS = [s['regional_name'] for s in named_regionals]
    _TOURNAMENT_DRAW = draw

    return draw


def tag_overall_one_seed(seeded_field):
    """
    After seeding is assigned, find the #1 overall seed —
    the best team among the four 1-seeds by selection score.
    Tags them with overall_one_seed=True on their ncaa_tournament_result.
    """
    one_seeds = [e for e in seeded_field if e['seed'] == 1]
    if not one_seeds:
        return
    best = max(one_seeds, key=lambda e: _selection_score(e['program']))
    best['program']['ncaa_tournament_result']['overall_one_seed'] = True


def assign_first_round_sites(seeded_field):
    """
    Assign opening weekend sites using the S-curve pick order.

    Teams ranked 1-8 on the S-curve pick their opening weekend site
    in order, each choosing the closest available site from the pool.
    S-curve ranks 1-4 are the four 1 seeds (they pick pod A sites).
    S-curve ranks 5-8 are the four 2 seeds (they pick pod B sites).
    Everyone else slots into their regional pod automatically.

    Pod A (1-seed side): seeds 1, 4, 5, 8, 9, 12, 13, 16
    Pod B (2-seed side): seeds 2, 3, 6, 7, 10, 11, 14, 15
    """
    if not _TOURNAMENT_DRAW:
        return

    from tournament_sites import haversine

    all_first_sites = list(_TOURNAMENT_DRAW['first_second'])
    regional_sites  = {s['regional_name']: s for s in _TOURNAMENT_DRAW['sweet16_elite8']}

    pod_a_seeds = {1, 4, 5, 8, 9, 12, 13, 16}
    pod_b_seeds = {2, 3, 6, 7, 10, 11, 14, 15}

    # Group entries by region
    by_region = {r: [] for r in REGIONS}
    for entry in seeded_field:
        r = entry.get('region')
        if r in by_region:
            by_region[r].append(entry)

    # --- S-CURVE SITE SELECTION: ranks 1-8 pick in order ---
    # Ranks 1-4 (1 seeds) pick pod A sites
    # Ranks 5-8 (2 seeds) pick pod B sites
    top_8 = sorted(
        [e for e in seeded_field if e.get('s_curve_rank', 99) <= 8],
        key=lambda e: e.get('s_curve_rank', 99)
    )

    available_sites = list(all_first_sites)
    pod_a_site = {}  # region_name -> site
    pod_b_site = {}  # region_name -> site

    for entry in top_8:
        if not available_sites:
            break
        prog   = entry['program']
        lat    = prog.get('latitude', 39.5)
        lon    = prog.get('longitude', -98.5)
        city   = prog.get('city', '')
        region = entry['region']
        rank   = entry.get('s_curve_rank', 99)

        # Home city advantage — if campus city matches a site, take it
        home_match = next(
            (s for s in available_sites if s['city'].lower() == city.lower()),
            None
        )
        if home_match:
            best = home_match
        else:
            best = min(available_sites,
                       key=lambda s: haversine(lat, lon, s['latitude'], s['longitude']))

        available_sites.remove(best)

        if rank <= 4:
            pod_a_site[region] = best   # 1 seed picks pod A site
        else:
            pod_b_site[region] = best   # 2 seed picks pod B site

    # --- ASSIGN EVERY TEAM TO THEIR SITE ---
    for region_name, entries in by_region.items():
        site_a = pod_a_site.get(region_name)
        site_b = pod_b_site.get(region_name)

        # Fallback for edge cases
        if not site_a and available_sites:
            site_a = available_sites.pop(0)
        if not site_b and available_sites:
            site_b = available_sites.pop(0)
        if not site_b:
            site_b = site_a

        for entry in entries:
            seed    = entry['seed']
            program = entry['program']
            site    = site_a if seed in pod_a_seeds else site_b
            program['ncaa_tournament_result']['first_round_site']      = site
            program['ncaa_tournament_result']['first_round_site_city'] = site['city'] if site else ''

        # Regional site
        reg_site = regional_sites.get(region_name)
        if reg_site:
            for entry in entries:
                entry['program']['ncaa_tournament_result']['regional_site']      = reg_site
                entry['program']['ncaa_tournament_result']['regional_site_city'] = reg_site['city']

    # Final Four site
    ff_site = _TOURNAMENT_DRAW.get('final_four')
    if ff_site:
        for entry in seeded_field:
            entry['program']['ncaa_tournament_result']['final_four_site']      = ff_site
            entry['program']['ncaa_tournament_result']['final_four_site_city'] = ff_site['city']


# -----------------------------------------
# SELECTION SCORE
# -----------------------------------------

# -----------------------------------------
# SELECTION SCORE
# Uses NET quadrant ranking imported from season.py.
# Falls back to simple win_pct * tier_weight if NET score unavailable.
# _prog_lookup is set once per tournament run for efficiency.
# -----------------------------------------

_prog_lookup_cache = {}   # populated by simulate_ncaa_tournament before selection


def _selection_score(program):
    from program import get_effective_prestige
    from programs_data import get_conference_tier

    # Use cached NET score if available (set by simulate_ncaa_tournament)
    net = program.get("_net_score")
    if net is not None:
        # Small effective prestige tiebreaker -- identical NET scores go to
        # the program with more historical prestige
        ep_tb = get_effective_prestige(program) / 10000.0
        return net + ep_tb

    # Fallback: conference-weighted win percentage (original formula)
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

    # --- S-CURVE RANKING ---
    # After seeds and regions are assigned, stamp each entry with its
    # S-curve rank (1-64). This determines site selection order:
    # ranks 1-8 pick opening weekend sites in order, closest available.
    #
    # S-curve order within each seed group (4 teams):
    #   Seed 1: ranks 1,2,3,4     (best to worst 1 seed)
    #   Seed 2: ranks 5,6,7,8     (best to worst 2 seed)
    #   Seed 3: ranks 9,10,11,12  etc.
    #
    # Within each seed group, teams are ranked by selection score.
    s_curve_rank = 0
    for s in range(16):
        group = seed_groups[s]
        # Sort group by selection score descending to get intra-group ranking
        group_sorted = sorted(group, key=lambda e: _selection_score(e['program']), reverse=True)
        for entry in group_sorted:
            s_curve_rank += 1
            entry['s_curve_rank'] = s_curve_rank

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

def simulate_ncaa_tournament(all_programs, auto_bids, season_year=2024,
                              verbose=True, exclude_recent_tournament_cities=None):
    from season import calculate_net_score

    # --- Pre-season tournament geography draw ---
    # Sets REGIONS dynamically and stores site assignments.
    # Pass exclude_recent_tournament_cities from season.py to avoid repeats.
    draw_and_name_tournament_sites(
        exclude_recent_cities=exclude_recent_tournament_cities
    )

    if verbose:
        print("")
        print("  Tournament Sites:")
        print("    Final Four:  " + _TOURNAMENT_DRAW['final_four']['city'] + ", " +
              _TOURNAMENT_DRAW['final_four']['state'] +
              " -- " + _TOURNAMENT_DRAW['final_four']['arena'])
        for s in _TOURNAMENT_DRAW['sweet16_elite8']:
            print("    [" + s['regional_name'] + " Regional]  " +
                  s['city'] + ", " + s['state'] + " -- " + s['arena'])
        print("    Opening Weekend:")
        for s in _TOURNAMENT_DRAW['first_second']:
            print("      " + s['city'] + ", " + s['state'] +
                  " -- " + s['arena'] + " (" + str(s['capacity']) + ")")

    # Stamp NET scores on every program before selection runs.
    for p in all_programs:
        p["_net_score"] = calculate_net_score(p, all_programs)

    for p in all_programs:
        ensure_tournament_buzz(p)
        p["ncaa_tournament_result"] = {
            "seed":                  None,
            "region":                None,
            "result":                "none",
            "wins":                  0,
            "at_large":              False,
            "overall_one_seed":      False,
            "first_round_site":      None,
            "first_round_site_city": None,
            "regional_site":         None,
            "regional_site_city":    None,
            "final_four_site":       None,
            "final_four_site_city":  None,
        }

    field        = select_field(all_programs, auto_bids)
    seeded_field = _assign_seeds_and_regions(field)

    for entry in seeded_field:
        p = entry["program"]
        p["ncaa_tournament_result"]["seed"]     = entry["seed"]
        p["ncaa_tournament_result"]["region"]   = entry["region"]
        p["ncaa_tournament_result"]["at_large"] = entry["at_large"]

    # Tag overall #1 seed
    tag_overall_one_seed(seeded_field)

    # Assign geographic sites to every team
    assign_first_round_sites(seeded_field)

    region_groups = {r: [] for r in REGIONS}
    for entry in seeded_field:
        region_groups[entry["region"]].append(entry)

    if verbose:
        print("")
        print("--- NCAA Tournament ---")
        print("  Field: " + str(len(seeded_field)) + " teams")

        # Print S-curve top 8 — these are the teams that pick sites
        top_8 = sorted(
            [e for e in seeded_field if e.get('s_curve_rank', 99) <= 8],
            key=lambda e: e['s_curve_rank']
        )
        print("")
        print("  S-Curve Top 8 (site selection order):")
        for e in top_8:
            overall = " << OVERALL #1" if e['program']['ncaa_tournament_result'].get('overall_one_seed') else ""
            print("    #{rank}  ({seed} seed, {region})  {name}{overall}".format(
                rank=e['s_curve_rank'],
                seed=e['seed'],
                region=e['region'],
                name=e['program']['name'],
                overall=overall,
            ))

        # --- Opening Weekend Site Breakdown ---
        # Group all teams by their first round site city
        site_groups = {}
        for entry in seeded_field:
            r = entry["program"]["ncaa_tournament_result"]
            site_city = r.get("first_round_site_city") or "Unknown"
            site_obj  = r.get("first_round_site") or {}
            arena     = site_obj.get("arena", "")
            state     = site_obj.get("state", "")
            key       = site_city
            if key not in site_groups:
                site_groups[key] = {
                    "arena": arena,
                    "state": state,
                    "region": entry["region"],
                    "teams": []
                }
            site_groups[key]["teams"].append(entry)

        print("")
        print("  -- Opening Weekend Sites --")
        for city, info in sorted(site_groups.items(),
                                  key=lambda x: x[1]["region"]):
            teams = sorted(info["teams"], key=lambda e: e["seed"])
            print("")
            print("  [{region}]  {city}, {state}  --  {arena}".format(
                region=info["region"],
                city=city,
                state=info["state"],
                arena=info["arena"],
            ))
            # Print matchups: 1v16, 8v9, etc in pairs
            seed_map = {e["seed"]: e for e in teams}
            matchup_order = [(1,16),(8,9),(5,12),(4,13),(6,11),(3,14),(7,10),(2,15)]
            for hi, lo in matchup_order:
                if hi in seed_map and lo in seed_map:
                    hi_e = seed_map[hi]
                    lo_e = seed_map[lo]
                    al_hi = "*" if hi_e["at_large"] else " "
                    al_lo = "*" if lo_e["at_large"] else " "
                    print("    ({hi:>2}) {hi_name:<24}{al_hi}  vs  ({lo:>2}) {lo_name:<24}{al_lo}".format(
                        hi=hi,
                        hi_name=hi_e["program"]["name"][:23],
                        al_hi=al_hi,
                        lo=lo,
                        lo_name=lo_e["program"]["name"][:23],
                        al_lo=al_lo,
                    ))

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

    # Clean up temp NET score field
    for p in all_programs:
        p.pop("_net_score", None)

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
