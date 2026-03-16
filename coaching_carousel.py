# -----------------------------------------
# COLLEGE HOOPS SIM -- Coaching Carousel v1.3
#
# v1.3 CHANGES -- Contract Protection + Buyout Reputation + Blue Blood Cascade:
#
#   CONTRACT PROTECTION:
#     While a coach has contract_years_remaining > 0, the effective
#     firing threshold is reduced by CONTRACT_PROTECTION_POINTS (15).
#     So a blue blood (base threshold 40) needs security below 25 to
#     fire a coach under contract, not 40.
#     Hard floor (security <= 15) and stale meter still fire regardless --
#     no one gets infinite protection.
#     contract_years_remaining decrements each season in
#     _update_coach_career_record().
#
#   BUYOUT REPUTATION:
#     When a coach is fired while contract_years_remaining > 0,
#     record_buyout() is called on the program.
#     hot_seat_reputation builds up from repeated early firings.
#     In the job market, coaches with loyalty >= 14 or rebuild_tolerance >= 14
#     check hot_seat_reputation before accepting a job.
#     Programs with reputation >= 50 get skipped by quality coaches.
#     Programs with reputation >= 75 can only attract desperate hires.
#
#   BLUE BLOOD CASCADE EVENT:
#     When a prestige 95+ job opens, it triggers a special hiring phase
#     before the normal market runs.
#     Pass 1: entire displaced pool gets evaluated for the blue blood job.
#     Pass 2: if no suitable match, the AD approaches the best available
#             currently-employed coach -- triggering a voluntary departure
#             with 70% probability regardless of normal ambition threshold.
#     One cascade per blue blood opening. The cascade departure feeds
#     back into the job pool for normal market resolution.
#
# v1.2 CHANGES (preserved):
#   Style fit, breakout candidates, revised jump caps.
# -----------------------------------------

import random
from coach import (generate_coach, ensure_coach_carousel_attrs,
                   calculate_style_fit, is_breakout_candidate,
                   update_coach_buzz_history, check_retirement,
                   update_coach_age, record_job_change, get_age_inertia)
from player import ensure_player_carousel_attrs
from program import (ensure_carousel_state, get_firing_threshold,
                     update_stale_meter, update_coaching_capital,
                     record_buyout, get_hot_seat_reputation,
                     ensure_program_budget, get_effective_budget,
                     tick_budget_spike, apply_booster_spike)
from names import generate_coach_name

# -----------------------------------------
# CONSTANTS
# -----------------------------------------

HARD_FIRING_FLOOR                = 15
VOLUNTARY_DEPARTURE_MIN_SECURITY = 45
VOLUNTARY_DEPARTURE_PRESTIGE_GAP = 15
NEW_COACH_PROTECTION_SEASONS     = 1
PORTAL_WAVE_FIRING               = 1.0
PORTAL_WAVE_RESIGNATION          = 0.60
POACH_BASE_PROB                  = 0.18
POACH_RECRUITED_BY_BONUS         = 0.22

# Contract protection: while under contract, firing threshold reduced by this
# e.g. blue blood threshold 40 becomes 25 while coach is under contract
CONTRACT_PROTECTION_POINTS = 15

# Blue blood prestige threshold for cascade event
BLUE_BLOOD_CASCADE_THRESHOLD = 95

# Probability that a targeted currently-employed coach accepts a blue blood approach
BLUE_BLOOD_APPROACH_PROBABILITY = 0.70

# Hot seat reputation thresholds for coach willingness checks
HOT_SEAT_CONCERN_THRESHOLD    = 50   # loyalty/rebuild coaches avoid
HOT_SEAT_TOXIC_THRESHOLD      = 75   # almost no quality coach will sign here

# Max realistic jump by tier (base and breakout)
MAX_REALISTIC_JUMP = {
    "floor_conf":  22,
    "low_major":   28,
    "mid_major":   32,
    "high_major":  25,
    "power":       20,
}
MAX_REALISTIC_JUMP_BREAKOUT = {
    "floor_conf":  55,
    "low_major":   60,
    "mid_major":   55,
    "high_major":  45,
    "power":       35,
}
_DEFAULT_MAX_JUMP          = 25
_DEFAULT_MAX_JUMP_BREAKOUT = 50

_AD_BREAKOUT_EXP_FLOOR = {
    "veteran_preferred":  6,
    "pedigree_seeker":    5,
    "analytics_forward":  0,
    "hometown_loyalty":   2,
    "opportunist":        1,
}

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

STYLE_FIT_GOOD  = 65
STYLE_FIT_BAD   = 40
STYLE_FIT_DECAY = 0.15

# Free agent pool: coaches who have been without a job this many seasons retire
FREE_AGENT_MAX_SEASONS = 3

# Instability reputation threshold -- programs check before hiring
INSTABILITY_CONCERN_THRESHOLD = 40   # raises eyebrows
INSTABILITY_TOXIC_THRESHOLD   = 70   # most programs won't touch them


# -----------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------

def run_coaching_carousel(all_programs, season_year, free_agent_pool=None, verbose=True):
    if free_agent_pool is None:
        free_agent_pool = []

    for program in all_programs:
        ensure_carousel_state(program)
        ensure_program_budget(program)
        tick_budget_spike(program)
        apply_booster_spike(program)
        coach = program.get("coach", {})
        ensure_coach_carousel_attrs(coach)
        for player in program.get("roster", []):
            ensure_player_carousel_attrs(player, coach_id=coach.get("coach_id"))

    # Age all head coaches and staff by 1 season
    _age_all_coaches(all_programs, free_agent_pool)

    # Run retirement checks on free agents -- those who've waited too long exit
    free_agent_pool = _clean_free_agent_pool(free_agent_pool, season_year, verbose)

    _update_all_breakout_states(all_programs)

    changes = _evaluate_all_programs(
        all_programs, season_year, free_agent_pool, verbose
    )

    if verbose:
        fired      = [c for c in changes if c["reason"] == "fired"]
        resigned   = [c for c in changes if c["reason"] == "resigned"]
        poached    = [c for c in changes if c["reason"] == "poached"]
        breakouts  = sum(1 for p in all_programs if p.get("coach", {}).get("breakout_candidate"))
        buyouts    = [c for c in changes if c.get("is_buyout")]
        print("")
        print("--- " + str(season_year) + " Coaching Carousel ---")
        print("  Fired:    " + str(len(fired)) +
              (" (" + str(len(buyouts)) + " buyouts)" if buyouts else ""))
        print("  Resigned: " + str(len(resigned)))
        print("  Poached:  " + str(len(poached)))
        print("  Breakout candidates this offseason: " + str(breakouts))
        securities = sorted([p.get("job_security", 75) for p in all_programs])
        below_40   = sum(1 for s in securities if s < 40)
        below_25   = sum(1 for s in securities if s < 25)
        print("  Job security -- min: " + str(round(min(securities), 1)) +
              "  median: " + str(round(securities[len(securities)//2], 1)) +
              "  below 40: " + str(below_40) +
              "  below 25: " + str(below_25))

    all_programs, hire_log, free_agent_pool = _run_job_market(
        all_programs, changes, season_year, free_agent_pool, verbose
    )

    _apply_style_fit_all(all_programs, changes)
    _decay_style_fit(all_programs, changes)

    all_programs, portal_additions, impact_log = _run_player_impact(
        all_programs, changes, season_year, verbose
    )

    for program in all_programs:
        program.get("coach", {})["breakout_candidate"] = False

    carousel_report = {
        "season_year":      season_year,
        "changes":          changes,
        "hire_log":         hire_log,
        "portal_additions": len(portal_additions),
        "impact_log":       impact_log,
        "free_agent_pool_size": len(free_agent_pool),
    }

    return all_programs, carousel_report, portal_additions, free_agent_pool


# -----------------------------------------
# FREE AGENT POOL + AGING HELPERS
# -----------------------------------------

def _age_all_coaches(all_programs, free_agent_pool):
    """Ages all head coaches and free agents by 1 season."""
    for program in all_programs:
        coach = program.get("coach", {})
        if coach:
            update_coach_age(coach)
    for coach in free_agent_pool:
        update_coach_age(coach)


def _clean_free_agent_pool(free_agent_pool, season_year, verbose):
    """
    Removes coaches from the free agent pool who have been waiting too long
    or who decide to retire. Returns the cleaned pool.
    """
    survivors = []
    for coach in free_agent_pool:
        coach["free_agent_seasons"] = coach.get("free_agent_seasons", 0) + 1
        if coach["free_agent_seasons"] >= FREE_AGENT_MAX_SEASONS:
            if verbose:
                print("  RETIRED (free agent): " + coach.get("name", "?") +
                      " (age " + str(coach.get("age", "?")) +
                      ", " + str(coach["free_agent_seasons"]) + " seasons without work)")
            continue
        if check_retirement(coach, just_fired=False):
            if verbose:
                print("  RETIRED: " + coach.get("name", "?") +
                      " (age " + str(coach.get("age", "?")) + ", free agent)")
            continue
        survivors.append(coach)
    return survivors


# -----------------------------------------
# BREAKOUT STATE UPDATE
# -----------------------------------------

def _update_all_breakout_states(all_programs):
    for program in all_programs:
        coach = program.get("coach", {})
        ensure_coach_carousel_attrs(coach)

        season_history = program.get("season_history", [])
        if not season_history:
            continue

        last         = season_history[-1]
        conf_finish  = last.get("conf_finish_percentile", 0.5)
        ncaa_result  = program.get("ncaa_tournament_result", {})
        ncaa_wins    = ncaa_result.get("wins", 0) if ncaa_result else 0

        update_coach_buzz_history(coach, ncaa_wins, conf_finish)

        gravity = program.get("prestige_gravity", 50)
        coach["breakout_candidate"] = is_breakout_candidate(coach, gravity)


# -----------------------------------------
# PHASE 1: EVALUATE
# -----------------------------------------

def _evaluate_all_programs(all_programs, season_year, free_agent_pool, verbose):
    """
    Evaluates every program for coaching changes.
    Contract protection suppresses firing threshold while coach is under deal.
    Adds retirement check, greed-based lateral moves, and age inertia.
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

        # --- RETIREMENT CHECK ---
        just_fired = False  # set below if fired
        if check_retirement(coach, just_fired=False):
            changes.append(_build_change(program, "fired", "retirement"))
            free_agent_pool  # retiring coaches don't enter pool
            if verbose:
                print("  RETIRED: " + program["name"] +
                      " -- " + coach.get("name", "?") +
                      " (age " + str(coach.get("age", "?")) + ")")
            continue

        contract_remaining = coach.get("contract_years_remaining", 0)
        under_contract     = contract_remaining > 0

        # CHECK 1: HARD FLOOR -- fires regardless of contract
        if security <= HARD_FIRING_FLOOR:
            is_buyout = under_contract
            changes.append(_build_change(program, "fired", "job_security_floor",
                                         is_buyout=is_buyout))
            if is_buyout:
                record_buyout(program, season_year)
            if verbose:
                print("  FIRED (floor): " + program["name"] +
                      " -- " + coach.get("name", "?") +
                      " security=" + str(round(security, 1)) +
                      (" [BUYOUT]" if is_buyout else ""))
            continue

        # CHECK 2: BOARD PATIENCE -- suppressed by contract protection
        threshold = get_firing_threshold(program)
        if under_contract:
            threshold = max(HARD_FIRING_FLOOR + 1,
                            threshold - CONTRACT_PROTECTION_POINTS)

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
                is_buyout = under_contract
                changes.append(_build_change(program, "fired", "board_patience",
                                             is_buyout=is_buyout))
                if is_buyout:
                    record_buyout(program, season_year)
                if verbose:
                    print("  FIRED (board): " + program["name"] +
                          " -- " + coach.get("name", "?") +
                          " security=" + str(round(security, 1)) +
                          " threshold=" + str(threshold) +
                          (" [BUYOUT]" if is_buyout else ""))
                continue

        # CHECK 3: STALE METER -- fires regardless of contract
        stale = carousel.get("stale_meter", 0)
        if stale >= 100:
            is_buyout = under_contract
            changes.append(_build_change(program, "fired", "stale_meter",
                                         is_buyout=is_buyout))
            carousel["stale_meter"] = 0
            if is_buyout:
                record_buyout(program, season_year)
            if verbose:
                print("  FIRED (stale): " + program["name"] +
                      " -- " + coach.get("name", "?"))
            continue

        # CHECK 4: VOLUNTARY DEPARTURE
        # Ambition drives prestige-seeking moves.
        # Greed drives salary-seeking lateral moves.
        # Age inertia suppresses both.
        ambition    = coach.get("ambition", 10)
        loyalty     = coach.get("loyalty", 10)
        greed       = coach.get("greed", 10)
        age_inertia = get_age_inertia(coach)
        cooldown    = coach.get("job_change_cooldown", 0)

        # Cooldown suppresses willingness to move again soon
        if cooldown > 0:
            continue

        # AMBITION PATH: chase a better job
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
                    leave_chance   = (min(0.80, (ambition / 20.0) - loyalty_resist * 0.5)
                                      * age_inertia)

                    if random.random() < leave_chance:
                        reason = "poached" if prestige_gap >= 25 else "resigned"
                        claimed_destinations.add(best_job["name"])
                        changes.append(_build_change(
                            program, reason, "ambition",
                            destination=best_job["name"]
                        ))
                        if verbose:
                            bo_str = " [BREAKOUT]" if coach.get("breakout_candidate") else ""
                            print("  " + reason.upper() + ": " + program["name"] +
                                  " -- " + coach.get("name", "?") +
                                  " -> " + best_job["name"] +
                                  " (gap +" + str(round(prestige_gap, 0)) + ")" + bo_str)
                        continue

        # GREED PATH: take a lateral move for a better salary
        if (greed >= 15 and
                security >= VOLUNTARY_DEPARTURE_MIN_SECURITY and
                seasons >= 2):

            salary_job = _find_better_paying_job(
                program, all_programs, changes, claimed_destinations
            )

            if salary_job is not None:
                greed_leave = (greed / 20.0) * 0.40 * age_inertia
                if random.random() < greed_leave:
                    claimed_destinations.add(salary_job["name"])
                    changes.append(_build_change(
                        program, "resigned", "greed",
                        destination=salary_job["name"]
                    ))
                    if verbose:
                        print("  RESIGNED ($$): " + program["name"] +
                              " -- " + coach.get("name", "?") +
                              " -> " + salary_job["name"] + " (salary)")

    return changes


def _find_best_available_job(current_program, all_programs, existing_changes,
                              claimed_destinations):
    from programs_data import get_conference_tier

    current_prestige = current_program["prestige_current"]
    conf_tier        = get_conference_tier(current_program["conference"])["tier"]
    coach            = current_program.get("coach", {})
    is_breakout      = coach.get("breakout_candidate", False)

    max_jump = (MAX_REALISTIC_JUMP_BREAKOUT if is_breakout
                else MAX_REALISTIC_JUMP).get(conf_tier, _DEFAULT_MAX_JUMP)
    realistic_ceiling = current_prestige + max_jump

    changing = {c["program_name"] for c in existing_changes}

    candidates = []
    for prog in all_programs:
        if prog["name"] == current_program["name"]:         continue
        if prog["name"] in changing:                        continue
        if prog["name"] in claimed_destinations:            continue
        if prog["prestige_current"] <= current_prestige + VOLUNTARY_DEPARTURE_PRESTIGE_GAP - 1: continue
        if prog["prestige_current"] > realistic_ceiling:    continue
        candidates.append(prog)

    if not candidates:
        return None

    weights = [max(0.1, max(1, p["prestige_current"] - current_prestige) +
                   random.gauss(0, 5))
               for p in candidates]
    total  = sum(weights)
    roll   = random.random() * total
    cumul  = 0.0
    for prog, w in zip(candidates, weights):
        cumul += w
        if roll <= cumul:
            return prog
    return candidates[-1]


def _find_better_paying_job(current_program, all_programs, existing_changes,
                             claimed_destinations):
    """
    Finds a job that pays meaningfully more than current program.
    Used for greed-driven lateral/step-down moves.
    Must pay at least 30% more than current budget to be worth leaving.
    """
    current_budget = get_effective_budget(current_program)
    min_budget     = current_budget * 1.30

    changing = {c["program_name"] for c in existing_changes}

    candidates = []
    for prog in all_programs:
        if prog["name"] == current_program["name"]:  continue
        if prog["name"] in changing:                 continue
        if prog["name"] in claimed_destinations:     continue
        prog_budget = get_effective_budget(prog)
        if prog_budget >= min_budget:
            candidates.append((prog, prog_budget))

    if not candidates:
        return None

    # Weight by how much more it pays
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


def _build_change(program, reason, trigger, destination=None, is_buyout=False):
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
        "is_breakout":  coach.get("breakout_candidate", False),
        "is_buyout":    is_buyout,
    }


def _update_coach_career_record(program):
    coach = program.get("coach", {})
    coach["career_wins"]   = coach.get("career_wins", 0) + program.get("wins", 0)
    coach["career_losses"] = coach.get("career_losses", 0) + program.get("losses", 0)
    coach["experience"]    = coach.get("experience", 0) + 1
    # Decrement contract years remaining (floor 0)
    remaining = coach.get("contract_years_remaining", 0)
    coach["contract_years_remaining"] = max(0, remaining - 1)


# -----------------------------------------
# PHASE 2: JOB MARKET
# -----------------------------------------

def _run_job_market(all_programs, changes, season_year, free_agent_pool, verbose):
    """
    Matches displaced coaches to open jobs.
    Fired/unplaced coaches enter the free agent pool.
    Salary floors and instability reputation filter the market.
    """
    from programs_data import get_conference_tier

    if not changes:
        return all_programs, [], free_agent_pool

    hire_log = []

    # Build displaced pool: current changes + free agents
    current_displaced = [c["coach_obj"] for c in changes
                         if c["reason"] != "retirement"]
    displaced_pool    = current_displaced + list(free_agent_pool)

    # Track which coaches from free_agent_pool get placed
    free_agent_ids = {c.get("coach_id") for c in free_agent_pool}

    # Separate blue blood openings from normal openings
    open_jobs   = [c["program"] for c in changes]
    bb_jobs     = [p for p in open_jobs if p["prestige_current"] >= BLUE_BLOOD_CASCADE_THRESHOLD]
    normal_jobs = sorted(
        [p for p in open_jobs if p["prestige_current"] < BLUE_BLOOD_CASCADE_THRESHOLD],
        key=lambda p: p["prestige_current"],
        reverse=True
    )

    program_by_name = {p["name"]: p for p in all_programs}
    placed_ids      = set()   # track coach_ids that got placed

    # --- BLUE BLOOD CASCADE HIRING ---
    for bb_program in bb_jobs:
        if verbose:
            print("")
            print("  *** BLUE BLOOD OPENING: " + bb_program["name"] +
                  " (prestige " + str(round(bb_program["prestige_current"], 1)) + ") ***")

        new_coach, hire_type = _hire_for_blue_blood(
            bb_program, displaced_pool, all_programs, changes, season_year, verbose
        )

        if new_coach is None:
            new_coach = _generate_new_hire(bb_program,
                                           bb_program["carousel_state"].get("ad_hiring_profile", "opportunist"),
                                           season_year)
            hire_type = "fresh"
        else:
            if new_coach.get("coach_id") in free_agent_ids:
                placed_ids.add(new_coach.get("coach_id"))

        _update_salary_on_hire(new_coach, bb_program)
        record_job_change(new_coach)
        old_name = bb_program.get("coach_name", "Unknown")
        _install_coach(bb_program, new_coach, season_year)

        hire_log.append({
            "program":    bb_program["name"],
            "new_coach":  new_coach["name"],
            "old_coach":  old_name,
            "hire_type":  hire_type,
            "ad_profile": bb_program["carousel_state"].get("ad_hiring_profile", "opportunist"),
        })

        if verbose:
            print("  HIRED (" + hire_type + "): " + bb_program["name"] +
                  " -- " + new_coach["name"] +
                  " [" + new_coach["archetype"] + "]" +
                  " (exp=" + str(new_coach.get("experience", 0)) + ")")

    # --- NORMAL JOB MARKET ---
    for program in normal_jobs:
        hot_seat    = get_hot_seat_reputation(program, season_year)
        carousel    = program["carousel_state"]
        ad_profile  = carousel.get("ad_hiring_profile", "opportunist")
        conf_tier   = get_conference_tier(program["conference"])["tier"]
        prestige_floor = _PRESTIGE_HIRE_FLOOR.get(conf_tier, 1)
        exp_floor      = _AD_EXPERIENCE_FLOOR.get(ad_profile, 0)
        prog_budget    = get_effective_budget(program)

        eligible = [c for c in displaced_pool if c.get("experience", 0) >= exp_floor]

        # Salary floor filter: coaches won't take below their floor
        eligible = [c for c in eligible
                    if prog_budget >= c.get("salary_floor", 0)]

        # Instability reputation filter
        eligible = [c for c in eligible
                    if c.get("instability_reputation", 0) < INSTABILITY_TOXIC_THRESHOLD]
        if hot_seat >= HOT_SEAT_CONCERN_THRESHOLD:
            # Stable programs with hot seat issues also lose quality coaches who
            # care about instability -- use a tighter instability filter
            eligible = [c for c in eligible
                        if c.get("instability_reputation", 0) < INSTABILITY_CONCERN_THRESHOLD]

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

        # Breakout candidate consideration
        breakout_exp_floor  = _AD_BREAKOUT_EXP_FLOOR.get(ad_profile, 99)
        breakout_candidates = [
            c for c in eligible
            if c.get("breakout_candidate") and
               c.get("experience", 0) >= breakout_exp_floor
        ]

        # Hot seat reputation filter
        if hot_seat >= HOT_SEAT_TOXIC_THRESHOLD:
            eligible = [c for c in eligible
                        if c.get("loyalty", 10) < 10 and
                           c.get("rebuild_tolerance", 10) < 10]
            if verbose and hot_seat >= HOT_SEAT_TOXIC_THRESHOLD:
                print("  HOT SEAT WARNING: " + program["name"] +
                      " reputation=" + str(hot_seat) + " -- quality coaches avoiding")
        elif hot_seat >= HOT_SEAT_CONCERN_THRESHOLD:
            eligible = [c for c in eligible
                        if not (c.get("loyalty", 10) >= 14 or
                                c.get("rebuild_tolerance", 10) >= 14)]

        new_coach = None
        hire_type = "recycled"

        if ad_profile == "analytics_forward" and breakout_candidates:
            for bc in breakout_candidates[:3]:
                new_coach = bc
                displaced_pool.remove(bc)
                hire_type = "recycled_breakout"
                if bc.get("coach_id") in free_agent_ids:
                    placed_ids.add(bc.get("coach_id"))
                if verbose:
                    print("  BREAKOUT HIRE: " + program["name"] +
                          " pursues breakout coach " + bc.get("name", "?"))
                break

        if new_coach is None:
            for candidate in eligible[:5]:
                if candidate.get("ambition", 10) >= 16 and program["prestige_current"] < 30:
                    continue
                new_coach = candidate
                displaced_pool.remove(candidate)
                if candidate.get("coach_id") in free_agent_ids:
                    placed_ids.add(candidate.get("coach_id"))
                break

        if new_coach is None:
            new_coach = _generate_new_hire(program, ad_profile, season_year)
            hire_type = "fresh"

        _update_salary_on_hire(new_coach, program)
        record_job_change(new_coach)
        old_name = program.get("coach_name", "Unknown")
        _install_coach(program, new_coach, season_year)

        hire_log.append({
            "program":    program["name"],
            "new_coach":  new_coach["name"],
            "old_coach":  old_name,
            "hire_type":  hire_type,
            "ad_profile": ad_profile,
        })

        if verbose:
            rep_str = (" [hot_seat=" + str(hot_seat) + "]" if hot_seat >= 30 else "")
            budget_str = (" [$" + _fmt_salary(prog_budget) + "]"
                          if program.get("budget_spike", 0) > 0 else "")
            print("  HIRED (" + hire_type + "): " + program["name"] +
                  " -- " + new_coach["name"] +
                  " [" + new_coach["archetype"] + "]" +
                  " (exp=" + str(new_coach.get("experience", 0)) + ")" +
                  rep_str + budget_str)

    # Unplaced coaches from current changes enter the free agent pool
    placed_names = {h["new_coach"] for h in hire_log}
    for change in changes:
        if change["reason"] == "retirement":
            continue
        coach_obj = change["coach_obj"]
        if (coach_obj.get("name") not in placed_names and
                coach_obj.get("coach_id") not in placed_ids):
            coach_obj["staff_role"]       = "free_agent"
            coach_obj["free_agent_seasons"] = 0
            free_agent_pool.append(coach_obj)

    # Remove placed free agents from pool
    free_agent_pool = [c for c in free_agent_pool
                       if c.get("coach_id") not in placed_ids]

    return all_programs, hire_log, free_agent_pool


def _update_salary_on_hire(coach, program):
    """Updates coach salary_current and adjusts salary_floor upward on hire."""
    budget = get_effective_budget(program)
    coach["salary_current"] = budget
    # Floor rises to 70% of current salary -- won't take a big step down next time
    coach["salary_floor"] = max(
        coach.get("salary_floor", 0),
        int(budget * 0.70)
    )


def _fmt_salary(amount):
    """Formats salary as human-readable string."""
    if amount >= 1_000_000:
        return str(round(amount / 1_000_000, 1)) + "M"
    if amount >= 1_000:
        return str(round(amount / 1_000)) + "K"
    return str(amount)


def _hire_for_blue_blood(bb_program, displaced_pool, all_programs, changes, season_year, verbose):
    """
    Blue blood cascade hiring.
    Pass 1: evaluate full displaced pool.
    Pass 2: if no match, approach best currently-employed coach with 70% accept rate.
    Returns (coach_obj, hire_type) or (None, None) if nothing found.
    """
    from programs_data import get_conference_tier

    carousel   = bb_program["carousel_state"]
    ad_profile = carousel.get("ad_hiring_profile", "opportunist")

    # Pass 1: find best coach from displaced pool
    best_displaced = None
    best_score     = -999

    for coach in displaced_pool:
        # Blue blood jobs want quality -- filter by meaningful bar
        rec  = coach.get("recruiting_attraction", 10)
        tact = coach.get("tactics", 10)
        exp  = coach.get("experience", 0)
        score = rec + tact + exp * 0.3

        # AD profile preference
        if ad_profile == "veteran_preferred" and exp < 8:
            continue
        if ad_profile == "pedigree_seeker" and _estimate_coach_prestige(coach) < 35:
            continue

        if score > best_score:
            best_score     = score
            best_displaced = coach

    if best_displaced is not None:
        displaced_pool.remove(best_displaced)
        return best_displaced, "recycled"

    # Pass 2: approach a currently-employed coach
    changing_names = {c["program_name"] for c in changes}
    already_changing = {c["program_name"] for c in changes}

    candidates = []
    for prog in all_programs:
        if prog["name"] == bb_program["name"]:    continue
        if prog["name"] in already_changing:       continue
        if prog["prestige_current"] >= BLUE_BLOOD_CASCADE_THRESHOLD: continue

        coach = prog.get("coach", {})
        rec   = coach.get("recruiting_attraction", 10)
        tact  = coach.get("tactics", 10)
        exp   = coach.get("experience", 0)
        score = rec + tact + exp * 0.3

        if ad_profile == "veteran_preferred" and exp < 8:
            continue

        candidates.append((prog, coach, score))

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[2], reverse=True)
    target_prog, target_coach, _ = candidates[0]

    if random.random() < BLUE_BLOOD_APPROACH_PROBABILITY:
        if verbose:
            print("  BB APPROACH: " + bb_program["name"] +
                  " pursues " + target_coach.get("name", "?") +
                  " from " + target_prog["name"])

        # This triggers a cascade -- target_prog now has an opening
        # Add to changes list so it gets resolved in normal market
        from program import ensure_carousel_state
        ensure_carousel_state(target_prog)

        cascade_change = {
            "program_name": target_prog["name"],
            "program":      target_prog,
            "coach_name":   target_coach.get("name", "Unknown"),
            "coach_id":     target_coach.get("coach_id", None),
            "coach_obj":    dict(target_coach),
            "reason":       "poached",
            "trigger":      "blue_blood_approach",
            "destination":  bb_program["name"],
            "prestige":     target_prog["prestige_current"],
            "is_breakout":  target_coach.get("breakout_candidate", False),
            "is_buyout":    False,
        }
        changes.append(cascade_change)

        # The target program needs a new coach -- it goes into normal market
        # For now remove the coach from the target program so _run_player_impact works
        # The target gets resolved in the next pass of normal_jobs
        # We need to add target_prog to the open jobs list -- done via changes

        return dict(target_coach), "cascade_poach"

    return None, None


def _estimate_coach_prestige(coach):
    wins  = coach.get("career_wins", 0)
    losses = coach.get("career_losses", 0)
    total = wins + losses
    if total == 0: return 20
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
    board_patience = program.get("carousel_state", {}).get("board_patience", 5)

    if ad_profile == "veteran_preferred":   experience = random.randint(10, 25)
    elif ad_profile == "analytics_forward": experience = random.randint(0, 8)
    else:                                   experience = random.randint(3, 18)

    return generate_coach(coach_name, prestige=prestige,
                          experience=experience, board_patience=board_patience)


def _install_coach(program, new_coach, season_year):
    new_coach["staff_role"]   = "head_coach"
    new_coach["free_agent_seasons"] = 0
    program["coach"]         = new_coach
    program["coach_name"]    = new_coach["name"]
    program["coach_seasons"] = 0
    program["job_security"]  = 75
    carousel = program["carousel_state"]
    carousel["last_hire_year"] = season_year
    carousel["firing_reason"]  = None


# -----------------------------------------
# STYLE FIT
# -----------------------------------------

def _apply_style_fit_all(all_programs, changes):
    changed_programs = {c["program_name"] for c in changes}
    for program in all_programs:
        if program["name"] not in changed_programs:
            continue
        new_coach = program.get("coach", {})
        for player in program.get("roster", []):
            fit = calculate_style_fit(player, new_coach)
            player["system_fit"] = fit
            if player.get("year") == "Freshman":
                player["system_fit"] = int(fit * 0.5 + 50 * 0.5)


def _decay_style_fit(all_programs, changes):
    changed_programs = {c["program_name"] for c in changes}
    for program in all_programs:
        if program["name"] in changed_programs:
            continue
        for player in program.get("roster", []):
            fit = player.get("system_fit")
            if fit is None: continue
            if fit > 70:   player["system_fit"] = max(70, fit - int((fit - 70) * STYLE_FIT_DECAY))
            elif fit < 70: player["system_fit"] = min(70, fit + int((70 - fit) * STYLE_FIT_DECAY))


def get_style_fit_morale_modifier(player):
    """Returns morale_modifier (0.70-1.15) based on system_fit."""
    fit = player.get("system_fit")
    if fit is None: return 1.0

    coachability = player.get("coachability", 10)
    year         = player.get("year", "Sophomore")

    if fit >= STYLE_FIT_GOOD:
        return min(1.15, 1.0 + (fit - STYLE_FIT_GOOD) / 100.0 * 0.30)
    elif fit >= STYLE_FIT_BAD:
        return 1.0
    else:
        raw_penalty        = (STYLE_FIT_BAD - fit) / STYLE_FIT_BAD * 0.30
        coachability_factor = 1.0 - (coachability / 20.0) * 0.60
        effective_penalty  = raw_penalty * coachability_factor
        if year == "Freshman":
            effective_penalty *= 0.5
        return max(0.70, 1.0 - effective_penalty)


def get_style_fit_portal_bump(player):
    """Returns additional portal probability for bad system fit (0-0.15)."""
    fit = player.get("system_fit")
    if fit is None or fit >= STYLE_FIT_BAD: return 0.0
    coachability        = player.get("coachability", 10)
    raw_bump            = (STYLE_FIT_BAD - fit) / STYLE_FIT_BAD * 0.15
    coachability_factor = 1.0 - (coachability / 20.0) * 0.40
    return min(0.15, raw_bump * coachability_factor)


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
        if program is None: continue

        departing_coach    = change["coach_obj"]
        departing_coach_id = change.get("coach_id")
        reason             = change["reason"]

        wave_mult      = PORTAL_WAVE_FIRING if reason == "fired" else PORTAL_WAVE_RESIGNATION
        roster         = program.get("roster", [])
        portal_entries = []

        for player in roster:
            year = player.get("year", "Freshman")
            ensure_player_carousel_attrs(player)
            prob     = _portal_wave_probability(player, departing_coach_id, wave_mult)
            fit_bump = get_style_fit_portal_bump(player)
            prob     = min(0.80, prob + fit_bump)

            if random.random() < prob:
                portal_entries.append(player)
                impact_log.append({
                    "type": "portal_wave", "program": program_name,
                    "player": player["name"], "year": year, "reason": reason,
                })

        portal_names = {p["name"] for p in portal_entries}
        program["roster"] = [p for p in roster if p["name"] not in portal_names]
        portal_additions.extend(portal_entries)

        if reason in ("resigned", "poached", "cascade_poach") and change.get("destination"):
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
    year         = player.get("year", "Freshman")
    volatility   = player.get("volatility", 5)
    coach_loyalty = player.get("coach_loyalty", 10)
    home_loyalty  = player.get("home_loyalty", 7)
    pt_hunger     = player.get("playing_time_hunger", 10)
    recruited_by  = player.get("recruited_by")

    year_base = {"Freshman": 0.18, "Sophomore": 0.14, "Junior": 0.10, "Senior": 0.05}
    base = year_base.get(year, 0.12)

    raw_prob = (base
                + (volatility    - 10) / 20.0 * 0.15
                + (coach_loyalty - 10) / 20.0 * 0.10
                + (home_loyalty  - 10) / 20.0 * (-0.08)
                + (pt_hunger     - 10) / 20.0 * 0.08
                + (0.15 if recruited_by == departing_coach_id else 0.0))
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
        if open_slots <= 0: break

        year          = player.get("year", "Freshman")
        coach_loyalty = player.get("coach_loyalty", 10)
        volatility    = player.get("volatility", 5)
        recruited_by  = player.get("recruited_by")

        base_prob = POACH_BASE_PROB
        if recruited_by == coach_id:  base_prob += POACH_RECRUITED_BY_BONUS
        if coach_loyalty >= 15:       base_prob += 0.10
        if prestige_delta < -15:      base_prob *= 0.20
        elif prestige_delta < 0:      base_prob *= 0.55
        elif prestige_delta >= 20:    base_prob *= 1.30
        if year == "Senior":
            base_prob *= 0.45
            if prestige_delta <= 0:   base_prob *= 0.20
        base_prob += (volatility - 10) / 20.0 * 0.10
        final_prob = max(0.0, min(0.70, base_prob))

        if random.random() < final_prob:
            if open_slots <= 0: break
            poached_players.append(player)
            open_slots -= 1
            events.append({
                "type": "poach", "player": player["name"], "year": year,
                "from": old_program["name"], "to": new_program["name"],
                "coach": coach.get("name", "?"), "recruited_by_match": recruited_by == coach_id,
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
    events          = []
    committed       = program.get("committed_recruits", [])
    if not committed: return events

    base_decommit   = 0.30 if reason == "fired" else 0.15
    still_committed = []

    for recruit in committed:
        prob  = base_decommit
        prob += (recruit.get("volatility", 5)        - 5) / 15.0 * 0.15
        prob += (recruit.get("prestige_ambition", 7) - 7) / 13.0 * 0.10

        if random.random() < prob:
            recruit["status"] = "available"
            events.append({
                "type": "decommit", "recruit": recruit.get("name", "?"),
                "program": program["name"], "reason": reason,
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

    fired     = [c for c in changes if c["reason"] == "fired"]
    resigned  = [c for c in changes if c["reason"] == "resigned"]
    poached   = [c for c in changes if c["reason"] in ("poached", "cascade_poach")]
    breakouts = [c for c in changes if c.get("is_breakout")]
    buyouts   = [c for c in changes if c.get("is_buyout")]

    print("")
    print("=" * 60)
    print("  " + str(year) + " COACHING CAROUSEL")
    print("=" * 60)
    print("  Total changes:   " + str(len(changes)))
    print("  Fired:           " + str(len(fired)) +
          (" (" + str(len(buyouts)) + " buyouts)" if buyouts else ""))
    print("  Resigned:        " + str(len(resigned)))
    print("  Poached:         " + str(len(poached)))
    print("  Portal additions:" + str(carousel_report["portal_additions"]))
    if breakouts:
        print("  Breakout moves:  " + str(len(breakouts)))

    if fired:
        print("")
        print("  -- FIRED --")
        for c in fired:
            buyout_str = " [BUYOUT]" if c.get("is_buyout") else ""
            print("    {:<24} {:<22} trigger: {}  prestige: {}{}".format(
                c["program_name"], c["coach_name"],
                c["trigger"], round(c["prestige"], 1), buyout_str))

    if resigned or poached:
        print("")
        print("  -- DEPARTED (resigned / poached) --")
        for c in resigned + poached:
            dest   = (" -> " + c["destination"]) if c.get("destination") else ""
            bo_flag = " [BREAKOUT]" if c.get("is_breakout") else ""
            casc    = " [CASCADE]" if c.get("trigger") == "blue_blood_approach" else ""
            print("    {:<24} {:<22} {}  prestige: {}{}{}{}".format(
                c["program_name"], c["coach_name"],
                c["reason"], round(c["prestige"], 1), dest, bo_flag, casc))

    if hires:
        print("")
        print("  -- NEW HIRES --")
        for h in hires:
            print("    {:<24} {:<22} ({}) AD: {}".format(
                h["program"], h["new_coach"], h["hire_type"], h["ad_profile"]))

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
