# scheduler.py
# College Hoops Sim -- Non-Conference Scheduler v1.0
#
# Fills a SeasonCalendar with scheduled games.
# Handles:
#   - Conference schedule generation (all formats)
#   - Non-conference slot calculation
#   - Marquee destination events (resort sites)
#   - 4-team mini tournaments
#   - Standalone neutral site games (power/high-major only)
#   - Home-and-home series with prestige gap logic
#   - Geographic radius opponent selection
#   - Cross-season scheduling obligations
#
# PRESTIGE GAP RULES (non-conference home/away):
#   gap 0-12:   1-for-1 (home and away, return game next available year)
#   gap 13-25:  2-for-1 (higher prestige hosts 2, visits 1)
#   gap 26+:    3-for-1 (higher prestige hosts 3, visits 1)
#   gap 40+:    home only (lower prestige NEVER travels to power campus)
#
# ROAD GAME HARD RULES:
#   Power programs never travel to floor_conf campuses.
#   High major programs never travel to floor_conf campuses.
#   No program travels more than 2 true road games in non-conference.
#   Bottom tier (floor_conf) plays 80%+ home games in non-conference.

import random
from datetime import date, timedelta
from calendar import SeasonCalendar, get_conference_format
from schools_database import haversine
from programs_data import get_conference_tier

# -----------------------------------------
# GEOGRAPHIC RADIUS BY PRESTIGE TIER
# How far a program typically looks for
# non-conference opponents.
# Miles. Soft preference, not hard limit.
# -----------------------------------------

SCHEDULING_RADIUS = {
    "blue_blood":    2500,  # national -- anywhere
    "elite":         2000,
    "strong":        1500,
    "average":       1000,
    "below_average":  600,
    "poor":           400,  # mostly regional/local
}

# Probability of scheduling outside radius
# (the Cal State Fullerton exception)
OUT_OF_RADIUS_PROB = {
    "blue_blood":    0.30,
    "elite":         0.20,
    "strong":        0.15,
    "average":       0.08,
    "below_average": 0.04,
    "poor":          0.02,
}

# -----------------------------------------
# PRESTIGE GAP -- SERIES FORMAT
# -----------------------------------------

def get_series_format(prestige_a, prestige_b):
    """
    Returns series format based on prestige gap.
    higher_host = number of games at higher prestige team's campus
    lower_host  = number of games at lower prestige team's campus
    Returns (higher_host, lower_host, gap_category)
    """
    gap = abs(prestige_a - prestige_b)
    if gap <= 12:
        return (1, 1, "even")
    elif gap <= 25:
        return (2, 1, "moderate")
    elif gap <= 39:
        return (3, 1, "lopsided")
    else:
        return (1, 0, "mismatch")   # home only, no road trip


def _get_prestige_tier(prestige):
    """Map prestige value to tier label for radius lookup."""
    if prestige >= 95:
        return "blue_blood"
    elif prestige >= 79:
        return "elite"
    elif prestige >= 59:
        return "strong"
    elif prestige >= 39:
        return "average"
    elif prestige >= 21:
        return "below_average"
    else:
        return "poor"


# -----------------------------------------
# ROAD GAME ELIGIBILITY
# Hard rules on who can travel where.
# -----------------------------------------

def can_travel_to(traveler, host):
    """
    Returns True if traveler can play a road game at host's campus.
    Enforces the prestige-based road game rules.
    """
    traveler_tier = get_conference_tier(traveler["conference"])["tier"]
    host_tier     = get_conference_tier(host["conference"])["tier"]

    # Power and high_major never travel to floor_conf
    if host_tier == "floor_conf":
        if traveler_tier in ("power", "high_major"):
            return False

    # Large prestige gap -- don't make high prestige team travel to low
    prestige_gap = traveler.get("prestige_current", 50) - host.get("prestige_current", 50)
    if prestige_gap >= 40:
        return False   # traveler is way better -- they don't go there

    return True


# -----------------------------------------
# CONFERENCE SCHEDULE BUILDER
# Generates all conference matchups and
# places them on the calendar.
# -----------------------------------------

def build_conference_schedule(calendar, conference_name, teams, rng=None):
    """
    Build the full conference schedule for a conference.
    Places games on the calendar with real dates.
    Game count is calculated dynamically from actual team count,
    not the hardcoded CONFERENCE_FORMATS target -- conferences in
    the sim may have different sizes than real life.

    Returns list of (home, away) tuples that were scheduled.
    """
    if rng is None:
        rng = random.Random()

    n         = len(teams)
    fmt_data  = get_conference_format(conference_name)
    fmt       = fmt_data["format"]
    divisions = fmt_data.get("divisions")

    # Calculate actual game count from real conference size
    # double_rr: (n-1)*2, single_rr: n-1, divisions scale correctly
    # For partial/large conferences: cap at reasonable max
    if fmt == "double_rr":
        actual_conf_games = (n - 1) * 2
    elif fmt == "single_rr":
        actual_conf_games = n - 1
    elif fmt == "divisions_2x1":
        div_size = n // 2
        actual_conf_games = (div_size - 1) * 2 + div_size
    elif fmt in ("divisions_1x_plus_rival", "partial"):
        # Scale with size -- everyone once + rotating return games
        # Target: ~n+2 for smaller conferences, capped at 20
        base = n - 1
        extra = min(4, max(2, n // 4))
        actual_conf_games = min(20, base + extra)
    else:
        actual_conf_games = (n - 1) * 2

    # Validate divisions -- if member lists don't match actual teams,
    # fall back to no-divisions to avoid zero-game placement failures
    if divisions:
        team_names = {t["name"] for t in teams}
        div_members = {m for members in divisions.values() for m in members}
        overlap = len(team_names & div_members)
        if overlap < len(teams) * 0.5:
            # Less than half the teams match division lists -- divisions are stale
            divisions = None
            # Recalculate without divisions
            if fmt == "divisions_2x1":
                fmt = "double_rr"
                actual_conf_games = (n - 1) * 2

    # Override fmt_data conf_games with actual calculated value
    fmt_data = dict(fmt_data)
    fmt_data["conf_games"] = actual_conf_games

    # Generate raw matchup list -- pass actual_conf_games directly
    # so partial/large conference formats hit the right target
    matchups = _generate_conf_matchups(teams, fmt, divisions,
                                        fmt_data.get("protected_rivals", {}),
                                        rng,
                                        target_games=actual_conf_games)

    # Shuffle matchups before placement -- reduces scheduling conflicts
    # that arise from teams in the same conference all competing for
    # the same early-season dates.
    rng.shuffle(matchups)

    # Get available conference dates starting at the right date for this conference
    conf_start = calendar.get_conference_start(fmt_data.get("conf_games", 18))
    all_conf_dates = calendar.get_conference_dates()
    conf_dates = [d for d in all_conf_dates if d >= conf_start]
    if not conf_dates:
        return []

    scheduled = []

    for home, away in matchups:
        # Strict 2 games per week limit -- real D1 rule
        placed = False
        for d in conf_dates:
            if calendar.both_can_play(home["name"], away["name"], d,
                                      max_per_week=2):
                calendar.add_conference_game(d, home, away)
                scheduled.append((home, away))
                placed = True
                break

        if not placed:
            # Overflow -- scan full conference window
            for d in all_conf_dates:
                if calendar.both_can_play(home["name"], away["name"], d,
                                          max_per_week=2):
                    calendar.add_conference_game(d, home, away)
                    scheduled.append((home, away))
                    break

    return scheduled


def _generate_conf_matchups(teams, fmt, divisions, protected_rivals, rng,
                             target_games=None):
    """
    Generate list of (home, away) matchup pairs for a conference.
    Handles all scheduling formats.
    target_games: the actual per-team game count to hit (overrides format lookup).
    """
    matchups = []
    team_map = {t["name"]: t for t in teams}
    n        = len(teams)

    if fmt == "double_rr":
        pairs = _all_pairs(teams)
        for a, b in pairs:
            # Each pair plays twice -- randomize which is home first
            if rng.random() < 0.5:
                matchups.append((a, b))
                matchups.append((b, a))
            else:
                matchups.append((b, a))
                matchups.append((a, b))

    elif fmt == "single_rr":
        pairs = _all_pairs(teams)
        for a, b in pairs:
            if rng.random() < 0.5:
                matchups.append((a, b))
            else:
                matchups.append((b, a))

    elif fmt == "divisions_2x1":
        if not divisions:
            # Fall back to double round robin
            return _generate_conf_matchups(teams, "double_rr", None,
                                            protected_rivals, rng,
                                            target_games=target_games)
        div_names   = list(divisions.keys())
        div_a_names = set(divisions[div_names[0]])
        div_b_names = set(divisions[div_names[1]])
        div_a = [t for t in teams if t["name"] in div_a_names]
        div_b = [t for t in teams if t["name"] in div_b_names]

        # Assign any unmatched teams to the smaller division
        assigned = {t["name"] for t in div_a + div_b}
        unassigned = [t for t in teams if t["name"] not in assigned]
        for t in unassigned:
            if len(div_a) <= len(div_b):
                div_a.append(t)
            else:
                div_b.append(t)

        # If either division is empty, fall back to double round robin
        if not div_a or not div_b:
            return _generate_conf_matchups(teams, "double_rr", None,
                                            protected_rivals, rng,
                                            target_games=target_games)

        # Within division: double round robin
        for team_list in [div_a, div_b]:
            pairs = _all_pairs(team_list)
            for a, b in pairs:
                if rng.random() < 0.5:
                    matchups.append((a, b))
                    matchups.append((b, a))
                else:
                    matchups.append((b, a))
                    matchups.append((a, b))

        # Cross division: single round robin
        for a in div_a:
            for b in div_b:
                if rng.random() < 0.5:
                    matchups.append((a, b))
                else:
                    matchups.append((b, a))

    elif fmt in ("divisions_1x_plus_rival", "partial"):
        # Step 1: everyone plays everyone once (single round robin)
        pairs = _all_pairs(teams)
        for a, b in pairs:
            if rng.random() < 0.5:
                matchups.append((a, b))
            else:
                matchups.append((b, a))

        # Step 2: count current games per team
        game_counts = {t["name"]: 0 for t in teams}
        for h, a in matchups:
            game_counts[h["name"]] += 1
            game_counts[a["name"]] += 1

        # Step 3: determine target -- use passed-in value if available,
        # otherwise derive from format type.
        if target_games is not None:
            game_target = target_games
        elif fmt == "divisions_1x_plus_rival":
            game_target = len(teams) + 2
        else:
            # partial -- derive from actual conference size
            game_target = min(20, (len(teams) - 1) + max(2, len(teams) // 4))

        # Add protected rivals first
        for team_name, rival_name in protected_rivals.items():
            team  = team_map.get(team_name)
            rival = team_map.get(rival_name)
            if not team or not rival:
                continue
            # Find existing first meeting and flip home/away
            first = next(
                (m for m in matchups
                 if {m[0]["name"], m[1]["name"]} == {team_name, rival_name}),
                None
            )
            if first:
                matchups.append((first[1], first[0]))
                game_counts[team_name] += 1
                game_counts[rival_name] += 1

        # Add return games until every team hits the target
        # Prioritize pairs where BOTH teams still need games
        max_passes = game_target * len(teams)
        passes = 0
        all_pairs_list = _all_pairs(teams)

        while passes < max_passes:
            passes += 1
            # Find teams still below target
            needy = [t for t in teams if game_counts[t["name"]] < game_target]
            if not needy:
                break

            # Find a pair where both are below target
            rng.shuffle(all_pairs_list)
            placed = False
            for a, b in all_pairs_list:
                if (game_counts[a["name"]] < game_target and
                        game_counts[b["name"]] < game_target):
                    # Find existing first meeting and add return game
                    first = next(
                        (m for m in matchups
                         if {m[0]["name"], m[1]["name"]} == {a["name"], b["name"]}),
                        None
                    )
                    if first:
                        matchups.append((first[1], first[0]))
                    else:
                        if rng.random() < 0.5:
                            matchups.append((a, b))
                        else:
                            matchups.append((b, a))
                    game_counts[a["name"]] += 1
                    game_counts[b["name"]] += 1
                    placed = True
                    break

            if not placed:
                # One team needs a game but no mutual-need partner exists
                # Pair them with the team furthest below target
                for needy_team in needy:
                    partners = sorted(
                        [t for t in teams if t["name"] != needy_team["name"]
                         and game_counts[t["name"]] < game_target + 1],
                        key=lambda t: game_counts[t["name"]]
                    )
                    if partners:
                        partner = partners[0]
                        first = next(
                            (m for m in matchups
                             if {m[0]["name"], m[1]["name"]} ==
                             {needy_team["name"], partner["name"]}),
                            None
                        )
                        if first:
                            matchups.append((first[1], first[0]))
                        else:
                            matchups.append((needy_team, partner))
                        game_counts[needy_team["name"]] += 1
                        game_counts[partner["name"]] += 1
                        break
                else:
                    break

    return matchups


def _all_pairs(teams):
    """Return all unique pairs from a list of teams."""
    pairs = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            pairs.append((teams[i], teams[j]))
    return pairs


# -----------------------------------------
# NON-CONFERENCE SLOT CALCULATOR
# How many non-con games each team plays.
# -----------------------------------------

def get_noncon_slots(conference_name, conf_games_played):
    """
    Returns the number of non-conference slots for a team.
    Standard D1 season is 31 games total.
    Low major and floor_conf: 30 game season.
    32 never happens.
    conf_games_played should be ACTUAL games placed, not an estimate.
    """
    from programs_data import get_conference_tier
    tier = get_conference_tier(conference_name)["tier"]

    if tier in ("low_major", "floor_conf"):
        target_total = 30
    else:
        target_total = 31

    slots = max(0, target_total - conf_games_played)
    return max(8, min(14, slots))


# -----------------------------------------
# SCHEDULING AGGRESSION PROFILES
# Drives non-conference decisions per team.
# -----------------------------------------

def get_scheduling_profile(program):
    """
    Returns a scheduling profile dict based on coach's scheduling_aggression
    and program's conference tier.

    Fields:
      max_road_games     -- max true road non-con games allowed
      min_quality_games  -- min games vs prestige 50+ opponents
      signature_games    -- how many marquee/quality home games to seek
      neutral_appetite   -- True if program seeks neutral site games
      paycheck_road      -- True if program primarily takes road paycheck games
    """
    aggression = program.get("scheduling_aggression", 5)
    conf_tier  = get_conference_tier(program["conference"])["tier"]
    prestige   = program.get("prestige_current", 30)

    # Floor conf and low major reality check -- override aggression
    if conf_tier == "floor_conf":
        return {
            "max_road_games":    10,  # paycheck road teams -- almost all road
            "min_quality_games": 0,
            "signature_games":   0,
            "neutral_appetite":  False,
            "paycheck_road":     True,
            "home_games_target": random.randint(0, 2),
        }

    if conf_tier == "low_major":
        # Road games scale with aggression
        # Even low aggression low_major teams take several road paycheck games
        if aggression >= 7:
            max_road = 6
        elif aggression >= 4:
            max_road = 4
        else:
            max_road = 2
        return {
            "max_road_games":    max_road,
            "min_quality_games": 0,
            "signature_games":   1,
            "neutral_appetite":  False,
            "paycheck_road":     aggression <= 2,
            "home_games_target": random.randint(3, 7),
        }

    # Power and high major -- aggression drives road limits
    if aggression >= 9:
        max_road = 3
    elif aggression >= 7:
        max_road = 2
    elif aggression >= 5:
        max_road = 1
    else:
        max_road = 0  # no true road games for low aggression power programs

    if aggression >= 9:
        return {
            "max_road_games":    max_road,
            "min_quality_games": 4,
            "signature_games":   3,
            "neutral_appetite":  True,
            "paycheck_road":     False,
            "home_games_target": None,
        }
    elif aggression >= 7:
        return {
            "max_road_games":    max_road,
            "min_quality_games": 2,
            "signature_games":   2,
            "neutral_appetite":  True,
            "paycheck_road":     False,
            "home_games_target": None,
        }
    elif aggression >= 5:
        return {
            "max_road_games":    max_road,
            "min_quality_games": 1,
            "signature_games":   1,
            "neutral_appetite":  prestige >= 55,
            "paycheck_road":     False,
            "home_games_target": None,
        }
    elif aggression >= 3:
        return {
            "max_road_games":    max_road,
            "min_quality_games": 1,
            "signature_games":   1,
            "neutral_appetite":  False,
            "paycheck_road":     False,
            "home_games_target": None,
        }
    else:
        return {
            "max_road_games":    max_road,
            "min_quality_games": 1,
            "signature_games":   1,
            "neutral_appetite":  False,
            "paycheck_road":     False,
            "home_games_target": None,
        }

def build_opponent_pool(team, all_teams, exclude_conferences=None,
                         exclude_names=None, rng=None):
    """
    Build a ranked list of potential non-conference opponents for a team.
    Weighted by geographic proximity with prestige-based radius.
    Excludes conference mates and already-scheduled opponents.

    Returns list of program dicts, closest/most compatible first.
    """
    if rng is None:
        rng = random.Random()

    exclude_conferences = exclude_conferences or set()
    exclude_names       = exclude_names or set()

    team_lat  = team.get("latitude", 39.5)
    team_lon  = team.get("longitude", -98.0)
    prestige  = team.get("prestige_current", 30)
    tier      = _get_prestige_tier(prestige)
    radius    = SCHEDULING_RADIUS[tier]
    out_prob  = OUT_OF_RADIUS_PROB[tier]

    candidates = []
    for other in all_teams:
        if other["name"] == team["name"]:
            continue
        if other["conference"] == team["conference"]:
            continue
        if other["conference"] in exclude_conferences:
            continue
        if other["name"] in exclude_names:
            continue

        other_lat = other.get("latitude", 39.5)
        other_lon = other.get("longitude", -98.0)
        dist      = haversine(team_lat, team_lon, other_lat, other_lon)

        in_radius = dist <= radius
        if not in_radius:
            # Small chance of scheduling outside radius
            if rng.random() > out_prob:
                continue

        # Weight: closer = higher weight, with some randomness
        weight = max(0.1, 1.0 - (dist / 3000.0)) + rng.uniform(0, 0.3)
        candidates.append((weight, dist, other))

    # Sort by weight descending
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [c[2] for c in candidates]


# -----------------------------------------
# SCHEDULING OBLIGATIONS
# Tracks multi-year series commitments.
# Persists on program dicts as
# program["scheduling_obligations"] list.
# -----------------------------------------

def get_obligations(program):
    """Return the scheduling obligations list for a program."""
    if "scheduling_obligations" not in program:
        program["scheduling_obligations"] = []
    return program["scheduling_obligations"]


def add_obligation(program, opponent_name, games_at_home, games_away,
                   start_year, series_id):
    """
    Add a scheduling obligation to a program.
    games_at_home: how many home games remain in this series
    games_away:    how many away games remain
    """
    obs = get_obligations(program)
    obs.append({
        "opponent":     opponent_name,
        "games_at_home": games_at_home,
        "games_away":    games_away,
        "start_year":    start_year,
        "series_id":     series_id,
    })


def fulfill_obligation(program, series_id, is_home):
    """
    Mark one game of an obligation as fulfilled.
    Returns True if the entire obligation is now complete.
    """
    obs = get_obligations(program)
    for ob in obs:
        if ob["series_id"] == series_id:
            if is_home:
                ob["games_at_home"] = max(0, ob["games_at_home"] - 1)
            else:
                ob["games_away"] = max(0, ob["games_away"] - 1)
            if ob["games_at_home"] == 0 and ob["games_away"] == 0:
                obs.remove(ob)
                return True
            return False
    return False


def get_due_obligations(program, year):
    """
    Return obligations that are due this year.
    An obligation is due if it was created before this year.
    """
    obs = get_obligations(program)
    return [ob for ob in obs if ob["start_year"] <= year]


def _get_team_game_dates(calendar, team_name):
    """Return sorted list of all scheduled game dates for a team."""
    schedule = calendar.get_team_schedule(team_name)
    return sorted(s.date for s in schedule)


def _has_min_rest(calendar, team_name, proposed_date, min_days=2):
    """
    Returns True if the team has at least min_days rest before
    and after proposed_date based on their current schedule.
    """
    game_dates = _get_team_game_dates(calendar, team_name)
    for d in game_dates:
        gap = abs((proposed_date - d).days)
        if gap < min_days:
            return False
    return True


def _get_tournament_dates(calendar, team_name):
    """
    Return the date range (first_date, last_date) of any tournament
    block a team is in. Returns None if team has no tournament games.
    """
    tourney_slots = [s for s in calendar.get_team_schedule(team_name)
                     if s.event_name is not None]
    if not tourney_slots:
        return None
    dates = sorted(s.date for s in tourney_slots)
    return (dates[0], dates[-1])


def _has_tournament_buffer(calendar, team_name, proposed_date, buffer_days=2):
    """
    Returns True if proposed_date respects the 2-day buffer around
    any tournament block the team is already committed to.
    """
    tourney_range = _get_tournament_dates(calendar, team_name)
    if not tourney_range:
        return True
    t_start, t_end = tourney_range
    # Must be buffer_days before the tournament starts or after it ends
    before_gap = (t_start - proposed_date).days
    after_gap  = (proposed_date - t_end).days
    if 0 < before_gap < buffer_days:
        return False
    if 0 < after_gap < buffer_days:
        return False
    return True


def make_series_id(team_a_name, team_b_name, year):
    """Generate a unique series ID for a home-and-home."""
    a = team_a_name.replace(" ", "")[:6].upper()
    b = team_b_name.replace(" ", "")[:6].upper()
    return f"{a}_{b}_{year}"


# -----------------------------------------
# MAIN NON-CONFERENCE SCHEDULER
# Entry point for non-con scheduling.
# -----------------------------------------

def schedule_noncon(calendar, all_programs, year, rng=None):
    """
    Schedule all non-conference games for the season.

    Pass 1: Place marquee resort events
    Pass 2: Place 4-team mini tournaments
    Pass 3: Fulfill existing scheduling obligations
    Pass 4: Schedule remaining slots with geographic logic
    Pass 5: Fill remaining home slots with cupcakes

    Modifies calendar in place. Returns obligation updates
    (new obligations created this year) as a list.
    """
    if rng is None:
        rng = random.Random()

    prog_map      = {p["name"]: p for p in all_programs}
    new_obligations = []

    # Track how many non-con games each team has scheduled
    noncon_count  = {p["name"]: 0 for p in all_programs}
    road_count    = {p["name"]: 0 for p in all_programs}  # true road games

    # --- PASS 1: MARQUEE RESORT EVENTS ---
    marquee_participants = _schedule_marquee_events(
        calendar, all_programs, year, noncon_count, rng
    )

    # --- PASS 2: 4-TEAM MINI TOURNAMENTS ---
    mini_participants = _schedule_mini_tournaments(
        calendar, all_programs, year, noncon_count,
        exclude=marquee_participants, rng=rng
    )

    # --- PASS 3: FULFILL EXISTING OBLIGATIONS ---
    _fulfill_obligations(
        calendar, all_programs, year, noncon_count, road_count,
        new_obligations, rng
    )

    # --- PASS 4: SCHEDULE REMAINING SLOTS ---
    _schedule_remaining(
        calendar, all_programs, year, noncon_count, road_count,
        new_obligations, rng
    )

    return new_obligations


def _schedule_marquee_events(calendar, all_programs, year,
                              noncon_count, rng):
    """
    Place 4-5 marquee resort events.
    Each event: 8 teams, 3 games each, resort site.
    Returns set of participant names.
    """
    from neutral_sites import get_resort_sites, get_event_name

    resort_sites  = get_resort_sites()
    if not resort_sites:
        return set()

    rng.shuffle(resort_sites)

    # Separate programs by eligibility
    # Marquee events: power + high_major + top mid_major only
    eligible = []
    for p in all_programs:
        tier     = get_conference_tier(p["conference"])["tier"]
        prestige = p.get("prestige_current", 30)
        if tier in ("power", "high_major") and prestige >= 35:
            eligible.append(p)
        elif tier == "mid_major" and prestige >= 60:
            eligible.append(p)

    participants = set()
    num_events   = rng.randint(4, 5)
    sites_used   = resort_sites[:num_events]

    # Marquee events anchor around Thanksgiving and Christmas --
    # the two traditional destination tournament windows.
    # Each event runs 3 consecutive days.
    # Thanksgiving events: start Wed before Thanksgiving (teams arrive Tue)
    # Christmas events: start Dec 23 (teams arrive Dec 22)
    # Any remaining events spread into early November.
    w = calendar.windows
    thanksgiving = w["thanksgiving"]

    marquee_windows = [
        thanksgiving - timedelta(days=1),   # Wed-Fri Thanksgiving week
        date(w["noncon_start"].year, 12, 23),  # Dec 23-25 Christmas window
        w["noncon_start"] + timedelta(days=3),  # Early November fallback 1
        w["noncon_start"] + timedelta(days=10), # Early November fallback 2
        w["noncon_start"] + timedelta(days=17), # Early November fallback 3
    ]

    for event_idx, (site_key, site_dict) in enumerate(sites_used):
        # Pick 8 teams -- prestige-weighted, no conference duplication
        event_teams = _pick_event_field(
            eligible, 8, participants, rng,
            require_conference_diversity=True
        )
        if len(event_teams) < 8:
            continue

        event_name = get_event_name(site_key, rng)
        base_date  = marquee_windows[event_idx % len(marquee_windows)]

        # 3 rounds over 3 consecutive days
        round_dates = [
            base_date,
            base_date + timedelta(days=1),
            base_date + timedelta(days=2),
        ]

        # Bracket: pairs from 8 teams
        rng.shuffle(event_teams)
        round1_pairs = [
            (event_teams[0], event_teams[1]),
            (event_teams[2], event_teams[3]),
            (event_teams[4], event_teams[5]),
            (event_teams[6], event_teams[7]),
        ]

        for game_num, (home, away) in enumerate(round1_pairs):
            calendar.add_noncon_game(
                round_dates[0], home, away,
                is_neutral=True, neutral_site=site_key,
                event_name=event_name, event_round=1,
                series_id=f"MARQUEE_{site_key}_{year}_R1G{game_num+1}"
            )
            noncon_count[home["name"]] = noncon_count.get(home["name"], 0) + 1
            noncon_count[away["name"]] = noncon_count.get(away["name"], 0) + 1

        # Rounds 2 and 3 -- placeholder count (3 games total per team)
        for team in event_teams:
            participants.add(team["name"])
            noncon_count[team["name"]] = noncon_count.get(team["name"], 0) + 2

    return participants


def _pick_event_field(eligible, size, already_used, rng,
                       require_conference_diversity=True):
    """
    Pick a field of `size` teams from eligible pool.
    Enforces conference diversity (no two teams from same conference).
    Avoids teams already committed to another event.
    Prestige-weighted selection.
    """
    available = [p for p in eligible if p["name"] not in already_used]

    # Weight by prestige -- higher prestige programs get more invites
    weights = [max(1, p.get("prestige_current", 30)) for p in available]
    total_w = sum(weights)
    probs   = [w / total_w for w in weights]

    selected   = []
    used_confs = set()

    attempts = 0
    while len(selected) < size and attempts < len(available) * 3:
        attempts += 1
        idx  = rng.choices(range(len(available)), weights=probs, k=1)[0]
        team = available[idx]

        if require_conference_diversity:
            if team["conference"] in used_confs:
                continue

        selected.append(team)
        used_confs.add(team["conference"])
        available.pop(idx)
        probs.pop(idx)
        total_w = sum(probs) or 1
        probs   = [p / total_w for p in probs]

    return selected


def _schedule_mini_tournaments(calendar, all_programs, year,
                                noncon_count, exclude, rng):
    """
    Place 12-20 four-team mini tournaments on neutral sites.
    Each event: 4 teams, 2 games each.
    Primarily low and mid major programs.
    No resort sites. Neutral sites only.
    Returns set of participant names.
    """
    from neutral_sites import get_schedulable_sites, NEUTRAL_SITES

    # Get mid and small tier neutral sites
    schedulable = get_schedulable_sites()
    mini_sites  = [(k, s) for k, s in schedulable
                   if s["tier"] in ("mid", "small")]
    rng.shuffle(mini_sites)

    # Eligible teams: primarily low/mid major, some high major
    eligible = []
    for p in all_programs:
        if p["name"] in exclude:
            continue
        tier     = get_conference_tier(p["conference"])["tier"]
        prestige = p.get("prestige_current", 30)
        if tier in ("mid_major", "low_major", "floor_conf"):
            eligible.append(p)
        elif tier == "high_major" and prestige < 55:
            eligible.append(p)

    participants = set()
    num_events   = rng.randint(12, 20)
    w            = calendar.windows

    # Spread events through first 3 weeks of November
    event_dates = []
    for day_offset in range(0, 21, 2):
        d = w["noncon_start"] + timedelta(days=day_offset)
        if not calendar.is_blackout(d):
            event_dates.append(d)

    for event_idx in range(min(num_events, len(mini_sites), len(event_dates))):
        site_key, site_dict = mini_sites[event_idx]
        base_date           = event_dates[event_idx % len(event_dates)]
        event_name          = f"{site_dict['city']} Classic"

        # Pick 4 teams -- no conference duplication
        event_teams = _pick_event_field(
            eligible, 4, participants, rng,
            require_conference_diversity=True
        )
        if len(event_teams) < 4:
            continue

        # Day 1: semis (2 games)
        # Day 2: final + consolation
        semi_date  = base_date
        final_date = base_date + timedelta(days=1)

        rng.shuffle(event_teams)
        semis = [
            (event_teams[0], event_teams[1]),
            (event_teams[2], event_teams[3]),
        ]

        for game_num, (home, away) in enumerate(semis):
            calendar.add_noncon_game(
                semi_date, home, away,
                is_neutral=True, neutral_site=site_key,
                event_name=event_name, event_round=1,
                series_id=f"MINI_{site_key}_{year}_R1G{game_num+1}"
            )
            noncon_count[home["name"]] = noncon_count.get(home["name"], 0) + 1
            noncon_count[away["name"]] = noncon_count.get(away["name"], 0) + 1

        for team in event_teams:
            participants.add(team["name"])
            noncon_count[team["name"]] = noncon_count.get(team["name"], 0) + 1

    return participants


def _fulfill_obligations(calendar, all_programs, year,
                          noncon_count, road_count, new_obligations, rng):
    """
    Schedule games from existing cross-season obligations.
    A team that hosted Oral Roberts twice last year now owes them a road trip.
    """
    prog_map   = {p["name"]: p for p in all_programs}
    noncon_dates = calendar.get_noncon_dates()
    processed_series = set()

    for program in all_programs:
        due = get_due_obligations(program, year)
        for ob in due:
            series_id = ob["series_id"]
            if series_id in processed_series:
                continue

            opponent = prog_map.get(ob["opponent"])
            if not opponent:
                continue

            # Schedule home games owed
            for _ in range(ob["games_at_home"]):
                placed = _place_noncon_game(
                    calendar, program, opponent,
                    noncon_dates, noncon_count, road_count,
                    is_neutral=False, series_id=series_id
                )
                if placed:
                    fulfill_obligation(program, series_id, is_home=True)

            # Schedule away games owed
            for _ in range(ob["games_away"]):
                if not can_travel_to(program, opponent):
                    continue
                placed = _place_noncon_game(
                    calendar, opponent, program,
                    noncon_dates, noncon_count, road_count,
                    is_neutral=False, series_id=series_id
                )
                if placed:
                    fulfill_obligation(program, series_id, is_home=False)

            processed_series.add(series_id)


def _generate_wish_list(program, slots_needed, conf_game_counts, noncon_count, rng):
    """
    Generate a coach's ideal non-conference schedule as a list of slot demands.

    Each slot is a dict:
        location:  'home' | 'away' | 'neutral'
        opp_tier:  'elite' | 'quality' | 'mid' | 'low' | 'cupcake' | 'any'

    Opponent tiers by prestige:
        elite:   65+
        quality: 45-64
        mid:     25-44
        low:     12-24
        cupcake: <12

    Power conference teams always have 60%+ home games enforced.
    """
    aggression = program.get("scheduling_aggression", 5)
    conf_tier  = get_conference_tier(program["conference"])["tier"]
    prestige   = program.get("prestige_current", 30)

    wishes = []

    if conf_tier == "floor_conf":
        # Almost entirely road paycheck games, 0-2 home games
        home_count = rng.randint(0, 2)
        away_count = max(0, slots_needed - home_count)
        for _ in range(home_count):
            wishes.append({"location": "home", "opp_tier": "low"})
        for _ in range(away_count):
            wishes.append({"location": "away", "opp_tier": "elite"})
        return wishes

    if conf_tier == "low_major":
        # Mix of home games and road paycheck trips
        road_max   = 4 if aggression >= 3 else 2
        away_count = min(road_max, rng.randint(1, 4))
        home_count = max(0, slots_needed - away_count)
        for _ in range(home_count):
            tier = rng.choice(["low", "low", "mid", "cupcake"])
            wishes.append({"location": "home", "opp_tier": tier})
        for _ in range(away_count):
            wishes.append({"location": "away", "opp_tier": "elite"})
        return wishes

    # Power and high major -- aggression-driven wish list
    # Hard rule: 60%+ home games for power conference
    min_home = int(slots_needed * 0.6) if conf_tier == "power" else 0

    if aggression >= 9:
        # Aggressive: quality opponents, road trips, neutrals
        road_games    = min(3, rng.randint(2, 3))
        neutral_games = rng.randint(1, 2)
        home_games    = max(min_home, slots_needed - road_games - neutral_games)
        road_games    = slots_needed - home_games - neutral_games

        for _ in range(home_games):
            tier = rng.choices(
                ["elite", "quality", "mid", "low", "cupcake"],
                weights=[25, 30, 20, 15, 10], k=1)[0]
            wishes.append({"location": "home", "opp_tier": tier})
        for _ in range(neutral_games):
            wishes.append({"location": "neutral", "opp_tier": "quality"})
        for _ in range(max(0, road_games)):
            wishes.append({"location": "away", "opp_tier": "quality"})

    elif aggression >= 7:
        road_games    = min(2, rng.randint(1, 2))
        neutral_games = rng.randint(0, 1)
        home_games    = max(min_home, slots_needed - road_games - neutral_games)
        road_games    = slots_needed - home_games - neutral_games

        for _ in range(home_games):
            tier = rng.choices(
                ["elite", "quality", "mid", "low", "cupcake"],
                weights=[15, 25, 25, 20, 15], k=1)[0]
            wishes.append({"location": "home", "opp_tier": tier})
        for _ in range(neutral_games):
            wishes.append({"location": "neutral", "opp_tier": "mid"})
        for _ in range(max(0, road_games)):
            wishes.append({"location": "away", "opp_tier": "quality"})

    elif aggression >= 5:
        road_games    = rng.randint(0, 1)
        neutral_games = rng.randint(0, 1)
        home_games    = max(min_home, slots_needed - road_games - neutral_games)
        road_games    = slots_needed - home_games - neutral_games

        for _ in range(home_games):
            tier = rng.choices(
                ["quality", "mid", "low", "cupcake"],
                weights=[15, 25, 30, 30], k=1)[0]
            wishes.append({"location": "home", "opp_tier": tier})
        if neutral_games:
            wishes.append({"location": "neutral", "opp_tier": "mid"})
        for _ in range(max(0, road_games)):
            wishes.append({"location": "away", "opp_tier": "mid"})

    elif aggression >= 3:
        # Soft scheduler -- mostly home cupcakes, one quality home game
        road_games  = 0
        home_games  = slots_needed
        # At least one decent home game even for pillow-soft schedules
        wishes.append({"location": "home", "opp_tier": "quality"})
        for _ in range(home_games - 1):
            tier = rng.choices(
                ["mid", "low", "cupcake"],
                weights=[20, 40, 40], k=1)[0]
            wishes.append({"location": "home", "opp_tier": tier})

    else:
        # Maximum cowardice -- all home cupcakes + one okay opponent
        wishes.append({"location": "home", "opp_tier": "quality"})
        for _ in range(slots_needed - 1):
            wishes.append({"location": "home", "opp_tier": "cupcake"})

    rng.shuffle(wishes)
    return wishes[:slots_needed]


def _prestige_tier(prestige):
    """Map prestige to opponent tier label."""
    if prestige >= 65:   return "elite"
    if prestige >= 45:   return "quality"
    if prestige >= 25:   return "mid"
    if prestige >= 12:   return "low"
    return "cupcake"


def _schedule_remaining(calendar, all_programs, year,
                          noncon_count, road_count, new_obligations, rng):
    """
    Fill non-conference slots using wish list matchmaking.

    Each team generates an ideal schedule demand (wish list).
    The scheduler pairs supply with demand:
      - Home slots seek away teams whose road demands match
      - Away slots seek home teams whose home demands match
      - Neutral slots pair teams of similar prestige

    Power programs post their demands first (they set the market).
    Everyone else fills around them.
    Unmatched slots get filled with whatever's available.
    """
    noncon_dates     = calendar.get_noncon_dates()
    conf_game_counts = _estimate_conf_games(all_programs, calendar)

    def slots_remaining(prog):
        conf_games = conf_game_counts.get(prog["name"], 18)
        target     = get_noncon_slots(prog["conference"], conf_games)
        current    = noncon_count.get(prog["name"], 0)
        return max(0, target - current)

    # Build wish lists for every program
    wish_lists = {}
    for p in all_programs:
        n = slots_remaining(p)
        if n > 0:
            wish_lists[p["name"]] = _generate_wish_list(p, n, conf_game_counts,
                                                         noncon_count, rng)

    prog_map = {p["name"]: p for p in all_programs}

    # Sort by conference tier then aggression -- power programs post first
    tier_order = {"power": 0, "high_major": 1, "mid_major": 2,
                  "low_major": 3, "floor_conf": 4}
    sorted_programs = sorted(
        all_programs,
        key=lambda p: (
            tier_order.get(get_conference_tier(p["conference"])["tier"], 5),
            -p.get("scheduling_aggression", 5)
        )
    )

    scheduled_pairs = set()  # track (home, away) to avoid duplicates

    for program in sorted_programs:
        wishes = wish_lists.get(program["name"], [])
        if not wishes:
            continue

        already_scheduled = _get_scheduled_opponents(calendar, program["name"])
        prestige          = program.get("prestige_current", 30)

        for wish in list(wishes):
            location = wish["location"]
            opp_tier = wish["opp_tier"]

            # Build candidate pool for this wish
            candidates = []
            for other in all_programs:
                if other["name"] == program["name"]:
                    continue
                if other["conference"] == program["conference"]:
                    continue
                if other["name"] in already_scheduled:
                    continue
                if slots_remaining(other) <= 0:
                    continue

                opp_prestige = other.get("prestige_current", 30)
                other_tier   = _prestige_tier(opp_prestige)

                # Check tier match -- 'any' always matches
                if opp_tier != "any" and other_tier != opp_tier:
                    # Allow one tier up or down for flexibility
                    tier_ladder = ["cupcake", "low", "mid", "quality", "elite"]
                    wish_idx  = tier_ladder.index(opp_tier) if opp_tier in tier_ladder else 2
                    other_idx = tier_ladder.index(other_tier) if other_tier in tier_ladder else 2
                    if abs(wish_idx - other_idx) > 1:
                        continue

                candidates.append(other)

            # Distance-weighted selection:
            # < 500 miles:  weight 10x  (Kansas City vs Kansas -- happens constantly)
            # 500-1000 mi:  weight 3x   (regional but not local)
            # 1000-2000 mi: weight 1x   (base probability)
            # > 2000 miles: weight 0.1x (rare outlier -- Miami schedules Seattle once a century)
            team_lat = program.get("latitude", 39.5)
            team_lon = program.get("longitude", -98.0)

            weighted = []
            for other in candidates:
                dist = haversine(
                    team_lat, team_lon,
                    other.get("latitude", 39.5),
                    other.get("longitude", -98.0)
                )
                if dist < 500:
                    w = 10.0
                elif dist < 1000:
                    w = 3.0
                elif dist < 2000:
                    w = 1.0
                else:
                    w = 0.1
                weighted.append((w, other))

            # Sort by weight descending, shuffle within same weight band for variety
            weighted.sort(key=lambda x: x[0], reverse=True)

            # Build final ordered candidate list using weighted random draw
            # Pull from weighted pool so regional teams appear far more often
            # but distant teams still occasionally get picked
            ordered_candidates = []
            pool = list(weighted)
            while pool:
                weights = [w for w, _ in pool]
                total   = sum(weights)
                if total <= 0:
                    break
                probs = [w / total for w in weights]
                idx   = rng.choices(range(len(pool)), weights=probs, k=1)[0]
                ordered_candidates.append(pool[idx][1])
                pool.pop(idx)

            placed = False
            for opponent in ordered_candidates:
                pair_key = (program["name"], opponent["name"])
                if pair_key in scheduled_pairs:
                    continue

                if location == "home":
                    h, a = program, opponent
                elif location == "away":
                    h, a = opponent, program
                else:  # neutral -- use geographic midpoint logic later, home for now
                    h, a = program, opponent

                result = _place_noncon_game(
                    calendar, h, a,
                    noncon_dates, noncon_count, road_count,
                    is_neutral=(location == "neutral"),
                    series_id=make_series_id(program["name"], opponent["name"], year)
                )

                if result:
                    scheduled_pairs.add(pair_key)
                    scheduled_pairs.add((opponent["name"], program["name"]))
                    already_scheduled.add(opponent["name"])
                    wishes.remove(wish)

                    # Track 1-for-1 return obligation for even matchups
                    p_self = prestige
                    p_opp  = opponent.get("prestige_current", 30)
                    _, _, gap_cat = get_series_format(p_self, p_opp)
                    if gap_cat == "even" and location == "home":
                        sid = make_series_id(program["name"], opponent["name"], year)
                        add_obligation(
                            opponent, program["name"],
                            games_at_home=1, games_away=0,
                            start_year=year + 1,
                            series_id=sid + "_RET"
                        )
                        new_obligations.append((opponent["name"], program["name"], year + 1))
                    placed = True
                    break

            # If wish couldn't be fulfilled, try 'any' tier as fallback
            if not placed and opp_tier != "any":
                wish["opp_tier"] = "any"

        wish_lists[program["name"]] = wishes

    # Final pass -- fill any remaining slots with any available opponent
    for program in sorted_programs:
        remaining = slots_remaining(program)
        if remaining <= 0:
            continue

        conf_tier = get_conference_tier(program["conference"])["tier"]
        if conf_tier == "floor_conf":
            # Floor conf: try road games against anyone
            candidates = [
                p for p in all_programs
                if p["name"] != program["name"]
                and p["conference"] != program["conference"]
                and p["name"] not in _get_scheduled_opponents(calendar, program["name"])
                and slots_remaining(p) > 0
            ]
            rng.shuffle(candidates)
            for opp in candidates:
                if slots_remaining(program) <= 0:
                    break
                _place_noncon_game(
                    calendar, opp, program,
                    noncon_dates, noncon_count, road_count,
                    is_neutral=False,
                    series_id=make_series_id(program["name"], opp["name"], year)
                )
        else:
            # Everyone else: home games
            prestige   = program.get("prestige_current", 30)
            candidates = [
                p for p in all_programs
                if p["name"] != program["name"]
                and p["conference"] != program["conference"]
                and p["name"] not in _get_scheduled_opponents(calendar, program["name"])
                and slots_remaining(p) > 0
                and p.get("prestige_current", 0) <= prestige + 20
            ]
            rng.shuffle(candidates)
            for opp in candidates:
                if slots_remaining(program) <= 0:
                    break
                _place_noncon_game(
                    calendar, program, opp,
                    noncon_dates, noncon_count, road_count,
                    is_neutral=False,
                    series_id=make_series_id(program["name"], opp["name"], year)
                )


def _place_noncon_game(calendar, home, away, noncon_dates,
                        noncon_count, road_count,
                        is_neutral=False, neutral_site=None,
                        event_name=None, series_id=None):
    """
    Find an available date and place a non-conference game.
    Hard rules:
      - 2-day minimum rest between non-conference games
      - 2-day buffer around tournament blocks
      - Away team road limit enforced from their scheduling profile
    Returns True if placed successfully.
    """
    # Enforce road game cap for away team
    if not is_neutral:
        away_profile = get_scheduling_profile(away)
        if road_count.get(away["name"], 0) >= away_profile["max_road_games"]:
            return False

    for d in noncon_dates:
        if not calendar.both_can_play(home["name"], away["name"], d,
                                      max_per_week=3):
            continue
        # 2-day minimum rest for both teams
        if not _has_min_rest(calendar, home["name"], d, min_days=2):
            continue
        if not _has_min_rest(calendar, away["name"], d, min_days=2):
            continue
        # 2-day buffer around tournament blocks
        if not _has_tournament_buffer(calendar, home["name"], d):
            continue
        if not _has_tournament_buffer(calendar, away["name"], d):
            continue

        calendar.add_noncon_game(
            d, home, away,
            is_neutral=is_neutral,
            neutral_site=neutral_site,
            event_name=event_name,
            series_id=series_id
        )
        noncon_count[home["name"]] = noncon_count.get(home["name"], 0) + 1
        noncon_count[away["name"]] = noncon_count.get(away["name"], 0) + 1
        if not is_neutral:
            road_count[away["name"]] = road_count.get(away["name"], 0) + 1
        return True
    return False


def _get_scheduled_opponents(calendar, team_name):
    """Return set of opponent names already on the schedule."""
    schedule = calendar.get_team_schedule(team_name, game_type="noncon")
    opponents = set()
    for slot in schedule:
        opp = slot.get_opponent(team_name)
        if opp:
            opponents.add(opp["name"])
    return opponents


def _estimate_conf_games(all_programs, calendar=None):
    """
    Returns actual conference games per team from the calendar.
    Falls back to format-based estimate if calendar not provided.
    Using actual counts is critical -- conferences may have different
    real sizes than CONFERENCE_FORMATS expects.
    """
    result = {}
    if calendar is not None:
        for p in all_programs:
            conf_slots = calendar.get_team_schedule(p["name"],
                                                    game_type="conference")
            result[p["name"]] = len(conf_slots)
    else:
        for p in all_programs:
            fmt = get_conference_format(p["conference"])
            result[p["name"]] = fmt.get("conf_games", 18)
    return result
