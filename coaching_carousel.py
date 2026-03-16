# -----------------------------------------
# COLLEGE HOOPS SIM -- Coaching Carousel v1.0
#
# Runs ONCE per season, after the prestige pipeline and NCAA tournament
# resolve, and BEFORE the transfer portal opens.
#
# PIPELINE POSITION in season.py:
#   games → prestige pipeline → conf tournaments → NCAA tournament →
#   universe gravity → throne check → [COACHING CAROUSEL] →
#   transfer portal → recruiting → lifecycle
#
# WHAT THIS MODULE DOES:
#
#   Phase 1 -- EVALUATE (all 330 programs)
#     - Check job_security against firing threshold (board_patience-adjusted)
#     - Check stale_meter for floor_conf / low_major programs
#     - Check ambition for voluntary departures to better jobs
#     - Build list of coaching changes (fired, resigned, poached)
#
#   Phase 2 -- JOB MARKET
#     - Collect all open jobs
#     - Collect all displaced coaches (fired + resigned pool)
#     - Generate fresh young coaches for jobs that don't find a match
#     - Match coaches to jobs using AD hiring profile + tiered prestige market
#
#   Phase 3 -- PLAYER IMPACT
#     - Portal wave: returning players RNG check when coach leaves
#     - Poach check: departing coach (resign/poach only) pulls former players
#     - Recruiting class decommits: uncommitted recruits re-evaluate
#
# DESIGN PRINCIPLES:
#   - Fired coaches do NOT get poach rights (they didn't leave clean)
#   - Resignations to better jobs trigger lower portal wave than firings
#   - Poach only works with recruited_by match (real relationship required)
#   - Seniors can be poached but at lower base probability
#   - AD hiring profile gates which coaches can land at which jobs
#   - Experience edge is real but subtle -- 0.97x to 1.06x multiplier
#   - coaching_capital buffers job_security -- burns before security bleeds
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

# Job security floor -- below this, firing is automatic regardless of patience
HARD_FIRING_FLOOR = 15

# Minimum job_security to trigger a voluntary departure check
# A coach at 40 security won't leave -- things aren't good enough to attract
# a better offer
VOLUNTARY_DEPARTURE_MIN_SECURITY = 45

# Prestige gap required for a coach to consider leaving voluntarily
# A coach at a 60-prestige program needs a 75+ job to seriously consider it
VOLUNTARY_DEPARTURE_PRESTIGE_GAP = 15

# How many seasons before a new coach is protected from firing
# A new hire can't be fired in their first season regardless of record
NEW_COACH_PROTECTION_SEASONS = 1

# Portal wave probability modifiers by departure type
PORTAL_WAVE_FIRING     = 1.0    # full RNG weight -- trust is broken
PORTAL_WAVE_RESIGNATION = 0.60  # lower -- coach didn't abandon them

# Poach -- base probability before attribute modifiers
POACH_BASE_PROB = 0.18

# Poach probability bonus if player was personally recruited by this coach
POACH_RECRUITED_BY_BONUS = 0.22

# AD hiring profile restrictions
# Each profile lists which coach types it will consider
# "any" means no restriction
_AD_EXPERIENCE_FLOOR = {
    "veteran_preferred":  8,    # won't touch coaches under 8 years exp
    "pedigree_seeker":    3,    # some experience required
    "analytics_forward":  0,    # will take a first-year coach
    "hometown_loyalty":   0,    # regional fit > experience
    "opportunist":        0,    # no floor
}

# Programs above this prestige won't hire coaches below this floor prestige rating
# (prestige of their previous program, estimated by career record)
_PRESTIGE_HIRE_FLOOR = {
    "power":      35,    # power conf won't hire someone with no power conf background
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

    # --- MIGRATION: ensure all programs and coaches have carousel attrs ---
    for program in all_programs:
        ensure_carousel_state(program)
        coach = program.get("coach", {})
        ensure_coach_carousel_attrs(coach)
        for player in program.get("roster", []):
            ensure_player_carousel_attrs(player, coach_id=coach.get("coach_id"))

    # --- PHASE 1: EVALUATE ---
    changes = _evaluate_all_programs(all_programs, season_year, verbose)

    if verbose:
        fired      = [c for c in changes if c["reason"] == "fired"]
        resigned   = [c for c in changes if c["reason"] == "resigned"]
        poached    = [c for c in changes if c["reason"] == "poached"]
        print("")
        print("--- " + str(season_year) + " Coaching Carousel ---")
        print("  Fired:    " + str(len(fired)))
        print("  Resigned: " + str(len(resigned)))
        print("  Poached:  " + str(len(poached)))

    # --- PHASE 2: JOB MARKET ---
    all_programs, hire_log = _run_job_market(all_programs, changes, season_year, verbose)

    # --- PHASE 3: PLAYER IMPACT ---
    all_programs, portal_additions, impact_log = _run_player_impact(
        all_programs, changes, season_year, verbose
    )

    carousel_report = {
        "season_year":     season_year,
        "changes":         changes,
        "hire_log":        hire_log,
        "portal_additions": len(portal_additions),
        "impact_log":      impact_log,
    }

    return all_programs, carousel_report, portal_additions


# -----------------------------------------
# PHASE 1: EVALUATE
# -----------------------------------------

def _evaluate_all_programs(all_programs, season_year, verbose):
    """
    Evaluates every program for coaching changes.
    Returns list of change dicts.
    """
    changes = []

    # Collect open jobs first so resignation/poaching has targets to chase
    # We build a prestige-sorted list of all programs for ambition checks
    program_by_name = {p["name"]: p for p in all_programs}

    for program in all_programs:
        coach   = program.get("coach", {})
        seasons = program.get("coach_seasons", 0)
        security = program.get("job_security", 75)
        carousel = program["carousel_state"]

        # New coach protection -- can't be fired in first season
        if seasons <= NEW_COACH_PROTECTION_SEASONS:
            continue

        # Update career wins/losses on coach
        _update_coach_career_record(program)

        # --- CHECK 1: HARD FLOOR FIRING ---
        if security <= HARD_FIRING_FLOOR:
            changes.append(_build_change(program, "fired", "job_security_floor"))
            if verbose:
                print("  FIRED (floor): " + program["name"] +
                      " -- " + coach.get("name", "?") +
                      " security=" + str(round(security, 1)))
            continue

        # --- CHECK 2: BOARD PATIENCE FIRING ---
        threshold = get_firing_threshold(program)
        if security < threshold:
            # coaching_capital absorbs some of the shortfall before firing fires
            shortfall = threshold - security
            capital   = carousel.get("coaching_capital", 0.0)
            if capital >= shortfall:
                # Capital absorbs -- don't fire, but burn capital
                carousel["coaching_capital"] = round(capital - shortfall, 2)
                if verbose:
                    print("  CAPITAL SAVES: " + program["name"] +
                          " -- " + coach.get("name", "?") +
                          " (capital " + str(round(capital, 1)) +
                          " absorbed shortfall " + str(round(shortfall, 1)) + ")")
            else:
                # Not enough capital -- fire
                changes.append(_build_change(program, "fired", "board_patience"))
                if verbose:
                    print("  FIRED (board): " + program["name"] +
                          " -- " + coach.get("name", "?") +
                          " security=" + str(round(security, 1)) +
                          " threshold=" + str(threshold))
                continue

        # --- CHECK 3: STALE METER ---
        stale = carousel.get("stale_meter", 0)
        if stale >= 100:
            changes.append(_build_change(program, "fired", "stale_meter"))
            carousel["stale_meter"] = 0
            if verbose:
                print("  FIRED (stale): " + program["name"] +
                      " -- " + coach.get("name", "?"))
            continue

        # --- CHECK 4: VOLUNTARY DEPARTURE (ambition check) ---
        ambition = coach.get("ambition", 10)
        loyalty  = coach.get("loyalty", 10)

        if (ambition >= 14 and
                security >= VOLUNTARY_DEPARTURE_MIN_SECURITY and
                seasons >= 2):

            # Find the best open job available
            best_job = _find_best_available_job(
                program, all_programs, changes, season_year
            )

            if best_job is not None:
                prestige_gap = best_job["prestige_current"] - program["prestige_current"]
                if prestige_gap >= VOLUNTARY_DEPARTURE_PRESTIGE_GAP:
                    # Loyalty check -- high loyalty resists leaving
                    loyalty_resist = loyalty / 20.0
                    leave_chance   = min(0.80, (ambition / 20.0) - loyalty_resist * 0.5)

                    if random.random() < leave_chance:
                        reason = "poached" if prestige_gap >= 25 else "resigned"
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


def _find_best_available_job(current_program, all_programs, existing_changes, season_year):
    """
    Finds the best job this coach could realistically land,
    excluding programs that already have a coaching change pending.

    Returns program dict or None.
    """
    coach = current_program.get("coach", {})

    # Programs already changing coaches can't be targets
    changing = {c["program_name"] for c in existing_changes}

    candidates = []
    for prog in all_programs:
        if prog["name"] == current_program["name"]:
            continue
        if prog["name"] in changing:
            continue
        # Must be a meaningful upgrade
        if prog["prestige_current"] <= current_program["prestige_current"]:
            continue
        candidates.append(prog)

    if not candidates:
        return None

    # Return highest prestige candidate
    return max(candidates, key=lambda p: p["prestige_current"])


def _build_change(program, reason, trigger, destination=None):
    coach = program.get("coach", {})
    return {
        "program_name":    program["name"],
        "program":         program,
        "coach_name":      coach.get("name", "Unknown"),
        "coach_id":        coach.get("coach_id", None),
        "coach_obj":       dict(coach),   # snapshot of departing coach
        "reason":          reason,         # "fired", "resigned", "poached"
        "trigger":         trigger,        # "job_security_floor", "board_patience", etc.
        "destination":     destination,    # program name if resigned/poached
        "prestige":        program["prestige_current"],
    }


def _update_coach_career_record(program):
    """Stamps current season wins/losses onto coach career totals."""
    coach = program.get("coach", {})
    coach["career_wins"]   = coach.get("career_wins", 0) + program.get("wins", 0)
    coach["career_losses"] = coach.get("career_losses", 0) + program.get("losses", 0)
    coach["experience"]    = coach.get("experience", 0) + 1


# -----------------------------------------
# PHASE 2: JOB MARKET
# -----------------------------------------

def _run_job_market(all_programs, changes, season_year, verbose):
    """
    Matches displaced coaches to open jobs.
    Open jobs are filled in prestige order (best job gets first pick).

    Returns all_programs (modified), hire_log.
    """
    from programs_data import get_conference_tier

    if not changes:
        return all_programs, []

    hire_log = []

    # Build displaced coach pool (fired + resigned -- all available)
    displaced_pool = [c["coach_obj"] for c in changes]

    # Jobs ranked by prestige (best jobs pick first)
    open_jobs = sorted(
        [c["program"] for c in changes],
        key=lambda p: p["prestige_current"],
        reverse=True
    )

    program_by_name = {p["name"]: p for p in all_programs}

    for program in open_jobs:
        carousel       = program["carousel_state"]
        ad_profile     = carousel.get("ad_hiring_profile", "opportunist")
        conf_tier      = get_conference_tier(program["conference"])["tier"]
        prestige_floor = _PRESTIGE_HIRE_FLOOR.get(conf_tier, 1)
        exp_floor      = _AD_EXPERIENCE_FLOOR.get(ad_profile, 0)

        # Filter displaced pool for eligible candidates
        eligible = [
            c for c in displaced_pool
            if c.get("experience", 0) >= exp_floor
        ]

        # AD pedigree seeker: wants coaches from programs with prestige >= floor
        if ad_profile == "pedigree_seeker":
            eligible = [
                c for c in eligible
                if _estimate_coach_prestige(c) >= prestige_floor
            ]

        # AD hometown loyalty: prefers same region as program
        if ad_profile == "hometown_loyalty":
            program_region = _get_program_region(program)
            regional = [c for c in eligible
                        if c.get("home_region", "") == program_region]
            if regional:
                eligible = regional   # prioritize regional fit

        # AD veteran preferred: filter by experience floor (already applied above)
        # but also sort by experience descending
        if ad_profile == "veteran_preferred":
            eligible.sort(key=lambda c: c.get("experience", 0), reverse=True)

        # AD analytics forward: sort by scheme_adaptability + in_game_adaptability
        elif ad_profile == "analytics_forward":
            eligible.sort(
                key=lambda c: c.get("scheme_adaptability", 10) + c.get("in_game_adaptability", 10),
                reverse=True
            )

        new_coach = None

        if eligible:
            # Quality check -- don't place a highly ambitious coach at a floor job
            # unless they have no other options
            for candidate in eligible[:5]:   # check top 5
                ambition = candidate.get("ambition", 10)
                job_prestige = program["prestige_current"]
                if ambition >= 16 and job_prestige < 30:
                    continue   # high ambition coach skips floor job if they can
                new_coach = candidate
                displaced_pool.remove(candidate)
                break

        if new_coach is None:
            # No displaced coach fits -- generate a fresh coach
            new_coach = _generate_new_hire(program, ad_profile, season_year)
            hire_type = "fresh"
        else:
            hire_type = "recycled"

        # Install the new coach
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
            print("  HIRED (" + hire_type + "): " + program["name"] +
                  " -- " + new_coach["name"] +
                  " [" + new_coach["archetype"] + "]" +
                  " (exp=" + str(new_coach.get("experience", 0)) + ")")

    return all_programs, hire_log


def _estimate_coach_prestige(coach):
    """
    Rough prestige estimate for a coach based on career record.
    Used by pedigree_seeker ADs to filter candidates.
    """
    wins   = coach.get("career_wins", 0)
    losses = coach.get("career_losses", 0)
    total  = wins + losses
    if total == 0:
        return 20
    win_pct = wins / total
    exp     = coach.get("experience", 0)
    # Rough proxy: experienced winning coaches come from good programs
    return min(95, int(win_pct * 60 + min(exp, 20) * 1.5))


def _get_program_region(program):
    """Returns the region of a program based on its conference."""
    conf = program.get("conference", "")
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
    return _CONF_REGIONS.get(conf, "midwest")


def _generate_new_hire(program, ad_profile, season_year):
    """
    Generates a fresh coach tailored to the job opening.
    analytics_forward ADs get younger coaches.
    veteran_preferred ADs get experienced coaches.
    """
    prestige   = program["prestige_current"]
    coach_name = generate_coach_name()

    if ad_profile == "veteran_preferred":
        experience = random.randint(10, 25)
    elif ad_profile == "analytics_forward":
        experience = random.randint(0, 8)
    else:
        experience = random.randint(3, 18)

    return generate_coach(
        coach_name,
        prestige=prestige,
        experience=experience,
    )


def _install_coach(program, new_coach, season_year):
    """
    Installs a new coach at a program.
    Resets coach_seasons, sets carousel hire year.
    job_security resets to 75 for a new hire.
    """
    # Stamp recruited_by migration on existing players
    # New coach doesn't have a relationship with inherited roster yet
    # recruited_by stays as-is on existing players -- only new recruits get stamped

    program["coach"]      = new_coach
    program["coach_name"] = new_coach["name"]
    program["coach_seasons"] = 0
    program["job_security"]  = 75

    carousel = program["carousel_state"]
    carousel["last_hire_year"] = season_year
    carousel["firing_reason"]  = None


# -----------------------------------------
# PHASE 3: PLAYER IMPACT
# -----------------------------------------

def _run_player_impact(all_programs, changes, season_year, verbose):
    """
    Handles portal wave, poach checks, and recruit decommits
    triggered by coaching changes.

    Returns:
      all_programs   -- modified
      portal_additions -- list of player dicts that should enter the portal
      impact_log     -- list of event dicts for reporting
    """
    if not changes:
        return all_programs, [], []

    portal_additions = []
    impact_log       = []

    program_by_name = {p["name"]: p for p in all_programs}

    for change in changes:
        program_name  = change["program_name"]
        program       = program_by_name.get(program_name)
        if program is None:
            continue

        departing_coach    = change["coach_obj"]
        departing_coach_id = change.get("coach_id")
        reason             = change["reason"]   # fired / resigned / poached

        # Multiplier on portal probability based on how coach left
        wave_mult = PORTAL_WAVE_FIRING if reason == "fired" else PORTAL_WAVE_RESIGNATION

        # --- PORTAL WAVE: returning players re-evaluate ---
        roster = program.get("roster", [])
        portal_entries = []

        for player in roster:
            # Seniors almost never leave -- not worth uprooting for one year
            # But they can be poached (handled separately below)
            year = player.get("year", "Freshman")

            ensure_player_carousel_attrs(player)

            prob = _portal_wave_probability(player, departing_coach_id, wave_mult)

            if random.random() < prob:
                portal_entries.append(player)
                impact_log.append({
                    "type":         "portal_wave",
                    "program":      program_name,
                    "player":       player["name"],
                    "year":         year,
                    "reason":       reason,
                })

        # Remove portal wave players from roster
        portal_names = {p["name"] for p in portal_entries}
        program["roster"] = [p for p in roster if p["name"] not in portal_names]
        portal_additions.extend(portal_entries)

        # --- POACH CHECK: resigned/poached coaches pull former players ---
        # Fired coaches lose this right -- they didn't leave clean
        if reason in ("resigned", "poached") and change.get("destination"):
            destination_prog = program_by_name.get(change["destination"])
            if destination_prog is not None:
                poached_players, poach_events = _run_poach_check(
                    program, destination_prog, departing_coach,
                    departing_coach_id, season_year, verbose
                )
                portal_additions.extend(poached_players)
                impact_log.extend(poach_events)

        # --- RECRUIT DECOMMIT CHECK ---
        decommit_events = _run_recruit_decommits(program, departing_coach, reason)
        impact_log.extend(decommit_events)

    if verbose and portal_additions:
        print("  Portal wave + poach: " + str(len(portal_additions)) +
              " players added to portal by coaching changes")

    return all_programs, portal_additions, impact_log


def _portal_wave_probability(player, departing_coach_id, wave_mult):
    """
    Calculates the probability a player enters the portal after a coaching change.

    Inputs:
      volatility         -- high = more likely to leave
      coach_loyalty      -- high = follows coach, not school (more likely to leave)
      home_loyalty       -- high = stays near home (less likely to leave)
      playing_time_hunger -- high = if they were buried, more likely to bolt
      year               -- seniors have lower base, freshmen have higher
      recruited_by match -- if this coach recruited them, anchor is gone
    """
    year          = player.get("year", "Freshman")
    volatility    = player.get("volatility", 5)
    coach_loyalty = player.get("coach_loyalty", 10)
    home_loyalty  = player.get("home_loyalty", 7)
    pt_hunger     = player.get("playing_time_hunger", 10)
    recruited_by  = player.get("recruited_by")

    # Base probability by year
    year_base = {
        "Freshman":  0.18,
        "Sophomore": 0.14,
        "Junior":    0.10,
        "Senior":    0.05,   # seniors exist -- just lower
    }
    base = year_base.get(year, 0.12)

    # Attribute modifiers
    vol_mod         = (volatility    - 10) / 20.0 * 0.15    # -0.075 to +0.075
    loyalty_mod     = (coach_loyalty - 10) / 20.0 * 0.10    # high loyalty = want to follow = higher leave chance
    home_mod        = (home_loyalty  - 10) / 20.0 * (-0.08) # high home loyalty = stay put
    pt_mod          = (pt_hunger     - 10) / 20.0 * 0.08

    # recruited_by bonus -- losing your recruiting coach is the biggest trigger
    recruited_bonus = 0.15 if recruited_by == departing_coach_id else 0.0

    raw_prob = base + vol_mod + loyalty_mod + home_mod + pt_mod + recruited_bonus
    raw_prob = max(0.01, min(0.65, raw_prob)) * wave_mult

    return min(0.75, raw_prob)


def _run_poach_check(old_program, new_program, coach, coach_id, season_year, verbose):
    """
    Checks if the departing coach can pull former players to their new school.

    Rules:
      - Only works with recruited_by match (full strength) or coach_loyalty >= 15
      - New program must have scholarship slots
      - New program can't be a downgrade in prestige
      - Players already in portal wave skip this (they're already leaving)
    """
    poached_players = []
    events          = []

    roster = old_program.get("roster", [])

    # How many scholarship slots does the new program have?
    new_roster_size = len(new_program.get("roster", []))
    max_scholarships = 13
    open_slots = max(0, max_scholarships - new_roster_size)

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
        home_loyalty  = player.get("home_loyalty", 7)

        # Poach base probability
        base_prob = POACH_BASE_PROB

        # Strong recruited_by bonus
        if recruited_by == coach_id:
            base_prob += POACH_RECRUITED_BY_BONUS

        # High coach_loyalty players are moveable even without recruited_by
        if coach_loyalty >= 15:
            base_prob += 0.10

        # Prestige delta -- coaches moving DOWN have more pull over players
        # Players won't follow a coach to a significant downgrade
        if prestige_delta < -15:
            base_prob *= 0.20   # very unlikely to follow coach down hard
        elif prestige_delta < 0:
            base_prob *= 0.55   # mild downgrade -- possible but not likely
        elif prestige_delta >= 20:
            base_prob *= 1.30   # significant upgrade -- players want to come

        # Seniors: lower base but possible if opportunity is meaningful
        if year == "Senior":
            base_prob *= 0.45
            # Seniors need an actual upgrade
            if prestige_delta <= 0:
                base_prob *= 0.20

        # Volatility adds noise
        vol_bonus = (volatility - 10) / 20.0 * 0.10
        base_prob += vol_bonus

        final_prob = max(0.0, min(0.70, base_prob))

        if random.random() < final_prob:
            # Check new program actually has a slot
            if open_slots <= 0:
                break

            poached_players.append(player)
            open_slots -= 1

            events.append({
                "type":        "poach",
                "player":      player["name"],
                "year":        year,
                "from":        old_program["name"],
                "to":          new_program["name"],
                "coach":       coach.get("name", "?"),
                "recruited_by_match": recruited_by == coach_id,
            })

            if verbose:
                match_str = " [recruited_by match]" if recruited_by == coach_id else ""
                print("  POACH: " + player["name"] + " (" + year + ")" +
                      " follows " + coach.get("name", "?") +
                      " from " + old_program["name"] +
                      " to " + new_program["name"] + match_str)

    # Remove poached players from old roster
    if poached_players:
        poach_names = {p["name"] for p in poached_players}
        old_program["roster"] = [
            p for p in old_program.get("roster", [])
            if p["name"] not in poach_names
        ]
        # Add poached players to new program's roster
        new_program["roster"].extend(poached_players)

    return poached_players, events


def _run_recruit_decommits(program, departing_coach, reason):
    """
    Checks if uncommitted recruits decommit after a coaching change.
    Committed recruits (on committed_recruits list) re-evaluate.
    """
    events    = []
    committed = program.get("committed_recruits", [])
    if not committed:
        return events

    # fired = more uncertainty = higher decommit rate
    base_decommit = 0.30 if reason == "fired" else 0.15

    still_committed = []
    for recruit in committed:
        volatility = recruit.get("volatility", 5)
        ambition   = recruit.get("prestige_ambition", 7)

        prob = base_decommit
        prob += (volatility  - 5) / 15.0 * 0.15
        prob += (ambition    - 7) / 13.0 * 0.10

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

    # Poach events from impact log
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
