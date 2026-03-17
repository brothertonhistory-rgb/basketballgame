# calendar.py
# College Hoops Sim -- Season Calendar System v1.0
#
# Generates the full season date structure for a given year.
# Every game gets a real date. The scheduler fills in opponents.
# The simulation engine iterates the schedule in order.
#
# SEASON WINDOWS:
#   Exhibition:        last 2 weeks of October
#   Season opener:     first week of November (Nov 1-7)
#   Non-conference:    November through December (~12-14 games)
#   Conference play:   early January through first week of March
#   Conf tournament:   second week of March
#   NCAA tournament:   third week of March through first week of April
#
# SCHEDULING RULES:
#   - No more than 2 games per week per team
#   - Conference games: primarily Tuesday/Wednesday + Saturday
#   - Non-conference: primarily Monday/Wednesday/Saturday in Nov,
#     scattered through December
#   - Thanksgiving week: 1-2 marquee neutral games only
#   - Christmas week: 1 elite game only, most teams dark
#   - No games Dec 24-25

from datetime import date, timedelta

# -----------------------------------------
# SEASON WINDOW DEFINITIONS
# All dates relative to the season year.
# Conference tournament and NCAA tournament
# dates are fixed offsets from March 1.
# -----------------------------------------

def get_season_windows(year):
    """
    Returns a dict of key season dates for a given year.
    All windows are date objects.
    """
    # Exhibition window
    exhibition_start = date(year, 10, 18)
    exhibition_end   = date(year, 10, 31)

    # Non-conference window
    noncon_start     = date(year, 11, 1)
    noncon_end       = date(year, 12, 28)

    # Thanksgiving window -- marquee neutral games only
    thanksgiving     = _get_thanksgiving(year)
    thanksgiving_start = thanksgiving - timedelta(days=2)  # Tue before
    thanksgiving_end   = thanksgiving + timedelta(days=1)  # Fri after

    # Christmas blackout
    christmas_start  = date(year, 12, 24)
    christmas_end    = date(year, 12, 25)

    # Conference play window -- starts Dec 20 at earliest (large conferences),
    # Jan 1 for most. End date stays March 5.
    conf_start       = date(year, 12, 20)
    conf_end         = date(year + 1, 3, 5)

    # Conference tournament window
    conf_tourney_start = date(year + 1, 3, 6)
    conf_tourney_end   = date(year + 1, 3, 16)

    # NCAA tournament window
    ncaa_start       = date(year + 1, 3, 17)
    ncaa_end         = date(year + 1, 4, 7)

    return {
        "exhibition_start":    exhibition_start,
        "exhibition_end":      exhibition_end,
        "noncon_start":        noncon_start,
        "noncon_end":          noncon_end,
        "thanksgiving":        thanksgiving,
        "thanksgiving_start":  thanksgiving_start,
        "thanksgiving_end":    thanksgiving_end,
        "christmas_start":     christmas_start,
        "christmas_end":       christmas_end,
        "conf_start":          conf_start,
        "conf_end":            conf_end,
        "conf_tourney_start":  conf_tourney_start,
        "conf_tourney_end":    conf_tourney_end,
        "ncaa_start":          ncaa_start,
        "ncaa_end":            ncaa_end,
    }


def _get_thanksgiving(year):
    """Returns the date of Thanksgiving (4th Thursday of November)."""
    nov_1    = date(year, 11, 1)
    # Find first Thursday
    days_to_thu = (3 - nov_1.weekday()) % 7
    first_thu   = nov_1 + timedelta(days=days_to_thu)
    return first_thu + timedelta(weeks=3)


# -----------------------------------------
# GAME SLOT
# The atomic unit of the calendar.
# Every game played lives in one of these.
# -----------------------------------------

class GameSlot:
    """
    A single scheduled game.

    Fields set at creation (by calendar):
        date         -- datetime.date
        game_type    -- 'exhibition' | 'noncon' | 'conference' |
                        'conf_tournament' | 'ncaa_tournament'
        week_number  -- integer week of the season (1 = first week of Nov)

    Fields set by scheduler:
        home_team    -- program dict (or None for neutral)
        away_team    -- program dict
        neutral_site -- neutral site key from neutral_sites.py (or None)
        is_neutral   -- bool
        event_name   -- str (for tournament events, e.g. 'Maui Invitational')
        event_round  -- int (1/2/3 for multi-game events, None for standalone)
        series_id    -- str (tracks home-and-home obligations, e.g. 'OSU_ORU_2024')

    Fields set by simulation:
        result       -- dict with home_score, away_score, winner, stats
        simulated    -- bool
    """

    def __init__(self, game_date, game_type, week_number=None):
        self.date         = game_date
        self.game_type    = game_type
        self.week_number  = week_number

        # Scheduler fills these
        self.home_team    = None
        self.away_team    = None
        self.neutral_site = None
        self.is_neutral   = False
        self.event_name   = None
        self.event_round  = None
        self.series_id    = None

        # Simulation fills these
        self.result       = None
        self.simulated    = False

    def is_scheduled(self):
        return self.home_team is not None and self.away_team is not None

    def involves_team(self, team_name):
        home = self.home_team["name"] if self.home_team else None
        away = self.away_team["name"] if self.away_team else None
        return team_name in (home, away)

    def get_opponent(self, team_name):
        """Return the opponent program dict for a given team."""
        if self.home_team and self.home_team["name"] == team_name:
            return self.away_team
        if self.away_team and self.away_team["name"] == team_name:
            return self.home_team
        return None

    def is_home_game(self, team_name):
        """Returns True if team is the home team (not neutral)."""
        if self.is_neutral:
            return False
        return self.home_team and self.home_team["name"] == team_name

    def to_dict(self):
        """Serialize to plain dict for storage/database."""
        return {
            "date":         self.date.isoformat(),
            "game_type":    self.game_type,
            "week_number":  self.week_number,
            "home_team":    self.home_team["name"] if self.home_team else None,
            "away_team":    self.away_team["name"] if self.away_team else None,
            "neutral_site": self.neutral_site,
            "is_neutral":   self.is_neutral,
            "event_name":   self.event_name,
            "event_round":  self.event_round,
            "series_id":    self.series_id,
            "result":       self.result,
            "simulated":    self.simulated,
        }

    def __repr__(self):
        home = self.home_team["name"] if self.home_team else "TBD"
        away = self.away_team["name"] if self.away_team else "TBD"
        loc  = f" @ {self.neutral_site}" if self.is_neutral else ""
        return f"<GameSlot {self.date} {away} at {home}{loc} [{self.game_type}]>"


# -----------------------------------------
# SEASON CALENDAR
# The full schedule for one season.
# Generated before any games are simulated.
# -----------------------------------------

class SeasonCalendar:
    """
    Full season calendar for a given year.

    Holds all GameSlots. The scheduler populates them.
    The simulation engine iterates them in date order.

    Usage:
        cal = SeasonCalendar(2024)
        # scheduler fills slots
        for slot in cal.get_games_in_order():
            simulate_game(slot)
    """

    def __init__(self, year):
        self.year    = year
        self.windows = get_season_windows(year)
        self.slots   = []   # all GameSlot objects, unordered
        self._team_game_counts  = {}   # team_name -> game count (for limit enforcement)
        self._team_weekly_games = {}   # team_name -> {week_number: count}

    # -----------------------------------------
    # SLOT CREATION
    # -----------------------------------------

    def add_slot(self, game_date, game_type):
        """Create and register a new GameSlot. Returns the slot."""
        week = self._date_to_week(game_date)
        slot = GameSlot(game_date, game_type, week)
        self.slots.append(slot)
        return slot

    def add_conference_game(self, game_date, home_team, away_team):
        """Add a fully scheduled conference game."""
        slot = self.add_slot(game_date, "conference")
        slot.home_team = home_team
        slot.away_team = away_team
        self._register_game(home_team["name"], slot.week_number)
        self._register_game(away_team["name"], slot.week_number)
        return slot

    def add_noncon_game(self, game_date, home_team, away_team,
                        is_neutral=False, neutral_site=None,
                        event_name=None, event_round=None, series_id=None):
        """Add a fully scheduled non-conference game."""
        slot = self.add_slot(game_date, "noncon")
        slot.home_team    = home_team
        slot.away_team    = away_team
        slot.is_neutral   = is_neutral
        slot.neutral_site = neutral_site
        slot.event_name   = event_name
        slot.event_round  = event_round
        slot.series_id    = series_id
        self._register_game(home_team["name"], slot.week_number)
        self._register_game(away_team["name"], slot.week_number)
        return slot

    def add_exhibition_game(self, game_date, home_team, away_team):
        """Add an exhibition game."""
        slot = self.add_slot(game_date, "exhibition")
        slot.home_team = home_team
        slot.away_team = away_team
        return slot

    # -----------------------------------------
    # WEEK LIMIT ENFORCEMENT
    # No team plays more than 2 games per week.
    # -----------------------------------------

    def _register_game(self, team_name, week_number):
        """Track game counts per team per week."""
        if team_name not in self._team_weekly_games:
            self._team_weekly_games[team_name] = {}
        week = self._team_weekly_games[team_name]
        week[week_number] = week.get(week_number, 0) + 1

        if team_name not in self._team_game_counts:
            self._team_game_counts[team_name] = 0
        self._team_game_counts[team_name] += 1

    def games_this_week(self, team_name, week_number):
        """Return how many games a team has in a given week."""
        return self._team_weekly_games.get(team_name, {}).get(week_number, 0)

    def can_play(self, team_name, game_date, max_per_week=2):
        """Returns True if team has room to play on a given date."""
        week = self._date_to_week(game_date)
        return self.games_this_week(team_name, week) < max_per_week

    def both_can_play(self, team_a, team_b, game_date, max_per_week=2):
        """Returns True if both teams can play on a given date."""
        return (self.can_play(team_a, game_date, max_per_week) and
                self.can_play(team_b, game_date, max_per_week))

    # -----------------------------------------
    # CALENDAR QUERIES
    # -----------------------------------------

    def get_games_in_order(self, game_type=None):
        """
        Return all scheduled slots sorted by date.
        Optionally filter by game_type.
        """
        slots = [s for s in self.slots if s.is_scheduled()]
        if game_type:
            slots = [s for s in slots if s.game_type == game_type]
        return sorted(slots, key=lambda s: s.date)

    def get_team_schedule(self, team_name, game_type=None):
        """Return all games for a given team, sorted by date."""
        slots = [s for s in self.slots
                 if s.is_scheduled() and s.involves_team(team_name)]
        if game_type:
            slots = [s for s in slots if s.game_type == game_type]
        return sorted(slots, key=lambda s: s.date)

    def get_games_on_date(self, game_date):
        """Return all scheduled games on a specific date."""
        return [s for s in self.slots
                if s.is_scheduled() and s.date == game_date]

    def get_games_in_window(self, start_date, end_date, game_type=None):
        """Return all games within a date window."""
        slots = [s for s in self.slots
                 if s.is_scheduled() and start_date <= s.date <= end_date]
        if game_type:
            slots = [s for s in slots if s.game_type == game_type]
        return sorted(slots, key=lambda s: s.date)

    def total_games(self, team_name=None):
        """Total scheduled games. Optionally filtered by team."""
        if team_name:
            return self._team_game_counts.get(team_name, 0)
        return len([s for s in self.slots if s.is_scheduled()])

    def get_rest_days(self, team_name, game_date):
        """
        Returns the number of rest days before game_date for team_name.
        Used by cumulative fatigue system (when built).
        Returns None if no prior game found.
        """
        schedule = self.get_team_schedule(team_name)
        prior = [s for s in schedule if s.date < game_date]
        if not prior:
            return None
        last_game = max(prior, key=lambda s: s.date)
        return (game_date - last_game.date).days

    # -----------------------------------------
    # DATE UTILITIES
    # -----------------------------------------

    def _date_to_week(self, game_date):
        """
        Convert a date to a week number relative to season start.
        Week 1 = first week of November.
        Negative weeks = exhibition (October).
        """
        season_start = date(self.year, 11, 1)
        delta = (game_date - season_start).days
        return delta // 7

    def is_blackout(self, game_date):
        """Returns True if date is in a hard scheduling blackout."""
        w = self.windows
        # Christmas Day only -- Dec 25 reserved for marquee only
        if game_date == w["christmas_end"]:  # Dec 25
            return True
        return False

    def is_holiday_marquee_only(self, game_date):
        """
        Returns True if date is reserved for marquee/resort events only.
        Thanksgiving Day and Christmas Day.
        All other days around these holidays are normal scheduling.
        """
        w = self.windows
        if game_date == w["thanksgiving"]:
            return True
        if game_date == date(self.year, 12, 25):
            return True
        return False

    def is_thanksgiving_window(self, game_date):
        """Returns True if date falls in the Thanksgiving marquee window."""
        w = self.windows
        return w["thanksgiving_start"] <= game_date <= w["thanksgiving_end"]

    def is_noncon_window(self, game_date):
        """Returns True if date is in the non-conference window."""
        w = self.windows
        return w["noncon_start"] <= game_date <= w["noncon_end"]

    def is_conference_window(self, game_date):
        """Returns True if date is in the conference play window."""
        w = self.windows
        return w["conf_start"] <= game_date <= w["conf_end"]

    # -----------------------------------------
    # PREFERRED GAME DAYS
    # Returns lists of valid game dates within a window.
    # Conference: Tuesday/Wednesday + Saturday heavily weighted.
    # Non-con: Monday/Wednesday/Saturday in November,
    #          scattered in December.
    # -----------------------------------------

    def get_conference_dates(self):
        """
        Return all valid conference game dates in order.
        Hard rule: never more than 2 conference games per week per team.

        Start date scales with conference size:
          20+ game conferences: start Dec 20 (need ~10 weeks)
          18-19 game conferences: start Dec 27 (need ~9 weeks)
          16-17 game conferences: start Jan 1  (need ~8 weeks)
          14-15 game conferences: start Jan 6  (need ~7 weeks)
          <= 13 game conferences: start Jan 8  (need ~6-7 weeks)

        All conferences end by March 5.
        Any day of the week is allowed -- scheduling engine enforces
        the 2/week limit per team.
        """
        w = self.windows
        dates = []
        current = w["conf_start"]
        while current <= w["conf_end"]:
            if not self.is_blackout(current):
                dates.append(current)
            current += timedelta(days=1)
        return dates

    def get_conference_start(self, conf_games):
        """
        Returns the recommended conference start date based on game count.
        Called by the scheduler to set the earliest date for a conference.
        """
        if conf_games >= 20:
            return date(self.year, 12, 20)
        elif conf_games >= 18:
            return date(self.year, 12, 27)
        elif conf_games >= 16:
            return date(self.year + 1, 1, 1)
        elif conf_games >= 14:
            return date(self.year + 1, 1, 6)
        else:
            return date(self.year + 1, 1, 8)

    def get_noncon_dates(self, exclude_thanksgiving=True,
                         exclude_christmas=True):
        """
        Return all valid non-conference game dates in order.
        Excludes hard blackout dates and holiday marquee-only dates.
        Thanksgiving Day and Christmas Day are reserved for marquee events.
        All other days including days around holidays are fair game.
        """
        w       = self.windows
        dates   = []
        current = w["noncon_start"]

        while current <= w["noncon_end"]:
            if self.is_blackout(current):
                current += timedelta(days=1)
                continue
            if self.is_holiday_marquee_only(current):
                current += timedelta(days=1)
                continue
            dates.append(current)
            current += timedelta(days=1)

        return dates

    def get_thanksgiving_dates(self):
        """
        Return the Thanksgiving window dates.
        For marquee neutral games only.
        """
        w = self.windows
        dates = []
        current = w["thanksgiving_start"]
        while current <= w["thanksgiving_end"]:
            dates.append(current)
            current += timedelta(days=1)
        return dates

    # -----------------------------------------
    # SUMMARY / DEBUG
    # -----------------------------------------

    def print_summary(self):
        """Print a summary of the calendar."""
        total    = self.total_games()
        conf     = len(self.get_games_in_order("conference"))
        noncon   = len(self.get_games_in_order("noncon"))
        exhibit  = len(self.get_games_in_order("exhibition"))

        print(f"=== Season Calendar {self.year}-{self.year+1} ===")
        print(f"  Total games scheduled: {total}")
        print(f"  Exhibition:            {exhibit}")
        print(f"  Non-conference:        {noncon}")
        print(f"  Conference:            {conf}")

    def print_team_schedule(self, team_name):
        """Print a readable schedule for a single team."""
        schedule = self.get_team_schedule(team_name)
        print(f"\n=== {team_name} Schedule {self.year}-{self.year+1} ===")
        print(f"  {'Date':<12} {'Type':<14} {'Opponent':<28} {'Location'}")
        print("  " + "-" * 70)
        for slot in schedule:
            opp  = slot.get_opponent(team_name)
            opp_name = opp["name"] if opp else "TBD"
            if slot.is_neutral:
                loc = f"Neutral ({slot.neutral_site or '?'})"
            elif slot.is_home_game(team_name):
                loc = "Home"
            else:
                loc = "Away"
            event = f" [{slot.event_name}]" if slot.event_name else ""
            print(f"  {str(slot.date):<12} {slot.game_type:<14} "
                  f"{opp_name:<28} {loc}{event}")
        rest_days = []
        dates = [s.date for s in schedule]
        for i in range(1, len(dates)):
            rest_days.append((dates[i] - dates[i-1]).days)
        if rest_days:
            avg_rest = sum(rest_days) / len(rest_days)
            min_rest = min(rest_days)
            print(f"\n  Games: {len(schedule)}  "
                  f"Avg rest: {avg_rest:.1f} days  "
                  f"Min rest: {min_rest} days")


# -----------------------------------------
# CONFERENCE SCHEDULING FORMAT REGISTRY
# Defines how many conference games each
# conference plays based on size and format.
# Player can modify these. Sim uses them.
# -----------------------------------------

# Format types:
#   'double_rr'      -- everyone plays everyone twice
#   'single_rr'      -- everyone plays everyone once
#   'divisions_2x1'  -- division opponents 2x, cross-division 1x
#   'divisions_1x_plus_rival' -- everyone once + 1 permanent rival +
#                                N rotating partners for 2nd game
#   'partial'        -- play everyone once + rotating partners for remainder

CONFERENCE_FORMATS = {
    # Power conferences
    "ACC": {
        "size": 18,
        "format": "partial",
        "conf_games": 20,
        "divisions": None,
        "protected_rivals": {},   # name -> rival name
        "notes": "18-team ACC: everyone once (17) + 3 rotating for 2nd game = 20"
    },
    "Big Ten": {
        "size": 18,
        "format": "partial",
        "conf_games": 20,
        "divisions": None,
        "protected_rivals": {},
        "notes": "18-team Big Ten"
    },
    "Big 12": {
        "size": 16,
        "format": "partial",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "16-team Big 12: everyone once (15) + 3 rotating = 18"
    },
    "SEC": {
        "size": 16,
        "format": "partial",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "16-team SEC"
    },
    "Big East": {
        "size": 11,
        "format": "double_rr",
        "conf_games": 20,
        "divisions": None,
        "protected_rivals": {},
        "notes": "11-team Big East: everyone twice = 20"
    },
    # High major
    "American": {
        "size": 14,
        "format": "divisions_1x_plus_rival",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "14-team American: everyone once (13) + 1 rival + 2 rotating = 16"
    },
    "A-10": {
        "size": 14,
        "format": "divisions_1x_plus_rival",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "14-team A-10"
    },
    "Mountain West": {
        "size": 12,
        "format": "divisions_2x1",
        "conf_games": 16,
        "divisions": {
            "Mountain": ["Boise State", "Colorado State", "New Mexico",
                         "Utah State", "Wyoming", "Air Force"],
            "West":     ["Fresno State", "Hawaii", "Nevada", "San Diego State",
                         "UNLV", "San Jose State"],
        },
        "protected_rivals": {},
        "notes": "12-team MW: div opponents 2x (10) + cross-div once (6) = 16"
    },
    "WCC": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team WCC: everyone twice = 18"
    },
    # Mid major
    "Missouri Valley": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team MVC: everyone twice = 18"
    },
    "MAC": {
        "size": 12,
        "format": "divisions_2x1",
        "conf_games": 16,
        "divisions": {
            "East": ["Akron", "Bowling Green", "Buffalo", "Kent State",
                     "Miami (OH)", "Ohio"],
            "West": ["Ball State", "Central Michigan", "Eastern Michigan",
                     "Northern Illinois", "Toledo", "Western Michigan"],
        },
        "protected_rivals": {},
        "notes": "12-team MAC with East/West divisions"
    },
    "Sun Belt": {
        "size": 14,
        "format": "divisions_1x_plus_rival",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "14-team Sun Belt"
    },
    "Conference USA": {
        "size": 9,
        "format": "double_rr",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "9-team CUSA: double round robin = 16 games"
    },
    "MAAC": {
        "size": 11,
        "format": "double_rr",
        "conf_games": 20,
        "divisions": None,
        "protected_rivals": {},
        "notes": "11-team MAAC: everyone twice = 20"
    },
    "CAA": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team CAA"
    },
    "Big Sky": {
        "size": 11,
        "format": "double_rr",
        "conf_games": 20,
        "divisions": None,
        "protected_rivals": {},
        "notes": "11-team Big Sky"
    },
    "ASUN": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team ASUN"
    },
    "Horizon": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team Horizon"
    },
    "Summit": {
        "size": 9,
        "format": "double_rr",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "9-team Summit"
    },
    "Ivy League": {
        "size": 8,
        "format": "double_rr",
        "conf_games": 14,
        "divisions": None,
        "protected_rivals": {},
        "notes": "8-team Ivy: everyone twice = 14"
    },
    "Big West": {
        "size": 11,
        "format": "double_rr",
        "conf_games": 20,
        "divisions": None,
        "protected_rivals": {},
        "notes": "11-team Big West"
    },
    "Southern": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team Southern"
    },
    "Ohio Valley": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team OVC"
    },
    # Low major
    "Big South": {
        "size": 11,
        "format": "double_rr",
        "conf_games": 20,
        "divisions": None,
        "protected_rivals": {},
        "notes": "11-team Big South"
    },
    "Patriot": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team Patriot"
    },
    "Southland": {
        "size": 9,
        "format": "double_rr",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "9-team Southland"
    },
    "America East": {
        "size": 9,
        "format": "double_rr",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "9-team America East"
    },
    # Floor conferences
    "SWAC": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team SWAC"
    },
    "MEAC": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team MEAC"
    },
    "NEC": {
        "size": 10,
        "format": "double_rr",
        "conf_games": 18,
        "divisions": None,
        "protected_rivals": {},
        "notes": "10-team NEC"
    },
    "WAC": {
        "size": 9,
        "format": "double_rr",
        "conf_games": 16,
        "divisions": None,
        "protected_rivals": {},
        "notes": "9-team WAC"
    },
}

_DEFAULT_FORMAT = {
    "size":              10,
    "format":            "double_rr",
    "conf_games":        18,
    "divisions":         None,
    "protected_rivals":  {},
    "notes":             "Default: double round robin",
}


def get_conference_format(conference_name):
    """Return the scheduling format for a conference."""
    return CONFERENCE_FORMATS.get(conference_name, _DEFAULT_FORMAT)


def calculate_conf_games(size, fmt, divisions=None):
    """
    Calculate expected conference game count from size and format.
    Used to validate CONFERENCE_FORMATS entries and for dynamic
    conference resizing when the player adds/removes programs.
    """
    if fmt == "double_rr":
        return (size - 1) * 2

    if fmt == "single_rr":
        return size - 1

    if fmt == "divisions_2x1":
        # Assumes two equal divisions
        div_size   = size // 2
        div_games  = (div_size - 1) * 2       # everyone in division twice
        cross_games = div_size                 # everyone in other division once
        return div_games + cross_games

    if fmt == "divisions_1x_plus_rival":
        # Everyone once (size-1) + 1 rival + 2 rotating = size + 2
        return size + 2

    if fmt == "partial":
        # Defined explicitly in the format dict
        return None

    return (size - 1) * 2   # fallback: double round robin
