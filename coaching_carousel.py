# -----------------------------------------
# COLLEGE HOOPS SIM -- Coaching Carousel v1.1
#
# v1.1 CHANGES -- Realistic job destination logic:
#
#   ROOT CAUSE OF FUNNEL BUG:
#     _find_best_available_job() returned the single highest-prestige
#     program with no cap on the gap. Every ambitious coach in the world
#     targeted North Carolina or Kansas in the same offseason, creating
#     an absurd carousel where a coach from Arkansas-Pine Bluff gets
#     poached to a 95-prestige school.
#
#   FIX:
#     1. MAX_REALISTIC_JUMP cap: a coach can only jump a limited number
#        of prestige points based on their current program's prestige tier.
#        A coach at a 15-prestige school can realistically jump to ~35.
#        A coach at a 60-prestige school can jump to ~82.
#     2. Destination randomization: picks from a pool of eligible jobs
#        weighted by prestige with noise -- not always the single best.
#        This naturally distributes departures across multiple programs.
#     3. Destination exclusivity: claimed_destinations set prevents
#        multiple coaches from funneling to the same school.
#
# v1.0 (preserved):
#   Firing triggers, job market, player impact pipeline.
#   Security diagnostic output.
# -----------------------------------------

import random
from coach import generate_coach, ensure_coach_carousel_attrs
from player import ensure_player_carousel_attrs
from program import (ensure_carousel_state, get_firing_threshold,
                     update_stale_meter, update_coaching_capital)
from names import generate_coach_name

# -----------------------------------------
# CONSTANTS
# -----------------------------------------

HARD_FIRING_FLOOR              = 15
VOLUNTARY_DEPARTURE_MIN_SECURITY = 45
VOLUNTARY_DEPARTURE_PRESTIGE_GAP = 15
NEW_COACH_PROTECTION_SEASONS   = 1
PORTAL_WAVE_FIRING             = 1.0
PORTAL_WAVE_RESIGNATION        = 0.60
POACH_BASE_PROB                = 0.18
POACH_RECRUITED_BY_BONUS       = 0.22

# Maximum realistic prestige jump by current program's conference tier.
# A coach from a floor_conf school (~10 prestige) can realistically
# target a low_major job (~30), not North Carolina (~95).
MAX_REALISTIC_JUMP = {
    "floor_conf":  22,
    "low_major":   25,
    "mid_major":   28,
    "high_major":  22,
    "power":       20,
}
_DEFAULT_MAX_JUMP = 25

_AD_EXPERIENCE_FLOOR = {
    "veteran_preferred":  8,
    "pedigree_seeker":    3,
    "analytics_forward":  0,
    "hometown_loyalty":   0,
    "opportunist":        0,
}

_PRESTIGE_HIRE_FLOOR = {
    "power":      35,
    "high_major": 20,
    "mid_major":  10,
    "low_major":   1,
    "floor_conf":  1,
}


# -----------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------

def run_coaching_carousel(all_programs, season_year, verbose=True):
    """
    Runs the full coaching carousel for one offseason.

    Returns:
      all_programs     -- modified in place
      carousel_report  -- dict with firing/hiring summary
      portal_additions -- list of player dicts added to portal by carousel
    """
    for program in all_programs:
        ensure_carousel_state(program)
        coach = program.get("coach", {})
        ensure_coach_carousel_attrs(coach)
        for player in program.get("roster", []):
            ensure_player_carousel_attrs(player, coach_id=coach.get("coach_id"))

    changes = _evaluate_all_programs(all_programs, season_year, verbose)

    if verbose:
        fired    = [c for c in changes if c["reason"] == "fired"]
        resigned = [c for c in changes if c["reason"] == "resigned"]
        poached  = [c for c in changes if c["reason"] == "poached"]
        print("")
        print("--- " + str(season_year) + " Coaching Carousel ---")
        print("  Fired:    " + str(len(fired)))
        print("  Resigned: " + str(len(resigned)))
        print("  Poached:  " + str(len(poached)))
        securities = sorted([p.get("job_security", 75) for p in all_programs])
        below_40   = sum(1 for s in securities if s < 40)
        below_25   = sum(1 for s in securities if s < 25)
        print("  Job security -- min: " + str(round(min(securities), 1)) +
              "  median: " + str(round(securities[len(securities)//2], 1)) +
              "  below 40: " + str(below_40) +
              "  below 25: " + str(below_25))

    all_programs, hire_log = _run_job_market(all_programs, changes, season_year, verbose)

    all_programs, portal_additions, impact_log = _run_player_impact(
        all_programs, changes, season_year, verbose
    )

    carousel_report = {
        "season_year":      season_year,
        "changes":          changes,
        "hire_log":         hire_log,
        "portal_additions": len(portal_additions),
        "impact_log":       impact_log,
    }

    return all_programs, carousel_report, portal_additions


# -----------------------------------------
# PHASE 1: EVALUATE
# -----------------------------------------

def _evaluate_all_programs(all_programs, season_year, verbose):
    """
    Evaluates every program for coaching changes.
    claimed_destinations prevents multiple coaches targeting the same school.
    """
    changes              = []
    claimed_destinations = set()

    for program in all_programs:
        coach    = program.get("coach", {})
        seasons  = program.get("coach_seasons", 0)
        security = program.get("job_security", 75)
        carousel = program["carousel_state"]

        if seasons <= NEW_COACH_PROTECTION_SEASONS:
            continue

        _update_coach_career_record(program)

        # CHECK 1: HARD FLOOR FIRING
        if security <= HARD_FIRING_FLOOR:
            changes.append(_build_change(program, "fired", "job_security_floor"))
            if verbose:
                print("  FIRED (floor): " + program["name"] +
                      " -- " + coach.get("name", "?") +
                      " security=" + str(round(security, 1)))
            continue

        # CHECK 2: BOARD PATIENCE FIRING
        threshold = get_firing_threshold(program)
        if security < threshold:
            shortfall = threshold - security
            capital   = carousel.get("coaching_capital", 0.0)
            if capital >= shortfall:
                carousel["coaching_capital"] = round(capital - shortfall, 2)
                if verbose:
                    print("  CAPITAL SAVES: " + program["name"] +
                          " -- " + coach.get("name", "?") +
                          " (capital " + str(round(capital, 1)) +
                          " absorbed shortfall " + str(round(shortfall, 1)) + ")")
            else:
                changes.append(_build_change(program, "fired", "board_patience"))
                if verbose:
                    print("  FIRED (board): " + program["name"] +
                          " -- " + coach.get("name", "?") +
                          " security=" + str(round(security, 1)) +
                          " threshold=" + str(threshold))
                continue

        # CHECK 3: STALE METER
        stale = carousel.get("stale_meter", 0)
        if stale >= 100:
            changes.append(_build_change(program, "fired", "stale_meter"))
            carousel["stale_meter"] = 0
            if verbose:
                print("  FIRED (stale): " + program["name"] +
                      " -- " + coach.get("name", "?"))
            continue

        # CHECK 4: VOLUNTARY DEPARTURE
        ambition = coach.get("ambition", 10)
        loyalty  = coach.get("loyalty", 10)

        if (ambition >= 14 and
                security >= VOLUNTARY_DEPARTURE_MIN_SECURITY and
                seasons >= 2):

            best_job = _find_best_available_job(
                program, all_programs, changes, claimed_destinations
            )

            if best_job is not None:
                prestige_gap = best_job["prestige_current"] - program["prestige_current"]
                if prestige_gap >= VOLUNTARY_DEPARTURE_PRESTIGE_GAP:
                    loyalty_resist = loyalty / 20.0
                    leave_chance   = min(0.80, (ambition / 20.0) - loyalty_resist * 0.5)

                    if random.random() < leave_chance:
                        reason = "poached" if prestige_gap >= 25 else "resigned"
                        claimed_destinations.add(best_job["name"])
                        changes.append(_build_change(
                            program, reason, "ambition",
                            destination=best_job["name"]
                        ))
                        if verbose:
                            print("  " + reason.upper() + ": " + program["name"] +
                                  " -- " + coach.get("name", "?") +
                                  " -> " + best_job["name"] +
                                  " (gap +" + str(round(prestige_gap, 0)) + ")")

    return changes


def _find_best_available_job(current_program, all_programs, existing_changes,
                              claimed_destinations):
    """
    Finds a realistic job destination for this coach.

    Hard cap on how far a coach can realistically jump based on their
    current program's conference tier. A floor_conf coach can jump ~22
    prestige points max -- not to a 95-prestige blue blood.

    Uses weighted random selection from eligible candidates so departures
    spread across multiple programs rather than funneling to one school.
    """
    from programs_data import get_conference_tier

    current_prestige = current_program["prestige_current"]
    conf_tier        = get_conference_tier(current_program["conference"])["tier"]
    max_jump         = MAX_REALISTIC_JUMP.get(conf_tier, _DEFAULT_MAX_JUMP)
    realistic_ceiling = current_prestige + max_jump

    changing = {c["program_name"] for c in existing_changes}

    candidates = []
    for prog in all_programs:
        if prog["name"] == current_program["name"]:
            continue
        if prog["name"] in changing:
            continue
        if prog["name"] in claimed_destinations:
            continue
        if prog["prestige_current"] <= current_prestige + VOLUNTARY_DEPARTURE_PRESTIGE_GAP - 1:
            continue
        if prog["prestige_current"] > realistic_ceiling:
            continue
        candidates.append(prog)

    if not candidates:
        return None

    # Weighted random -- higher prestige more attractive but not deterministic
    weights = []
    for prog in candidates:
        weight = max(1, prog["prestige_current"] - current_prestige)
        weight += random.gauss(0, 5)
        weights.append(max(0.1, weight))

    total = sum(weights)
    if total <= 0:
        return random.choice(candidates)

    roll       = random.random() * total
    cumulative = 0.0
    for prog, w in zip(candidates, weights):
        cumulative += w
        if roll <= cumulative:
            return prog

    return candidates[-1]


def _build_change(program, reason, trigger, destination=None):
    coach = program.get("coach", {})
    return {
        "program_name": program["name"],
        "program":      program,
        "coach_name":   coach.get("name", "Unknown"),
        "coach_id":     coach.get("coach_id", None),
        "coach_obj":    dict(coach),
        "reason":       reason,
        "trigger":      trigger,
        "destination":  destination,
        "prestige":     program["prestige_current"],
    }


def _update_coach_career_record(program):
    coach = program.get("coach", {})
    coach["career_wins"]   = coach.get("career_wins", 0) + program.get("wins", 0)
    coach["career_losses"] = coach.get("career_losses", 0) + program.get("losses", 0)
    coach["experience"]    = coach.get("experience", 0) + 1


# -----------------------------------------
# PHASE 2: JOB MARKET
# -----------------------------------------

def _run_job_market(all_programs, changes, season_year, verbose):
    from programs_data import get_conference_tier

    if not changes:
        return all_programs, []

    hire_log       = []
    displaced_pool = [c["coach_obj"] for c in changes]

    open_jobs = sorted(
        [c["program"] for c in changes],
        key=lambda p: p["prestige_current"],
        reverse=True
    )

    for program in open_jobs:
        carousel       = program["carousel_state"]
        ad_profile     = carousel.get("ad_hiring_profile", "opportunist")
        conf_tier      = get_conference_tier(program["conference"])["tier"]
        prestige_floor = _PRESTIGE_HIRE_FLOOR.get(conf_tier, 1)
        exp_floor      = _AD_EXPERIENCE_FLOOR.get(ad_profile, 0)

        eligible = [c for c in displaced_pool if c.get("experience", 0) >= exp_floor]

        if ad_profile == "pedigree_seeker":
            eligible = [c for c in eligible
                        if _estimate_coach_prestige(c) >= prestige_floor]

        if ad_profile == "hometown_loyalty":
            program_region = _get_program_region(program)
            regional = [c for c in eligible if c.get("home_region", "") == program_region]
            if regional:
                eligible = regional

        if ad_profile == "veteran_preferred":
            eligible.sort(key=lambda c: c.get("experience", 0), reverse=True)
        elif ad_profile == "analytics_forward":
            eligible.sort(
                key=lambda c: c.get("scheme_adaptability", 10) + c.get("in_game_adaptability", 10),
                reverse=True
            )

        new_coach = None
        if eligible:
            for candidate in eligible[:5]:
                if candidate.get("ambition", 10) >= 16 and program["prestige_current"] < 30:
                    continue
                new_coach = candidate
                displaced_pool.remove(candidate)
                break

        if new_coach is None:
            new_coach = _generate_new_hire(program, ad_profile, season_year)
            hire_type = "fresh"
        else:
            hire_type = "recycled"

        old_name = program.get("coach_name", "Unknown")
        _install_coach(program, new_coach, season_year)

        hire_log.append({
            "program":   program["name"],
            "new_coach": new_coach["name"],
            "old_coach": old_name,
            "hire_type": hire_type,
            "ad_profile": ad_profile,
        })

        if verbose:
            print("  HIRED (" + hire_type + "): " + program["name"] +
                  " -- " + new_coach["name"] +
                  " [" + new_coach["archetype"] + "]" +
                  " (exp=" + str(new_coach.get("experience", 0)) + ")")

    return all_programs, hire_log


def _estimate_coach_prestige(coach):
    wins   = coach.get("career_wins", 0)
    losses = coach.get("career_losses", 0)
    total  = wins + losses
    if total == 0:
        return 20
    return min(95, int((wins / total) * 60 + min(coach.get("experience", 0), 20) * 1.5))


def _get_program_region(program):
    _CONF_REGIONS = {
        "ACC": "southeast", "SEC": "southeast", "Big East": "northeast",
        "Big Ten": "midwest", "Big 12": "midwest", "American": "southeast",
        "A-10": "northeast", "Mountain West": "west", "WCC": "west",
        "Missouri Valley": "midwest", "MAC": "midwest", "Sun Belt": "southeast",
        "Conference USA": "southeast", "MAAC": "northeast", "CAA": "northeast",
        "Big Sky": "west", "ASUN": "southeast", "Horizon": "midwest",
        "Summit": "midwest", "Ivy League": "northeast", "Big West": "west",
        "Southern": "southeast", "Ohio Valley": "southeast",
        "Big South": "southeast", "Patriot": "northeast",
        "Southland": "southwest", "America East": "northeast",
        "SWAC": "southeast", "MEAC": "southeast",
        "NEC": "northeast", "WAC": "southwest",
    }
    return _CONF_REGIONS.get(program.get("conference", ""), "midwest")


def _generate_new_hire(program, ad_profile, season_year):
    prestige   = program["prestige_current"]
    coach_name = generate_coach_name()
    if ad_profile == "veteran_preferred":
        experience = random.randint(10, 25)
    elif ad_profile == "analytics_forward":
        experience = random.randint(0, 8)
    else:
        experience = random.randint(3, 18)
    return generate_coach(coach_name, prestige=prestige, experience=experience)


def _install_coach(program, new_coach, season_year):
    program["coach"]         = new_coach
    program["coach_name"]    = new_coach["name"]
    program["coach_seasons"] = 0
    program["job_security"]  = 75
    carousel = program["carousel_state"]
    carousel["last_hire_year"] = season_year
    carousel["firing_reason"]  = None


# -----------------------------------------
# PHASE 3: PLAYER IMPACT
# -----------------------------------------

def _run_player_impact(all_programs, changes, season_year, verbose):
    if not changes:
        return all_programs, [], []

    portal_additions = []
    impact_log       = []
    program_by_name  = {p["name"]: p for p in all_programs}

    for change in changes:
        program_name       = change["program_name"]
        program            = program_by_name.get(program_name)
        if program is None:
            continue

        departing_coach    = change["coach_obj"]
        departing_coach_id = change.get("coach_id")
        reason             = change["reason"]

        wave_mult      = PORTAL_WAVE_FIRING if reason == "fired" else PORTAL_WAVE_RESIGNATION
        roster         = program.get("roster", [])
        portal_entries = []

        for player in roster:
            year = player.get("year", "Freshman")
            ensure_player_carousel_attrs(player)
            prob = _portal_wave_probability(player, departing_coach_id, wave_mult)
            if random.random() < prob:
                portal_entries.append(player)
                impact_log.append({
                    "type":    "portal_wave",
                    "program": program_name,
                    "player":  player["name"],
                    "year":    year,
                    "reason":  reason,
                })

        portal_names = {p["name"] for p in portal_entries}
        program["roster"] = [p for p in roster if p["name"] not in portal_names]
        portal_additions.extend(portal_entries)

        if reason in ("resigned", "poached") and change.get("destination"):
            destination_prog = program_by_name.get(change["destination"])
            if destination_prog is not None:
                poached_players, poach_events = _run_poach_check(
                    program, destination_prog, departing_coach,
                    departing_coach_id, season_year, verbose
                )
                portal_additions.extend(poached_players)
                impact_log.extend(poach_events)

        decommit_events = _run_recruit_decommits(program, departing_coach, reason)
        impact_log.extend(decommit_events)

    if verbose and portal_additions:
        print("  Portal wave + poach: " + str(len(portal_additions)) +
              " players added to portal by coaching changes")

    return all_programs, portal_additions, impact_log


def _portal_wave_probability(player, departing_coach_id, wave_mult):
    year          = player.get("year", "Freshman")
    volatility    = player.get("volatility", 5)
    coach_loyalty = player.get("coach_loyalty", 10)
    home_loyalty  = player.get("home_loyalty", 7)
    pt_hunger     = player.get("playing_time_hunger", 10)
    recruited_by  = player.get("recruited_by")

    year_base = {"Freshman": 0.18, "Sophomore": 0.14, "Junior": 0.10, "Senior": 0.05}
    base = year_base.get(year, 0.12)

    vol_mod         = (volatility    - 10) / 20.0 * 0.15
    loyalty_mod     = (coach_loyalty - 10) / 20.0 * 0.10
    home_mod        = (home_loyalty  - 10) / 20.0 * (-0.08)
    pt_mod          = (pt_hunger     - 10) / 20.0 * 0.08
    recruited_bonus = 0.15 if recruited_by == departing_coach_id else 0.0

    raw_prob = base + vol_mod + loyalty_mod + home_mod + pt_mod + recruited_bonus
    return min(0.75, max(0.01, min(0.65, raw_prob)) * wave_mult)


def _run_poach_check(old_program, new_program, coach, coach_id, season_year, verbose):
    poached_players = []
    events          = []
    roster          = old_program.get("roster", [])
    open_slots      = max(0, 13 - len(new_program.get("roster", [])))

    if open_slots == 0:
        return poached_players, events

    prestige_delta = new_program["prestige_current"] - old_program["prestige_current"]

    for player in roster:
        if open_slots <= 0:
            break

        year          = player.get("year", "Freshman")
        coach_loyalty = player.get("coach_loyalty", 10)
        volatility    = player.get("volatility", 5)
        recruited_by  = player.get("recruited_by")

        base_prob = POACH_BASE_PROB
        if recruited_by == coach_id:
            base_prob += POACH_RECRUITED_BY_BONUS
        if coach_loyalty >= 15:
            base_prob += 0.10
        if prestige_delta < -15:
            base_prob *= 0.20
        elif prestige_delta < 0:
            base_prob *= 0.55
        elif prestige_delta >= 20:
            base_prob *= 1.30
        if year == "Senior":
            base_prob *= 0.45
            if prestige_delta <= 0:
                base_prob *= 0.20
        base_prob += (volatility - 10) / 20.0 * 0.10
        final_prob = max(0.0, min(0.70, base_prob))

        if random.random() < final_prob:
            if open_slots <= 0:
                break
            poached_players.append(player)
            open_slots -= 1
            events.append({
                "type":               "poach",
                "player":             player["name"],
                "year":               year,
                "from":               old_program["name"],
                "to":                 new_program["name"],
                "coach":              coach.get("name", "?"),
                "recruited_by_match": recruited_by == coach_id,
            })
            if verbose:
                match_str = " [recruited_by match]" if recruited_by == coach_id else ""
                print("  POACH: " + player["name"] + " (" + year + ")" +
                      " follows " + coach.get("name", "?") +
                      " from " + old_program["name"] +
                      " to " + new_program["name"] + match_str)

    if poached_players:
        poach_names = {p["name"] for p in poached_players}
        old_program["roster"] = [p for p in old_program.get("roster", [])
                                  if p["name"] not in poach_names]
        new_program["roster"].extend(poached_players)

    return poached_players, events


def _run_recruit_decommits(program, departing_coach, reason):
    events    = []
    committed = program.get("committed_recruits", [])
    if not committed:
        return events

    base_decommit   = 0.30 if reason == "fired" else 0.15
    still_committed = []

    for recruit in committed:
        prob  = base_decommit
        prob += (recruit.get("volatility", 5)        - 5) / 15.0 * 0.15
        prob += (recruit.get("prestige_ambition", 7) - 7) / 13.0 * 0.10

        if random.random() < prob:
            recruit["status"] = "available"
            events.append({
                "type":    "decommit",
                "recruit": recruit.get("name", "?"),
                "program": program["name"],
                "reason":  reason,
            })
        else:
            still_committed.append(recruit)

    program["committed_recruits"] = still_committed
    return events


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_carousel_report(carousel_report, verbose=True):
    year    = carousel_report["season_year"]
    changes = carousel_report["changes"]
    hires   = carousel_report["hire_log"]

    fired    = [c for c in changes if c["reason"] == "fired"]
    resigned = [c for c in changes if c["reason"] == "resigned"]
    poached  = [c for c in changes if c["reason"] == "poached"]

    print("")
    print("=" * 60)
    print("  " + str(year) + " COACHING CAROUSEL")
    print("=" * 60)
    print("  Total changes:   " + str(len(changes)))
    print("  Fired:           " + str(len(fired)))
    print("  Resigned:        " + str(len(resigned)))
    print("  Poached:         " + str(len(poached)))
    print("  Portal additions:" + str(carousel_report["portal_additions"]))

    if fired:
        print("")
        print("  -- FIRED --")
        for c in fired:
            print("    {:<24} {:<22} trigger: {}  prestige: {}".format(
                c["program_name"], c["coach_name"],
                c["trigger"], round(c["prestige"], 1)))

    if resigned or poached:
        print("")
        print("  -- DEPARTED (resigned / poached) --")
        for c in resigned + poached:
            dest = (" -> " + c["destination"]) if c.get("destination") else ""
            print("    {:<24} {:<22} {}  prestige: {}{}".format(
                c["program_name"], c["coach_name"],
                c["reason"], round(c["prestige"], 1), dest))

    if hires:
        print("")
        print("  -- NEW HIRES --")
        for h in hires:
            print("    {:<24} {:<22} ({}) AD: {}".format(
                h["program"], h["new_coach"],
                h["hire_type"], h["ad_profile"]))

    poach_events = [e for e in carousel_report["impact_log"] if e["type"] == "poach"]
    if poach_events:
        print("")
        print("  -- COACH POACHES --")
        for e in poach_events:
            match = " [bond]" if e.get("recruited_by_match") else ""
            print("    {:<22} ({}) {} -> {}{}".format(
                e["player"], e["year"], e["from"], e["to"], match))

    decommit_events = [e for e in carousel_report["impact_log"] if e["type"] == "decommit"]
    if decommit_events:
        print("")
        print("  -- RECRUIT DECOMMITS --")
        for e in decommit_events:
            print("    {:<22} decommitted from {} ({})".format(
                e["recruit"], e["program"], e["reason"]))
