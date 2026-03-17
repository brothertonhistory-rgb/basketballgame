# scheduler.py
# College Hoops Sim -- Scheduler v2.0
#
# WHAT THIS FILE DOES:
#   1. Conference schedule builder (unchanged from v1.0 -- works correctly)
#   2. Non-conference scheduler (complete rewrite)
#
# NON-CONFERENCE ARCHITECTURE (v2.0):
#   Phase 1 -- Tournament placement
#     1a. Resort/marquee events (Thanksgiving + Christmas windows)
#         8 teams, 3 real games each, 3 consecutive days
#     1b. Regular 8-team neutral events (10 events)
#         8 teams, 3 real games each, 2 consecutive days
#     1c. 4-team mini tournaments (15 events)
#         4 teams, 2 real games each, 2 consecutive days
#     All games placed as real GameSlots. No ghost accounting.
#     2-day buffers marked. Teams committed to one event only.
#
#   Phase 2 -- Supply-demand matching (the key inversion)
#     Power/high_major post HOME slots (they set the market).
#     Floor_conf post ROAD availability (they fill the market).
#     Match floor_conf road seekers to power home slots first.
#     Then match remaining home slots across all tiers.
#     Road cap enforced at POSTING time, not placement time.
#     Geographic weighting drives candidate selection.
#
#   Phase 3 -- Gap fill
#     Anyone still short of target gets remaining slots filled.
#     Respects road caps, geographic weighting, back-to-back rules.
#     Preference for home games for programs with home slots open.
#
# HARD RULES (enforced throughout):
#   - No back-to-backs ever (min 2 days between games)
#   - Season total: 31 (power/high/mid), 30 (low_major/floor_conf), never 32
#   - Power/high_major never travel to floor_conf campuses
#   - Floor_conf: 0-2 home games, rest are road paycheck trips
#   - No two teams from same conference in same tournament event
#   - Resort sites used ONLY for marquee events
#   - Tournament teams committed to exactly one event
#
# GEOGRAPHIC WEIGHTING:
#   < 500 miles:   10x weight
#   500-1000 mi:    3x weight
#   1000-2000 mi:   1x weight
#   > 2000 miles: 0.1x weight

import random
from datetime import date, timedelta
from calendar import SeasonCalendar, get_conference_format
from programs_data import get_conference_tier

# ---------------------------------------------------------------------------
# HAVERSINE DISTANCE
# Inline so schools_database.py is not required for scheduler to run.
# ---------------------------------------------------------------------------

import math

def _haversine(lat1, lon1, lat2, lon2):
    """Returns distance in miles between two lat/lon points."""
    R = 3958.8  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Attempt to use schools_database haversine if available
try:
    from schools_database import haversine as _haversine_ext
    def haversine(lat1, lon1, lat2, lon2):
        return _haversine_ext(lat1, lon1, lat2, lon2)
except ImportError:
    def haversine(lat1, lon1, lat2, lon2):
        return _haversine(lat1, lon1, lat2, lon2)


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

# Geographic distance weight bands
_GEO_WEIGHTS = [
    (500,   10.0),   # < 500 miles: regional neighbor
    (1000,   3.0),   # 500-1000: same region
    (2000,   1.0),   # 1000-2000: national
    (99999,  0.1),   # > 2000: cross-country rarity
]

# Conference tier processing order (power posts first, floor fills last)
_TIER_ORDER = {
    "power":      0,
    "high_major": 1,
    "mid_major":  2,
    "low_major":  3,
    "floor_conf": 4,
}

# Prestige-to-tier bucket for opponent quality matching
def _prestige_bucket(prestige):
    if prestige >= 65:   return "elite"
    if prestige >= 45:   return "quality"
    if prestige >= 25:   return "mid"
    if prestige >= 12:   return "low"
    return "cupcake"

def _tier_idx(bucket):
    return ["cupcake", "low", "mid", "quality", "elite"].index(bucket) if bucket in ["cupcake", "low", "mid", "quality", "elite"] else 2


# ---------------------------------------------------------------------------
# ROAD GAME ELIGIBILITY
# Hard rules: power/high_major never go to floor_conf campuses.
# ---------------------------------------------------------------------------

def can_travel_to(traveler, host):
    """True if traveler can play a road game at host's campus."""
    traveler_tier = get_conference_tier(traveler["conference"])["tier"]
    host_tier     = get_conference_tier(host["conference"])["tier"]

    if host_tier == "floor_conf":
        if traveler_tier in ("power", "high_major"):
            return False

    # Large prestige gap -- high prestige programs don't travel to weak campuses
    gap = traveler.get("prestige_current", 50) - host.get("prestige_current", 50)
    if gap >= 40:
        return False

    return True


# ---------------------------------------------------------------------------
# NON-CONFERENCE SLOT CALCULATOR
# How many non-con games each team needs.
# ---------------------------------------------------------------------------

def get_noncon_target(conference_name, conf_games_played):
    """
    Returns target non-conference game count.
    Season total: 31 (power/high_major/mid_major), 30 (low_major/floor_conf).
    Never 32.
    """
    tier = get_conference_tier(conference_name)["tier"]
    target_total = 30 if tier in ("low_major", "floor_conf") else 31
    slots = max(0, target_total - conf_games_played)
    return max(8, min(14, slots))


# ---------------------------------------------------------------------------
# SCHEDULING PROFILE
# Road cap and home target by tier + aggression.
# Enforced at posting time, not placement time.
# ---------------------------------------------------------------------------

def get_scheduling_profile(program):
    """
    Returns scheduling profile:
      max_road_games    -- hard cap on true road non-con games
      home_target_min   -- minimum home games (power: 60% of noncon)
      neutral_appetite  -- True if program seeks neutral games
      paycheck_road     -- True if program primarily takes road paycheck trips
    """
    aggression = program.get("scheduling_aggression", 5)
    conf_tier  = get_conference_tier(program["conference"])["tier"]

    if conf_tier == "floor_conf":
        return {
            "max_road_games":   12,  # Almost all road
            "home_target_min":  0,
            "home_target_max":  2,
            "neutral_appetite": False,
            "paycheck_road":    True,
        }

    if conf_tier == "low_major":
        max_road = 6 if aggression >= 7 else (4 if aggression >= 4 else 2)
        return {
            "max_road_games":   max_road,
            "home_target_min":  3,
            "home_target_max":  7,
            "neutral_appetite": False,
            "paycheck_road":    aggression <= 2,
        }

    # Power and high_major
    if aggression >= 9:
        max_road = 3
    elif aggression >= 7:
        max_road = 2
    elif aggression >= 5:
        max_road = 1
    else:
        max_road = 0

    return {
        "max_road_games":   max_road,
        "home_target_min":  None,   # 60% enforced at wish-list generation
        "home_target_max":  None,
        "neutral_appetite": aggression >= 5,
        "paycheck_road":    False,
    }


# ---------------------------------------------------------------------------
# REST / BUFFER CHECKS
# Checks only noncon-window games to avoid false positives from conference schedule.
# ---------------------------------------------------------------------------

def _get_noncon_dates_for_team(calendar, team_name):
    """Return sorted list of noncon game dates for a team."""
    schedule = calendar.get_team_schedule(team_name, game_type="noncon")
    return sorted(s.date for s in schedule)


def _get_all_dates_for_team(calendar, team_name):
    """Return sorted list of ALL game dates for a team (conf + noncon)."""
    schedule = calendar.get_team_schedule(team_name)
    return sorted(s.date for s in schedule)


def _has_min_rest_noncon(calendar, team_name, proposed_date, min_days=2):
    """
    True if team has at least min_days rest before/after proposed_date
    looking only at their full schedule (conf games matter for rest).
    """
    for d in _get_all_dates_for_team(calendar, team_name):
        if abs((proposed_date - d).days) < min_days:
            return False
    return True


def _get_tournament_block(calendar, team_name):
    """
    Return (first_date, last_date) of any tournament block the team is committed to.
    Returns None if not in any tournament.
    """
    tourney_slots = [s for s in calendar.get_team_schedule(team_name, game_type="noncon")
                     if s.event_name is not None]
    if not tourney_slots:
        return None
    dates = sorted(s.date for s in tourney_slots)
    return (dates[0], dates[-1])


def _has_tournament_buffer(calendar, team_name, proposed_date, buffer=2):
    """True if proposed_date is outside the 2-day buffer around any tournament block."""
    block = _get_tournament_block(calendar, team_name)
    if not block:
        return True
    t_start, t_end = block
    before_gap = (t_start - proposed_date).days
    after_gap  = (proposed_date - t_end).days
    if 0 < before_gap < buffer:
        return False
    if 0 < after_gap < buffer:
        return False
    return True


def _can_schedule(calendar, team_name, proposed_date):
    """Combined eligibility check: weekly limit + rest + tournament buffer."""
    if not calendar.can_play(team_name, proposed_date, max_per_week=2):
        return False
    if not _has_min_rest_noncon(calendar, team_name, proposed_date, min_days=2):
        return False
    if not _has_tournament_buffer(calendar, team_name, proposed_date):
        return False
    return True


# ---------------------------------------------------------------------------
# GEOGRAPHIC WEIGHT
# ---------------------------------------------------------------------------

def _geo_weight(dist_miles):
    for threshold, weight in _GEO_WEIGHTS:
        if dist_miles < threshold:
            return weight
    return 0.1


def _weighted_sample(candidates, key_fn, rng, k=1):
    """
    Draw k items from candidates using weights from key_fn.
    Returns list of sampled items. Does not remove from pool.
    """
    if not candidates:
        return []
    weights = [max(0.001, key_fn(c)) for c in candidates]
    return rng.choices(candidates, weights=weights, k=min(k, len(candidates)))


def _build_geo_weighted_pool(team, pool, rng):
    """
    Sort pool by geographic weight (closest first, probabilistically).
    Returns ordered list of programs from pool.
    """
    team_lat = team.get("latitude", 39.5)
    team_lon = team.get("longitude", -98.0)

    weighted = []
    for p in pool:
        dist = haversine(team_lat, team_lon,
                         p.get("latitude", 39.5),
                         p.get("longitude", -98.0))
        w = _geo_weight(dist)
        weighted.append((w, p))

    # Weighted shuffle: draw without replacement using weights
    ordered = []
    remaining = list(weighted)
    while remaining:
        total = sum(w for w, _ in remaining)
        if total <= 0:
            break
        probs = [w / total for w, _ in remaining]
        idx = rng.choices(range(len(remaining)), weights=probs, k=1)[0]
        ordered.append(remaining[idx][1])
        remaining.pop(idx)

    return ordered


# ---------------------------------------------------------------------------
# DATE FINDER
# Finds first available date from a sorted date list for two teams.
# ---------------------------------------------------------------------------

def _find_date(calendar, home_name, away_name, date_pool):
    """
    Return first date from date_pool where both teams can play.
    Returns None if no date works.
    """
    for d in date_pool:
        if _can_schedule(calendar, home_name, d) and _can_schedule(calendar, away_name, d):
            return d
    return None


# ---------------------------------------------------------------------------
# SCHEDULED OPPONENT TRACKING
# ---------------------------------------------------------------------------

def _get_scheduled_opponents(calendar, team_name):
    """Set of opponent names already on this team's noncon schedule."""
    schedule = calendar.get_team_schedule(team_name, game_type="noncon")
    opponents = set()
    for slot in schedule:
        opp = slot.get_opponent(team_name)
        if opp:
            opponents.add(opp["name"])
    return opponents


def _noncon_count(calendar, team_name):
    """How many noncon games this team already has scheduled."""
    return len(calendar.get_team_schedule(team_name, game_type="noncon"))


def _road_count(calendar, team_name):
    """How many true road noncon games this team has."""
    count = 0
    for slot in calendar.get_team_schedule(team_name, game_type="noncon"):
        if not slot.is_neutral and slot.away_team and slot.away_team["name"] == team_name:
            count += 1
    return count


# ---------------------------------------------------------------------------
# CONFERENCE SCHEDULE BUILDER (unchanged from v1.0 -- works correctly)
# ---------------------------------------------------------------------------

def build_conference_schedule(calendar, conference_name, teams, rng=None):
    """
    Build the full conference schedule for a conference.
    Places games on the calendar with real dates.
    Returns list of (home, away) tuples scheduled.
    """
    if rng is None:
        rng = random.Random()

    n         = len(teams)
    fmt_data  = get_conference_format(conference_name)
    fmt       = fmt_data["format"]
    divisions = fmt_data.get("divisions")

    if fmt == "double_rr":
        actual_conf_games = (n - 1) * 2
    elif fmt == "single_rr":
        actual_conf_games = n - 1
    elif fmt == "divisions_2x1":
        div_size = n // 2
        actual_conf_games = (div_size - 1) * 2 + div_size
    elif fmt in ("divisions_1x_plus_rival", "partial"):
        base  = n - 1
        extra = min(4, max(2, n // 4))
        actual_conf_games = min(20, base + extra)
    else:
        actual_conf_games = (n - 1) * 2

    if divisions:
        team_names  = {t["name"] for t in teams}
        div_members = {m for members in divisions.values() for m in members}
        overlap = len(team_names & div_members)
        if overlap < len(teams) * 0.5:
            divisions = None
            if fmt == "divisions_2x1":
                fmt = "double_rr"
                actual_conf_games = (n - 1) * 2

    fmt_data = dict(fmt_data)
    fmt_data["conf_games"] = actual_conf_games

    matchups = _generate_conf_matchups(teams, fmt, divisions,
                                        fmt_data.get("protected_rivals", {}),
                                        rng,
                                        target_games=actual_conf_games)
    rng.shuffle(matchups)

    conf_start    = calendar.get_conference_start(fmt_data.get("conf_games", 18))
    all_conf_dates = calendar.get_conference_dates()
    conf_dates    = [d for d in all_conf_dates if d >= conf_start]
    if not conf_dates:
        return []

    scheduled = []
    for home, away in matchups:
        placed = False
        for d in conf_dates:
            if calendar.both_can_play(home["name"], away["name"], d, max_per_week=2):
                calendar.add_conference_game(d, home, away)
                scheduled.append((home, away))
                placed = True
                break

        if not placed:
            for d in all_conf_dates:
                if calendar.both_can_play(home["name"], away["name"], d, max_per_week=2):
                    calendar.add_conference_game(d, home, away)
                    scheduled.append((home, away))
                    break

    return scheduled


def _generate_conf_matchups(teams, fmt, divisions, protected_rivals, rng,
                             target_games=None):
    """Generate list of (home, away) pairs for a conference."""
    matchups = []
    team_map = {t["name"]: t for t in teams}
    n        = len(teams)

    if fmt == "double_rr":
        pairs = _all_pairs(teams)
        for a, b in pairs:
            if rng.random() < 0.5:
                matchups.extend([(a, b), (b, a)])
            else:
                matchups.extend([(b, a), (a, b)])

    elif fmt == "single_rr":
        pairs = _all_pairs(teams)
        for a, b in pairs:
            matchups.append((a, b) if rng.random() < 0.5 else (b, a))

    elif fmt == "divisions_2x1":
        if not divisions:
            return _generate_conf_matchups(teams, "double_rr", None,
                                            protected_rivals, rng, target_games)
        div_names   = list(divisions.keys())
        div_a_names = set(divisions[div_names[0]])
        div_b_names = set(divisions[div_names[1]])
        div_a = [t for t in teams if t["name"] in div_a_names]
        div_b = [t for t in teams if t["name"] in div_b_names]

        assigned   = {t["name"] for t in div_a + div_b}
        unassigned = [t for t in teams if t["name"] not in assigned]
        for t in unassigned:
            if len(div_a) <= len(div_b):
                div_a.append(t)
            else:
                div_b.append(t)

        if not div_a or not div_b:
            return _generate_conf_matchups(teams, "double_rr", None,
                                            protected_rivals, rng, target_games)

        for team_list in [div_a, div_b]:
            pairs = _all_pairs(team_list)
            for a, b in pairs:
                if rng.random() < 0.5:
                    matchups.extend([(a, b), (b, a)])
                else:
                    matchups.extend([(b, a), (a, b)])

        for a in div_a:
            for b in div_b:
                matchups.append((a, b) if rng.random() < 0.5 else (b, a))

    elif fmt in ("divisions_1x_plus_rival", "partial"):
        pairs = _all_pairs(teams)
        for a, b in pairs:
            matchups.append((a, b) if rng.random() < 0.5 else (b, a))

        game_counts = {t["name"]: 0 for t in teams}
        for h, a in matchups:
            game_counts[h["name"]] += 1
            game_counts[a["name"]] += 1

        game_target = target_games if target_games is not None else min(20, (n-1) + max(2, n//4))

        for team_name, rival_name in protected_rivals.items():
            team  = team_map.get(team_name)
            rival = team_map.get(rival_name)
            if not team or not rival:
                continue
            first = next((m for m in matchups if {m[0]["name"], m[1]["name"]} == {team_name, rival_name}), None)
            if first:
                matchups.append((first[1], first[0]))
                game_counts[team_name] += 1
                game_counts[rival_name] += 1

        all_pairs_list = _all_pairs(teams)
        max_passes = game_target * len(teams)
        passes = 0

        while passes < max_passes:
            passes += 1
            needy = [t for t in teams if game_counts[t["name"]] < game_target]
            if not needy:
                break

            rng.shuffle(all_pairs_list)
            placed = False
            for a, b in all_pairs_list:
                if game_counts[a["name"]] < game_target and game_counts[b["name"]] < game_target:
                    first = next((m for m in matchups if {m[0]["name"], m[1]["name"]} == {a["name"], b["name"]}), None)
                    if first:
                        matchups.append((first[1], first[0]))
                    else:
                        matchups.append((a, b) if rng.random() < 0.5 else (b, a))
                    game_counts[a["name"]] += 1
                    game_counts[b["name"]] += 1
                    placed = True
                    break

            if not placed:
                for needy_team in needy:
                    partners = sorted(
                        [t for t in teams if t["name"] != needy_team["name"]
                         and game_counts[t["name"]] < game_target + 1],
                        key=lambda t: game_counts[t["name"]]
                    )
                    if partners:
                        partner = partners[0]
                        first = next((m for m in matchups if {m[0]["name"], m[1]["name"]} == {needy_team["name"], partner["name"]}), None)
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
    """All unique pairs from a list of teams."""
    return [(teams[i], teams[j]) for i in range(len(teams)) for j in range(i+1, len(teams))]


# ---------------------------------------------------------------------------
# SERIES ID UTILITY
# ---------------------------------------------------------------------------

def make_series_id(team_a_name, team_b_name, year):
    a = team_a_name.replace(" ", "")[:6].upper()
    b = team_b_name.replace(" ", "")[:6].upper()
    return f"{a}_{b}_{year}"


# ---------------------------------------------------------------------------
# SCHEDULING OBLIGATIONS (cross-year return trips)
# ---------------------------------------------------------------------------

def get_obligations(program):
    if "scheduling_obligations" not in program:
        program["scheduling_obligations"] = []
    return program["scheduling_obligations"]


def add_obligation(program, opponent_name, games_at_home, games_away, start_year, series_id):
    obs = get_obligations(program)
    obs.append({
        "opponent":      opponent_name,
        "games_at_home": games_at_home,
        "games_away":    games_away,
        "start_year":    start_year,
        "series_id":     series_id,
    })


def get_due_obligations(program, year):
    return [ob for ob in get_obligations(program) if ob["start_year"] <= year]


# ---------------------------------------------------------------------------
# MAIN NON-CONFERENCE SCHEDULER
# Entry point. Called by season.py simulate_world_season.
# ---------------------------------------------------------------------------

def schedule_noncon(calendar, all_programs, year, rng=None):
    """
    Schedule all non-conference games for the season.

    Phase 1a: Resort/marquee events (Thanksgiving + Christmas windows)
    Phase 1b: Regular 8-team neutral events
    Phase 1c: 4-team mini tournaments
    Phase 2:  Supply-demand matching (home/road/neutral standalone games)
    Phase 3:  Gap fill (anyone still short)

    Returns list of new cross-year obligations created.
    """
    if rng is None:
        rng = random.Random()

    prog_map        = {p["name"]: p for p in all_programs}
    new_obligations = []

    # Track which teams are committed to a tournament event (can't be in two)
    tournament_committed = set()

    # --- PHASE 1a: RESORT / MARQUEE EVENTS ---
    _place_resort_events(calendar, all_programs, year, tournament_committed, rng)

    # --- PHASE 1b: REGULAR 8-TEAM NEUTRAL EVENTS ---
    _place_8team_events(calendar, all_programs, year, tournament_committed, rng)

    # --- PHASE 1c: 4-TEAM MINI TOURNAMENTS ---
    _place_mini_tournaments(calendar, all_programs, year, tournament_committed, rng)

    # --- PHASE 2: SUPPLY-DEMAND MATCHING ---
    _match_standalone_games(calendar, all_programs, year, new_obligations, rng)

    # --- PHASE 3: GAP FILL ---
    _fill_gaps(calendar, all_programs, year, rng)

    return new_obligations


# ---------------------------------------------------------------------------
# PHASE 1a: RESORT / MARQUEE EVENTS
# 4-5 events, 8 teams each, 3 real games each, 3 consecutive days.
# Thanksgiving + Christmas windows. Power + top mid-major only.
# ---------------------------------------------------------------------------

def _place_resort_events(calendar, all_programs, year, committed, rng):
    """Place 4-5 marquee resort destination events."""
    from neutral_sites import get_resort_sites, get_event_name

    resort_sites = get_resort_sites()
    if not resort_sites:
        return

    rng.shuffle(resort_sites)

    # Eligible: power + high_major (prestige >= 35) + top mid_major (prestige >= 60)
    eligible = []
    for p in all_programs:
        tier     = get_conference_tier(p["conference"])["tier"]
        prestige = p.get("prestige_current", 30)
        if tier in ("power", "high_major") and prestige >= 35:
            eligible.append(p)
        elif tier == "mid_major" and prestige >= 60:
            eligible.append(p)

    w            = calendar.windows
    thanksgiving = w["thanksgiving"]

    # Marquee windows: Thanksgiving first (2 events), Christmas (1 event), early November (2 more)
    marquee_starts = [
        thanksgiving - timedelta(days=1),               # Wed-Fri Thanksgiving
        thanksgiving,                                    # Thu-Sat (second Thanksgiving event)
        date(year, 12, 19),                             # Dec 19-21 pre-Christmas
        w["noncon_start"] + timedelta(days=3),          # Early November
        w["noncon_start"] + timedelta(days=10),         # Mid-early November
    ]

    num_events = rng.randint(4, 5)
    used_sites  = resort_sites[:num_events]

    for event_idx, (site_key, site_dict) in enumerate(used_sites):
        base_date  = marquee_starts[event_idx % len(marquee_starts)]
        event_name = get_event_name(site_key, rng)

        # 3 consecutive days
        round_dates = [base_date + timedelta(days=i) for i in range(3)]

        # Skip if dates fall outside noncon window or are blackout
        if any(calendar.is_blackout(d) for d in round_dates):
            continue
        if any(not calendar.is_noncon_window(d) for d in round_dates):
            continue

        # Pick 8 teams: no conference duplication, not already committed
        event_teams = _pick_event_field(eligible, 8, committed, rng)
        if len(event_teams) < 8:
            continue

        # Generate bracket: 4 games in round 1, each team plays once
        # Round 2: winners bracket + losers bracket (each team gets 2nd game)
        # Round 3: each team gets 3rd game
        # Simple implementation: random bracket, everyone gets 3 games

        rng.shuffle(event_teams)
        # Round 1 pairs (4 games, day 1)
        r1_pairs = [
            (event_teams[0], event_teams[1]),
            (event_teams[2], event_teams[3]),
            (event_teams[4], event_teams[5]),
            (event_teams[6], event_teams[7]),
        ]
        # Round 2 pairs (4 games, day 2) - winners vs winners, losers vs losers (shuffled)
        r2_pairs = [
            (event_teams[0], event_teams[2]),
            (event_teams[4], event_teams[6]),
            (event_teams[1], event_teams[3]),
            (event_teams[5], event_teams[7]),
        ]
        # Round 3 pairs (4 games, day 3)
        r3_pairs = [
            (event_teams[0], event_teams[4]),
            (event_teams[2], event_teams[6]),
            (event_teams[1], event_teams[5]),
            (event_teams[3], event_teams[7]),
        ]

        # Check weekly limits for all teams across all 3 days
        # If any team can't fit all 3 games, skip this event
        can_fit = True
        for team in event_teams:
            for d in round_dates:
                if not calendar.can_play(team["name"], d, max_per_week=2):
                    can_fit = False
                    break
            if not can_fit:
                break
        if not can_fit:
            continue

        # Place all games
        for pairs, d, round_num in [(r1_pairs, round_dates[0], 1),
                                     (r2_pairs, round_dates[1], 2),
                                     (r3_pairs, round_dates[2], 3)]:
            for game_num, (home, away) in enumerate(pairs):
                calendar.add_noncon_game(
                    d, home, away,
                    is_neutral=True, neutral_site=site_key,
                    event_name=event_name, event_round=round_num,
                    series_id=f"MARQUEE_{site_key}_{year}_R{round_num}G{game_num+1}"
                )

        for team in event_teams:
            committed.add(team["name"])


# ---------------------------------------------------------------------------
# PHASE 1b: REGULAR 8-TEAM NEUTRAL EVENTS
# 10 events, 8 teams, 3 games each over 2-3 days.
# Power + high_major + strong mid_major. Neutral (non-resort) sites.
# ---------------------------------------------------------------------------

def _place_8team_events(calendar, all_programs, year, committed, rng):
    """Place 10 regular 8-team neutral site tournaments."""
    from neutral_sites import get_schedulable_sites

    schedulable = get_schedulable_sites()
    sites       = [(k, s) for k, s in schedulable if s["tier"] in ("marquee", "major", "mid")]
    rng.shuffle(sites)

    eligible = []
    for p in all_programs:
        if p["name"] in committed:
            continue
        tier     = get_conference_tier(p["conference"])["tier"]
        prestige = p.get("prestige_current", 30)
        if tier in ("power", "high_major"):
            eligible.append(p)
        elif tier in ("mid_major", "low_major") and prestige >= 40:
            eligible.append(p)

    w             = calendar.windows
    num_events    = 10
    # Spread across first 5 weeks of non-con window
    event_offsets = [4, 5, 7, 8, 10, 11, 14, 15, 18, 19]

    for event_idx in range(min(num_events, len(sites))):
        offset       = event_offsets[event_idx % len(event_offsets)]
        base_date    = w["noncon_start"] + timedelta(days=offset)
        site_key, sd = sites[event_idx % len(sites)]
        event_name   = f"{sd['city']} Invitational"

        round_dates = [base_date + timedelta(days=i) for i in range(2)]

        if any(calendar.is_blackout(d) for d in round_dates):
            continue
        if any(not calendar.is_noncon_window(d) for d in round_dates):
            continue

        event_teams = _pick_event_field(eligible, 8, committed, rng)
        if len(event_teams) < 8:
            continue

        # Check weekly limits
        can_fit = True
        for team in event_teams:
            for d in round_dates:
                if not calendar.can_play(team["name"], d, max_per_week=2):
                    can_fit = False
                    break
            if not can_fit:
                break
        if not can_fit:
            continue

        rng.shuffle(event_teams)
        # Day 1: 4 games (semifinals)
        # Day 2: 4 games (finals + consolation)
        r1_pairs = [(event_teams[i*2], event_teams[i*2+1]) for i in range(4)]
        r2_pairs = [
            (event_teams[0], event_teams[2]),
            (event_teams[4], event_teams[6]),
            (event_teams[1], event_teams[3]),
            (event_teams[5], event_teams[7]),
        ]

        for pairs, d, round_num in [(r1_pairs, round_dates[0], 1),
                                     (r2_pairs, round_dates[1], 2)]:
            for game_num, (home, away) in enumerate(pairs):
                calendar.add_noncon_game(
                    d, home, away,
                    is_neutral=True, neutral_site=site_key,
                    event_name=event_name, event_round=round_num,
                    series_id=f"EIGHT_{site_key}_{year}_R{round_num}G{game_num+1}"
                )

        # Teams get 2 games from 8-team event (not 3 -- only 2 days)
        for team in event_teams:
            committed.add(team["name"])


# ---------------------------------------------------------------------------
# PHASE 1c: 4-TEAM MINI TOURNAMENTS
# 15 events, 4 teams, 2 games each over 2 days.
# Primarily low/mid major. Non-resort neutral sites.
# ---------------------------------------------------------------------------

def _place_mini_tournaments(calendar, all_programs, year, committed, rng):
    """Place 15 four-team mini tournaments."""
    from neutral_sites import get_schedulable_sites

    schedulable = get_schedulable_sites()
    sites       = [(k, s) for k, s in schedulable if s["tier"] in ("mid", "small")]
    rng.shuffle(sites)

    eligible = []
    for p in all_programs:
        if p["name"] in committed:
            continue
        tier = get_conference_tier(p["conference"])["tier"]
        if tier in ("mid_major", "low_major", "floor_conf"):
            eligible.append(p)
        elif tier == "high_major" and p.get("prestige_current", 30) < 55:
            eligible.append(p)

    w          = calendar.windows
    num_events = 15
    # Spread through first 3 weeks of November -- 2-day blocks
    event_offsets = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 1, 3, 5, 7]

    for event_idx in range(min(num_events, len(sites), len(eligible) // 4)):
        offset    = event_offsets[event_idx % len(event_offsets)]
        base_date = w["noncon_start"] + timedelta(days=offset)
        site_key, sd = sites[event_idx % len(sites)]
        event_name   = f"{sd['city']} Classic"

        round_dates = [base_date + timedelta(days=i) for i in range(2)]

        if any(calendar.is_blackout(d) for d in round_dates):
            continue
        if any(not calendar.is_noncon_window(d) for d in round_dates):
            continue

        event_teams = _pick_event_field(eligible, 4, committed, rng)
        if len(event_teams) < 4:
            continue

        can_fit = True
        for team in event_teams:
            for d in round_dates:
                if not calendar.can_play(team["name"], d, max_per_week=2):
                    can_fit = False
                    break
            if not can_fit:
                break
        if not can_fit:
            continue

        rng.shuffle(event_teams)
        # Day 1: 2 semis
        # Day 2: final + consolation
        r1_pairs = [(event_teams[0], event_teams[1]), (event_teams[2], event_teams[3])]
        r2_pairs = [(event_teams[0], event_teams[2]), (event_teams[1], event_teams[3])]

        for pairs, d, round_num in [(r1_pairs, round_dates[0], 1),
                                     (r2_pairs, round_dates[1], 2)]:
            for game_num, (home, away) in enumerate(pairs):
                calendar.add_noncon_game(
                    d, home, away,
                    is_neutral=True, neutral_site=site_key,
                    event_name=event_name, event_round=round_num,
                    series_id=f"MINI_{site_key}_{year}_R{round_num}G{game_num+1}"
                )

        for team in event_teams:
            committed.add(team["name"])


# ---------------------------------------------------------------------------
# FIELD PICKER (used by all tournament placers)
# No two teams from same conference. Prestige-weighted. Not already committed.
# ---------------------------------------------------------------------------

def _pick_event_field(eligible, size, already_committed, rng):
    """
    Pick `size` teams from eligible pool.
    - Conference diversity: no two teams from same conference
    - Not already committed to another event
    - Prestige-weighted
    Returns list of program dicts (may be < size if pool too small).
    """
    available  = [p for p in eligible if p["name"] not in already_committed]
    weights    = [max(1, p.get("prestige_current", 30)) for p in available]
    total_w    = sum(weights) or 1

    selected   = []
    used_confs = set()
    pool       = list(zip(weights, available))

    attempts = 0
    while len(selected) < size and pool and attempts < len(available) * 4:
        attempts += 1
        total = sum(w for w, _ in pool)
        if total <= 0:
            break
        probs = [w / total for w, _ in pool]
        idx   = rng.choices(range(len(pool)), weights=probs, k=1)[0]
        w, team = pool[idx]

        if team["conference"] in used_confs:
            continue

        selected.append(team)
        used_confs.add(team["conference"])
        pool.pop(idx)

    return selected


# ---------------------------------------------------------------------------
# PHASE 2: SUPPLY-DEMAND MATCHING
#
# KEY INSIGHT: Floor conf teams don't schedule -- they get scheduled.
# Power programs post home slots. Floor conf fills them.
# Road cap enforced at POSTING time so Vermont doesn't get drafted
# as away team 12 times before its own scheduler runs.
#
# Pass order:
#   A) Match floor_conf road supply to power/high_major home demand
#   B) Match remaining home/away/neutral for all programs by tier
#   C) Fulfill cross-year obligations
# ---------------------------------------------------------------------------

def _match_standalone_games(calendar, all_programs, year, new_obligations, rng):
    """Phase 2: Supply-demand matching for standalone non-con games."""

    noncon_dates = calendar.get_noncon_dates()
    prog_map     = {p["name"]: p for p in all_programs}

    # Pre-calculate conference game counts (actual games scheduled, not estimates)
    conf_counts = {}
    for p in all_programs:
        conf_counts[p["name"]] = len(calendar.get_team_schedule(p["name"], game_type="conference"))

    def target(p):
        return get_noncon_target(p["conference"], conf_counts.get(p["name"], 18))

    def slots_left(p):
        return max(0, target(p) - _noncon_count(calendar, p["name"]))

    def roads_left(p):
        profile = get_scheduling_profile(p)
        return max(0, profile["max_road_games"] - _road_count(calendar, p["name"]))

    # --- PASS A: Floor conf road supply matched to power home demand ---
    # Find floor_conf teams that need road games
    floor_travelers = [p for p in all_programs
                       if get_conference_tier(p["conference"])["tier"] == "floor_conf"
                       and slots_left(p) > 0]

    # Find power/high_major programs that still have home slots open
    power_hosts = [p for p in all_programs
                   if get_conference_tier(p["conference"])["tier"] in ("power", "high_major")
                   and slots_left(p) > 0]

    # Shuffle for variety
    rng.shuffle(floor_travelers)
    rng.shuffle(power_hosts)

    for traveler in floor_travelers:
        if slots_left(traveler) <= 0:
            continue
        if roads_left(traveler) <= 0:
            continue

        # How many home games does this floor_conf team want?
        profile        = get_scheduling_profile(traveler)
        home_target    = rng.randint(0, profile.get("home_target_max", 2))
        current_home   = _noncon_count(calendar, traveler["name"]) - _road_count(calendar, traveler["name"])
        wants_road     = slots_left(traveler) - max(0, home_target - current_home)

        if wants_road <= 0:
            continue

        # Geographic pool: floor_conf teams go wherever they're paid
        # No geographic restriction -- Prairie View flies to Illinois
        geo_pool = _build_geo_weighted_pool(traveler, power_hosts, rng)

        roads_placed = 0
        for host in geo_pool:
            if roads_placed >= wants_road:
                break
            if slots_left(traveler) <= 0:
                break
            if slots_left(host) <= 0:
                continue
            if host["name"] in _get_scheduled_opponents(calendar, traveler["name"]):
                continue

            d = _find_date(calendar, host["name"], traveler["name"], noncon_dates)
            if d is None:
                continue

            calendar.add_noncon_game(d, host, traveler, is_neutral=False,
                                     series_id=make_series_id(host["name"], traveler["name"], year))
            roads_placed += 1

    # --- PASS B: Remaining home/road/neutral for all programs ---
    # Sort by tier then aggression -- power posts first
    sorted_programs = sorted(
        all_programs,
        key=lambda p: (
            _TIER_ORDER.get(get_conference_tier(p["conference"])["tier"], 5),
            -p.get("scheduling_aggression", 5)
        )
    )

    # Fulfill cross-year obligations first (they take priority over fresh scheduling)
    _fulfill_obligations(calendar, all_programs, year, noncon_dates, new_obligations, rng)

    for program in sorted_programs:
        if slots_left(program) <= 0:
            continue

        conf_tier  = get_conference_tier(program["conference"])["tier"]
        prestige   = program.get("prestige_current", 30)
        aggression = program.get("scheduling_aggression", 5)
        profile    = get_scheduling_profile(program)

        # Calculate how many home, road, neutral slots this program still wants
        current_total = _noncon_count(calendar, program["name"])
        current_road  = _road_count(calendar, program["name"])
        remaining     = slots_left(program)

        if conf_tier == "floor_conf":
            # Floor conf: fill remaining with road trips (already handled mostly by Pass A)
            # Add home games up to home_target_max if slots remain
            home_max   = profile.get("home_target_max", 2)
            home_used  = current_total - current_road
            home_open  = max(0, home_max - home_used)

            # Home games: host any non-floor-conf team nearby
            if home_open > 0:
                home_pool = [
                    p for p in all_programs
                    if p["name"] != program["name"]
                    and p["conference"] != program["conference"]
                    and p["name"] not in _get_scheduled_opponents(calendar, program["name"])
                    and slots_left(p) > 0
                    and get_conference_tier(p["conference"])["tier"] in ("low_major", "mid_major")
                ]
                geo_pool = _build_geo_weighted_pool(program, home_pool, rng)
                for opp in geo_pool:
                    if home_open <= 0 or slots_left(program) <= 0:
                        break
                    d = _find_date(calendar, program["name"], opp["name"], noncon_dates)
                    if d:
                        calendar.add_noncon_game(d, program, opp, is_neutral=False,
                                                 series_id=make_series_id(program["name"], opp["name"], year))
                        home_open -= 1

            # Remaining slots: road trips to power programs with open home slots
            road_open = slots_left(program)
            if road_open > 0 and roads_left(program) > 0:
                road_pool = [
                    p for p in all_programs
                    if p["name"] != program["name"]
                    and p["conference"] != program["conference"]
                    and p["name"] not in _get_scheduled_opponents(calendar, program["name"])
                    and slots_left(p) > 0
                    and get_conference_tier(p["conference"])["tier"] in ("power", "high_major", "mid_major")
                ]
                geo_pool = _build_geo_weighted_pool(program, road_pool, rng)
                for opp in geo_pool:
                    if slots_left(program) <= 0 or roads_left(program) <= 0:
                        break
                    d = _find_date(calendar, opp["name"], program["name"], noncon_dates)
                    if d:
                        calendar.add_noncon_game(d, opp, program, is_neutral=False,
                                                 series_id=make_series_id(opp["name"], program["name"], year))

            continue

        # --- Power, high_major, mid_major, low_major ---
        # Build a demand profile: what mix of home/neutral/road does this program want?
        home_games, neutral_games, road_games = _build_demand(
            program, remaining, conf_tier, aggression, prestige, current_road, profile, rng
        )

        # HOME GAMES
        home_candidates = _candidate_pool_home(program, all_programs, conf_tier, prestige, calendar)
        geo_pool = _build_geo_weighted_pool(program, home_candidates, rng)
        homes_placed = 0
        for opp in geo_pool:
            if homes_placed >= home_games or slots_left(program) <= 0:
                break
            if slots_left(opp) <= 0:
                continue
            d = _find_date(calendar, program["name"], opp["name"], noncon_dates)
            if d:
                calendar.add_noncon_game(d, program, opp, is_neutral=False,
                                         series_id=make_series_id(program["name"], opp["name"], year))
                # Create return obligation for peer matchups
                p_gap = abs(prestige - opp.get("prestige_current", 30))
                if p_gap <= 15 and conf_tier in ("power", "high_major"):
                    sid = make_series_id(program["name"], opp["name"], year)
                    add_obligation(opp, program["name"], 0, 1, year + 1, sid + "_RET")
                    new_obligations.append((opp["name"], program["name"], year + 1))
                homes_placed += 1

        # NEUTRAL GAMES
        if neutral_games > 0 and profile.get("neutral_appetite", False):
            from neutral_sites import get_schedulable_sites
            neutral_sites = get_schedulable_sites()
            rng.shuffle(neutral_sites)

            neutral_pool = [
                p for p in all_programs
                if p["name"] != program["name"]
                and p["conference"] != program["conference"]
                and p["name"] not in _get_scheduled_opponents(calendar, program["name"])
                and slots_left(p) > 0
                and abs(prestige - p.get("prestige_current", 30)) <= 25
            ]
            geo_pool = _build_geo_weighted_pool(program, neutral_pool, rng)

            neutrals_placed = 0
            for opp in geo_pool:
                if neutrals_placed >= neutral_games or slots_left(program) <= 0:
                    break
                if slots_left(opp) <= 0:
                    continue
                site_key = neutral_sites[neutrals_placed % len(neutral_sites)][0] if neutral_sites else None
                d = _find_date(calendar, program["name"], opp["name"], noncon_dates)
                if d:
                    calendar.add_noncon_game(d, program, opp, is_neutral=True,
                                             neutral_site=site_key,
                                             series_id=make_series_id(program["name"], opp["name"], year))
                    neutrals_placed += 1

        # ROAD GAMES (power/high_major only travel to peers or paycheck hosts)
        roads_available = min(road_games, roads_left(program))
        if roads_available > 0:
            road_pool = _candidate_pool_road(program, all_programs, conf_tier, prestige, calendar)
            geo_pool  = _build_geo_weighted_pool(program, road_pool, rng)
            roads_placed = 0
            for opp in geo_pool:
                if roads_placed >= roads_available or slots_left(program) <= 0:
                    break
                if slots_left(opp) <= 0:
                    continue
                if not can_travel_to(program, opp):
                    continue
                d = _find_date(calendar, opp["name"], program["name"], noncon_dates)
                if d:
                    calendar.add_noncon_game(d, opp, program, is_neutral=False,
                                             series_id=make_series_id(opp["name"], program["name"], year))
                    roads_placed += 1


def _build_demand(program, slots_remaining, conf_tier, aggression, prestige,
                  current_road, profile, rng):
    """
    Returns (home_games, neutral_games, road_games) for this program's remaining slots.
    Power conference: 60%+ home enforced.
    """
    if conf_tier == "power":
        min_home = max(1, int(slots_remaining * 0.60))
    elif conf_tier == "high_major":
        min_home = max(1, int(slots_remaining * 0.50))
    else:
        min_home = max(0, int(slots_remaining * 0.40))

    max_new_road = max(0, profile["max_road_games"] - current_road)

    if aggression >= 9:
        road_want    = min(max_new_road, rng.randint(1, 3))
        neutral_want = rng.randint(0, 2) if profile.get("neutral_appetite") else 0
    elif aggression >= 7:
        road_want    = min(max_new_road, rng.randint(0, 2))
        neutral_want = rng.randint(0, 1) if profile.get("neutral_appetite") else 0
    elif aggression >= 5:
        road_want    = min(max_new_road, rng.randint(0, 1))
        neutral_want = rng.randint(0, 1) if profile.get("neutral_appetite") else 0
    else:
        road_want    = 0
        neutral_want = 0

    home_want = max(min_home, slots_remaining - road_want - neutral_want)
    # Re-cap so total == slots_remaining
    road_want    = slots_remaining - home_want - neutral_want
    if road_want < 0:
        neutral_want += road_want
        road_want = 0
    if neutral_want < 0:
        home_want += neutral_want
        neutral_want = 0

    return max(0, home_want), max(0, neutral_want), max(0, road_want)


def _candidate_pool_home(program, all_programs, conf_tier, prestige, calendar):
    """Build home opponent candidate pool with prestige-appropriate filtering."""
    scheduled = _get_scheduled_opponents(calendar, program["name"])

    candidates = []
    for p in all_programs:
        if p["name"] == program["name"]:
            continue
        if p["conference"] == program["conference"]:
            continue
        if p["name"] in scheduled:
            continue

        opp_prestige = p.get("prestige_current", 30)
        opp_tier     = get_conference_tier(p["conference"])["tier"]

        # Power programs can host anyone. Floor_conf doesn't host power.
        # Rough prestige filter: home team can host up to prestige+30 above
        if conf_tier in ("power", "high_major"):
            if opp_prestige > prestige + 30:
                continue  # Don't schedule equal/better teams as home cupcakes
        elif conf_tier in ("mid_major", "low_major"):
            if opp_prestige > prestige + 20:
                continue

        candidates.append(p)

    return candidates


def _candidate_pool_road(program, all_programs, conf_tier, prestige, calendar):
    """Build road opponent pool: peer-to-peer only for power/high_major."""
    scheduled = _get_scheduled_opponents(calendar, program["name"])

    candidates = []
    for p in all_programs:
        if p["name"] == program["name"]:
            continue
        if p["conference"] == program["conference"]:
            continue
        if p["name"] in scheduled:
            continue

        opp_prestige = p.get("prestige_current", 30)
        opp_tier     = get_conference_tier(p["conference"])["tier"]

        # Power/high_major road games are peer-to-peer
        if conf_tier in ("power", "high_major"):
            if opp_prestige < prestige - 25:
                continue  # Don't make power teams travel to weak programs
            if opp_tier == "floor_conf":
                continue  # Hard rule: never

        if not can_travel_to(program, p):
            continue

        candidates.append(p)

    return candidates


# ---------------------------------------------------------------------------
# FULFILL CROSS-YEAR OBLIGATIONS
# ---------------------------------------------------------------------------

def _fulfill_obligations(calendar, all_programs, year, noncon_dates, new_obligations, rng):
    """Schedule games from existing cross-season return trip obligations."""
    prog_map         = {p["name"]: p for p in all_programs}
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
                d = _find_date(calendar, program["name"], opponent["name"], noncon_dates)
                if d:
                    calendar.add_noncon_game(d, program, opponent, is_neutral=False,
                                             series_id=series_id)

            # Schedule away games owed
            for _ in range(ob["games_away"]):
                if not can_travel_to(program, opponent):
                    continue
                d = _find_date(calendar, opponent["name"], program["name"], noncon_dates)
                if d:
                    calendar.add_noncon_game(d, opponent, program, is_neutral=False,
                                             series_id=series_id)

            processed_series.add(series_id)

        # Remove fulfilled obligations
        program["scheduling_obligations"] = [
            ob for ob in get_obligations(program)
            if ob["games_at_home"] > 0 or ob["games_away"] > 0
        ]


# ---------------------------------------------------------------------------
# PHASE 3: GAP FILL
# Anyone still short of target gets filled with whatever's available.
# Home games preferred. Floor_conf gets road games.
# ---------------------------------------------------------------------------

def _fill_gaps(calendar, all_programs, year, rng):
    """Phase 3: Fill remaining slots for any team still short of target."""

    noncon_dates = calendar.get_noncon_dates()
    prog_map     = {p["name"]: p for p in all_programs}

    conf_counts = {}
    for p in all_programs:
        conf_counts[p["name"]] = len(calendar.get_team_schedule(p["name"], game_type="conference"))

    def target(p):
        return get_noncon_target(p["conference"], conf_counts.get(p["name"], 18))

    def slots_left(p):
        return max(0, target(p) - _noncon_count(calendar, p["name"]))

    # Sort: programs with most remaining slots first (avoid leaving anyone stranded)
    sorted_progs = sorted(all_programs, key=lambda p: -slots_left(p))

    for program in sorted_progs:
        remaining = slots_left(program)
        if remaining <= 0:
            continue

        conf_tier = get_conference_tier(program["conference"])["tier"]
        prestige  = program.get("prestige_current", 30)

        # Build a broad candidate pool for gap fill
        scheduled = _get_scheduled_opponents(calendar, program["name"])
        candidates = [
            p for p in all_programs
            if p["name"] != program["name"]
            and p["conference"] != program["conference"]
            and p["name"] not in scheduled
            and slots_left(p) > 0
        ]

        if not candidates:
            continue

        geo_pool = _build_geo_weighted_pool(program, candidates, rng)

        for opp in geo_pool:
            if slots_left(program) <= 0:
                break

            opp_tier = get_conference_tier(opp["conference"])["tier"]

            # Determine home/away for this pairing
            if conf_tier == "floor_conf":
                # Floor conf goes on road
                if not can_travel_to(program, opp):
                    continue
                if _road_count(calendar, program["name"]) >= get_scheduling_profile(program)["max_road_games"]:
                    # Try hosting instead
                    if opp_tier in ("low_major", "mid_major"):
                        d = _find_date(calendar, program["name"], opp["name"], noncon_dates)
                        if d:
                            calendar.add_noncon_game(d, program, opp, is_neutral=False,
                                                     series_id=make_series_id(program["name"], opp["name"], year))
                    continue
                d = _find_date(calendar, opp["name"], program["name"], noncon_dates)
                if d:
                    calendar.add_noncon_game(d, opp, program, is_neutral=False,
                                             series_id=make_series_id(opp["name"], program["name"], year))
            else:
                # Everyone else: home games preferred in gap fill
                d = _find_date(calendar, program["name"], opp["name"], noncon_dates)
                if d and slots_left(opp) > 0:
                    calendar.add_noncon_game(d, program, opp, is_neutral=False,
                                             series_id=make_series_id(program["name"], opp["name"], year))


# ---------------------------------------------------------------------------
# ESTIMATE CONF GAMES (used by season.py if called separately)
# ---------------------------------------------------------------------------

def _estimate_conf_games(all_programs, calendar=None):
    """Returns actual conference games per team from calendar."""
    result = {}
    if calendar is not None:
        for p in all_programs:
            conf_slots = calendar.get_team_schedule(p["name"], game_type="conference")
            result[p["name"]] = len(conf_slots)
    else:
        for p in all_programs:
            fmt = get_conference_format(p["conference"])
            result[p["name"]] = fmt.get("conf_games", 18)
    return result
