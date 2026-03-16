import random
from game_engine import simulate_game
from program import (create_program, record_game_result, apply_gravity_pull,
                     update_prestige_for_results, get_record_string, prestige_grade,
                     apply_conference_tier_pressure, recalculate_gravity_pull_rate)
from programs_data import (build_all_d1_programs, get_conference_ceiling,
                            get_conference_floor)
from recruiting import generate_recruiting_class, print_class_summary
from recruiting_offers import generate_offers, calculate_interest_scores
from recruiting_commitments import resolve_full_recruiting_cycle, print_cycle_summary
from lifecycle import advance_season, print_lifecycle_summary
from conference_tournament import simulate_all_conference_tournaments
from tournament import simulate_ncaa_tournament, print_tournament_summary
from transfer_portal import run_transfer_portal, print_portal_summary
from coaching_carousel import run_coaching_carousel, print_carousel_report
from program import update_stale_meter, update_coaching_capital

# -----------------------------------------
# NET RANKING SYSTEM
# Quadrant-based strength of schedule ranking.
# Mirrors the NCAA NET formula using prestige instead of NET rank.
#
# QUADRANT DEFINITIONS (opponent prestige by game location):
#   Q1: Home vs 75+,  Neutral vs 65+,  Away vs 55+
#   Q2: Home vs 50-74, Neutral vs 40-64, Away vs 30-54
#   Q3: Home vs 25-49, Neutral vs 20-39, Away vs 15-29
#   Q4: Everything else
#
# RANKING SCORE:
#   win_pct * 0.35
#   + Q1 wins * 4.0   (gold)
#   + Q2 wins * 1.5
#   + Q3 wins * 0.5
#   + Q4 wins * 0.1   (barely counts)
#   - Q1 loss * 0.5   (forgivable)
#   - Q2 loss * 1.5
#   - Q3 loss * 3.0   (damaging)
#   - Q4 loss * 6.0   (devastating)
#   + avg_opp_prestige / 100 * 0.20
# -----------------------------------------

# Quadrant prestige thresholds by location
_Q_HOME    = [(75, 1), (50, 2), (25, 3)]   # (min_prestige, quadrant)
_Q_NEUTRAL = [(65, 1), (40, 2), (20, 3)]
_Q_AWAY    = [(55, 1), (30, 2), (15, 3)]

# Score weights
_NET_WIN_PCT_WEIGHT   = 0.35
_NET_OPP_WEIGHT       = 0.20
_NET_Q_WIN_WEIGHTS    = {1: 4.0, 2: 1.5, 3: 0.5, 4: 0.1}
_NET_Q_LOSS_WEIGHTS   = {1: -0.5, 2: -1.5, 3: -3.0, 4: -6.0}


def _get_quadrant(opp_prestige, is_home, is_neutral=False):
    """Returns quadrant (1-4) for a game based on opponent prestige and location."""
    if is_neutral:
        thresholds = _Q_NEUTRAL
    elif is_home:
        thresholds = _Q_HOME
    else:
        thresholds = _Q_AWAY

    for min_p, quad in thresholds:
        if opp_prestige >= min_p:
            return quad
    return 4


def calculate_net_score(program, all_programs):
    """
    Calculates a program's NET-style ranking score for the current season.

    Uses season_results on the program dict (set during simulate_conference_season).
    Opponent prestige is looked up live from all_programs -- valid because
    prestige doesn't change during the season, only in the post-season pipeline.

    Returns a float. Higher = better ranking.
    """
    results = program.get("season_results", [])
    if not results:
        return 0.0

    prog_lookup = {p["name"]: p for p in all_programs}

    wins   = 0
    losses = 0
    q_wins   = {1: 0, 2: 0, 3: 0, 4: 0}
    q_losses = {1: 0, 2: 0, 3: 0, 4: 0}
    opp_prestige_sum = 0
    games_with_opp   = 0

    for result in results:
        opp_name = result.get("opponent", "")
        opp      = prog_lookup.get(opp_name)

        if opp is None:
            continue

        opp_prestige      = opp.get("prestige_current", 30)
        is_home           = result.get("is_home", True)
        won               = result.get("won", False)

        quad = _get_quadrant(opp_prestige, is_home)

        if won:
            wins += 1
            q_wins[quad] += 1
        else:
            losses += 1
            q_losses[quad] += 1

        opp_prestige_sum += opp_prestige
        games_with_opp   += 1

    total    = wins + losses
    win_pct  = wins / max(1, total)
    avg_opp  = opp_prestige_sum / max(1, games_with_opp)

    score = (win_pct * _NET_WIN_PCT_WEIGHT)
    for q in range(1, 5):
        score += q_wins[q]   * _NET_Q_WIN_WEIGHTS[q]
        score += q_losses[q] * _NET_Q_LOSS_WEIGHTS[q]
    score += (avg_opp / 100.0) * _NET_OPP_WEIGHT

    return score

# -----------------------------------------
# COLLEGE HOOPS SIM -- Season Calendar v0.7
# Full world simulation -- all 326 D1 programs
#
# v0.5 CHANGES -- Prestige System Overhaul:
#
#   CHANGE 3: apply_gravity_drift() slowed significantly.
#     - Min 5 seasons history before drift activates (was 3).
#     - Drift rate 1.5 (was 3.0). Annual cap +-0.75 (was +-1.5).
#     - Anchor is geological. One Cinderella run doesn't move it.
#
#   CHANGE 4: apply_universe_gravity() -- world population correction.
#     Bottom-heavy pyramid target distribution. Subtle whisper strength.
#     Conference floors always protected as hard stop.
#
#   CHANGE 5: apply_conference_tier_pressure() in pipeline.
#
# v0.6 CHANGES -- Non-conference double-counting fix:
#
#   ROOT CAUSE OF RUNAWAY PRESTIGE BUG:
#     build_non_conference_schedule() was alternating home/away and
#     calling record_game_result() on BOTH teams. This meant Texas
#     (Big 12) accumulated wins as an away team in every other
#     conference's simulation. By season end, Texas had 150+ games
#     recorded and update_prestige_for_results() saw a massive win
#     total -- gaining 28 prestige points in a single season.
#
#   FIX: Non-conference matchups always have the conference's own
#     program as HOME. record_game_result() is only called for a
#     team if they belong to the conference currently being simulated.
#     Away non-conference opponents get their result recorded when
#     their OWN conference simulation runs.
#     Called as LAST prestige step each season, after gravity drift.
#     Conference identity enforced via soft ceiling/floor.
#
# SEASON PRESTIGE PIPELINE ORDER (per program per season):
#   1. update_prestige_for_results()    -- performance delta, hard cap
#   2. apply_gravity_pull()             -- pull toward historical anchor
#   3. apply_gravity_drift()            -- slowly adjust anchor itself
#   4. apply_conference_tier_pressure() -- conf ceiling/floor enforcement
#   5. apply_universe_gravity()         -- world population correction
# -----------------------------------------

# -----------------------------------------
# UNIVERSE GRAVITY
# Bottom-heavy pyramid -- reflects real D1 population shape
# ~330 programs total
#
# 6 tiers:
#   blue_blood:  95-100  target  4  -- Kentucky/Duke/Kansas/UNC tier
#   elite:       79-94   target 18  -- knocking on blue blood door
#   high_major:  59-78   target 45  -- established power programs
#   mid_major:   39-58   target 85  -- competitive mid-majors
#   low_major:   21-38   target 90  -- lower tier programs
#   floor:        1-20   target 88  -- bottom of the barrel
#
# Total: 4+18+45+85+90+88 = 330
# -----------------------------------------

UNIVERSE_TIERS = [
    ("blue_blood",    95.0, 100.0,   4),
    ("elite",         79.0,  94.95, 18),
    ("strong",        59.0,  78.95, 45),
    ("average",       39.0,  58.95, 85),
    ("below_average", 21.0,  38.95, 90),
    ("poor",           1.0,  20.95, 88),
]

UNIVERSE_NUDGE_NONE     = 0.0
UNIVERSE_NUDGE_SMALL    = 0.25
UNIVERSE_NUDGE_MODERATE = 0.50
UNIVERSE_NUDGE_STRONG   = 0.80

# Blended gravity earn period.
# New programs use conference floor as gravity anchor for this many seasons,
# then blend linearly toward their earned prestige_gravity over the same
# number of seasons again. Full earned gravity kicks in at 2x this value.
# Raise this if seeded prestiges are unreliable (e.g. early sim runs).
# Lower this if you're loading curated world files with trusted gravity values.
GRAVITY_EARN_SEASONS = 5

# Auto-correction thresholds
# If a tier is below AUTO_CORRECT_LOW, pull programs up to hit AUTO_CORRECT_TARGET
# If a tier is above AUTO_CORRECT_HIGH, push programs down to hit AUTO_CORRECT_TARGET
AUTO_CORRECT_LOW    = 0.85   # below 85% triggers upward pull (was 0.75)
AUTO_CORRECT_HIGH   = 1.20   # above 120% triggers downward push (was 1.25)
AUTO_CORRECT_TARGET = 0.90   # correct to 90% of target (was 0.80)

# Smooth drift caps -- REPLACES hard boundary teleport.
# Instead of snapping programs to exact tier boundaries,
# we nudge them by at most this many points per season.
# Programs drift to the right tier over 2-4 seasons rather than jumping.
# Tune here if distribution is correcting too slowly or too fast.
AUTO_CORRECT_UP_CAP   = 5.0   # max points moved upward per program per season
AUTO_CORRECT_DOWN_CAP = 4.0   # max points moved downward per program per season
# Fraction of gap to boundary used as the nudge size.
# 0.5 = move 50% of the remaining gap each season (geometric approach).
AUTO_CORRECT_GAP_FRAC = 0.50

# Blue blood identity pull -- programs above 95 get strong upward
# resistance to decline. Programs in 85-94 feel a weaker upward
# pull -- the "lurking" mechanic. One good season with high gravity
# snaps a struggling blue blood back toward their rightful tier.
BLUE_BLOOD_THRESHOLD    = 95
BLUE_BLOOD_PULL_UP      = 0.40   # per season for programs above 95
LURKING_THRESHOLD       = 85
LURKING_PULL_UP         = 0.15   # per season for programs 85-94

# Blue blood throne -- maximum seats at the table
BLUE_BLOOD_MAX_SEATS    = 4

# Tenure tiers -- consecutive blue blood seasons before gravity is protected
# (seasons_threshold, label, gravity_protection_pct)
# protection_pct = how much gravity erosion is blocked
#   0.95 = dynasty tier, anchor barely moves even through sustained losing
#   0.00 = newcomer, no protection
BLUE_BLOOD_TENURE_TIERS = [
    (30, "dynasty",     0.95),
    (16, "entrenched",  0.70),
    (6,  "established", 0.40),
    (0,  "newcomer",    0.00),
]

# Throne check push -- how hard the most vulnerable blue blood
# gets pushed down when the tier is overcrowded
# Overcrowded by 1: mild shove
# Overcrowded by 2: moderate push
# Overcrowded by 3+: hard push
THRONE_PUSH    = {1: -1.5, 2: -2.5}
THRONE_PUSH_MAX = -4.0

# Gravity drift annual cap by conference tier.
# Low major anchors are nearly geological -- a MEAC dynasty earns
# maybe +1.5 points of anchor movement over a decade, not +7.
# Power conference programs have more legitimate room to grow.
GRAVITY_DRIFT_CAP = {
    "power":      0.50,
    "high_major": 0.35,
    "mid_major":  0.25,
    "low_major":  0.15,
    "floor_conf": 0.10,
}
_DEFAULT_DRIFT_CAP = 0.25

# Conference identity pull -- active force toward conference floor.
# This is NOT a floor stop. It's gravity toward the conference's
# natural identity range, firing every season regardless of performance.
# Only floor_conf and low_major feel this force.
# Strength varies by where the program finished in their conference.
#
# floor_conf (SWAC/MEAC/NEC/WAC):
#   bottom third:  prestige pull -1.5/season, anchor erode -0.3/season
#   middle third:  prestige pull -0.8/season
#   top third:     prestige pull -0.2/season  (gravity never sleeps)
#
# low_major (Big South/Patriot/Southland/America East):
#   bottom third:  prestige pull -0.6/season, anchor erode -0.1/season
#   middle third:  prestige pull -0.3/season
#   top third:     prestige pull -0.1/season
IDENTITY_PULL = {
    "floor_conf": {
        "bottom": {"prestige": -1.5, "anchor": -0.3},
        "middle": {"prestige": -0.8, "anchor":  0.0},
        "top":    {"prestige": -0.2, "anchor":  0.0},
    },
    "low_major": {
        "bottom": {"prestige": -0.6, "anchor": -0.1},
        "middle": {"prestige": -0.3, "anchor":  0.0},
        "top":    {"prestige": -0.1, "anchor":  0.0},
    },
}


# -----------------------------------------
# BLUE BLOOD STATE
# -----------------------------------------

def _init_blue_blood_state(program):
    """Initialize blue_blood_state if not present."""
    if "blue_blood_state" not in program:
        program["blue_blood_state"] = {
            "seasons":           0,
            "legacy_credit":     0,
            "siege_count":       0,      # times pushed to the gate (94.9)
            "is_blue_blood":     False,
            "ever_blue_blood":   False,
            "tenure_tier":       "newcomer",
            "gravity_protected": False,
            "protection_pct":    0.0,
        }
    elif "siege_count" not in program["blue_blood_state"]:
        program["blue_blood_state"]["siege_count"] = 0
    elif "protection_pct" not in program["blue_blood_state"]:
        program["blue_blood_state"]["protection_pct"] = 0.0
    return program["blue_blood_state"]


def _get_tenure_tier(seasons):
    """Returns tenure label and gravity protection pct for given seasons."""
    for threshold, label, protection in BLUE_BLOOD_TENURE_TIERS:
        if seasons >= threshold:
            return label, protection
    return "newcomer", 0.0


def update_blue_blood_state(program):
    """
    Called each season after prestige pipeline.
    Tracks blue blood tenure and applies gravity protection.

    If a program falls out of blue blood territory:
      - seasons halved (legacy credit retained)
      - is_blue_blood set to False
      - gravity protection removed

    Gravity protection works by reducing how much the anchor
    can erode in a given season. A dynasty-tier blue blood's
    anchor barely moves even through years of losing -- the
    institutional weight of 30+ years of dominance.
    """
    state   = _init_blue_blood_state(program)
    current = program["prestige_current"]

    if current >= BLUE_BLOOD_THRESHOLD:
        # Entered or held blue blood status
        state["seasons"]       += 1
        state["is_blue_blood"]  = True
        state["ever_blue_blood"] = True
    else:
        # Fallen out
        if state["is_blue_blood"]:
            # Just fell out -- halve seasons, retain as legacy credit
            state["legacy_credit"] = state["seasons"] // 2
            state["seasons"]       = state["legacy_credit"]
        state["is_blue_blood"]  = False

    label, protection = _get_tenure_tier(state["seasons"])
    state["tenure_tier"]       = label
    state["gravity_protected"] = protection > 0

    # Apply gravity protection -- reduce anchor erosion proportionally
    # This is subtle: we don't directly change gravity here.
    # Instead we store the protection pct so apply_gravity_drift()
    # can use it to dampen downward drift.
    state["protection_pct"] = protection

    return program


def run_blue_blood_throne_check(all_programs, season_year, verbose=False):
    """
    The throne check. Hard cap: NEVER more than 4 blue bloods.

    If more than 4 programs are above 95, the most vulnerable are
    placed at exactly 94.9 -- just outside the gate. Not destroyed,
    just held back. They have to earn their way back in next season.

    SIEGE MECHANIC:
    Each time a program is placed at 94.9, their siege_count increments.
    Each siege attempt nudges their prestige_gravity upward slightly --
    the institution is building legitimacy through repeated challenges.
    After 6+ sieges, the program applies extra downward pressure on
    the weakest incumbent blue blood every season they sit at 94.9.
    This is how the barbarians eventually breach the gate.

    VULNERABILITY RANKING (most vulnerable = pushed out first):
      1. Lowest siege_count -- challengers go before veterans
      2. Lowest blue_blood_state.seasons -- newcomers before legacy
      3. Lowest prestige_gravity -- pretenders before true blue bloods
      4. Lowest prestige_current -- weakest form as final tiebreaker

    SIEGE PRESSURE ON INCUMBENTS:
    Programs sitting at 94.9 with siege_count >= 6 apply -0.15/season
    to the weakest incumbent's prestige_current. Multiple siegers
    stack. A coordinated siege from 3 programs = -0.45/season on
    the weakest blue blood -- eventually forcing them below 95.

    The absolute cap is enforced AFTER siege pressure, so if siege
    pressure drops an incumbent below 95 it opens a seat for the
    strongest challenger to claim.
    """
    # --- SIEGE PRESSURE ON INCUMBENTS ---
    # Programs sitting just outside the gate (94.5-94.9) with
    # high siege counts apply pressure to the weakest blue blood
    siegers = [p for p in all_programs
               if 94.5 <= p["prestige_current"] <= 94.95]

    blue_bloods = [p for p in all_programs
                   if p["prestige_current"] >= BLUE_BLOOD_THRESHOLD]

    if blue_bloods and siegers:
        # Find the most vulnerable incumbent
        def incumbent_vulnerability(p):
            state = p.get("blue_blood_state", {})
            return (state.get("seasons", 0) * 10) + p["prestige_gravity"]

        weakest = min(blue_bloods, key=incumbent_vulnerability)

        total_siege_pressure = 0.0
        for sieger in siegers:
            siege_state = sieger.get("blue_blood_state", {})
            siege_count = siege_state.get("siege_count", 0)
            if siege_count >= 6:
                total_siege_pressure -= 0.15

        if total_siege_pressure < 0:
            weakest_state = weakest.get("blue_blood_state", {})
            protection    = weakest_state.get("protection_pct", 0.0)
            effective_pressure = total_siege_pressure * (1.0 - protection)
            new_prestige = max(1, weakest["prestige_current"] + effective_pressure)
            weakest["prestige_current"] = round(new_prestige, 1)
            weakest["prestige_grade"]   = prestige_grade(weakest["prestige_current"])

            if verbose and effective_pressure < 0:
                print("  SIEGE PRESSURE: " + weakest["name"] +
                      " pressured to " + str(weakest["prestige_current"]) +
                      " by " + str(len([s for s in siegers
                          if s.get("blue_blood_state", {}).get("siege_count", 0) >= 6])) +
                      " siege(s)")

    # --- HARD CAP ENFORCEMENT ---
    # Recount after siege pressure (a blue blood may have fallen below 95)
    blue_bloods = [p for p in all_programs
                   if p["prestige_current"] >= BLUE_BLOOD_THRESHOLD]

    overcrowded = len(blue_bloods) - BLUE_BLOOD_MAX_SEATS

    if overcrowded <= 0:
        return all_programs

    # Rank by vulnerability -- most vulnerable first
    def vulnerability_score(p):
        state       = p.get("blue_blood_state", {})
        seasons     = state.get("seasons", 0)
        siege_count = state.get("siege_count", 0)
        gravity     = p["prestige_gravity"]
        current     = p["prestige_current"]
        # Lower score = more vulnerable
        # Siege count included -- a program that just stormed in
        # is more vulnerable than a long-siege program
        return (seasons * 10) + (siege_count * 2) + gravity + (current / 10)

    ranked = sorted(blue_bloods, key=vulnerability_score)

    # Hard cap -- push exactly to 94.9, no gradual nudge
    for i in range(overcrowded):
        if i >= len(ranked):
            break

        target = ranked[i]
        state  = _init_blue_blood_state(target)
        protection = state.get("protection_pct", 0.0)

        # Dynasty programs can resist being placed at the gate
        # but NEVER stay above 95 if there are more than 4
        # The gate is absolute -- protection just determines
        # how close to 95 they land (94.9 vs 93-94)
        if protection >= 0.95:
            # True dynasty -- nudged just below gate
            gate_position = 94.9
        elif protection >= 0.70:
            # Entrenched -- pushed slightly further back
            gate_position = 94.5
        elif protection >= 0.40:
            # Established -- pushed back meaningfully
            gate_position = 94.0
        else:
            # Newcomer or low-siege -- pushed to standard gate
            gate_position = 94.9

        target["prestige_current"] = gate_position
        target["prestige_grade"]   = prestige_grade(target["prestige_current"])

        # Increment siege count -- each confrontation builds legitimacy
        state["siege_count"] = state.get("siege_count", 0) + 1

        # Gravity nudge -- each siege attempt makes you more legitimate
        # Capped at a modest amount -- you still have to earn it on the court
        siege_gravity_bonus = min(0.3, state["siege_count"] * 0.05)
        new_gravity = min(100, target["prestige_gravity"] + siege_gravity_bonus)
        target["prestige_gravity"] = round(new_gravity, 1)

        if verbose:
            print("  THRONE: " + target["name"] +
                  " held at gate " + str(gate_position) +
                  " (tenure: " + str(state.get("seasons", 0)) +
                  " seasons, siege #" + str(state["siege_count"]) +
                  ", protection: " + str(round(protection * 100)) + "%)")

    # Final verification -- absolute guarantee
    for p in all_programs:
        if p["prestige_current"] >= BLUE_BLOOD_THRESHOLD:
            pass  # counted below

    final_count = sum(1 for p in all_programs
                      if p["prestige_current"] >= BLUE_BLOOD_THRESHOLD)
    if final_count > BLUE_BLOOD_MAX_SEATS:
        # Emergency fallback -- should never reach here but just in case
        overflow = sorted(
            [p for p in all_programs if p["prestige_current"] >= BLUE_BLOOD_THRESHOLD],
            key=vulnerability_score
        )
        for p in overflow[:final_count - BLUE_BLOOD_MAX_SEATS]:
            p["prestige_current"] = 94.9
            p["prestige_grade"]   = prestige_grade(94.9)

    return all_programs


# -----------------------------------------
# CONFERENCE IDENTITY PULL
# -----------------------------------------

def apply_conference_identity_pull(program, conf_finish_percentile):
    """
    Active gravity toward conference floor. Fires every season.
    Only affects floor_conf and low_major programs.

    Also handles blue blood upward resistance and lurking pull
    for programs in the 85-94 range.
    """
    from programs_data import get_conference_tier

    current  = program["prestige_current"]
    gravity  = program["prestige_gravity"]

    # --- BLUE BLOOD UPWARD RESISTANCE ---
    # Programs above 95: strong pull back up if they've fallen below
    # Programs in 85-94: weaker pull upward -- the "lurking" mechanic
    # This fires regardless of conference tier.
    if gravity >= BLUE_BLOOD_THRESHOLD:
        if current < BLUE_BLOOD_THRESHOLD:
            # Fallen blue blood -- gravity fights hard to restore them
            gap  = BLUE_BLOOD_THRESHOLD - current
            pull = min(BLUE_BLOOD_PULL_UP, gap * 0.08)
            program["prestige_current"] = round(min(100, current + pull), 1)
            program["prestige_grade"]   = prestige_grade(program["prestige_current"])
        return program

    if gravity >= LURKING_THRESHOLD:
        if current < gravity:
            # Lurking program below their gravity -- nudge upward
            gap  = gravity - current
            pull = min(LURKING_PULL_UP, gap * 0.03)
            program["prestige_current"] = round(min(100, current + pull), 1)
            program["prestige_grade"]   = prestige_grade(program["prestige_current"])
        return program

    # --- CONFERENCE IDENTITY PULL (floor_conf and low_major only) ---
    tier_obj = get_conference_tier(program["conference"])
    tier     = tier_obj["tier"]
    floor    = tier_obj["floor"]

    if tier not in IDENTITY_PULL:
        return program

    pull_table = IDENTITY_PULL[tier]

    if conf_finish_percentile < 0.33:
        pull = pull_table["bottom"]
    elif conf_finish_percentile < 0.67:
        pull = pull_table["middle"]
    else:
        pull = pull_table["top"]

    new_prestige = max(1, current + pull["prestige"])
    program["prestige_current"] = round(new_prestige, 1)
    program["prestige_grade"]   = prestige_grade(program["prestige_current"])

    if pull["anchor"] < 0:
        new_gravity = max(1, gravity + pull["anchor"])
        program["prestige_gravity"] = round(new_gravity, 1)

    return program


# -----------------------------------------
# CONFERENCE FINISH TRACKING
# -----------------------------------------

def calculate_conference_standings(conference_programs):
    """
    Calculates finish percentile for every program in the conference.
    1.0 = first place, 0.0 = last place.
    Stored on program as conf_finish_percentile.
    """
    n = len(conference_programs)
    if n < 2:
        for p in conference_programs:
            p["conf_finish_percentile"] = 0.5
        return

    ranked = sorted(
        conference_programs,
        key=lambda p: (p["conf_wins"], p["wins"]),
        reverse=True
    )

    for i, p in enumerate(ranked):
        p["conf_finish_percentile"] = round(1.0 - (i / (n - 1)), 3)


# -----------------------------------------
# SCHEDULE BUILDERS
# -----------------------------------------

# Target games per season
SEASON_GAME_TARGET = 30

# Conference games per team by conference size.
# Every team plays each opponent at least once.
# Remaining games filled by random second (or third) matchups.
# Minimum 14 conference games guaranteed.
def _conf_games_target(n):
    """Returns target conference games per team given n teams in conference."""
    if n <= 5:   return 16
    if n <= 6:   return 15
    if n <= 7:   return 14
    if n <= 8:   return 14
    if n <= 11:  return 18
    if n <= 17:  return 18
    return 20    # 18+ team conferences (ACC, Big Ten, Big 12)


def build_conference_schedule(programs):
    """
    Builds a realistic conference schedule hitting the target game count.

    Every team plays every other team at least once (single round-robin base).
    Remaining slots filled by randomly selected rematches until target is hit.
    For large conferences (18 teams, target 20), uses random selection of 20
    opponents without a full round-robin (not everyone plays everyone).

    Home/away: each matchup generates one home and one away game.
    Target conference games per team maintained within +/-1.
    """
    n      = len(programs)
    target = _conf_games_target(n)

    matchups = []

    if n >= 18:
        # Large conference -- random selection of opponents, no full round-robin
        # Each team plays exactly target opponents, each game played once
        # (home for one team, away for the other)
        for i, prog in enumerate(programs):
            others    = [p for p in programs if p["name"] != prog["name"]]
            opponents = random.sample(others, min(target, len(others)))
            for opp in opponents:
                # Only add if this matchup hasn't been added yet
                already = any(
                    (m["home"]["name"] == prog["name"] and m["away"]["name"] == opp["name"]) or
                    (m["home"]["name"] == opp["name"]  and m["away"]["name"] == prog["name"])
                    for m in matchups
                )
                if not already:
                    if random.random() < 0.5:
                        matchups.append({"home": prog, "away": opp, "is_conference": True})
                    else:
                        matchups.append({"home": opp, "away": prog, "is_conference": True})
    else:
        # Smaller conferences -- single round-robin base, then random rematches
        # Step 1: single round-robin (every team plays every other team once)
        base_matchups = []
        for i in range(n):
            for j in range(i + 1, n):
                if random.random() < 0.5:
                    base_matchups.append({
                        "home": programs[i], "away": programs[j], "is_conference": True})
                else:
                    base_matchups.append({
                        "home": programs[j], "away": programs[i], "is_conference": True})
        matchups.extend(base_matchups)

        # Step 2: count current games per team
        game_counts = {p["name"]: 0 for p in programs}
        for m in matchups:
            game_counts[m["home"]["name"]] += 1
            game_counts[m["away"]["name"]] += 1

        # Step 3: add rematches until everyone hits target (+/-1)
        # Pair teams that both need more games
        max_attempts = n * target * 4
        attempts     = 0
        pairs        = [(programs[i], programs[j])
                        for i in range(n) for j in range(i+1, n)]

        while attempts < max_attempts:
            attempts += 1
            # Find teams still below target
            needy = [p for p in programs if game_counts[p["name"]] < target]
            if not needy:
                break

            # Pick a random needy team and find a valid rematch partner
            prog = random.choice(needy)
            partners = [
                p for p in programs
                if p["name"] != prog["name"]
                and game_counts[p["name"]] < target
            ]
            if not partners:
                break

            opp = random.choice(partners)
            if random.random() < 0.5:
                matchups.append({"home": prog, "away": opp, "is_conference": True})
            else:
                matchups.append({"home": opp, "away": prog, "is_conference": True})

            game_counts[prog["name"]] += 1
            game_counts[opp["name"]]  += 1

    return matchups


def build_non_conference_schedule(programs, all_programs):
    """
    Builds non-conference HOME games to fill each team's schedule to
    SEASON_GAME_TARGET total games.

    Each team's non-conference game count = SEASON_GAME_TARGET - conf_games_played.
    Uses prestige-bracketed matching (existing logic).

    CRITICAL: Conference program is always HOME. Away team's result recorded
    by their own conference simulation. (v0.6 double-counting fix preserved.)
    """
    matchups   = []
    conf_names = set(p["conference"] for p in programs)
    non_conf_pool = [p for p in all_programs if p["conference"] not in conf_names]

    if len(non_conf_pool) < 2:
        return matchups

    # Count conference games already scheduled for each program
    # We can't know exact conf games at this point so use the target
    n              = len(programs)
    conf_target    = _conf_games_target(n)
    non_conf_count = max(8, SEASON_GAME_TARGET - conf_target)

    for program in programs:
        scheduled = 0
        attempts  = 0
        while scheduled < non_conf_count and attempts < 300:
            attempts += 1
            limit     = 30 + random.randint(0, 30)
            candidate = random.choice(non_conf_pool)
            if candidate["name"] == program["name"]:
                continue
            if abs(candidate["prestige_current"] - program["prestige_current"]) > limit:
                continue
            matchups.append({"home": program, "away": candidate, "is_conference": False})
            scheduled += 1

    return matchups


# -----------------------------------------
# GRAVITY DRIFT
# -----------------------------------------

def update_job_security(program, win_pct, conf_finish_percentile):
    """
    Updates job_security based on performance vs gravity expectations.
    Blue bloods are less patient -- erode security faster when results disappoint.

    TUNING TARGETS:
      A coach going 3 bad seasons in a row should reach firing threshold.
      A coach going 5+ bad seasons should definitely be fired.
      A good season buys back some runway but not a full reset.
      Blue blood / impatient boards fire faster.

    Floor: 5 (not 10 -- needs to be reachable for firing thresholds to matter).
    Ceiling: 100.
    """
    gravity          = program["prestige_gravity"]
    security         = program.get("job_security", 75)
    expected_pct     = 0.35 + (gravity / 100) * 0.45
    gap              = win_pct - expected_pct
    impatience_scale = 0.5 + (gravity / 100) * 1.0

    # Performance delta -- sharpened erosion, capped recovery
    if gap > 0.15:
        delta = 4.0 + (gap * 8)        # great season: +5 to +8
    elif gap > 0.05:
        delta = 2.0                    # solid season: +2
    elif gap > -0.05:
        delta = -1.5 * impatience_scale  # near-expectation: small bleed
    elif gap > -0.15:
        delta = (-5.0) * impatience_scale  # bad season: -2.5 to -7.5
    else:
        delta = (-9.0 - (abs(gap) * 12)) * impatience_scale  # terrible: -5 to -18

    # Conference finish penalty -- bottom half costs extra
    if conf_finish_percentile < 0.50:
        bottom_half_gap = 0.50 - conf_finish_percentile
        delta -= bottom_half_gap * 6.0 * impatience_scale

    # Floor is 5, not 10 -- must be below all firing thresholds
    new_security = max(5, min(100, security + delta))
    program["job_security"] = round(new_security, 1)
    return program


def apply_gravity_drift(program, season_year, win_pct, conf_finish_percentile=0.5):
    """
    Momentum-based gravity anchor drift.
    Performance signal: 70% conference finish + 30% overall win pct.
    Momentum builds over consecutive seasons of consistent over/underperformance.
    A single bad season resets upward momentum to zero.
    """
    from programs_data import get_conference_tier

    if "drift_state" not in program:
        program["drift_state"] = {
            "consecutive_above":   0,
            "consecutive_below":   0,
            "last_direction":      "none",
            "seasons_bottom_half": 0,
        }

    if "performance_history" not in program:
        program["performance_history"] = []

    program["performance_history"].append({
        "year":    season_year,
        "win_pct": round(win_pct, 3),
        "conf_finish_percentile": round(conf_finish_percentile, 3),
    })

    if len(program["performance_history"]) < 3:
        return

    state      = program["drift_state"]
    gravity    = program["prestige_gravity"]
    tier_obj   = get_conference_tier(program["conference"])
    tier       = tier_obj["tier"]
    floor      = tier_obj["floor"]
    annual_cap = GRAVITY_DRIFT_CAP.get(tier, _DEFAULT_DRIFT_CAP)

    expected_win_pct     = 0.35 + (gravity / 100) * 0.45
    expected_conf_finish = 0.35 + (gravity / 100) * 0.45
    conf_gap             = conf_finish_percentile - expected_conf_finish
    overall_gap          = win_pct - expected_win_pct
    performance_gap      = (conf_gap * 0.70) + (overall_gap * 0.30)

    if performance_gap > 0.05:
        if state["last_direction"] == "up":
            state["consecutive_above"] += 1
        else:
            state["consecutive_below"] = 0
            state["consecutive_above"] = 1
        state["last_direction"] = "up"
        momentum = state["consecutive_above"]
    elif performance_gap < -0.05:
        if state["last_direction"] == "down":
            state["consecutive_below"] += 1
        else:
            state["consecutive_above"] = 0
            state["consecutive_below"] = 1
        state["last_direction"] = "down"
        momentum = state["consecutive_below"]
    else:
        state["last_direction"] = "none"
        momentum = 0

    if momentum == 0:
        return

    momentum_table = {1: 0.15, 2: 0.15, 3: 0.15,
                      4: 0.40, 5: 0.40, 6: 0.40,
                      7: 0.70, 8: 0.70, 9: 0.70}
    momentum_mult  = momentum_table.get(momentum, 1.00)
    coach_seasons  = program.get("coach_seasons", 0)
    tenure_mult    = max(0.20, min(1.0, coach_seasons / 8.0))
    security       = program.get("job_security", 75)
    security_mod   = 0.5 + (security / 200.0)

    raw_drift = performance_gap * 1.5 * momentum_mult * tenure_mult * security_mod
    drift     = max(-annual_cap, min(annual_cap, raw_drift))

    new_gravity = max(floor, min(100, gravity + drift))
    program["prestige_gravity"] = round(new_gravity, 1)


# -----------------------------------------
# UNIVERSE GRAVITY
# -----------------------------------------

def apply_universe_gravity(all_programs):
    """
    World-level population auto-correction toward target distribution.
    Blue blood tier is exempt -- throne check handles that separately.
    Conference floors protected as hard stop on downward movement.

    SMOOTH DRIFT RULES (runs each season):

    If a tier is below 75% of target:
      Nudge the top programs from the tier below upward by a fraction
      of the gap to the boundary. Maximum AUTO_CORRECT_UP_CAP pts/season.
      Programs are NOT snapped to the boundary -- they drift toward it
      over 2-4 seasons. This eliminates the teleport artifact.
      prestige_current only -- gravity anchor untouched.

    If a tier is above 125% of target:
      Nudge the weakest programs in the tier downward by a fraction
      of the gap to the boundary. Maximum AUTO_CORRECT_DOWN_CAP pts/season.
      Programs are NOT snapped to exact boundaries -- gradual drift.
      prestige_current only -- gravity anchor untouched.

    Runs top-down so corrections cascade correctly:
      elite corrected first, then strong, then average, etc.
    """
    tier_list = list(UNIVERSE_TIERS)

    # Top-down pass: correct each non-blue-blood tier
    for i, (tier_name, p_min, p_max, target) in enumerate(tier_list):
        if tier_name == "blue_blood":
            continue

        # Recount fresh each iteration -- prior corrections change counts
        actual = sum(
            1 for p in all_programs
            if p_min <= p["prestige_current"] <= p_max
        )
        fill_pct = actual / max(1, target)

        # --- UNDERPOPULATED: drift programs up from tier below ---
        if fill_pct < AUTO_CORRECT_LOW:
            needed = int(target * AUTO_CORRECT_TARGET) - actual
            if needed <= 0:
                continue

            # Find tier below
            if i + 1 >= len(tier_list):
                continue
            _, below_min, below_max, _ = tier_list[i + 1]

            # Get programs from tier below, sorted by prestige desc
            # (closest to the boundary get nudged first)
            candidates = sorted(
                [p for p in all_programs
                 if below_min <= p["prestige_current"] <= below_max],
                key=lambda p: p["prestige_current"],
                reverse=True
            )

            moved = 0
            for program in candidates:
                if moved >= needed:
                    break
                conf_floor   = get_conference_floor(program["conference"])
                current      = program["prestige_current"]
                # Nudge = fraction of gap to boundary, capped at UP_CAP
                gap_to_boundary = p_min - current
                nudge = min(AUTO_CORRECT_UP_CAP,
                            max(0.3, gap_to_boundary * AUTO_CORRECT_GAP_FRAC))
                new_prestige = max(conf_floor, current + nudge)
                # Never snap exactly to boundary -- stop just short
                # so the program earns the final crossing organically
                new_prestige = min(new_prestige, p_min - 0.1)
                if new_prestige <= current:
                    moved += 1
                    continue
                program["prestige_current"] = round(new_prestige, 1)
                program["prestige_grade"]   = prestige_grade(program["prestige_current"])
                moved += 1

        # --- OVERCROWDED: drift weakest programs down ---
        elif fill_pct > AUTO_CORRECT_HIGH:
            excess = actual - int(target * (AUTO_CORRECT_HIGH - 0.15))
            if excess <= 0:
                continue

            # Get weakest programs in this tier
            candidates = sorted(
                [p for p in all_programs
                 if p_min <= p["prestige_current"] <= p_max],
                key=lambda p: p["prestige_current"]
            )

            moved = 0
            for program in candidates:
                if moved >= excess:
                    break
                conf_floor = get_conference_floor(program["conference"])
                current    = program["prestige_current"]
                # Nudge = fraction of gap below boundary, capped at DOWN_CAP
                gap_below_boundary = current - p_min
                nudge = min(AUTO_CORRECT_DOWN_CAP,
                            max(0.3, gap_below_boundary * AUTO_CORRECT_GAP_FRAC))
                new_prestige = max(conf_floor, current - nudge)
                if new_prestige >= current:
                    moved += 1
                    continue
                if new_prestige < conf_floor:
                    moved += 1
                    continue  # can't push below conference floor
                program["prestige_current"] = round(new_prestige, 1)
                program["prestige_grade"]   = prestige_grade(program["prestige_current"])
                moved += 1

    return all_programs


def get_universe_tier_snapshot(all_programs):
    snapshot = []
    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        actual       = sum(1 for p in all_programs if p_min <= p["prestige_current"] <= p_max)
        overflow     = actual - target
        overflow_pct = round((actual - target) / max(1, target) * 100, 1)
        snapshot.append({
            "tier": tier_name, "range": str(p_min) + "-" + str(p_max),
            "target": target, "actual": actual,
            "overflow": overflow, "overflow_pct": overflow_pct,
        })
    return snapshot


def print_tier_snapshot(all_programs, season_year):
    snapshot = get_universe_tier_snapshot(all_programs)
    total    = len(all_programs)
    print("")
    print("--- " + str(season_year) + " Universe Tier Distribution ---")
    print("{:<12} {:<8} {:<8} {:<8} {:<12} {}".format(
        "Tier", "Range", "Target", "Actual", "Overflow", "Bar"))
    print("-" * 65)
    for row in snapshot:
        overflow_str = ("+" if row["overflow"] >= 0 else "") + str(row["overflow"])
        pct_str      = ("+" if row["overflow_pct"] >= 0 else "") + str(row["overflow_pct"]) + "%"
        bar_fill     = min(40, int(row["actual"] / max(1, total) * 80))
        bar_target   = min(40, int(row["target"] / max(1, total) * 80))
        bar = "█" * bar_fill + ("░" * max(0, bar_target - bar_fill) if bar_fill < bar_target else "")
        print("{:<12} {:<8} {:<8} {:<8} {:<12} {}".format(
            row["tier"], row["range"], row["target"], row["actual"],
            overflow_str + " (" + pct_str + ")", bar))


def print_ceiling_breakers(all_programs, season_year):
    """Shows programs currently above their conference ceiling."""
    breakers = []
    for p in all_programs:
        ceiling = get_conference_ceiling(p["conference"])
        if p["prestige_current"] > ceiling and ceiling < 100:
            state = p.get("conference_tier_state", {})
            breakers.append((
                p["name"], p["conference"], ceiling,
                p["prestige_current"],
                state.get("seasons_above_ceiling", 0)
            ))
    if not breakers:
        return
    breakers.sort(key=lambda x: x[3] - x[2], reverse=True)
    print("")
    print("--- " + str(season_year) + " Programs Above Conference Ceiling ---")
    print("{:<24} {:<20} {:<8} {:<10} {:<8}".format(
        "Program", "Conference", "Ceiling", "Prestige", "Seasons"))
    print("-" * 70)
    for name, conf, ceiling, prestige, seasons in breakers[:15]:
        print("{:<24} {:<20} {:<8} {:<10} {:<8}".format(
            name, conf[:19], str(ceiling), str(prestige), str(seasons)))


# -----------------------------------------
# CONFERENCE SEASON
# -----------------------------------------

def simulate_conference_season(conference_programs, all_programs, season_year, verbose=False):
    for p in conference_programs:
        p["wins"] = 0; p["losses"] = 0
        p["conf_wins"] = 0; p["conf_losses"] = 0
        p["season_results"] = []

    conf_schedule     = build_conference_schedule(conference_programs)
    non_conf_schedule = build_non_conference_schedule(conference_programs, all_programs)
    full_schedule     = conf_schedule + non_conf_schedule
    random.shuffle(full_schedule)

    conf_program_names = set(p["name"] for p in conference_programs)

    for matchup in full_schedule:
        home   = matchup["home"]
        away   = matchup["away"]
        result = simulate_game(home, away, verbose=False)

        # Always record result for the home team if they belong to this conference
        if home["name"] in conf_program_names:
            record_game_result(home, away["name"], result["home"], result["away"],
                               is_home=True, is_conference=matchup["is_conference"])

        # Only record result for the away team if they ALSO belong to this conference
        # (i.e. conference games). Non-conference away teams get their result
        # recorded by their own conference simulation.
        if away["name"] in conf_program_names:
            record_game_result(away, home["name"], result["away"], result["home"],
                               is_home=False, is_conference=matchup["is_conference"])

    # Calculate conference standings before prestige pipeline
    calculate_conference_standings(conference_programs)

    for p in conference_programs:
        games   = p["wins"] + p["losses"]
        win_pct = p["wins"] / games if games > 0 else 0.0
        conf_finish_percentile = p.get("conf_finish_percentile", 0.5)

        # Cap prestige calculation at 32 games -- standardized seasons
        # shouldn't exceed this but guard against edge cases
        PRESTIGE_GAME_CAP = 32
        if games > PRESTIGE_GAME_CAP:
            capped_wins   = round(win_pct * PRESTIGE_GAME_CAP)
            capped_losses = PRESTIGE_GAME_CAP - capped_wins
        else:
            capped_wins   = p["wins"]
            capped_losses = p["losses"]

        made_tournament = p["conf_wins"] >= (len(conference_programs) // 2)
        tournament_wins = max(0, p["conf_wins"] - len(conference_programs) // 2)

        # Prestige pipeline
        update_prestige_for_results(p, capped_wins, capped_losses, made_tournament, tournament_wins)
        apply_gravity_pull(p, gravity_earn_seasons=GRAVITY_EARN_SEASONS)
        apply_gravity_drift(p, season_year, win_pct, conf_finish_percentile)
        recalculate_gravity_pull_rate(p)
        update_job_security(p, win_pct, conf_finish_percentile)
        # Stale meter -- floor_conf and low_major programs accumulate stagnation
        made_ncaa = p.get("ncaa_tournament_result", {}).get("seed") is not None
        update_stale_meter(p, conf_finish_percentile, made_tournament=made_ncaa)
        apply_conference_tier_pressure(p)
        apply_conference_identity_pull(p, conf_finish_percentile)
        update_blue_blood_state(p)

        if "season_history" not in p:
            p["season_history"] = []
        p["season_history"].append({
            "year":       season_year,
            "wins":       p["wins"],
            "losses":     p["losses"],
            "conf_wins":  p["conf_wins"],
            "conf_losses": p["conf_losses"],
            "prestige_end": p["prestige_current"],
            "gravity_end":  p["prestige_gravity"],
            "conf_finish_percentile": conf_finish_percentile,
            "job_security": p.get("job_security", 75),
        })
        p["coach_seasons"] += 1

    return conference_programs


# -----------------------------------------
# WORLD SEASON
# -----------------------------------------

def simulate_world_season(all_programs, season_year, verbose=True):
    """
    Simulates a COMPLETE year for the entire world.

    Pipeline:
      Step 1 -- Minutes allocation + stat init.
      Step 2 -- Cohesion initialization (first season).
      Step 3 -- Season simulation (games + per-program prestige pipeline).
      Step 3b -- Conference tournaments (auto-bid determination).
      Step 4 -- Universe gravity (world population correction).
      Step 4b -- Blue blood throne check.
      Step 5 -- Recruiting cycle.
      Step 6 -- Finalize season stats.
      Step 7 -- Lifecycle (graduation, aging, enrollment, cohesion).
    """
    from roster_minutes import allocate_minutes
    from cohesion import update_cohesion
    from game_engine import initialize_season_stats, finalize_season_stats

    for program in all_programs:
        allocate_minutes(program)
        if "cohesion_score" not in program:
            update_cohesion(program, previous_minutes=None)
        initialize_season_stats(program, season_year=season_year)

    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)

    if verbose:
        print("")
        print("=" * 60)
        print("WORLD SEASON " + str(season_year))
        print(str(len(all_programs)) + " programs across " + str(len(conferences)) + " conferences")
        print("=" * 60)

    for conf_name, conf_programs in conferences.items():
        if len(conf_programs) < 2:
            continue
        simulate_conference_season(conf_programs, all_programs, season_year, verbose=False)

    # National Top 25 -- now uses NET quadrant rankings, always print when verbose
    if verbose:
        print_national_standings(all_programs, season_year)

    # Step 3b: Conference tournaments -- determines auto-bids for NCAA tournament
    auto_bids, conf_tourney_results = simulate_all_conference_tournaments(
        all_programs, verbose=verbose
    )

    # Step 3c: NCAA Tournament
    # verbose=False suppresses full bracket play-by-play.
    # print_tournament_summary still runs -- shows champion, Final Four, cinderellas.
    all_programs, tournament_results = simulate_ncaa_tournament(
        all_programs, auto_bids, season_year=season_year, verbose=False
    )
    if verbose:
        print_tournament_summary(tournament_results, season_year)

    # Step 4: Universe gravity
    apply_universe_gravity(all_programs)

    # Step 4b: Blue blood throne check
    run_blue_blood_throne_check(all_programs, season_year, verbose=verbose)

    # Step 4c: Coaching capital update (tournament performance -> coach runway)
    for program in all_programs:
        ncaa_result    = program.get("ncaa_tournament_result", {})
        tourney_result = ncaa_result.get("result", "none")
        update_coaching_capital(program, tourney_result, season_year)

    # Step 4d: Coaching carousel
    # Runs BEFORE transfer portal -- coaching changes trigger portal wave entries
    all_programs, carousel_report, carousel_portal_additions = run_coaching_carousel(
        all_programs, season_year=season_year, verbose=verbose
    )
    if verbose:
        print_carousel_report(carousel_report)

    if verbose:
        print("")
        print("--- " + str(season_year) + " Recruiting Cycle ---")

    recruiting_class = generate_recruiting_class(season=season_year)

    if verbose:
        print("  Class generated: " + str(len(recruiting_class)) + " prospects")

    all_programs, recruiting_class = generate_offers(all_programs, recruiting_class)
    all_programs, recruiting_class = calculate_interest_scores(all_programs, recruiting_class)
    all_programs, recruiting_class, cycle_summary = resolve_full_recruiting_cycle(
        all_programs, recruiting_class, verbose=False
    )

    if verbose:
        print("  Early signings:  " + str(len(cycle_summary["early_commits"])))
        print("  Late signings:   " + str(len(cycle_summary["late_commits"])))
        print("  Total committed: " + str(cycle_summary["total_commits"]))
        print("  Unsigned:        " + str(len(cycle_summary["unsigned"])))

    for program in all_programs:
        finalize_season_stats(program, season_year=season_year)

    if verbose:
        print("")
        print("--- " + str(season_year) + " Roster Turnover ---")

    all_programs, lifecycle_summary = advance_season(all_programs, recruiting_class)

    if verbose:
        print("  Seniors graduated: " + str(lifecycle_summary["total_graduated"]))
        print("  Recruits enrolled: " + str(lifecycle_summary["total_enrolled"]))
        reports = lifecycle_summary.get("program_reports", [])
        if reports:
            avg_cohesion = sum(r.get("cohesion", 50) for r in reports) / len(reports)
            high_coh     = [r for r in reports if r.get("cohesion_tier") in ("very_high", "high")]
            low_coh      = [r for r in reports if r.get("cohesion_tier") in ("low", "very_low")]
            total_bonds  = sum(r.get("combo_bonds", 0) for r in reports)
            print("  Avg cohesion:      " + str(round(avg_cohesion, 1)) + "/100")
            print("  High cohesion:     " + str(len(high_coh)) + " programs")
            print("  Low cohesion:      " + str(len(low_coh)) + " programs")
            print("  Veteran bonds:     " + str(total_bonds) + " total")

    # Step 8: Tournament buzz decay
    # Each program's buzz decays based on this season's tournament performance
    # relative to gravity. Missing the tournament bleeds 60% of buzz.
    # Deep run memory (Final Four+) slows decay for low-gravity programs.
    from program import apply_buzz_decay
    for program in all_programs:
        ncaa_result   = program.get("ncaa_tournament_result", {})
        made_tourney  = ncaa_result.get("seed") is not None
        tourney_result = ncaa_result.get("result", "none")
        apply_buzz_decay(program, made_tourney, tourney_result, season_year)

    # Step 9: Transfer portal
    # Carousel portal wave additions are injected here -- they skip the entry
    # filter (already removed from rosters) but go through destination matching.
    all_programs, portal_pool, portal_report = run_transfer_portal(
        all_programs, season_year=season_year, verbose=verbose,
        extra_portal_players=carousel_portal_additions
    )

    return all_programs, recruiting_class, cycle_summary, lifecycle_summary, auto_bids, tournament_results, portal_report


# -----------------------------------------
# REPORTING
# -----------------------------------------

def print_national_standings(all_programs, season_year):
    from program import get_effective_prestige

    # Calculate NET scores for all programs with games played
    active = [p for p in all_programs if p["wins"] + p["losses"] > 0]
    net_scores = {p["name"]: calculate_net_score(p, all_programs) for p in active}

    ranked = sorted(active, key=lambda p: net_scores[p["name"]], reverse=True)

    print("")
    print("--- " + str(season_year) + " National Top 25 (NET Rankings) ---")
    print("{:<3} {:<22} {:<18} {:<10} {:<8} {:<8} {}".format(
        "#", "Team", "Conference", "Record", "NET", "Base", "Effective"))
    print("-" * 85)
    for i, p in enumerate(ranked[:25]):
        overall  = str(p["wins"]) + "-" + str(p["losses"])
        ep       = round(get_effective_prestige(p), 1)
        buzz     = round(p.get("tournament_buzz", {}).get("current", 0.0), 1)
        ep_str   = str(ep) + (" (+"+str(buzz)+")" if buzz > 0 else "")
        net_str  = str(round(net_scores[p["name"]], 2))
        print("{:<3} {:<22} {:<18} {:<10} {:<8} {:<8} {}".format(
            i+1, p["name"], p["conference"][:17], overall,
            net_str,
            str(p["prestige_current"]) + " (" + p["prestige_grade"] + ")",
            ep_str))

    print("")
    print("--- " + str(season_year) + " Conference Leaders ---")
    conferences = {}
    for p in all_programs:
        conf = p["conference"]
        if conf not in conferences:
            conferences[conf] = []
        conferences[conf].append(p)
    for conf_name, conf_programs in sorted(conferences.items()):
        if not conf_programs:
            continue
        leader      = max(conf_programs, key=lambda p: (p["conf_wins"], p["wins"]))
        conf_record = str(leader["conf_wins"]) + "-" + str(leader["conf_losses"])
        overall     = str(leader["wins"]) + "-" + str(leader["losses"])
        print("{:<20} {:<22} {:<10} {:<10}".format(
            conf_name[:19], leader["name"], overall, conf_record + " conf"))


def print_prestige_movers(all_programs, start_prestiges, season_year):
    changes = []
    for p in all_programs:
        start  = start_prestiges.get(p["name"], p["prestige_current"])
        change = p["prestige_current"] - start
        changes.append((p["name"], p["conference"], start, p["prestige_current"], change))
    changes.sort(key=lambda x: x[4], reverse=True)

    print("")
    print("--- " + str(season_year) + " Biggest Prestige Movers ---")
    print("Top 10 risers:")
    for name, conf, start, end, change in changes[:10]:
        print("  +" + str(round(change, 1)) + "  " + name +
              " (" + conf + ")  " + str(start) + " -> " + str(end))
    print("Top 10 fallers:")
    for name, conf, start, end, change in changes[-10:]:
        print("  " + str(round(change, 1)) + "  " + name +
              " (" + conf + ")  " + str(start) + " -> " + str(end))


def print_roster_evolution(program):
    roster = program.get("roster", [])
    year_counts = {"Freshman": 0, "Sophomore": 0, "Junior": 0, "Senior": 0}
    for p in roster:
        yr = p.get("year", "Unknown")
        if yr in year_counts:
            year_counts[yr] += 1
    print("  " + program["name"] + " roster (" + str(len(roster)) + " players):  " +
          "Fr:" + str(year_counts["Freshman"]) +
          " So:" + str(year_counts["Sophomore"]) +
          " Jr:" + str(year_counts["Junior"]) +
          " Sr:" + str(year_counts["Senior"]))


def print_blue_blood_throne(all_programs, season_year):
    """Shows current blue blood throne occupants, tenure, and siege activity."""
    blue_bloods = sorted(
        [p for p in all_programs if p["prestige_current"] >= BLUE_BLOOD_THRESHOLD],
        key=lambda p: p.get("blue_blood_state", {}).get("seasons", 0),
        reverse=True
    )
    at_gate = sorted(
        [p for p in all_programs
         if 94.5 <= p["prestige_current"] < BLUE_BLOOD_THRESHOLD],
        key=lambda p: p["prestige_current"],
        reverse=True
    )[:6]
    lurking = sorted(
        [p for p in all_programs
         if LURKING_THRESHOLD <= p["prestige_current"] < 94.5],
        key=lambda p: p["prestige_current"],
        reverse=True
    )[:4]

    print("")
    print("--- " + str(season_year) + " Blue Blood Throne (" +
          str(len(blue_bloods)) + "/" + str(BLUE_BLOOD_MAX_SEATS) + " seats) ---")
    print("  {:<24} {:<10} {:<10} {:<8} {:<8} {:<14} {}".format(
        "Program", "Prestige", "Gravity", "Seasons", "Sieges", "Tenure", "Protected"))
    print("  " + "-" * 80)
    for p in blue_bloods:
        state = p.get("blue_blood_state", {})
        print("  {:<24} {:<10} {:<10} {:<8} {:<8} {:<14} {}".format(
            p["name"],
            str(p["prestige_current"]),
            str(p["prestige_gravity"]),
            str(state.get("seasons", 0)),
            str(state.get("siege_count", 0)),
            state.get("tenure_tier", "newcomer"),
            "YES" if state.get("gravity_protected") else "no"
        ))

    if at_gate:
        print("")
        print("  At the gate (94.5-94.9) -- knocking:")
        for p in at_gate:
            state = p.get("blue_blood_state", {})
            print("    {:<24} prestige: {:<8} gravity: {:<8} sieges: {:<4} ever_BB: {}".format(
                p["name"],
                str(p["prestige_current"]),
                str(p["prestige_gravity"]),
                str(state.get("siege_count", 0)),
                "yes" if state.get("ever_blue_blood") else "no"
            ))

    if lurking:
        print("")
        print("  Lurking (85-94.4):")
        for p in lurking:
            state = p.get("blue_blood_state", {})
            print("    {:<24} prestige: {:<8} gravity: {:<8} sieges: {}".format(
                p["name"],
                str(p["prestige_current"]),
                str(p["prestige_gravity"]),
                str(state.get("siege_count", 0))
            ))


# -----------------------------------------
# TEST -- 10-season world simulation
# -----------------------------------------

if __name__ == "__main__":

    print("Loading all D1 programs...")
    all_programs = build_all_d1_programs()
    print("Loaded " + str(len(all_programs)) + " programs")

    print("")
    print("=== STARTING TIER DISTRIBUTION ===")
    print_tier_snapshot(all_programs, "PRE-SIM")
    print_ceiling_breakers(all_programs, "PRE-SIM")

    start_prestiges_global = {p["name"]: p["prestige_current"] for p in all_programs}
    start_prestiges        = {p["name"]: p["prestige_current"] for p in all_programs}

    for year in range(2024, 2030):
        all_programs, recruiting_class, cycle_summary, lifecycle_summary, auto_bids, tournament_results, portal_report = simulate_world_season(
            all_programs, season_year=year, verbose=True
        )
        print_prestige_movers(all_programs, start_prestiges, year)
        print_blue_blood_throne(all_programs, year)
        print_tier_snapshot(all_programs, year)
        print_ceiling_breakers(all_programs, year)
        start_prestiges = {p["name"]: p["prestige_current"] for p in all_programs}

    print("")
    print("=" * 60)
    print("  WORLD SIMULATION COMPLETE")
    print("=" * 60)

    print("")
    print("=== FINAL TIER DISTRIBUTION ===")
    print_tier_snapshot(all_programs, "FINAL")

    all_changes = []
    for p in all_programs:
        start  = start_prestiges_global.get(p["name"], p["prestige_current"])
        change = p["prestige_current"] - start
        all_changes.append(abs(change))

    avg_abs_change = sum(all_changes) / max(1, len(all_changes))
    max_change     = max(all_changes)
    big_movers     = sum(1 for c in all_changes if c > 15)

    print("")
    print("=== PRESTIGE STABILITY OVER 21 SEASONS ===")
    print("  Avg absolute change:            " + str(round(avg_abs_change, 1)) + " points")
    print("  Max change (any program):       " + str(round(max_change, 1)) + " points")
    print("  Programs that moved 15+ points: " + str(big_movers) + " of " + str(len(all_programs)))
    print("  (Target: avg < 8, max < 20, big movers < 10% of programs)")

    sorted_by_change = sorted(
        [(p["name"], p["conference"],
          start_prestiges_global.get(p["name"], p["prestige_current"]),
          p["prestige_current"]) for p in all_programs],
        key=lambda x: abs(x[3] - x[2]), reverse=True
    )
    print("")
    print("  Top 10 programs by total movement:")
    print("  {:<24} {:<20} {:<8} {:<8} {:<8}".format(
        "Program", "Conference", "Start", "End", "Change"))
    print("  " + "-" * 68)
    for name, conf, start, end in sorted_by_change[:10]:
        change = round(end - start, 1)
        sign   = "+" if change >= 0 else ""
        print("  {:<24} {:<20} {:<8} {:<8} {:<8}".format(
            name, conf[:19], str(start), str(round(end, 1)), sign + str(change)))

    print("")
    print("=== CONFERENCE CEILING CONTAINMENT ===")
    print_ceiling_breakers(all_programs, "FINAL")

    osu = next((p for p in all_programs if p["name"] == "Oklahoma State"), None)
    if osu:
        print("")
        print("=== Oklahoma State -- 10-Year Journey ===")
        print("Start: " + str(start_prestiges_global.get("Oklahoma State", "?")))
        print("End:   " + str(osu["prestige_current"]) + " (" + osu["prestige_grade"] + ")")
        print("Anchor:" + str(osu["prestige_gravity"]))
        for s in osu.get("season_history", []):
            print("  " + str(s["year"]) + ": " + str(s["wins"]) + "-" + str(s["losses"]) +
                  "  Prestige: " + str(s["prestige_end"]))

    kentucky = next((p for p in all_programs if p["name"] == "Kentucky"), None)
    if kentucky:
        print("")
        print("=== Kentucky -- Roster After 10 Seasons ===")
        print_roster_evolution(kentucky)

    thin = [p for p in all_programs if len(p["roster"]) < 8]
    print("")
    if thin:
        print("WARNING: " + str(len(thin)) + " programs with thin rosters (<8 players):")
        for p in thin:
            print("  " + p["name"] + ": " + str(len(p["roster"])) + " players")
    else:
        print("PASS: All programs have 8+ players after 10 seasons.")
