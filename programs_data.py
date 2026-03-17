import random
from names import generate_coach_name

# -----------------------------------------
# COLLEGE HOOPS SIM -- Full D1 Program Database v0.4
# ~326 D1 programs with real data
#
# v0.4 CHANGES -- Conference Tier System:
#   CONFERENCE_FLOORS replaced by CONFERENCE_TIERS.
#   Every conference now has a ceiling AND a floor.
#   Soft limits enforced by apply_conference_tier_pressure() in program.py.
#
#   power      -- ACC, Big Ten, Big 12, SEC, Big East. No ceiling. Floor 45.
#   high_major -- AAC, A-10, Mountain West, WCC. Ceiling 85. Floor 30.
#   mid_major  -- MVC, MAC, Sun Belt, CUSA, MAAC, CAA, Big Sky, ASUN,
#                 Horizon, Summit, Ivy, Big West, Southern, Ohio Valley.
#                 Ceiling 68. Floor 20.
#   low_major  -- Big South, Patriot, Southland, America East.
#                 Ceiling 52. Floor 15.
#   floor_conf -- SWAC, MEAC, NEC, WAC. Ceiling 40. Floor 8.
# -----------------------------------------

CONFERENCE_TIERS = {
    "ACC":      {"tier": "power",      "ceiling": 100, "floor": 45},
    "Big Ten":  {"tier": "power",      "ceiling": 100, "floor": 45},
    "Big 12":   {"tier": "power",      "ceiling": 100, "floor": 45},
    "SEC":      {"tier": "power",      "ceiling": 100, "floor": 45},
    "Big East": {"tier": "power",      "ceiling": 100, "floor": 45},
    "American":      {"tier": "high_major", "ceiling": 85, "floor": 30},
    "A-10":          {"tier": "high_major", "ceiling": 85, "floor": 30},
    "Mountain West": {"tier": "high_major", "ceiling": 85, "floor": 30},
    "WCC":           {"tier": "high_major", "ceiling": 85, "floor": 30},
    "Missouri Valley": {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "MAC":             {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Sun Belt":        {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Conference USA":  {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "MAAC":            {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "CAA":             {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Big Sky":         {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "ASUN":            {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Atlantic Sun":    {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Horizon":         {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Summit":          {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Ivy League":      {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Big West":        {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Southern":        {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Ohio Valley":     {"tier": "mid_major", "ceiling": 68, "floor": 20},
    "Big South":    {"tier": "low_major", "ceiling": 52, "floor": 15},
    "Patriot":      {"tier": "low_major", "ceiling": 52, "floor": 15},
    "Southland":    {"tier": "low_major", "ceiling": 52, "floor": 15},
    "America East": {"tier": "low_major", "ceiling": 52, "floor": 15},
    "SWAC": {"tier": "floor_conf", "ceiling": 40, "floor": 8},
    "MEAC": {"tier": "floor_conf", "ceiling": 40, "floor": 8},
    "NEC":  {"tier": "floor_conf", "ceiling": 40, "floor": 8},
    "WAC":  {"tier": "floor_conf", "ceiling": 40, "floor": 8},
}

_DEFAULT_TIER = {"tier": "mid_major", "ceiling": 68, "floor": 20}


def get_conference_tier(conference):
    return CONFERENCE_TIERS.get(conference, _DEFAULT_TIER)

def get_conference_floor(conference):
    return CONFERENCE_TIERS.get(conference, _DEFAULT_TIER)["floor"]

def get_conference_ceiling(conference):
    return CONFERENCE_TIERS.get(conference, _DEFAULT_TIER)["ceiling"]

def calc_prestige(tourney, ff, titles, conference):
    tier  = get_conference_tier(conference)["tier"]
    floor = get_conference_floor(conference)

    # Tier-aware base score and tournament value.
    # floor_conf programs start low -- ancient tournament appearances
    # don't reflect current program strength in the SWAC/MEAC/NEC/WAC.
    # low_major programs get a modest discount for the same reason.
    if tier == "floor_conf":
        score = 6
        if tourney <= 10:
            score += tourney * 0.4
        else:
            score += 4 + (tourney - 10) * 0.2
        score += ff * 1.5
        title_bonus = [0, 5, 8, 10]
        if titles < len(title_bonus):
            score += title_bonus[titles]
        else:
            score += title_bonus[-1]
        return max(floor, min(20, round(score)))

    elif tier == "low_major":
        score = 8
        if tourney <= 10:
            score += tourney * 0.6
        else:
            score += 6 + (tourney - 10) * 0.3
        score += ff * 2.0
        title_bonus = [0, 8, 12, 15]
        if titles < len(title_bonus):
            score += title_bonus[titles]
        else:
            score += title_bonus[-1]
        return max(floor, min(30, round(score)))

    else:
        # mid_major, high_major, power -- unchanged
        score = 10
        if tourney <= 10:
            score += tourney * 0.8
        elif tourney <= 25:
            score += 8 + (tourney - 10) * 0.5
        else:
            score += 15.5 + (tourney - 25) * 0.3
        score += ff * 3.0
        title_bonus = [0, 10, 17, 22, 26, 29, 31, 33, 35, 37, 39]
        if titles < len(title_bonus):
            score += title_bonus[titles]
        else:
            score += title_bonus[-1] + (titles - len(title_bonus) + 1) * 2
        return max(floor, min(97, round(score)))


def get_gravity(prestige, conference):
    floor = get_conference_tier(conference)["floor"]
    tier  = get_conference_tier(conference)["tier"]

    # floor_conf anchors sit close to the conference floor.
    # These programs' historical identity IS being a bottom-tier program.
    if tier == "floor_conf":
        return max(floor, floor + random.randint(0, 3))
    elif tier == "low_major":
        return max(floor, prestige - random.randint(3, 7))
    else:
        return max(floor, prestige - random.randint(2, 5))

def get_coach_name(school_name):
    return generate_coach_name()


ALL_D1_PROGRAMS = [
    # AMERICA EAST
    {"name": "Albany",          "nickname": "Great Danes",   "city": "Albany",        "state": "NY", "conference": "America East", "home_court": "SEFCU Arena",                         "venue_rating": 45, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Binghamton",      "nickname": "Bearcats",      "city": "Binghamton",    "state": "NY", "conference": "America East", "home_court": "Binghamton Events Center",             "venue_rating": 42, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Bryant",          "nickname": "Bulldogs",      "city": "Smithfield",    "state": "RI", "conference": "America East", "home_court": "Chace Athletic Center",                "venue_rating": 38, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Maine",           "nickname": "Black Bears",   "city": "Orono",         "state": "ME", "conference": "America East", "home_court": "Memorial Gymnasium",                   "venue_rating": 40, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "UMBC",            "nickname": "Retrievers",    "city": "Baltimore",     "state": "MD", "conference": "America East", "home_court": "Chesapeake Employers Insurance Arena",  "venue_rating": 44, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "UMass Lowell",    "nickname": "River Hawks",   "city": "Lowell",        "state": "MA", "conference": "America East", "home_court": "Tsongas Center",                       "venue_rating": 46, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "New Hampshire",   "nickname": "Wildcats",      "city": "Durham",        "state": "NH", "conference": "America East", "home_court": "Lundholm Gym",                         "venue_rating": 36, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Vermont",         "nickname": "Catamounts",    "city": "Burlington",    "state": "VT", "conference": "America East", "home_court": "Patrick Gym",                          "venue_rating": 48, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "NJIT",            "nickname": "Highlanders","city": "Newark",        "state": "NJ", "conference": "America East", "home_court": "Fleisher Athletic Center",              "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Hartford",        "nickname": "Hawks",         "city": "West Hartford", "state": "CT", "conference": "America East", "home_court": "Chase Family Arena",                   "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},
    # AMERICAN ATHLETIC
    {"name": "Charlotte",        "nickname": "49ers",           "city": "Charlotte",    "state": "NC", "conference": "American", "home_court": "Halton Arena",                      "venue_rating": 58, "tourney": 11, "ff": 1, "titles": 0},
    {"name": "East Carolina",    "nickname": "Pirates",         "city": "Greenville",   "state": "NC", "conference": "American", "home_court": "Williams Arena at Minges Coliseum",  "venue_rating": 52, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Florida Atlantic", "nickname": "Owls",            "city": "Boca Raton",   "state": "FL", "conference": "American", "home_court": "Eleanor R. Baldwin Arena",           "venue_rating": 50, "tourney": 3,  "ff": 1, "titles": 0},
    {"name": "Memphis",          "nickname": "Tigers",          "city": "Memphis",      "state": "TN", "conference": "American", "home_court": "FedExForum",                        "venue_rating": 82, "tourney": 29, "ff": 3, "titles": 0},
    {"name": "North Texas",      "nickname": "Mean Green",      "city": "Denton",       "state": "TX", "conference": "American", "home_court": "UNT Coliseum",                      "venue_rating": 50, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Rice",             "nickname": "Owls",            "city": "Houston",      "state": "TX", "conference": "American", "home_court": "Tudor Fieldhouse",                  "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "South Florida",    "nickname": "Bulls",           "city": "Tampa",        "state": "FL", "conference": "American", "home_court": "Yuengling Center",                  "venue_rating": 55, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Temple",           "nickname": "Owls",            "city": "Philadelphia", "state": "PA", "conference": "American", "home_court": "Liacouras Center",                  "venue_rating": 66, "tourney": 33, "ff": 2, "titles": 0},
    {"name": "UAB",              "nickname": "Blazers",         "city": "Birmingham",   "state": "AL", "conference": "American", "home_court": "Bartow Arena",                      "venue_rating": 58, "tourney": 17, "ff": 0, "titles": 0},
    {"name": "Tulane",           "nickname": "Green Wave",      "city": "New Orleans",  "state": "LA", "conference": "American", "home_court": "Devlin Fieldhouse",                 "venue_rating": 50, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Tulsa",            "nickname": "Golden Hurricane","city": "Tulsa",        "state": "OK", "conference": "American", "home_court": "Reynolds Center",                   "venue_rating": 60, "tourney": 16, "ff": 0, "titles": 0},
    {"name": "Wichita State",    "nickname": "Shockers",        "city": "Wichita",      "state": "KS", "conference": "American", "home_court": "Charles Koch Arena",                "venue_rating": 68, "tourney": 16, "ff": 2, "titles": 0},
    {"name": "UTSA",             "nickname": "Roadrunners",     "city": "San Antonio",  "state": "TX", "conference": "American", "home_court": "Convocation Center",                "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},
    # ACC
    {"name": "Boston College", "nickname": "Eagles",         "city": "Chestnut Hill","state": "MA", "conference": "ACC", "home_court": "Conte Forum",                               "venue_rating": 65, "tourney": 18, "ff": 0,  "titles": 0},
    {"name": "California",     "nickname": "Golden Bears",   "city": "Berkeley",     "state": "CA", "conference": "ACC", "home_court": "Haas Pavilion",                             "venue_rating": 70, "tourney": 19, "ff": 3,  "titles": 1},
    {"name": "Clemson",        "nickname": "Tigers",         "city": "Clemson",      "state": "SC", "conference": "ACC", "home_court": "Littlejohn Coliseum",                       "venue_rating": 64, "tourney": 15, "ff": 0,  "titles": 0},
    {"name": "Duke",           "nickname": "Blue Devils",    "city": "Durham",       "state": "NC", "conference": "ACC", "home_court": "Cameron Indoor Stadium",                    "venue_rating": 99, "tourney": 48, "ff": 18, "titles": 5},
    {"name": "Florida State",  "nickname": "Seminoles",      "city": "Tallahassee",  "state": "FL", "conference": "ACC", "home_court": "Donald L. Tucker Center",                   "venue_rating": 65, "tourney": 18, "ff": 1,  "titles": 0},
    {"name": "Georgia Tech",   "nickname": "Yellow Jackets", "city": "Atlanta",      "state": "GA", "conference": "ACC", "home_court": "Hank McCamish Pavilion",                    "venue_rating": 66, "tourney": 17, "ff": 2,  "titles": 0},
    {"name": "Louisville",     "nickname": "Cardinals",      "city": "Louisville",   "state": "KY", "conference": "ACC", "home_court": "KFC Yum! Center",                           "venue_rating": 88, "tourney": 44, "ff": 10, "titles": 3},
    {"name": "Miami",          "nickname": "Hurricanes",     "city": "Coral Gables", "state": "FL", "conference": "ACC", "home_court": "Watsco Center",                             "venue_rating": 62, "tourney": 12, "ff": 1,  "titles": 0},
    {"name": "North Carolina", "nickname": "Tar Heels",      "city": "Chapel Hill",  "state": "NC", "conference": "ACC", "home_court": "Dean Smith Center",                         "venue_rating": 91, "tourney": 54, "ff": 21, "titles": 6},
    {"name": "NC State",       "nickname": "Wolfpack",       "city": "Raleigh",      "state": "NC", "conference": "ACC", "home_court": "PNC Arena",                                 "venue_rating": 76, "tourney": 29, "ff": 4,  "titles": 2},
    {"name": "Notre Dame",     "nickname": "Fighting Irish", "city": "Notre Dame",   "state": "IN", "conference": "ACC", "home_court": "Edmund P. Joyce Center",                    "venue_rating": 74, "tourney": 38, "ff": 1,  "titles": 0},
    {"name": "Pittsburgh",     "nickname": "Panthers",       "city": "Pittsburgh",   "state": "PA", "conference": "ACC", "home_court": "Petersen Events Center",                    "venue_rating": 74, "tourney": 27, "ff": 1,  "titles": 0},
    {"name": "SMU",            "nickname": "Mustangs",       "city": "Dallas",       "state": "TX", "conference": "ACC", "home_court": "Moody Coliseum",                            "venue_rating": 60, "tourney": 12, "ff": 1,  "titles": 0},
    {"name": "Stanford",       "nickname": "Cardinal",       "city": "Stanford",     "state": "CA", "conference": "ACC", "home_court": "Maples Pavilion",                           "venue_rating": 72, "tourney": 17, "ff": 2,  "titles": 1},
    {"name": "Syracuse",       "nickname": "Orange",         "city": "Syracuse",     "state": "NY", "conference": "ACC", "home_court": "Carrier Dome",                              "venue_rating": 85, "tourney": 41, "ff": 6,  "titles": 1},
    {"name": "Virginia",       "nickname": "Cavaliers",      "city": "Charlottesville","state":"VA", "conference": "ACC", "home_court": "John Paul Jones Arena",                    "venue_rating": 74, "tourney": 27, "ff": 3,  "titles": 1},
    {"name": "Virginia Tech",  "nickname": "Hokies",         "city": "Blacksburg",   "state": "VA", "conference": "ACC", "home_court": "Cassell Coliseum",                          "venue_rating": 65, "tourney": 13, "ff": 0,  "titles": 0},
    {"name": "Wake Forest",    "nickname": "Demon Deacons",  "city": "Winston-Salem","state": "NC", "conference": "ACC", "home_court": "Lawrence Joel Veterans Memorial Coliseum",  "venue_rating": 62, "tourney": 24, "ff": 1,  "titles": 0},
    # ASUN
    {"name": "Austin Peay",       "nickname": "Governors","city": "Clarksville",  "state": "TN", "conference": "ASUN", "home_court": "F&M Bank Arena",        "venue_rating": 44, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Eastern Kentucky",  "nickname": "Colonels", "city": "Richmond",     "state": "KY", "conference": "ASUN", "home_court": "Baptist Health Arena",   "venue_rating": 44, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Florida Gulf Coast","nickname": "Eagles",   "city": "Fort Myers",   "state": "FL", "conference": "ASUN", "home_court": "Alico Arena",            "venue_rating": 48, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Jacksonville",      "nickname": "Dolphins", "city": "Jacksonville", "state": "FL", "conference": "ASUN", "home_court": "Swisher Gymnasium",      "venue_rating": 40, "tourney": 5,  "ff": 1, "titles": 0},
    {"name": "Lipscomb",          "nickname": "Bisons",   "city": "Nashville",    "state": "TN", "conference": "ASUN", "home_court": "Allen Arena",            "venue_rating": 42, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "North Florida",     "nickname": "Ospreys",  "city": "Jacksonville", "state": "FL", "conference": "ASUN", "home_court": "UNF Arena",              "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Stetson",           "nickname": "Hatters",  "city": "DeLand",       "state": "FL", "conference": "ASUN", "home_court": "Edmunds Center",         "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Kennesaw State",    "nickname": "Owls",     "city": "Kennesaw",     "state": "GA", "conference": "ASUN", "home_court": "KSU Convocation Center",  "venue_rating": 38, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Queens",            "nickname": "Royals",   "city": "Charlotte",    "state": "NC", "conference": "ASUN", "home_court": "Levine Center",          "venue_rating": 36, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Central Arkansas",  "nickname": "Bears",    "city": "Conway",       "state": "AR", "conference": "ASUN", "home_court": "Farris Center",          "venue_rating": 40, "tourney": 1,  "ff": 0, "titles": 0},
    # ATLANTIC 10
    {"name": "Davidson",          "nickname": "Wildcats",        "city": "Davidson",     "state": "NC", "conference": "A-10", "home_court": "John M. Belk Arena",          "venue_rating": 52, "tourney": 15, "ff": 0, "titles": 0},
    {"name": "Dayton",            "nickname": "Flyers",          "city": "Dayton",       "state": "OH", "conference": "A-10", "home_court": "University of Dayton Arena",  "venue_rating": 72, "tourney": 20, "ff": 1, "titles": 0},
    {"name": "Duquesne",          "nickname": "Dukes",           "city": "Pittsburgh",   "state": "PA", "conference": "A-10", "home_court": "UPMC Cooper Fieldhouse",      "venue_rating": 55, "tourney": 6,  "ff": 1, "titles": 0},
    {"name": "Fordham",           "nickname": "Rams",            "city": "Bronx",        "state": "NY", "conference": "A-10", "home_court": "Rose Hill Gymnasium",         "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "George Mason",      "nickname": "Patriots",        "city": "Fairfax",      "state": "VA", "conference": "A-10", "home_court": "EagleBank Arena",             "venue_rating": 58, "tourney": 6,  "ff": 1, "titles": 0},
    {"name": "George Washington", "nickname": "Revolutionaries", "city": "Washington",   "state": "DC", "conference": "A-10", "home_court": "Charles E. Smith Center",     "venue_rating": 55, "tourney": 11, "ff": 0, "titles": 0},
    {"name": "La Salle",          "nickname": "Explorers",       "city": "Philadelphia", "state": "PA", "conference": "A-10", "home_court": "Tom Gola Arena",              "venue_rating": 50, "tourney": 12, "ff": 2, "titles": 1},
    {"name": "Loyola Chicago",    "nickname": "Ramblers",        "city": "Chicago",      "state": "IL", "conference": "A-10", "home_court": "Joseph J. Gentile Arena",      "venue_rating": 55, "tourney": 8,  "ff": 2, "titles": 1},
    {"name": "Rhode Island",      "nickname": "Rams",            "city": "Kingston",     "state": "RI", "conference": "A-10", "home_court": "Ryan Center",                 "venue_rating": 58, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "Richmond",          "nickname": "Spiders",         "city": "Richmond",     "state": "VA", "conference": "A-10", "home_court": "Robins Center",               "venue_rating": 56, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "Saint Bonaventure", "nickname": "Bonnies",         "city": "St. Bonaventure","state":"NY","conference": "A-10", "home_court": "Reilly Center",               "venue_rating": 50, "tourney": 8,  "ff": 1, "titles": 0},
    {"name": "Saint Joseph's",    "nickname": "Hawks",           "city": "Philadelphia", "state": "PA", "conference": "A-10", "home_court": "Hagan Arena",                 "venue_rating": 55, "tourney": 21, "ff": 1, "titles": 0},
    {"name": "Saint Louis",       "nickname": "Billikens",       "city": "Saint Louis",  "state": "MO", "conference": "A-10", "home_court": "Chaifetz Arena",              "venue_rating": 58, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "VCU",               "nickname": "Rams",            "city": "Richmond",     "state": "VA", "conference": "A-10", "home_court": "Stuart C. Siegel Center",      "venue_rating": 62, "tourney": 21, "ff": 1, "titles": 0},
    # BIG EAST
    {"name": "Butler",     "nickname": "Bulldogs",      "city": "Indianapolis", "state": "IN", "conference": "Big East", "home_court": "Hinkle Fieldhouse",       "venue_rating": 78, "tourney": 16, "ff": 2,  "titles": 0},
    {"name": "Creighton",  "nickname": "Bluejays",      "city": "Omaha",        "state": "NE", "conference": "Big East", "home_court": "CHI Health Center Omaha", "venue_rating": 72, "tourney": 26, "ff": 0,  "titles": 0},
    {"name": "DePaul",     "nickname": "Blue Demons",   "city": "Chicago",      "state": "IL", "conference": "Big East", "home_court": "Wintrust Arena",          "venue_rating": 62, "tourney": 22, "ff": 2,  "titles": 0},
    {"name": "Georgetown", "nickname": "Hoyas",         "city": "Washington",   "state": "DC", "conference": "Big East", "home_court": "Capital One Arena",       "venue_rating": 76, "tourney": 31, "ff": 5,  "titles": 1},
    {"name": "Marquette",  "nickname": "Golden Eagles", "city": "Milwaukee",    "state": "WI", "conference": "Big East", "home_court": "Fiserv Forum",            "venue_rating": 82, "tourney": 34, "ff": 3,  "titles": 2},
    {"name": "Providence", "nickname": "Friars",        "city": "Providence",   "state": "RI", "conference": "Big East", "home_court": "Amica Mutual Pavilion",   "venue_rating": 68, "tourney": 26, "ff": 2,  "titles": 0},
    {"name": "Seton Hall", "nickname": "Pirates",       "city": "South Orange", "state": "NJ", "conference": "Big East", "home_court": "Prudential Center",       "venue_rating": 72, "tourney": 23, "ff": 1,  "titles": 0},
    {"name": "St. John's", "nickname": "Red Storm",     "city": "New York",     "state": "NY", "conference": "Big East", "home_court": "Madison Square Garden",   "venue_rating": 88, "tourney": 28, "ff": 2,  "titles": 0},
    {"name": "UConn",      "nickname": "Huskies",       "city": "Storrs",       "state": "CT", "conference": "Big East", "home_court": "Harry A. Gampel Pavilion","venue_rating": 82, "tourney": 40, "ff": 11, "titles": 5},
    {"name": "Villanova",  "nickname": "Wildcats",      "city": "Villanova",    "state": "PA", "conference": "Big East", "home_court": "Finneran Pavilion",       "venue_rating": 76, "tourney": 41, "ff": 10, "titles": 3},
    {"name": "Xavier",     "nickname": "Musketeers",    "city": "Cincinnati",   "state": "OH", "conference": "Big East", "home_court": "Cintas Center",           "venue_rating": 72, "tourney": 29, "ff": 1,  "titles": 0},
    # BIG SKY
    {"name": "Eastern Washington","nickname": "Eagles",      "city": "Cheney",     "state": "WA", "conference": "Big Sky", "home_court": "Reese Court",             "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Idaho",             "nickname": "Vandals",     "city": "Moscow",     "state": "ID", "conference": "Big Sky", "home_court": "ICCU Arena",              "venue_rating": 52, "tourney": 17, "ff": 0, "titles": 0},
    {"name": "Idaho State",       "nickname": "Bengals",     "city": "Pocatello",  "state": "ID", "conference": "Big Sky", "home_court": "Holt Arena",              "venue_rating": 44, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Montana",           "nickname": "Grizzlies",   "city": "Missoula",   "state": "MT", "conference": "Big Sky", "home_court": "Adams Center",            "venue_rating": 52, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Montana State",     "nickname": "Bobcats",     "city": "Bozeman",    "state": "MT", "conference": "Big Sky", "home_court": "Brick Breeden Fieldhouse","venue_rating": 46, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Northern Arizona",  "nickname": "Lumberjacks", "city": "Flagstaff",  "state": "AZ", "conference": "Big Sky", "home_court": "Rolle Activity Center",   "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Northern Colorado", "nickname": "Bears",       "city": "Greeley",    "state": "CO", "conference": "Big Sky", "home_court": "Bank of Colorado Arena",  "venue_rating": 44, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Portland State",    "nickname": "Vikings",     "city": "Portland",   "state": "OR", "conference": "Big Sky", "home_court": "Stott Center",            "venue_rating": 42, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Sacramento State",  "nickname": "Hornets",     "city": "Sacramento", "state": "CA", "conference": "Big Sky", "home_court": "The Nest",                "venue_rating": 42, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Weber State",       "nickname": "Wildcats",    "city": "Ogden",      "state": "UT", "conference": "Big Sky", "home_court": "Dee Events Center",       "venue_rating": 50, "tourney": 8,  "ff": 0, "titles": 0},
    # BIG SOUTH
    {"name": "Campbell",           "nickname": "Camels",           "city": "Buies Creek",    "state": "NC", "conference": "Big South", "home_court": "Gore Arena",             "venue_rating": 36, "tourney": 2, "ff": 0, "titles": 0},
    {"name": "Charleston Southern","nickname": "Buccaneers",       "city": "Charleston",     "state": "SC", "conference": "Big South", "home_court": "CSU Fieldhouse",         "venue_rating": 36, "tourney": 3, "ff": 0, "titles": 0},
    {"name": "Gardner-Webb",       "nickname": "Runnin Bulldogs",  "city": "Boiling Springs","state": "NC", "conference": "Big South", "home_court": "Paul Porter Arena",      "venue_rating": 36, "tourney": 2, "ff": 0, "titles": 0},
    {"name": "High Point",         "nickname": "Panthers",         "city": "High Point",     "state": "NC", "conference": "Big South", "home_court": "Millis Athletic Center", "venue_rating": 42, "tourney": 2, "ff": 0, "titles": 0},
    {"name": "Longwood",           "nickname": "Lancers",          "city": "Farmville",      "state": "VA", "conference": "Big South", "home_court": "Willett Hall",           "venue_rating": 36, "tourney": 2, "ff": 0, "titles": 0},
    {"name": "Presbyterian",       "nickname": "Blue Hose",        "city": "Clinton",        "state": "SC", "conference": "Big South", "home_court": "Templeton Arena",        "venue_rating": 32, "tourney": 0, "ff": 0, "titles": 0},
    {"name": "Radford",            "nickname": "Highlanders",      "city": "Radford",        "state": "VA", "conference": "Big South", "home_court": "Dedmon Center",          "venue_rating": 38, "tourney": 2, "ff": 0, "titles": 0},
    {"name": "UNC Asheville",      "nickname": "Bulldogs",         "city": "Asheville",      "state": "NC", "conference": "Big South", "home_court": "Kimmel Arena",           "venue_rating": 42, "tourney": 3, "ff": 0, "titles": 0},
    {"name": "Winthrop",           "nickname": "Eagles",           "city": "Rock Hill",      "state": "SC", "conference": "Big South", "home_court": "Winthrop Coliseum",      "venue_rating": 44, "tourney": 7, "ff": 0, "titles": 0},
    # BIG TEN
    {"name": "Illinois",      "nickname": "Fighting Illini","city": "Champaign",    "state": "IL", "conference": "Big Ten", "home_court": "State Farm Center",             "venue_rating": 78, "tourney": 32, "ff": 6,  "titles": 5},
    {"name": "Indiana",       "nickname": "Hoosiers",       "city": "Bloomington",  "state": "IN", "conference": "Big Ten", "home_court": "Assembly Hall",                 "venue_rating": 86, "tourney": 40, "ff": 8,  "titles": 5},
    {"name": "Iowa",          "nickname": "Hawkeyes",       "city": "Iowa City",    "state": "IA", "conference": "Big Ten", "home_court": "Carver-Hawkeye Arena",           "venue_rating": 74, "tourney": 27, "ff": 2,  "titles": 0},
    {"name": "Maryland",      "nickname": "Terrapins",      "city": "College Park",  "state": "MD","conference": "Big Ten", "home_court": "XFINITY Center",               "venue_rating": 70, "tourney": 22, "ff": 2,  "titles": 1},
    {"name": "Michigan",      "nickname": "Wolverines",     "city": "Ann Arbor",    "state": "MI", "conference": "Big Ten", "home_court": "Crisler Center",                "venue_rating": 80, "tourney": 36, "ff": 8,  "titles": 1},
    {"name": "Michigan State","nickname": "Spartans",       "city": "East Lansing", "state": "MI", "conference": "Big Ten", "home_court": "Breslin Student Events Center", "venue_rating": 82, "tourney": 35, "ff": 10, "titles": 2},
    {"name": "Minnesota",     "nickname": "Golden Gophers", "city": "Minneapolis",  "state": "MN", "conference": "Big Ten", "home_court": "Williams Arena",                "venue_rating": 68, "tourney": 17, "ff": 1,  "titles": 0},
    {"name": "Nebraska",      "nickname": "Cornhuskers",    "city": "Lincoln",      "state": "NE", "conference": "Big Ten", "home_court": "Pinnacle Bank Arena",           "venue_rating": 70, "tourney": 13, "ff": 0,  "titles": 0},
    {"name": "Northwestern",  "nickname": "Wildcats",       "city": "Evanston",     "state": "IL", "conference": "Big Ten", "home_court": "Welsh-Ryan Arena",              "venue_rating": 62, "tourney": 7,  "ff": 0,  "titles": 0},
    {"name": "Ohio State",    "nickname": "Buckeyes",       "city": "Columbus",     "state": "OH", "conference": "Big Ten", "home_court": "Value City Arena",              "venue_rating": 82, "tourney": 30, "ff": 5,  "titles": 1},
    {"name": "Oregon",        "nickname": "Ducks",          "city": "Eugene",       "state": "OR", "conference": "Big Ten", "home_court": "Matthew Knight Arena",          "venue_rating": 72, "tourney": 20, "ff": 2,  "titles": 0},
    {"name": "Penn State",    "nickname": "Nittany Lions",  "city": "State College","state": "PA", "conference": "Big Ten", "home_court": "Bryce Jordan Center",           "venue_rating": 72, "tourney": 12, "ff": 0,  "titles": 0},
    {"name": "Purdue",        "nickname": "Boilermakers",   "city": "West Lafayette","state": "IN","conference": "Big Ten", "home_court": "Mackey Arena",                  "venue_rating": 80, "tourney": 32, "ff": 3,  "titles": 0},
    {"name": "Rutgers",       "nickname": "Scarlet Knights","city": "Piscataway",   "state": "NJ", "conference": "Big Ten", "home_court": "Jersey Mike's Arena",           "venue_rating": 62, "tourney": 8,  "ff": 0,  "titles": 0},
    {"name": "UCLA",          "nickname": "Bruins",         "city": "Los Angeles",  "state": "CA", "conference": "Big Ten", "home_court": "Pauley Pavilion",               "venue_rating": 88, "tourney": 52, "ff": 18, "titles": 11},
    {"name": "USC",           "nickname": "Trojans",        "city": "Los Angeles",  "state": "CA", "conference": "Big Ten", "home_court": "Galen Center",                  "venue_rating": 72, "tourney": 16, "ff": 2,  "titles": 0},
    {"name": "Washington",    "nickname": "Huskies",        "city": "Seattle",      "state": "WA", "conference": "Big Ten", "home_court": "Alaska Airlines Arena",         "venue_rating": 68, "tourney": 20, "ff": 1,  "titles": 0},
    {"name": "Wisconsin",     "nickname": "Badgers",        "city": "Madison",      "state": "WI", "conference": "Big Ten", "home_court": "Kohl Center",                   "venue_rating": 78, "tourney": 28, "ff": 3,  "titles": 0},
    # BIG 12
    {"name": "Arizona",       "nickname": "Wildcats",     "city": "Tucson",        "state": "AZ", "conference": "Big 12", "home_court": "McKale Center",           "venue_rating": 84, "tourney": 37, "ff": 4,  "titles": 1},
    {"name": "Arizona State", "nickname": "Sun Devils",   "city": "Tempe",         "state": "AZ", "conference": "Big 12", "home_court": "Desert Financial Arena",   "venue_rating": 70, "tourney": 14, "ff": 0,  "titles": 0},
    {"name": "Baylor",        "nickname": "Bears",        "city": "Waco",          "state": "TX", "conference": "Big 12", "home_court": "Foster Pavilion",          "venue_rating": 82, "tourney": 21, "ff": 3,  "titles": 1},
    {"name": "BYU",           "nickname": "Cougars",      "city": "Provo",         "state": "UT", "conference": "Big 12", "home_court": "Marriott Center",          "venue_rating": 74, "tourney": 30, "ff": 1,  "titles": 0},
    {"name": "Cincinnati",    "nickname": "Bearcats",     "city": "Cincinnati",    "state": "OH", "conference": "Big 12", "home_court": "Fifth Third Arena",        "venue_rating": 72, "tourney": 32, "ff": 5,  "titles": 0},
    {"name": "Colorado",      "nickname": "Buffaloes",    "city": "Boulder",       "state": "CO", "conference": "Big 12", "home_court": "CU Events Center",         "venue_rating": 66, "tourney": 21, "ff": 1,  "titles": 0},
    {"name": "Houston",       "nickname": "Cougars",      "city": "Houston",       "state": "TX", "conference": "Big 12", "home_court": "Fertitta Center",          "venue_rating": 78, "tourney": 25, "ff": 5,  "titles": 0},
    {"name": "Iowa State",    "nickname": "Cyclones",     "city": "Ames",          "state": "IA", "conference": "Big 12", "home_court": "Hilton Coliseum",          "venue_rating": 74, "tourney": 24, "ff": 1,  "titles": 0},
    {"name": "Kansas",        "nickname": "Jayhawks",     "city": "Lawrence",      "state": "KS", "conference": "Big 12", "home_court": "Allen Fieldhouse",         "venue_rating": 98, "tourney": 54, "ff": 16, "titles": 3},
    {"name": "Kansas State",  "nickname": "Wildcats",     "city": "Manhattan",     "state": "KS", "conference": "Big 12", "home_court": "Bramlage Coliseum",        "venue_rating": 72, "tourney": 27, "ff": 1,  "titles": 0},
    {"name": "Oklahoma",      "nickname": "Sooners",      "city": "Norman",        "state": "OK", "conference": "Big 12", "home_court": "Lloyd Noble Center",       "venue_rating": 74, "tourney": 28, "ff": 2,  "titles": 0},
    {"name": "Oklahoma State","nickname": "Cowboys",      "city": "Stillwater",    "state": "OK", "conference": "Big 12", "home_court": "Gallagher-Iba Arena",      "venue_rating": 72, "tourney": 23, "ff": 1,  "titles": 0},
    {"name": "TCU",           "nickname": "Horned Frogs", "city": "Fort Worth",    "state": "TX", "conference": "Big 12", "home_court": "Ed and Rae Schollmaier Arena","venue_rating": 68,"tourney": 5,"ff": 0,  "titles": 0},
    {"name": "Texas",         "nickname": "Longhorns",    "city": "Austin",        "state": "TX", "conference": "Big 12", "home_court": "Moody Center",             "venue_rating": 82, "tourney": 37, "ff": 5,  "titles": 0},
    {"name": "Texas Tech",    "nickname": "Red Raiders",  "city": "Lubbock",       "state": "TX", "conference": "Big 12", "home_court": "United Supermarkets Arena", "venue_rating": 74, "tourney": 19, "ff": 1,  "titles": 0},
    {"name": "UCF",           "nickname": "Knights",      "city": "Orlando",       "state": "FL", "conference": "Big 12", "home_court": "Addition Financial Arena", "venue_rating": 68, "tourney": 5,  "ff": 0,  "titles": 0},
    {"name": "Utah",          "nickname": "Utes",         "city": "Salt Lake City","state": "UT", "conference": "Big 12", "home_court": "Jon M. Huntsman Center",   "venue_rating": 72, "tourney": 21, "ff": 2,  "titles": 0},
    {"name": "West Virginia", "nickname": "Mountaineers", "city": "Morgantown",    "state": "WV", "conference": "Big 12", "home_court": "WVU Coliseum",             "venue_rating": 72, "tourney": 28, "ff": 3,  "titles": 0},
    # BIG WEST
    {"name": "Cal Poly",             "nickname": "Mustangs",    "city": "San Luis Obispo","state": "CA","conference": "Big West","home_court": "Mott Athletics Center",     "venue_rating": 44,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Cal State Bakersfield","nickname": "Roadrunners", "city": "Bakersfield",    "state": "CA","conference": "Big West","home_court": "Mechanics Bank Arena",      "venue_rating": 46,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Cal State Fullerton",  "nickname": "Titans",      "city": "Fullerton",      "state": "CA","conference": "Big West","home_court": "Titan Gym",                 "venue_rating": 42,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Cal State Northridge", "nickname": "Matadors",    "city": "Northridge",     "state": "CA","conference": "Big West","home_court": "Matadome",                  "venue_rating": 40,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Long Beach State",     "nickname": "Beach",       "city": "Long Beach",     "state": "CA","conference": "Big West","home_court": "Walter Pyramid",            "venue_rating": 52,"tourney": 8, "ff": 1,"titles": 0},
    {"name": "UC Davis",             "nickname": "Aggies",      "city": "Davis",          "state": "CA","conference": "Big West","home_court": "UC Davis Activities Center","venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "UC Irvine",            "nickname": "Anteaters",   "city": "Irvine",         "state": "CA","conference": "Big West","home_court": "Bren Events Center",        "venue_rating": 50,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "UC Riverside",         "nickname": "Highlanders", "city": "Riverside",      "state": "CA","conference": "Big West","home_court": "Student Recreation Center", "venue_rating": 40,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "UC Santa Barbara",     "nickname": "Gauchos",     "city": "Santa Barbara",  "state": "CA","conference": "Big West","home_court": "Thunderdome",               "venue_rating": 52,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Hawaii",               "nickname": "Rainbow Warriors","city": "Honolulu",   "state": "HI","conference": "Big West","home_court": "SimpliFi Arena at Stan Sheriff Center","venue_rating": 58,"tourney": 10,"ff": 0,"titles": 0},
    # CAA
    {"name": "Charleston",    "nickname": "Cougars",   "city": "Charleston",    "state": "SC","conference": "CAA","home_court": "TD Arena",                 "venue_rating": 52,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Delaware",      "nickname": "Blue Hens", "city": "Newark",        "state": "DE","conference": "CAA","home_court": "Bob Carpenter Center",      "venue_rating": 48,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Drexel",        "nickname": "Dragons",   "city": "Philadelphia",  "state": "PA","conference": "CAA","home_court": "Daskalakis Athletic Center","venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Elon",          "nickname": "Phoenix",   "city": "Elon",          "state": "NC","conference": "CAA","home_court": "Schar Center",              "venue_rating": 46,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Hampton",       "nickname": "Pirates",   "city": "Hampton",       "state": "VA","conference": "CAA","home_court": "Hampton Convocation Center", "venue_rating": 44,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Hofstra",       "nickname": "Pride",     "city": "Hempstead",     "state": "NY","conference": "CAA","home_court": "David S. Mack Sports Center","venue_rating": 46,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Monmouth",      "nickname": "Hawks",     "city": "West Long Branch","state": "NJ","conference": "CAA","home_court": "OceanFirst Bank Center",  "venue_rating": 42,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Northeastern",  "nickname": "Huskies",   "city": "Boston",        "state": "MA","conference": "CAA","home_court": "Matthews Arena",            "venue_rating": 48,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Stony Brook",   "nickname": "Seawolves", "city": "Stony Brook",   "state": "NY","conference": "CAA","home_court": "Island Federal Credit Union Arena","venue_rating": 48,"tourney": 3,"ff": 0,"titles": 0},
    {"name": "Towson",        "nickname": "Tigers",    "city": "Towson",        "state": "MD","conference": "CAA","home_court": "SECU Arena",                "venue_rating": 46,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "UNC Wilmington","nickname": "Seahawks",  "city": "Wilmington",    "state": "NC","conference": "CAA","home_court": "Trask Coliseum",            "venue_rating": 44,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "William & Mary","nickname": "Tribe",     "city": "Williamsburg",  "state": "VA","conference": "CAA","home_court": "Kaplan Arena",              "venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    # CONFERENCE USA
    {"name": "Florida International","nickname": "Panthers",    "city": "Miami",         "state": "FL","conference": "Conference USA","home_court": "Ocean Bank Convocation Center","venue_rating": 46,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Jacksonville State",   "nickname": "Gamecocks",   "city": "Jacksonville",  "state": "AL","conference": "Conference USA","home_court": "Pete Mathews Coliseum",        "venue_rating": 40,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Liberty",              "nickname": "Flames",      "city": "Lynchburg",     "state": "VA","conference": "Conference USA","home_court": "Liberty Arena",                "venue_rating": 52,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Middle Tennessee",     "nickname": "Blue Raiders","city": "Murfreesboro",  "state": "TN","conference": "Conference USA","home_court": "Murphy Center",                "venue_rating": 52,"tourney": 11,"ff": 0,"titles": 0},
    {"name": "New Mexico State",     "nickname": "Aggies",      "city": "Las Cruces",    "state": "NM","conference": "Conference USA","home_court": "Pan American Center",          "venue_rating": 58,"tourney": 25,"ff": 0,"titles": 0},
    {"name": "Sam Houston",          "nickname": "Bearkats",    "city": "Huntsville",    "state": "TX","conference": "Conference USA","home_court": "Bernard G. Johnson Coliseum",  "venue_rating": 44,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "UTEP",                 "nickname": "Miners",      "city": "El Paso",       "state": "TX","conference": "Conference USA","home_court": "Don Haskins Center",           "venue_rating": 60,"tourney": 23,"ff": 2,"titles": 1},
    {"name": "Western Kentucky",     "nickname": "Hilltoppers", "city": "Bowling Green", "state": "KY","conference": "Conference USA","home_court": "E.A. Diddle Arena",            "venue_rating": 58,"tourney": 24,"ff": 1,"titles": 0},
    {"name": "Delaware State",       "nickname": "Hornets",     "city": "Dover",         "state": "DE","conference": "Conference USA","home_court": "Memorial Hall",                "venue_rating": 32,"tourney": 0, "ff": 0,"titles": 0},
    # HORIZON
    {"name": "Cleveland State",   "nickname": "Vikings",         "city": "Cleveland",      "state": "OH","conference": "Horizon","home_court": "Wolstein Center",         "venue_rating": 50,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Detroit Mercy",     "nickname": "Titans",          "city": "Detroit",        "state": "MI","conference": "Horizon","home_court": "Calihan Hall",             "venue_rating": 52,"tourney": 9, "ff": 0,"titles": 0},
    {"name": "Green Bay",         "nickname": "Phoenix",         "city": "Green Bay",      "state": "WI","conference": "Horizon","home_court": "Resch Center",             "venue_rating": 52,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Milwaukee",         "nickname": "Panthers",        "city": "Milwaukee",      "state": "WI","conference": "Horizon","home_court": "UWM Panther Arena",        "venue_rating": 48,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Northern Kentucky", "nickname": "Norse",           "city": "Highland Heights","state": "KY","conference": "Horizon","home_court": "BB&T Arena",              "venue_rating": 46,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Oakland",           "nickname": "Golden Grizzlies","city": "Rochester",      "state": "MI","conference": "Horizon","home_court": "Allentown Arena",          "venue_rating": 44,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Wright State",      "nickname": "Raiders",         "city": "Dayton",         "state": "OH","conference": "Horizon","home_court": "Nutter Center",            "venue_rating": 54,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Youngstown State",  "nickname": "Penguins",        "city": "Youngstown",     "state": "OH","conference": "Horizon","home_court": "Beeghly Center",           "venue_rating": 44,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "IUPUI",             "nickname": "Jaguars",         "city": "Indianapolis",   "state": "IN","conference": "Horizon","home_court": "Indiana Farmers Coliseum", "venue_rating": 44,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Purdue Fort Wayne", "nickname": "Mastodons",       "city": "Fort Wayne",     "state": "IN","conference": "Horizon","home_court": "Memorial Coliseum",        "venue_rating": 42,"tourney": 0, "ff": 0,"titles": 0},
    # IVY LEAGUE
    {"name": "Brown",     "nickname": "Bears",     "city": "Providence",   "state": "RI","conference": "Ivy League","home_court": "Pizzitola Sports Center","venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Columbia",  "nickname": "Lions",     "city": "New York",     "state": "NY","conference": "Ivy League","home_court": "Levien Gymnasium",       "venue_rating": 42,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Cornell",   "nickname": "Big Red",   "city": "Ithaca",       "state": "NY","conference": "Ivy League","home_court": "Newman Arena",           "venue_rating": 44,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Dartmouth", "nickname": "Big Green", "city": "Hanover",      "state": "NH","conference": "Ivy League","home_court": "Leede Arena",            "venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Harvard",   "nickname": "Crimson",   "city": "Cambridge",    "state": "MA","conference": "Ivy League","home_court": "Lavietes Pavilion",      "venue_rating": 46,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Penn",      "nickname": "Quakers",   "city": "Philadelphia", "state": "PA","conference": "Ivy League","home_court": "The Palestra",           "venue_rating": 60,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "Princeton", "nickname": "Tigers",    "city": "Princeton",    "state": "NJ","conference": "Ivy League","home_court": "Jadwin Gymnasium",       "venue_rating": 52,"tourney": 10,"ff": 0,"titles": 0},
    {"name": "Yale",      "nickname": "Bulldogs",  "city": "New Haven",    "state": "CT","conference": "Ivy League","home_court": "Lee Amphitheater",        "venue_rating": 46,"tourney": 3, "ff": 0,"titles": 0},
    # MAAC
    {"name": "Canisius",      "nickname": "Golden Griffins","city": "Buffalo",       "state": "NY","conference": "MAAC","home_court": "Koessler Athletic Center","venue_rating": 44,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Fairfield",     "nickname": "Stags",          "city": "Fairfield",     "state": "CT","conference": "MAAC","home_court": "Webster Bank Arena",     "venue_rating": 52,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Iona",          "nickname": "Gaels",          "city": "New Rochelle",  "state": "NY","conference": "MAAC","home_court": "Hynes Athletics Center", "venue_rating": 42,"tourney": 14,"ff": 0,"titles": 0},
    {"name": "Marist",        "nickname": "Red Foxes",      "city": "Poughkeepsie",  "state": "NY","conference": "MAAC","home_court": "McCann Arena",           "venue_rating": 42,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Manhattan",     "nickname": "Jaspers",        "city": "Riverdale",     "state": "NY","conference": "MAAC","home_court": "Draddy Gymnasium",       "venue_rating": 40,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Niagara",       "nickname": "Purple Eagles",  "city": "Lewiston",      "state": "NY","conference": "MAAC","home_court": "Gallagher Center",       "venue_rating": 38,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "Quinnipiac",    "nickname": "Bobcats",        "city": "Hamden",        "state": "CT","conference": "MAAC","home_court": "TD Bank Sports Center",  "venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Rider",         "nickname": "Broncs",         "city": "Lawrenceville", "state": "NJ","conference": "MAAC","home_court": "Alumni Gymnasium",       "venue_rating": 40,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Saint Peter's", "nickname": "Peacocks",       "city": "Jersey City",   "state": "NJ","conference": "MAAC","home_court": "Bob Hurley Sr. Court",   "venue_rating": 40,"tourney": 6, "ff": 1,"titles": 0},
    {"name": "Siena",         "nickname": "Saints",         "city": "Loudonville",   "state": "NY","conference": "MAAC","home_court": "Times Union Center",     "venue_rating": 52,"tourney": 5, "ff": 0,"titles": 0},
    # MAC
    {"name": "Akron",           "nickname": "Zips",           "city": "Akron",         "state": "OH","conference": "MAC","home_court": "James A. Rhodes Arena",    "venue_rating": 56,"tourney": 8, "ff": 0,"titles": 0},
    {"name": "Ball State",      "nickname": "Cardinals",      "city": "Muncie",        "state": "IN","conference": "MAC","home_court": "Worthen Arena",             "venue_rating": 52,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Bowling Green",   "nickname": "Falcons",        "city": "Bowling Green", "state": "OH","conference": "MAC","home_court": "Stroh Center",              "venue_rating": 52,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Buffalo",         "nickname": "Bulls",          "city": "Buffalo",       "state": "NY","conference": "MAC","home_court": "Alumni Arena",              "venue_rating": 54,"tourney": 9, "ff": 0,"titles": 0},
    {"name": "Central Michigan","nickname": "Chippewas",      "city": "Mount Pleasant","state": "MI","conference": "MAC","home_court": "McGuirk Arena",             "venue_rating": 48,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Eastern Michigan","nickname": "Eagles",         "city": "Ypsilanti",     "state": "MI","conference": "MAC","home_court": "Convocation Center",        "venue_rating": 46,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Kent State",      "nickname": "Golden Flashes", "city": "Kent",          "state": "OH","conference": "MAC","home_court": "Memorial Athletic and Convocation Center","venue_rating": 52,"tourney": 4,"ff": 0,"titles": 0},
    {"name": "Miami (OH)",      "nickname": "RedHawks",       "city": "Oxford",        "state": "OH","conference": "MAC","home_court": "Millett Hall",              "venue_rating": 52,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "Northern Illinois","nickname": "Huskies",       "city": "DeKalb",        "state": "IL","conference": "MAC","home_court": "Convocation Center",        "venue_rating": 50,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Ohio",            "nickname": "Bobcats",        "city": "Athens",        "state": "OH","conference": "MAC","home_court": "Convocation Center",        "venue_rating": 54,"tourney": 10,"ff": 0,"titles": 0},
    {"name": "Toledo",          "nickname": "Rockets",        "city": "Toledo",        "state": "OH","conference": "MAC","home_court": "Savage Arena",              "venue_rating": 56,"tourney": 11,"ff": 0,"titles": 0},
    {"name": "UMass",           "nickname": "Minutemen",      "city": "Amherst",       "state": "MA","conference": "MAC","home_court": "Mullins Center",            "venue_rating": 62,"tourney": 14,"ff": 1,"titles": 0},
    {"name": "Western Michigan","nickname": "Broncos",        "city": "Kalamazoo",     "state": "MI","conference": "MAC","home_court": "University Arena",          "venue_rating": 52,"tourney": 5, "ff": 0,"titles": 0},
    # MEAC
    {"name": "Coppin State",           "nickname": "Eagles",   "city": "Baltimore",    "state": "MD","conference": "MEAC","home_court": "Physical Education Complex",      "venue_rating": 32,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Florida A&M",            "nickname": "Rattlers", "city": "Tallahassee",  "state": "FL","conference": "MEAC","home_court": "Al Lawson Multipurpose Center",   "venue_rating": 34,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Howard",                 "nickname": "Bison",    "city": "Washington",   "state": "DC","conference": "MEAC","home_court": "Burr Gymnasium",                 "venue_rating": 36,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Maryland-Eastern Shore", "nickname": "Hawks",    "city": "Princess Anne","state": "MD","conference": "MEAC","home_court": "William P. Hytche Athletic Center","venue_rating": 28,"tourney": 1,"ff": 0,"titles": 0},
    {"name": "Morgan State",           "nickname": "Bears",    "city": "Baltimore",    "state": "MD","conference": "MEAC","home_court": "Hill Field House",                "venue_rating": 32,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Norfolk State",          "nickname": "Spartans", "city": "Norfolk",      "state": "VA","conference": "MEAC","home_court": "Joseph G. Echols Memorial Hall",  "venue_rating": 34,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "North Carolina A&T",     "nickname": "Aggies",   "city": "Greensboro",   "state": "NC","conference": "MEAC","home_court": "Corbett Sports Center",          "venue_rating": 36,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "North Carolina Central", "nickname": "Eagles",   "city": "Durham",       "state": "NC","conference": "MEAC","home_court": "McDougald-McLendon Arena",       "venue_rating": 34,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "South Carolina State",   "nickname": "Bulldogs", "city": "Orangeburg",   "state": "SC","conference": "MEAC","home_court": "Smith Hammond Middleton Memorial Center","venue_rating": 30,"tourney": 5,"ff": 0,"titles": 0},
    # MISSOURI VALLEY
    {"name": "Bradley",           "nickname": "Braves",       "city": "Peoria",      "state": "IL","conference": "Missouri Valley","home_court": "Carver Arena",         "venue_rating": 62,"tourney": 14,"ff": 1,"titles": 0},
    {"name": "Drake",             "nickname": "Bulldogs",     "city": "Des Moines",  "state": "IA","conference": "Missouri Valley","home_court": "Knapp Center",         "venue_rating": 60,"tourney": 9, "ff": 0,"titles": 0},
    {"name": "Evansville",        "nickname": "Purple Aces",  "city": "Evansville",  "state": "IN","conference": "Missouri Valley","home_court": "Ford Center",          "venue_rating": 58,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "Illinois State",    "nickname": "Redbirds",     "city": "Normal",      "state": "IL","conference": "Missouri Valley","home_court": "Redbird Arena",        "venue_rating": 56,"tourney": 11,"ff": 0,"titles": 0},
    {"name": "Missouri State",    "nickname": "Bears",        "city": "Springfield", "state": "MO","conference": "Missouri Valley","home_court": "JQH Arena",            "venue_rating": 60,"tourney": 11,"ff": 0,"titles": 0},
    {"name": "Northern Iowa",     "nickname": "Panthers",     "city": "Cedar Falls", "state": "IA","conference": "Missouri Valley","home_court": "McLeod Center",        "venue_rating": 60,"tourney": 10,"ff": 0,"titles": 0},
    {"name": "Southern Illinois", "nickname": "Salukis",      "city": "Carbondale",  "state": "IL","conference": "Missouri Valley","home_court": "Banterra Center",      "venue_rating": 60,"tourney": 10,"ff": 0,"titles": 0},
    {"name": "Valparaiso",        "nickname": "Beacons",      "city": "Valparaiso",  "state": "IN","conference": "Missouri Valley","home_court": "Athletics-Recreation Center","venue_rating": 48,"tourney": 3,"ff": 0,"titles": 0},
    {"name": "Belmont",           "nickname": "Bruins",       "city": "Nashville",   "state": "TN","conference": "Missouri Valley","home_court": "Curb Event Center",    "venue_rating": 54,"tourney": 8, "ff": 0,"titles": 0},
    # MOUNTAIN WEST
    {"name": "Air Force",      "nickname": "Falcons",       "city": "Colorado Springs","state": "CO","conference": "Mountain West","home_court": "Clune Arena",             "venue_rating": 52,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Boise State",    "nickname": "Broncos",       "city": "Boise",           "state": "ID","conference": "Mountain West","home_court": "ExtraMile Arena",          "venue_rating": 64,"tourney": 12,"ff": 0,"titles": 0},
    {"name": "Colorado State", "nickname": "Rams",          "city": "Fort Collins",    "state": "CO","conference": "Mountain West","home_court": "Moby Arena",              "venue_rating": 66,"tourney": 20,"ff": 1,"titles": 0},
    {"name": "Fresno State",   "nickname": "Bulldogs",      "city": "Fresno",          "state": "CA","conference": "Mountain West","home_court": "Save Mart Center",         "venue_rating": 66,"tourney": 11,"ff": 0,"titles": 0},
    {"name": "Grand Canyon",   "nickname": "Antelopes",     "city": "Phoenix",         "state": "AZ","conference": "Mountain West","home_court": "GCU Arena",               "venue_rating": 62,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Nevada",         "nickname": "Wolf Pack",     "city": "Reno",            "state": "NV","conference": "Mountain West","home_court": "Lawlor Events Center",     "venue_rating": 62,"tourney": 15,"ff": 1,"titles": 0},
    {"name": "New Mexico",     "nickname": "Lobos",         "city": "Albuquerque",     "state": "NM","conference": "Mountain West","home_court": "The Pit",                  "venue_rating": 74,"tourney": 23,"ff": 1,"titles": 0},
    {"name": "San Diego State","nickname": "Aztecs",        "city": "San Diego",       "state": "CA","conference": "Mountain West","home_court": "Viejas Arena",             "venue_rating": 72,"tourney": 22,"ff": 1,"titles": 0},
    {"name": "San Jose State", "nickname": "Spartans",      "city": "San Jose",        "state": "CA","conference": "Mountain West","home_court": "Provident Credit Union Event Center","venue_rating": 52,"tourney": 4,"ff": 0,"titles": 0},
    {"name": "UNLV",           "nickname": "Runnin Rebels", "city": "Las Vegas",       "state": "NV","conference": "Mountain West","home_court": "Thomas & Mack Center",     "venue_rating": 78,"tourney": 29,"ff": 3,"titles": 1},
    {"name": "Utah State",     "nickname": "Aggies",        "city": "Logan",           "state": "UT","conference": "Mountain West","home_court": "Dee Glen Smith Spectrum",  "venue_rating": 66,"tourney": 20,"ff": 0,"titles": 0},
    {"name": "Wyoming",        "nickname": "Cowboys",       "city": "Laramie",         "state": "WY","conference": "Mountain West","home_court": "Arena-Auditorium",         "venue_rating": 58,"tourney": 13,"ff": 0,"titles": 0},
    # NEC
    {"name": "Central Connecticut","nickname": "Blue Devils","city": "New Britain",  "state": "CT","conference": "NEC","home_court": "Detrick Gymnasium",         "venue_rating": 36,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Fairleigh Dickinson","nickname": "Knights",   "city": "Teaneck",       "state": "NJ","conference": "NEC","home_court": "Rothman Center",             "venue_rating": 38,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "LIU",               "nickname": "Sharks",    "city": "Brookville",    "state": "NY","conference": "NEC","home_court": "Steinberg Wellness Center",  "venue_rating": 36,"tourney": 8, "ff": 0,"titles": 0},
    {"name": "Merrimack",         "nickname": "Warriors",  "city": "North Andover", "state": "MA","conference": "NEC","home_court": "Hammel Court",               "venue_rating": 32,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Mount St. Mary's",  "nickname": "Mountaineers","city": "Emmitsburg",  "state": "MD","conference": "NEC","home_court": "Knott Arena",                "venue_rating": 38,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Sacred Heart",      "nickname": "Pioneers",  "city": "Fairfield",     "state": "CT","conference": "NEC","home_court": "William H. Pitt Center",     "venue_rating": 36,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Saint Francis (PA)","nickname": "Red Flash", "city": "Loretto",       "state": "PA","conference": "NEC","home_court": "DeGol Arena",                "venue_rating": 32,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Wagner",            "nickname": "Seahawks",  "city": "Staten Island", "state": "NY","conference": "NEC","home_court": "Spiro Sports Center",        "venue_rating": 34,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Stonehill",           "nickname": "Skyhawks",  "city": "North Easton",  "state": "MA","conference": "NEC","home_court": "Merkert Gymnasium",          "venue_rating": 32,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "St. Francis Brooklyn","nickname": "Terriers","city": "Brooklyn",      "state": "NY","conference": "NEC","home_court": "Pope Physical Education Center","venue_rating": 32,"tourney": 2,"ff": 0,"titles": 0},
    # OHIO VALLEY
    {"name": "Eastern Illinois",        "nickname": "Panthers",    "city": "Charleston",     "state": "IL","conference": "Ohio Valley","home_court": "Lantz Arena",          "venue_rating": 42,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Morehead State",          "nickname": "Eagles",      "city": "Morehead",       "state": "KY","conference": "Ohio Valley","home_court": "Johnson Arena",        "venue_rating": 42,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Southeast Missouri State","nickname": "Redhawks",    "city": "Cape Girardeau", "state": "MO","conference": "Ohio Valley","home_court": "Show Me Center",       "venue_rating": 48,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Tennessee State",         "nickname": "Tigers",      "city": "Nashville",      "state": "TN","conference": "Ohio Valley","home_court": "Gentry Center",        "venue_rating": 40,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Tennessee Tech",          "nickname": "Golden Eagles","city": "Cookeville",    "state": "TN","conference": "Ohio Valley","home_court": "Hooper Eblen Center",  "venue_rating": 46,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "UT Martin",               "nickname": "Skyhawks",    "city": "Martin",         "state": "TN","conference": "Ohio Valley","home_court": "Elam Center",          "venue_rating": 40,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Murray State",            "nickname": "Racers",      "city": "Murray",         "state": "KY","conference": "Ohio Valley","home_court": "CFSB Center",          "venue_rating": 52,"tourney": 15,"ff": 0,"titles": 0},
    {"name": "Lindenwood",              "nickname": "Lions",       "city": "St. Charles",    "state": "MO","conference": "Ohio Valley","home_court": "Hyland Arena",         "venue_rating": 40,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Southern Indiana",        "nickname": "Screaming Eagles","city": "Evansville", "state": "IN","conference": "Ohio Valley","home_court": "PAC",                  "venue_rating": 42,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "SIU Edwardsville",        "nickname": "Cougars",     "city": "Edwardsville",   "state": "IL","conference": "Ohio Valley","home_court": "First Community Arena", "venue_rating": 44,"tourney": 0, "ff": 0,"titles": 0},
    # PATRIOT
    {"name": "American",         "nickname": "Eagles",       "city": "Washington",  "state": "DC","conference": "Patriot","home_court": "Bender Arena",         "venue_rating": 46,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Army",             "nickname": "Black Knights","city": "West Point",  "state": "NY","conference": "Patriot","home_court": "Christl Arena",        "venue_rating": 44,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Boston University","nickname": "Terriers",    "city": "Boston",      "state": "MA","conference": "Patriot","home_court": "Case Gymnasium",       "venue_rating": 46,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Bucknell",         "nickname": "Bison",        "city": "Lewisburg",   "state": "PA","conference": "Patriot","home_court": "Sojka Pavilion",       "venue_rating": 44,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Colgate",          "nickname": "Raiders",      "city": "Hamilton",    "state": "NY","conference": "Patriot","home_court": "Cotterell Court",      "venue_rating": 42,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Holy Cross",       "nickname": "Crusaders",    "city": "Worcester",   "state": "MA","conference": "Patriot","home_court": "Hart Center",          "venue_rating": 46,"tourney": 10,"ff": 0,"titles": 1},
    {"name": "Lafayette",        "nickname": "Leopards",     "city": "Easton",      "state": "PA","conference": "Patriot","home_court": "Kirby Sports Center",  "venue_rating": 42,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Lehigh",           "nickname": "Mountain Hawks","city": "Bethlehem",  "state": "PA","conference": "Patriot","home_court": "Stabler Arena",        "venue_rating": 46,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Loyola Maryland",  "nickname": "Greyhounds",   "city": "Baltimore",   "state": "MD","conference": "Patriot","home_court": "Reitz Arena",          "venue_rating": 42,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Navy",             "nickname": "Midshipmen",   "city": "Annapolis",   "state": "MD","conference": "Patriot","home_court": "Alumni Hall",          "venue_rating": 44,"tourney": 4, "ff": 0,"titles": 0},
    # SEC
    {"name": "Alabama",       "nickname": "Crimson Tide","city": "Tuscaloosa",    "state": "AL","conference": "SEC","home_court": "Coleman Coliseum",              "venue_rating": 76,"tourney": 32,"ff": 4, "titles": 1},
    {"name": "Arkansas",      "nickname": "Razorbacks",  "city": "Fayetteville", "state": "AR","conference": "SEC","home_court": "Bud Walton Arena",              "venue_rating": 80,"tourney": 31,"ff": 6, "titles": 1},
    {"name": "Auburn",        "nickname": "Tigers",      "city": "Auburn",        "state": "AL","conference": "SEC","home_court": "Neville Arena",                "venue_rating": 72,"tourney": 24,"ff": 3, "titles": 0},
    {"name": "Florida",       "nickname": "Gators",      "city": "Gainesville",   "state": "FL","conference": "SEC","home_court": "Exactech Arena",               "venue_rating": 78,"tourney": 33,"ff": 7, "titles": 2},
    {"name": "Georgia",       "nickname": "Bulldogs",    "city": "Athens",        "state": "GA","conference": "SEC","home_court": "Stegeman Coliseum",            "venue_rating": 68,"tourney": 16,"ff": 0, "titles": 0},
    {"name": "Kentucky",      "nickname": "Wildcats",    "city": "Lexington",     "state": "KY","conference": "SEC","home_court": "Rupp Arena",                   "venue_rating": 97,"tourney": 61,"ff": 19,"titles": 8},
    {"name": "LSU",           "nickname": "Tigers",      "city": "Baton Rouge",   "state": "LA","conference": "SEC","home_court": "Pete Maravich Assembly Center", "venue_rating": 80,"tourney": 28,"ff": 4, "titles": 0},
    {"name": "Mississippi State","nickname": "Bulldogs", "city": "Starkville",    "state": "MS","conference": "SEC","home_court": "Humphrey Coliseum",            "venue_rating": 66,"tourney": 25,"ff": 1, "titles": 0},
    {"name": "Missouri",      "nickname": "Tigers",      "city": "Columbia",      "state": "MO","conference": "SEC","home_court": "Mizzou Arena",                 "venue_rating": 72,"tourney": 18,"ff": 0, "titles": 0},
    {"name": "Ole Miss",      "nickname": "Rebels",      "city": "Oxford",        "state": "MS","conference": "SEC","home_court": "The Sandy and John Black Pavilion","venue_rating": 70,"tourney": 17,"ff": 0,"titles": 0},
    {"name": "South Carolina","nickname": "Gamecocks",   "city": "Columbia",      "state": "SC","conference": "SEC","home_court": "Colonial Life Arena",          "venue_rating": 74,"tourney": 21,"ff": 2, "titles": 0},
    {"name": "Tennessee",     "nickname": "Volunteers",  "city": "Knoxville",     "state": "TN","conference": "SEC","home_court": "Thompson-Boling Arena",         "venue_rating": 80,"tourney": 27,"ff": 1, "titles": 0},
    {"name": "Texas A&M",     "nickname": "Aggies",      "city": "College Station","state": "TX","conference": "SEC","home_court": "Reed Arena",                  "venue_rating": 72,"tourney": 19,"ff": 1, "titles": 0},
    {"name": "Vanderbilt",    "nickname": "Commodores",  "city": "Nashville",     "state": "TN","conference": "SEC","home_court": "Memorial Gymnasium",           "venue_rating": 66,"tourney": 21,"ff": 1, "titles": 0},
    # SOUTHERN
    {"name": "Chattanooga",       "nickname": "Mocs",       "city": "Chattanooga", "state": "TN","conference": "Southern","home_court": "McKenzie Arena",               "venue_rating": 56,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "East Tennessee State","nickname": "Buccaneers","city": "Johnson City","state": "TN","conference": "Southern","home_court": "Freedom Hall Civic Center",     "venue_rating": 52,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Furman",            "nickname": "Paladins",   "city": "Greenville",  "state": "SC","conference": "Southern","home_court": "Timmons Arena",                "venue_rating": 46,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Mercer",            "nickname": "Bears",      "city": "Macon",       "state": "GA","conference": "Southern","home_court": "Hawkins Arena",                "venue_rating": 42,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Samford",           "nickname": "Bulldogs",   "city": "Birmingham",  "state": "AL","conference": "Southern","home_court": "Pete Hanna Center",            "venue_rating": 44,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "UNC Greensboro",    "nickname": "Spartans",   "city": "Greensboro",  "state": "NC","conference": "Southern","home_court": "Fleming Gymnasium",            "venue_rating": 44,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "VMI",               "nickname": "Keydets",    "city": "Lexington",   "state": "VA","conference": "Southern","home_court": "Cameron Hall",                 "venue_rating": 38,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Western Carolina",  "nickname": "Catamounts", "city": "Cullowhee",   "state": "NC","conference": "Southern","home_court": "Ramsey Regional Activity Center","venue_rating": 44,"tourney": 1,"ff": 0,"titles": 0},
    {"name": "Wofford",           "nickname": "Terriers",   "city": "Spartanburg", "state": "SC","conference": "Southern","home_court": "Jerry Richardson Indoor Stadium","venue_rating": 46,"tourney": 4,"ff": 0,"titles": 0},
    # SOUTHLAND
    {"name": "Houston Christian",     "nickname": "Huskies",     "city": "Houston",      "state": "TX","conference": "Southland","home_court": "Bradshaw Fieldhouse",         "venue_rating": 40,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Lamar",                 "nickname": "Cardinals",   "city": "Beaumont",     "state": "TX","conference": "Southland","home_court": "Montagne Center",             "venue_rating": 44,"tourney": 10,"ff": 0,"titles": 0},
    {"name": "McNeese",               "nickname": "Cowboys",     "city": "Lake Charles", "state": "LA","conference": "Southland","home_court": "Burton Coliseum",             "venue_rating": 40,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "New Orleans",           "nickname": "Privateers",  "city": "New Orleans",  "state": "LA","conference": "Southland","home_court": "Lakefront Arena",             "venue_rating": 44,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Nicholls",              "nickname": "Colonels",    "city": "Thibodaux",    "state": "LA","conference": "Southland","home_court": "Stopher Gymnasium",           "venue_rating": 36,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Northwestern State",    "nickname": "Demons",      "city": "Natchitoches", "state": "LA","conference": "Southland","home_court": "Prather Coliseum",            "venue_rating": 38,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Southeastern Louisiana","nickname": "Lions",       "city": "Hammond",      "state": "LA","conference": "Southland","home_court": "University Center",           "venue_rating": 38,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Stephen F. Austin",     "nickname": "Lumberjacks", "city": "Nacogdoches",  "state": "TX","conference": "Southland","home_court": "William R. Johnson Coliseum", "venue_rating": 42,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Incarnate Word",        "nickname": "Cardinals",   "city": "San Antonio",  "state": "TX","conference": "Southland","home_court": "McDermott Convocation Center","venue_rating": 38,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Texas A&M-Corpus Christi","nickname": "Islanders", "city": "Corpus Christi","state": "TX","conference": "Southland","home_court": "American Bank Center",       "venue_rating": 40,"tourney": 1, "ff": 0,"titles": 0},
    # SWAC
    {"name": "Alabama A&M",          "nickname": "Bulldogs",    "city": "Huntsville",    "state": "AL","conference": "SWAC","home_court": "Alabama A&M Events Center",         "venue_rating": 34,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Alabama State",        "nickname": "Hornets",     "city": "Montgomery",    "state": "AL","conference": "SWAC","home_court": "Dunn-Oliver Acadome",               "venue_rating": 38,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Alcorn State",         "nickname": "Braves",      "city": "Lorman",        "state": "MS","conference": "SWAC","home_court": "Davey Whitney Complex",             "venue_rating": 32,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "Arkansas-Pine Bluff",  "nickname": "Golden Lions","city": "Pine Bluff",    "state": "AR","conference": "SWAC","home_court": "K. L. Johnson Complex",             "venue_rating": 30,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Bethune-Cookman",      "nickname": "Wildcats",    "city": "Daytona Beach", "state": "FL","conference": "SWAC","home_court": "Moore Gymnasium",                   "venue_rating": 30,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Grambling State",      "nickname": "Tigers",      "city": "Grambling",     "state": "LA","conference": "SWAC","home_court": "Fredrick C. Hobdy Assembly Center",  "venue_rating": 32,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Jackson State",        "nickname": "Tigers",      "city": "Jackson",       "state": "MS","conference": "SWAC","home_court": "Williams Assembly Center",           "venue_rating": 34,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Mississippi Valley State","nickname": "Delta Devils","city": "Itta Bena",  "state": "MS","conference": "SWAC","home_court": "Harrison HPER Complex",             "venue_rating": 28,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Prairie View A&M",     "nickname": "Panthers",    "city": "Prairie View",  "state": "TX","conference": "SWAC","home_court": "William Nicks Building",            "venue_rating": 30,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Southern",             "nickname": "Jaguars",     "city": "Baton Rouge",   "state": "LA","conference": "SWAC","home_court": "F. G. Clark Center",                "venue_rating": 36,"tourney": 9, "ff": 0,"titles": 0},
    {"name": "Texas Southern",       "nickname": "Tigers",      "city": "Houston",       "state": "TX","conference": "SWAC","home_court": "Health and Physical Education Arena","venue_rating": 38,"tourney": 11,"ff": 0,"titles": 0},
    # SUMMIT LEAGUE
    {"name": "Kansas City",        "nickname": "Roos",          "city": "Kansas City", "state": "MO","conference": "Summit","home_court": "Swinney Recreation Center",    "venue_rating": 40,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "North Dakota",       "nickname": "Fighting Hawks", "city": "Grand Forks", "state": "ND","conference": "Summit","home_court": "Betty Engelstad Sioux Center", "venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "North Dakota State",  "nickname": "Bison",         "city": "Fargo",       "state": "ND","conference": "Summit","home_court": "Bison Sports Arena",           "venue_rating": 46,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Omaha",              "nickname": "Mavericks",     "city": "Omaha",       "state": "NE","conference": "Summit","home_court": "Baxter Arena",                 "venue_rating": 52,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Oral Roberts",       "nickname": "Golden Eagles", "city": "Tulsa",       "state": "OK","conference": "Summit","home_court": "Mabee Center",                 "venue_rating": 52,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "South Dakota",       "nickname": "Coyotes",       "city": "Vermillion",  "state": "SD","conference": "Summit","home_court": "Sanford Coyote Sports Center", "venue_rating": 48,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "South Dakota State", "nickname": "Jackrabbits",   "city": "Brookings",   "state": "SD","conference": "Summit","home_court": "Frost Arena",                  "venue_rating": 50,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Western Illinois",   "nickname": "Leathernecks",  "city": "Macomb",      "state": "IL","conference": "Summit","home_court": "Western Hall",                 "venue_rating": 42,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Denver",             "nickname": "Pioneers",      "city": "Denver",      "state": "CO","conference": "Summit","home_court": "Magness Arena",                "venue_rating": 46,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "St. Thomas",         "nickname": "Tommies",       "city": "St. Paul",    "state": "MN","conference": "Summit","home_court": "Schoenecker Arena",            "venue_rating": 40,"tourney": 0, "ff": 0,"titles": 0},
    # SUN BELT
    {"name": "Appalachian State","nickname": "Mountaineers","city": "Boone",       "state": "NC","conference": "Sun Belt","home_court": "Holmes Convocation Center", "venue_rating": 50,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Arkansas State",   "nickname": "Red Wolves",  "city": "Jonesboro",   "state": "AR","conference": "Sun Belt","home_court": "First National Bank Arena", "venue_rating": 48,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Coastal Carolina", "nickname": "Chanticleers","city": "Conway",      "state": "SC","conference": "Sun Belt","home_court": "HTC Center",               "venue_rating": 46,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "Georgia Southern", "nickname": "Eagles",      "city": "Statesboro",  "state": "GA","conference": "Sun Belt","home_court": "Hanner Fieldhouse",        "venue_rating": 44,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Georgia State",    "nickname": "Panthers",    "city": "Atlanta",     "state": "GA","conference": "Sun Belt","home_court": "GSU Sports Arena",         "venue_rating": 50,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "James Madison",    "nickname": "Dukes",       "city": "Harrisonburg","state": "VA","conference": "Sun Belt","home_court": "Atlantic Union Bank Center","venue_rating": 52,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "Louisiana",        "nickname": "Ragin Cajuns","city": "Lafayette",   "state": "LA","conference": "Sun Belt","home_court": "Cajundome",                "venue_rating": 58,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Louisiana-Monroe", "nickname": "Warhawks",    "city": "Monroe",      "state": "LA","conference": "Sun Belt","home_court": "Fant-Ewing Coliseum",      "venue_rating": 44,"tourney": 7, "ff": 0,"titles": 0},
    {"name": "Marshall",         "nickname": "Thundering Herd","city": "Huntington","state": "WV","conference": "Sun Belt","home_court": "Cam Henderson Center",    "venue_rating": 52,"tourney": 6, "ff": 0,"titles": 0},
    {"name": "Old Dominion",     "nickname": "Monarchs",    "city": "Norfolk",     "state": "VA","conference": "Sun Belt","home_court": "Chartway Arena",           "venue_rating": 56,"tourney": 12,"ff": 0,"titles": 0},
    {"name": "South Alabama",    "nickname": "Jaguars",     "city": "Mobile",      "state": "AL","conference": "Sun Belt","home_court": "Mitchell Center",          "venue_rating": 50,"tourney": 8, "ff": 0,"titles": 0},
    {"name": "Southern Miss",    "nickname": "Golden Eagles","city": "Hattiesburg","state": "MS","conference": "Sun Belt","home_court": "Reed Green Coliseum",      "venue_rating": 50,"tourney": 3, "ff": 0,"titles": 0},
    {"name": "Texas State",      "nickname": "Bobcats",     "city": "San Marcos",  "state": "TX","conference": "Sun Belt","home_court": "Strahan Coliseum",         "venue_rating": 48,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Troy",             "nickname": "Trojans",     "city": "Troy",        "state": "AL","conference": "Sun Belt","home_court": "Trojan Arena",             "venue_rating": 44,"tourney": 3, "ff": 0,"titles": 0},
    # WCC
    {"name": "Gonzaga",         "nickname": "Bulldogs",    "city": "Spokane",       "state": "WA","conference": "WCC","home_court": "McCarthey Athletic Center",         "venue_rating": 82,"tourney": 27,"ff": 2,"titles": 0},
    {"name": "Loyola Marymount","nickname": "Lions",       "city": "Los Angeles",   "state": "CA","conference": "WCC","home_court": "Gersten Pavilion",                 "venue_rating": 50,"tourney": 5, "ff": 0,"titles": 0},
    {"name": "Oregon State",    "nickname": "Beavers",     "city": "Corvallis",     "state": "OR","conference": "WCC","home_court": "Gill Coliseum",                    "venue_rating": 64,"tourney": 18,"ff": 2,"titles": 0},
    {"name": "Pacific",         "nickname": "Tigers",      "city": "Stockton",      "state": "CA","conference": "WCC","home_court": "Alex G. Spanos Center",            "venue_rating": 50,"tourney": 9, "ff": 0,"titles": 0},
    {"name": "Pepperdine",      "nickname": "Waves",       "city": "Malibu",        "state": "CA","conference": "WCC","home_court": "Firestone Fieldhouse",             "venue_rating": 52,"tourney": 13,"ff": 0,"titles": 0},
    {"name": "Portland",        "nickname": "Pilots",      "city": "Portland",      "state": "OR","conference": "WCC","home_court": "Chiles Center",                    "venue_rating": 48,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Saint Mary's",    "nickname": "Gaels",       "city": "Moraga",        "state": "CA","conference": "WCC","home_court": "University Credit Union Pavilion", "venue_rating": 62,"tourney": 14,"ff": 0,"titles": 0},
    {"name": "San Diego",       "nickname": "Toreros",     "city": "San Diego",     "state": "CA","conference": "WCC","home_court": "Jenny Craig Pavilion",             "venue_rating": 48,"tourney": 4, "ff": 0,"titles": 0},
    {"name": "San Francisco",   "nickname": "Dons",        "city": "San Francisco", "state": "CA","conference": "WCC","home_court": "The Sobrato Center",               "venue_rating": 52,"tourney": 16,"ff": 3,"titles": 2},
    {"name": "Santa Clara",     "nickname": "Broncos",     "city": "Santa Clara",   "state": "CA","conference": "WCC","home_court": "Leavey Center",                    "venue_rating": 50,"tourney": 11,"ff": 1,"titles": 0},
    {"name": "Seattle",         "nickname": "Redhawks",    "city": "Seattle",       "state": "WA","conference": "WCC","home_court": "Redhawk Center",                   "venue_rating": 46,"tourney": 11,"ff": 1,"titles": 0},
    {"name": "Washington State","nickname": "Cougars",     "city": "Pullman",       "state": "WA","conference": "WCC","home_court": "Beasley Coliseum",                 "venue_rating": 60,"tourney": 7, "ff": 1,"titles": 0},
    # WAC
    {"name": "Abilene Christian", "nickname": "Wildcats",    "city": "Abilene",       "state": "TX","conference": "WAC","home_court": "Moody Coliseum",             "venue_rating": 40,"tourney": 2, "ff": 0,"titles": 0},
    {"name": "Southern Utah",     "nickname": "Thunderbirds","city": "Cedar City",    "state": "UT","conference": "WAC","home_court": "America First Event Center",  "venue_rating": 42,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Tarleton State",    "nickname": "Texans",      "city": "Stephenville",  "state": "TX","conference": "WAC","home_court": "EECU Center",                 "venue_rating": 38,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "UT Arlington",      "nickname": "Mavericks",   "city": "Arlington",     "state": "TX","conference": "WAC","home_court": "College Park Center",         "venue_rating": 46,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "Utah Valley",       "nickname": "Wolverines",  "city": "Orem",          "state": "UT","conference": "WAC","home_court": "UCCU Center",                 "venue_rating": 44,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Dixie State",        "nickname": "Trailblazers","city": "St. George",    "state": "UT","conference": "WAC","home_court": "Burns Arena",                 "venue_rating": 40,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "California Baptist","nickname": "Lancers",     "city": "Riverside",     "state": "CA","conference": "WAC","home_court": "CBU Events Center",           "venue_rating": 42,"tourney": 0, "ff": 0,"titles": 0},
    {"name": "Seattle U",         "nickname": "Redhawks",    "city": "Seattle",       "state": "WA","conference": "WAC","home_court": "Redhawk Center WAC",          "venue_rating": 44,"tourney": 1, "ff": 0,"titles": 0},
    {"name": "UMKC",              "nickname": "Kangaroos",   "city": "Kansas City",   "state": "MO","conference": "WAC","home_court": "Swinney Recreation Center WAC","venue_rating": 40,"tourney": 0, "ff": 0,"titles": 0},
]


def build_all_d1_programs():
    from program import create_program
    from coach import ARCHETYPE_WEIGHTS, seed_legacy_coach

    archetypes = list(ARCHETYPE_WEIGHTS.keys())
    weights    = list(ARCHETYPE_WEIGHTS.values())

    programs = []
    for data in ALL_D1_PROGRAMS:
        prestige  = calc_prestige(data["tourney"], data["ff"], data["titles"], data["conference"])
        gravity   = get_gravity(prestige, data["conference"])
        archetype = random.choices(archetypes, weights=weights, k=1)[0]

        # Prestige-calibrated experience range at world build.
        # Blue blood coaches are veterans. Floor conf coaches may be less experienced
        # but still have real HC history -- nobody starts day 1 at a D1 program.
        if prestige >= 90:
            exp = random.randint(12, 28)   # blue blood -- seasoned veterans
        elif prestige >= 75:
            exp = random.randint(8, 22)    # elite -- established coaches
        elif prestige >= 59:
            exp = random.randint(6, 18)    # strong -- solid mid-career
        elif prestige >= 39:
            exp = random.randint(4, 15)    # average -- mix of experience
        elif prestige >= 21:
            exp = random.randint(3, 12)    # below average -- younger coaches OK
        else:
            exp = random.randint(2, 10)    # poor/floor -- first-time HCs happen here

        p = create_program(
            name=data["name"],
            nickname=data["nickname"],
            city=data["city"],
            state=data["state"],
            division="D1",
            conference=data["conference"],
            home_court=data["home_court"],
            venue_rating=data["venue_rating"],
            prestige_current=prestige,
            prestige_gravity=gravity,
            coach_name=get_coach_name(data["name"]),
            coach_archetype=archetype,
            coach_experience=exp,
        )

        # Stamp coordinates from schools_database for geographic calculations
        # (tournament site selection, recruiting distance, travel fatigue)
        try:
            from schools_database import SCHOOLS_DATABASE
            school = next(
                (s for s in SCHOOLS_DATABASE.values()
                 if s["name"].lower() == data["name"].lower()
                 and s["division"] == "D1"),
                None
            )
            # Fallback: match by city if name doesn't match exactly
            if not school:
                school = next(
                    (s for s in SCHOOLS_DATABASE.values()
                     if s["city"].lower() == data["city"].lower()
                     and s["state"].lower() == data["state"].lower()
                     and s["division"] == "D1"),
                    None
                )
            if school:
                p["latitude"]  = school["latitude"]
                p["longitude"] = school["longitude"]
            else:
                # Hard fallback: center of US — logs a warning
                p["latitude"]  = 39.5
                p["longitude"] = -98.5
        except Exception:
            p["latitude"]  = 39.5
            p["longitude"] = -98.5

        # v0.7: seed legacy history for established programs (75+ prestige)
        if prestige >= 75:
            seed_legacy_coach(p["coach"], prestige)
            p["coach_seasons"] = p["coach"]["seasons_at_program"]

        # Seed scheduling_aggression -- fixed coach personality trait (1-10).
        # Drives non-conference scheduling behavior: road game willingness,
        # quality of opponents sought, neutral site appetite.
        # Capped by conference tier -- floor_conf programs max out at 3
        # regardless of coach (program reality overrides personality).
        conf_tier = get_conference_tier(data["conference"])["tier"]
        if conf_tier == "power":
            # Power: full range, weighted toward middle (5-7 most common)
            aggression = random.choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                weights=[2, 3, 5, 8, 14, 16, 18, 16, 10, 8],
                k=1
            )[0]
        elif conf_tier == "high_major":
            # High major: slightly less aggressive on average
            aggression = random.choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                weights=[3, 5, 8, 12, 16, 18, 16, 12, 6, 4],
                k=1
            )[0]
        elif conf_tier == "mid_major":
            # Mid major: centered around 4-6
            aggression = random.choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                weights=[4, 7, 12, 16, 18, 16, 12, 8, 4, 3],
                k=1
            )[0]
        elif conf_tier == "low_major":
            # Low major: lower aggression, take the paycheck games
            aggression = random.choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                weights=[10, 16, 18, 16, 14, 10, 8, 5, 2, 1],
                k=1
            )[0]
        else:
            # floor_conf: almost entirely road paycheck games, cap at 3
            aggression = random.choices(
                [1, 2, 3],
                weights=[40, 40, 20],
                k=1
            )[0]

        p["coach"]["scheduling_aggression"] = aggression
        p["scheduling_aggression"] = aggression  # convenience shortcut

        programs.append(p)
    return programs


if __name__ == "__main__":
    programs = build_all_d1_programs()
    print("Total D1 programs: " + str(len(programs)))
    for tier_name in ["power", "high_major", "mid_major", "low_major", "floor_conf"]:
        tp = [p for p in programs if CONFERENCE_TIERS.get(p["conference"], _DEFAULT_TIER)["tier"] == tier_name]
        if not tp:
            continue
        avg_p = sum(p["prestige_current"] for p in tp) / len(tp)
        t = CONFERENCE_TIERS.get(tp[0]["conference"], _DEFAULT_TIER)
        print("{:<12} {:>3} programs  avg prestige: {:.1f}  ceiling: {}  floor: {}".format(
            tier_name, len(tp), avg_p, t["ceiling"], t["floor"]))
    above = [p for p in programs
             if p["prestige_current"] > get_conference_ceiling(p["conference"])
             and get_conference_ceiling(p["conference"]) < 100]
    print("\nPrograms above conference ceiling at world-build: " + str(len(above)))
    for p in sorted(above, key=lambda x: x["prestige_current"], reverse=True)[:5]:
        print("  " + p["name"] + " (" + p["conference"] + ")  " +
              str(p["prestige_current"]) + " > ceiling " + str(get_conference_ceiling(p["conference"])))
