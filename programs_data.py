import random
from names import generate_coach_name

# -----------------------------------------
# COLLEGE HOOPS SIM -- Full D1 Program Database v0.3
# ~329 D1 programs with real data
# Prestige v3 formula with conference floors
# -----------------------------------------

# Conference tier floors -- gravity never falls below these
CONFERENCE_FLOORS = {
    # Power conferences
    "ACC": 45, "Big Ten": 45, "Big 12": 45, "SEC": 45, "Big East": 45,
    # High major
    "American": 30, "A-10": 30, "Mountain West": 30, "WCC": 30,
    # Mid major
    "Missouri Valley": 20, "MAC": 20, "CAA": 20, "Atlantic Sun": 20,
    "ASUN": 20, "Big Sky": 20, "Big South": 20, "Horizon": 20,
    "MAAC": 20, "Ohio Valley": 20, "Patriot": 20, "Southern": 20,
    "Southland": 20, "Summit": 20, "Sun Belt": 20, "Big West": 20,
    "Ivy League": 20,
    # Low major
    "SWAC": 8, "MEAC": 8, "NEC": 8, "WAC": 8,
    "America East": 12,
}

def calc_prestige(tourney, ff, titles, conference):
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

    floor = CONFERENCE_FLOORS.get(conference, 15)
    return max(floor, min(97, round(score)))


def get_gravity(prestige, conference):
    floor = CONFERENCE_FLOORS.get(conference, 15)
    return max(floor, prestige - random.randint(2, 5))


def get_coach_name(school_name):
    return generate_coach_name()


ALL_D1_PROGRAMS = [

    # AMERICA EAST
    {"name": "Albany",          "nickname": "Great Danes",    "city": "Albany",       "state": "NY", "conference": "America East", "home_court": "SEFCU Arena",                         "venue_rating": 45, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Binghamton",      "nickname": "Bearcats",       "city": "Binghamton",   "state": "NY", "conference": "America East", "home_court": "Binghamton Events Center",             "venue_rating": 42, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Bryant",          "nickname": "Bulldogs",       "city": "Smithfield",   "state": "RI", "conference": "America East", "home_court": "Chace Athletic Center",                "venue_rating": 38, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Maine",           "nickname": "Black Bears",    "city": "Orono",        "state": "ME", "conference": "America East", "home_court": "Memorial Gymnasium",                   "venue_rating": 40, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "UMBC",            "nickname": "Retrievers",     "city": "Baltimore",    "state": "MD", "conference": "America East", "home_court": "Chesapeake Employers Insurance Arena",  "venue_rating": 44, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "UMass Lowell",    "nickname": "River Hawks",    "city": "Lowell",       "state": "MA", "conference": "America East", "home_court": "Tsongas Center",                       "venue_rating": 46, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "New Hampshire",   "nickname": "Wildcats",       "city": "Durham",       "state": "NH", "conference": "America East", "home_court": "Lundholm Gym",                         "venue_rating": 36, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Vermont",         "nickname": "Catamounts",     "city": "Burlington",   "state": "VT", "conference": "America East", "home_court": "Patrick Gym",                          "venue_rating": 48, "tourney": 10, "ff": 0, "titles": 0},

    # AMERICAN ATHLETIC
    {"name": "Charlotte",       "nickname": "49ers",           "city": "Charlotte",    "state": "NC", "conference": "American", "home_court": "Halton Arena",                      "venue_rating": 58, "tourney": 11, "ff": 1, "titles": 0},
    {"name": "East Carolina",   "nickname": "Pirates",         "city": "Greenville",   "state": "NC", "conference": "American", "home_court": "Williams Arena at Minges Coliseum",  "venue_rating": 52, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Florida Atlantic", "nickname": "Owls",           "city": "Boca Raton",   "state": "FL", "conference": "American", "home_court": "Eleanor R. Baldwin Arena",           "venue_rating": 50, "tourney": 3,  "ff": 1, "titles": 0},
    {"name": "Memphis",         "nickname": "Tigers",          "city": "Memphis",      "state": "TN", "conference": "American", "home_court": "FedExForum",                        "venue_rating": 82, "tourney": 29, "ff": 3, "titles": 0},
    {"name": "North Texas",     "nickname": "Mean Green",      "city": "Denton",       "state": "TX", "conference": "American", "home_court": "UNT Coliseum",                      "venue_rating": 50, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Rice",            "nickname": "Owls",            "city": "Houston",      "state": "TX", "conference": "American", "home_court": "Tudor Fieldhouse",                  "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "South Florida",   "nickname": "Bulls",           "city": "Tampa",        "state": "FL", "conference": "American", "home_court": "Yuengling Center",                  "venue_rating": 55, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Temple",          "nickname": "Owls",            "city": "Philadelphia", "state": "PA", "conference": "American", "home_court": "Liacouras Center",                  "venue_rating": 66, "tourney": 33, "ff": 2, "titles": 0},
    {"name": "UAB",             "nickname": "Blazers",         "city": "Birmingham",   "state": "AL", "conference": "American", "home_court": "Bartow Arena",                      "venue_rating": 58, "tourney": 17, "ff": 0, "titles": 0},
    {"name": "Tulane",          "nickname": "Green Wave",      "city": "New Orleans",  "state": "LA", "conference": "American", "home_court": "Devlin Fieldhouse",                 "venue_rating": 50, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Tulsa",           "nickname": "Golden Hurricane", "city": "Tulsa",       "state": "OK", "conference": "American", "home_court": "Reynolds Center",                   "venue_rating": 60, "tourney": 16, "ff": 0, "titles": 0},
    {"name": "Wichita State",   "nickname": "Shockers",        "city": "Wichita",      "state": "KS", "conference": "American", "home_court": "Charles Koch Arena",                "venue_rating": 68, "tourney": 16, "ff": 2, "titles": 0},
    {"name": "UTSA",            "nickname": "Roadrunners",     "city": "San Antonio",  "state": "TX", "conference": "American", "home_court": "Convocation Center",                "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},

    # ACC
    {"name": "Boston College",  "nickname": "Eagles",          "city": "Chestnut Hill","state": "MA", "conference": "ACC", "home_court": "Conte Forum",                               "venue_rating": 65, "tourney": 18, "ff": 0,  "titles": 0},
    {"name": "California",      "nickname": "Golden Bears",    "city": "Berkeley",     "state": "CA", "conference": "ACC", "home_court": "Haas Pavilion",                             "venue_rating": 70, "tourney": 19, "ff": 3,  "titles": 1},
    {"name": "Clemson",         "nickname": "Tigers",          "city": "Clemson",      "state": "SC", "conference": "ACC", "home_court": "Littlejohn Coliseum",                       "venue_rating": 64, "tourney": 15, "ff": 0,  "titles": 0},
    {"name": "Duke",            "nickname": "Blue Devils",     "city": "Durham",       "state": "NC", "conference": "ACC", "home_court": "Cameron Indoor Stadium",                    "venue_rating": 99, "tourney": 48, "ff": 18, "titles": 5},
    {"name": "Florida State",   "nickname": "Seminoles",       "city": "Tallahassee",  "state": "FL", "conference": "ACC", "home_court": "Donald L. Tucker Center",                   "venue_rating": 65, "tourney": 18, "ff": 1,  "titles": 0},
    {"name": "Georgia Tech",    "nickname": "Yellow Jackets",  "city": "Atlanta",      "state": "GA", "conference": "ACC", "home_court": "Hank McCamish Pavilion",                    "venue_rating": 66, "tourney": 17, "ff": 2,  "titles": 0},
    {"name": "Louisville",      "nickname": "Cardinals",       "city": "Louisville",   "state": "KY", "conference": "ACC", "home_court": "KFC Yum! Center",                           "venue_rating": 88, "tourney": 44, "ff": 10, "titles": 3},
    {"name": "Miami",           "nickname": "Hurricanes",      "city": "Coral Gables", "state": "FL", "conference": "ACC", "home_court": "Watsco Center",                             "venue_rating": 62, "tourney": 12, "ff": 1,  "titles": 0},
    {"name": "North Carolina",  "nickname": "Tar Heels",       "city": "Chapel Hill",  "state": "NC", "conference": "ACC", "home_court": "Dean Smith Center",                         "venue_rating": 91, "tourney": 54, "ff": 21, "titles": 6},
    {"name": "NC State",        "nickname": "Wolfpack",        "city": "Raleigh",      "state": "NC", "conference": "ACC", "home_court": "PNC Arena",                                 "venue_rating": 76, "tourney": 29, "ff": 4,  "titles": 2},
    {"name": "Notre Dame",      "nickname": "Fighting Irish",  "city": "Notre Dame",   "state": "IN", "conference": "ACC", "home_court": "Edmund P. Joyce Center",                    "venue_rating": 74, "tourney": 38, "ff": 1,  "titles": 0},
    {"name": "Pittsburgh",      "nickname": "Panthers",        "city": "Pittsburgh",   "state": "PA", "conference": "ACC", "home_court": "Petersen Events Center",                    "venue_rating": 74, "tourney": 27, "ff": 1,  "titles": 0},
    {"name": "SMU",             "nickname": "Mustangs",        "city": "Dallas",       "state": "TX", "conference": "ACC", "home_court": "Moody Coliseum",                            "venue_rating": 60, "tourney": 12, "ff": 1,  "titles": 0},
    {"name": "Stanford",        "nickname": "Cardinal",        "city": "Stanford",     "state": "CA", "conference": "ACC", "home_court": "Maples Pavilion",                           "venue_rating": 72, "tourney": 17, "ff": 2,  "titles": 1},
    {"name": "Syracuse",        "nickname": "Orange",          "city": "Syracuse",     "state": "NY", "conference": "ACC", "home_court": "Carrier Dome",                              "venue_rating": 85, "tourney": 41, "ff": 6,  "titles": 1},
    {"name": "Virginia",        "nickname": "Cavaliers",       "city": "Charlottesville","state":"VA", "conference": "ACC", "home_court": "John Paul Jones Arena",                    "venue_rating": 74, "tourney": 27, "ff": 3,  "titles": 1},
    {"name": "Virginia Tech",   "nickname": "Hokies",          "city": "Blacksburg",   "state": "VA", "conference": "ACC", "home_court": "Cassell Coliseum",                          "venue_rating": 65, "tourney": 13, "ff": 0,  "titles": 0},
    {"name": "Wake Forest",     "nickname": "Demon Deacons",   "city": "Winston-Salem","state": "NC", "conference": "ACC", "home_court": "Lawrence Joel Veterans Memorial Coliseum",  "venue_rating": 62, "tourney": 24, "ff": 1,  "titles": 0},

    # ASUN
    {"name": "Austin Peay",     "nickname": "Governors",  "city": "Clarksville",  "state": "TN", "conference": "ASUN", "home_court": "F&M Bank Arena",       "venue_rating": 44, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Eastern Kentucky","nickname": "Colonels",   "city": "Richmond",     "state": "KY", "conference": "ASUN", "home_court": "Baptist Health Arena",  "venue_rating": 44, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Florida Gulf Coast","nickname": "Eagles",   "city": "Fort Myers",   "state": "FL", "conference": "ASUN", "home_court": "Alico Arena",           "venue_rating": 48, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Jacksonville",    "nickname": "Dolphins",   "city": "Jacksonville", "state": "FL", "conference": "ASUN", "home_court": "Swisher Gymnasium",     "venue_rating": 40, "tourney": 5,  "ff": 1, "titles": 0},
    {"name": "Lipscomb",        "nickname": "Bisons",     "city": "Nashville",    "state": "TN", "conference": "ASUN", "home_court": "Allen Arena",           "venue_rating": 42, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "North Florida",   "nickname": "Ospreys",    "city": "Jacksonville", "state": "FL", "conference": "ASUN", "home_court": "UNF Arena",             "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Stetson",         "nickname": "Hatters",    "city": "DeLand",       "state": "FL", "conference": "ASUN", "home_court": "Edmunds Center",        "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},

    # ATLANTIC 10
    {"name": "Davidson",        "nickname": "Wildcats",        "city": "Davidson",     "state": "NC", "conference": "A-10", "home_court": "John M. Belk Arena",           "venue_rating": 52, "tourney": 15, "ff": 0, "titles": 0},
    {"name": "Dayton",          "nickname": "Flyers",          "city": "Dayton",       "state": "OH", "conference": "A-10", "home_court": "University of Dayton Arena",   "venue_rating": 72, "tourney": 20, "ff": 1, "titles": 0},
    {"name": "Duquesne",        "nickname": "Dukes",           "city": "Pittsburgh",   "state": "PA", "conference": "A-10", "home_court": "UPMC Cooper Fieldhouse",       "venue_rating": 55, "tourney": 6,  "ff": 1, "titles": 0},
    {"name": "Fordham",         "nickname": "Rams",            "city": "Bronx",        "state": "NY", "conference": "A-10", "home_court": "Rose Hill Gymnasium",          "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "George Mason",    "nickname": "Patriots",        "city": "Fairfax",      "state": "VA", "conference": "A-10", "home_court": "EagleBank Arena",              "venue_rating": 58, "tourney": 6,  "ff": 1, "titles": 0},
    {"name": "George Washington","nickname": "Revolutionaries","city": "Washington",   "state": "DC", "conference": "A-10", "home_court": "Charles E. Smith Center",      "venue_rating": 55, "tourney": 11, "ff": 0, "titles": 0},
    {"name": "La Salle",        "nickname": "Explorers",       "city": "Philadelphia", "state": "PA", "conference": "A-10", "home_court": "Tom Gola Arena",               "venue_rating": 50, "tourney": 12, "ff": 2, "titles": 1},
    {"name": "Loyola Chicago",  "nickname": "Ramblers",        "city": "Chicago",      "state": "IL", "conference": "A-10", "home_court": "Joseph J. Gentile Arena",       "venue_rating": 55, "tourney": 8,  "ff": 2, "titles": 1},
    {"name": "Rhode Island",    "nickname": "Rams",            "city": "Kingston",     "state": "RI", "conference": "A-10", "home_court": "Ryan Center",                  "venue_rating": 58, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "Richmond",        "nickname": "Spiders",         "city": "Richmond",     "state": "VA", "conference": "A-10", "home_court": "Robins Center",                "venue_rating": 56, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "Saint Bonaventure","nickname": "Bonnies",        "city": "St. Bonaventure","state":"NY", "conference": "A-10", "home_court": "Reilly Center",               "venue_rating": 50, "tourney": 8,  "ff": 1, "titles": 0},
    {"name": "Saint Joseph's",  "nickname": "Hawks",           "city": "Philadelphia", "state": "PA", "conference": "A-10", "home_court": "Hagan Arena",                  "venue_rating": 55, "tourney": 21, "ff": 1, "titles": 0},
    {"name": "Saint Louis",     "nickname": "Billikens",       "city": "Saint Louis",  "state": "MO", "conference": "A-10", "home_court": "Chaifetz Arena",               "venue_rating": 58, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "VCU",             "nickname": "Rams",            "city": "Richmond",     "state": "VA", "conference": "A-10", "home_court": "Stuart C. Siegel Center",       "venue_rating": 62, "tourney": 21, "ff": 1, "titles": 0},

    # BIG EAST
    {"name": "Butler",          "nickname": "Bulldogs",        "city": "Indianapolis", "state": "IN", "conference": "Big East", "home_court": "Hinkle Fieldhouse",      "venue_rating": 78, "tourney": 16, "ff": 2,  "titles": 0},
    {"name": "Creighton",       "nickname": "Bluejays",        "city": "Omaha",        "state": "NE", "conference": "Big East", "home_court": "CHI Health Center Omaha","venue_rating": 72, "tourney": 26, "ff": 0,  "titles": 0},
    {"name": "DePaul",          "nickname": "Blue Demons",     "city": "Chicago",      "state": "IL", "conference": "Big East", "home_court": "Wintrust Arena",         "venue_rating": 62, "tourney": 22, "ff": 2,  "titles": 0},
    {"name": "Georgetown",      "nickname": "Hoyas",           "city": "Washington",   "state": "DC", "conference": "Big East", "home_court": "Capital One Arena",      "venue_rating": 76, "tourney": 31, "ff": 5,  "titles": 1},
    {"name": "Marquette",       "nickname": "Golden Eagles",   "city": "Milwaukee",    "state": "WI", "conference": "Big East", "home_court": "Fiserv Forum",           "venue_rating": 80, "tourney": 37, "ff": 3,  "titles": 1},
    {"name": "Providence",      "nickname": "Friars",          "city": "Providence",   "state": "RI", "conference": "Big East", "home_court": "Amica Mutual Pavilion",  "venue_rating": 68, "tourney": 22, "ff": 2,  "titles": 0},
    {"name": "Saint John's",    "nickname": "Red Storm",       "city": "Queens",       "state": "NY", "conference": "Big East", "home_court": "Carnesecca Arena",       "venue_rating": 70, "tourney": 31, "ff": 2,  "titles": 0},
    {"name": "Seton Hall",      "nickname": "Pirates",         "city": "South Orange", "state": "NJ", "conference": "Big East", "home_court": "Prudential Center",      "venue_rating": 72, "tourney": 14, "ff": 1,  "titles": 0},
    {"name": "UConn",           "nickname": "Huskies",         "city": "Storrs",       "state": "CT", "conference": "Big East", "home_court": "Harry A. Gampel Pavilion","venue_rating": 82, "tourney": 38, "ff": 7,  "titles": 6},
    {"name": "Villanova",       "nickname": "Wildcats",        "city": "Villanova",    "state": "PA", "conference": "Big East", "home_court": "Finneran Pavilion",      "venue_rating": 80, "tourney": 43, "ff": 7,  "titles": 3},
    {"name": "Xavier",          "nickname": "Musketeers",      "city": "Cincinnati",   "state": "OH", "conference": "Big East", "home_court": "Cintas Center",          "venue_rating": 72, "tourney": 30, "ff": 0,  "titles": 0},

    # BIG SKY
    {"name": "Eastern Washington","nickname": "Eagles",  "city": "Cheney",     "state": "WA", "conference": "Big Sky", "home_court": "Reese Court",                        "venue_rating": 42, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Idaho",           "nickname": "Vandals",   "city": "Moscow",     "state": "ID", "conference": "Big Sky", "home_court": "Idaho Central Credit Union Arena",    "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Idaho State",     "nickname": "Bengals",   "city": "Pocatello",  "state": "ID", "conference": "Big Sky", "home_court": "Holt Arena",                         "venue_rating": 42, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "Montana",         "nickname": "Grizzlies", "city": "Missoula",   "state": "MT", "conference": "Big Sky", "home_court": "Dahlberg Arena",                     "venue_rating": 50, "tourney": 13, "ff": 0, "titles": 0},
    {"name": "Montana State",   "nickname": "Bobcats",   "city": "Bozeman",    "state": "MT", "conference": "Big Sky", "home_court": "Worthington Arena",                  "venue_rating": 46, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Northern Arizona","nickname": "Lumberjacks","city": "Flagstaff", "state": "AZ", "conference": "Big Sky", "home_court": "Walkup Skydome",                     "venue_rating": 44, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Northern Colorado","nickname": "Bears",    "city": "Greeley",    "state": "CO", "conference": "Big Sky", "home_court": "Butler-Hancock Sports Pavilion",      "venue_rating": 40, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Portland State",  "nickname": "Vikings",   "city": "Portland",   "state": "OR", "conference": "Big Sky", "home_court": "Viking Pavilion",                    "venue_rating": 40, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Weber State",     "nickname": "Wildcats",  "city": "Ogden",      "state": "UT", "conference": "Big Sky", "home_court": "Dee Events Center",                  "venue_rating": 50, "tourney": 16, "ff": 0, "titles": 0},

    # BIG SOUTH
    {"name": "Charleston Southern","nickname": "Buccaneers", "city": "North Charleston","state": "SC", "conference": "Big South", "home_court": "CSU Field House",      "venue_rating": 36, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Gardner-Webb",    "nickname": "Runnin' Bulldogs","city": "Boiling Springs","state": "NC", "conference": "Big South", "home_court": "Paul Porter Arena",    "venue_rating": 36, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "High Point",      "nickname": "Panthers",    "city": "High Point",  "state": "NC", "conference": "Big South", "home_court": "Qubein Center",             "venue_rating": 42, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Longwood",        "nickname": "Lancers",     "city": "Farmville",   "state": "VA", "conference": "Big South", "home_court": "Joan Perry Brock Center",   "venue_rating": 38, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Radford",         "nickname": "Highlanders", "city": "Radford",     "state": "VA", "conference": "Big South", "home_court": "Dedmon Center",             "venue_rating": 38, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "UNC Asheville",   "nickname": "Bulldogs",    "city": "Asheville",   "state": "NC", "conference": "Big South", "home_court": "Kimmel Arena",              "venue_rating": 44, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Winthrop",        "nickname": "Eagles",      "city": "Rock Hill",   "state": "SC", "conference": "Big South", "home_court": "Winthrop Coliseum",         "venue_rating": 48, "tourney": 11, "ff": 0, "titles": 0},

    # BIG TEN
    {"name": "UCLA",            "nickname": "Bruins",          "city": "Los Angeles",  "state": "CA", "conference": "Big Ten", "home_court": "Pauley Pavilion",                   "venue_rating": 88, "tourney": 53, "ff": 19, "titles": 11},
    {"name": "Illinois",        "nickname": "Fighting Illini", "city": "Champaign",    "state": "IL", "conference": "Big Ten", "home_court": "State Farm Center",                 "venue_rating": 76, "tourney": 35, "ff": 5,  "titles": 0},
    {"name": "Indiana",         "nickname": "Hoosiers",        "city": "Bloomington",  "state": "IN", "conference": "Big Ten", "home_court": "Simon Skjodt Assembly Hall",         "venue_rating": 86, "tourney": 49, "ff": 8,  "titles": 5},
    {"name": "Iowa",            "nickname": "Hawkeyes",        "city": "Iowa City",    "state": "IA", "conference": "Big Ten", "home_court": "Carver-Hawkeye Arena",               "venue_rating": 74, "tourney": 29, "ff": 3,  "titles": 0},
    {"name": "Maryland",        "nickname": "Terrapins",       "city": "College Park",  "state": "MD", "conference": "Big Ten", "home_court": "Xfinity Center",                   "venue_rating": 72, "tourney": 31, "ff": 2,  "titles": 1},
    {"name": "Michigan",        "nickname": "Wolverines",      "city": "Ann Arbor",    "state": "MI", "conference": "Big Ten", "home_court": "Crisler Center",                    "venue_rating": 76, "tourney": 32, "ff": 8,  "titles": 1},
    {"name": "Michigan State",  "nickname": "Spartans",        "city": "East Lansing", "state": "MI", "conference": "Big Ten", "home_court": "Breslin Student Events Center",      "venue_rating": 82, "tourney": 38, "ff": 10, "titles": 2},
    {"name": "Minnesota",       "nickname": "Golden Gophers",  "city": "Minneapolis",  "state": "MN", "conference": "Big Ten", "home_court": "Williams Arena",                    "venue_rating": 68, "tourney": 14, "ff": 1,  "titles": 0},
    {"name": "Nebraska",        "nickname": "Cornhuskers",     "city": "Lincoln",      "state": "NE", "conference": "Big Ten", "home_court": "Pinnacle Bank Arena",               "venue_rating": 65, "tourney": 8,  "ff": 0,  "titles": 0},
    {"name": "Northwestern",    "nickname": "Wildcats",        "city": "Evanston",     "state": "IL", "conference": "Big Ten", "home_court": "Welsh-Ryan Arena",                  "venue_rating": 60, "tourney": 3,  "ff": 0,  "titles": 0},
    {"name": "Ohio State",      "nickname": "Buckeyes",        "city": "Columbus",     "state": "OH", "conference": "Big Ten", "home_court": "Value City Arena",                  "venue_rating": 80, "tourney": 31, "ff": 10, "titles": 1},
    {"name": "Oregon",          "nickname": "Ducks",           "city": "Eugene",       "state": "OR", "conference": "Big Ten", "home_court": "Matthew Knight Arena",               "venue_rating": 74, "tourney": 19, "ff": 2,  "titles": 1},
    {"name": "Penn State",      "nickname": "Nittany Lions",   "city": "University Park","state": "PA","conference": "Big Ten", "home_court": "Bryce Jordan Center",               "venue_rating": 70, "tourney": 10, "ff": 1,  "titles": 0},
    {"name": "Purdue",          "nickname": "Boilermakers",    "city": "West Lafayette","state": "IN", "conference": "Big Ten", "home_court": "Mackey Arena",                      "venue_rating": 78, "tourney": 36, "ff": 3,  "titles": 0},
    {"name": "Rutgers",         "nickname": "Scarlet Knights", "city": "Piscataway",   "state": "NJ", "conference": "Big Ten", "home_court": "Jersey Mike's Arena",               "venue_rating": 62, "tourney": 8,  "ff": 1,  "titles": 0},
    {"name": "USC",             "nickname": "Trojans",         "city": "Los Angeles",  "state": "CA", "conference": "Big Ten", "home_court": "Galen Center",                      "venue_rating": 72, "tourney": 21, "ff": 2,  "titles": 0},
    {"name": "Washington",      "nickname": "Huskies",         "city": "Seattle",      "state": "WA", "conference": "Big Ten", "home_court": "Alaska Airlines Arena",              "venue_rating": 68, "tourney": 17, "ff": 1,  "titles": 0},
    {"name": "Wisconsin",       "nickname": "Badgers",         "city": "Madison",      "state": "WI", "conference": "Big Ten", "home_court": "Kohl Center",                       "venue_rating": 78, "tourney": 28, "ff": 4,  "titles": 1},

    # BIG 12
    {"name": "Arizona",         "nickname": "Wildcats",        "city": "Tucson",       "state": "AZ", "conference": "Big 12", "home_court": "McKale Center",              "venue_rating": 84, "tourney": 39, "ff": 4,  "titles": 1},
    {"name": "Arizona State",   "nickname": "Sun Devils",      "city": "Tempe",        "state": "AZ", "conference": "Big 12", "home_court": "Desert Financial Arena",     "venue_rating": 68, "tourney": 17, "ff": 0,  "titles": 0},
    {"name": "Baylor",          "nickname": "Bears",           "city": "Waco",         "state": "TX", "conference": "Big 12", "home_court": "Foster Pavilion",            "venue_rating": 74, "tourney": 17, "ff": 3,  "titles": 1},
    {"name": "BYU",             "nickname": "Cougars",         "city": "Provo",        "state": "UT", "conference": "Big 12", "home_court": "Marriott Center",            "venue_rating": 72, "tourney": 32, "ff": 0,  "titles": 0},
    {"name": "UCF",             "nickname": "Knights",         "city": "Orlando",      "state": "FL", "conference": "Big 12", "home_court": "Addition Financial Arena",   "venue_rating": 58, "tourney": 5,  "ff": 0,  "titles": 0},
    {"name": "Cincinnati",      "nickname": "Bearcats",        "city": "Cincinnati",   "state": "OH", "conference": "Big 12", "home_court": "Fifth Third Arena",          "venue_rating": 76, "tourney": 33, "ff": 6,  "titles": 2},
    {"name": "Colorado",        "nickname": "Buffaloes",       "city": "Boulder",      "state": "CO", "conference": "Big 12", "home_court": "CU Events Center",           "venue_rating": 64, "tourney": 16, "ff": 2,  "titles": 0},
    {"name": "Houston",         "nickname": "Cougars",         "city": "Houston",      "state": "TX", "conference": "Big 12", "home_court": "Fertitta Center",            "venue_rating": 78, "tourney": 26, "ff": 7,  "titles": 0},
    {"name": "Iowa State",      "nickname": "Cyclones",        "city": "Ames",         "state": "IA", "conference": "Big 12", "home_court": "Hilton Coliseum",            "venue_rating": 82, "tourney": 24, "ff": 1,  "titles": 0},
    {"name": "Kansas",          "nickname": "Jayhawks",        "city": "Lawrence",     "state": "KS", "conference": "Big 12", "home_court": "Allen Fieldhouse",           "venue_rating": 98, "tourney": 53, "ff": 16, "titles": 4},
    {"name": "Kansas State",    "nickname": "Wildcats",        "city": "Manhattan",    "state": "KS", "conference": "Big 12", "home_court": "Bramlage Coliseum",          "venue_rating": 76, "tourney": 32, "ff": 4,  "titles": 0},
    {"name": "Oklahoma State",  "nickname": "Cowboys",         "city": "Stillwater",   "state": "OK", "conference": "Big 12", "home_court": "Gallagher-Iba Arena",        "venue_rating": 88, "tourney": 29, "ff": 6,  "titles": 2},
    {"name": "TCU",             "nickname": "Horned Frogs",    "city": "Fort Worth",   "state": "TX", "conference": "Big 12", "home_court": "Schollmaier Arena",          "venue_rating": 62, "tourney": 11, "ff": 0,  "titles": 0},
    {"name": "Texas Tech",      "nickname": "Red Raiders",     "city": "Lubbock",      "state": "TX", "conference": "Big 12", "home_court": "United Supermarkets Arena",  "venue_rating": 72, "tourney": 21, "ff": 1,  "titles": 0},
    {"name": "Utah",            "nickname": "Utes",            "city": "Salt Lake City","state": "UT", "conference": "Big 12", "home_court": "Jon M. Huntsman Center",     "venue_rating": 70, "tourney": 30, "ff": 4,  "titles": 1},
    {"name": "West Virginia",   "nickname": "Mountaineers",    "city": "Morgantown",   "state": "WV", "conference": "Big 12", "home_court": "WVU Coliseum",               "venue_rating": 74, "tourney": 31, "ff": 2,  "titles": 0},

    # BIG WEST
    {"name": "Cal Poly",            "nickname": "Mustangs",    "city": "San Luis Obispo","state": "CA", "conference": "Big West", "home_court": "Mott Gym",                  "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Cal State Fullerton", "nickname": "Titans",      "city": "Fullerton",     "state": "CA", "conference": "Big West", "home_court": "Titan Gym",                 "venue_rating": 40, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Cal State Northridge","nickname": "Matadors",    "city": "Northridge",    "state": "CA", "conference": "Big West", "home_court": "Matadome",                  "venue_rating": 38, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Hawaii",              "nickname": "Rainbow Warriors","city": "Honolulu",  "state": "HI", "conference": "Big West", "home_court": "Stan Sheriff Center",       "venue_rating": 56, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Long Beach State",    "nickname": "The Beach",   "city": "Long Beach",    "state": "CA", "conference": "Big West", "home_court": "Walter Pyramid",            "venue_rating": 58, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "UC Davis",            "nickname": "Aggies",      "city": "Davis",         "state": "CA", "conference": "Big West", "home_court": "University Credit Union Center","venue_rating": 40, "tourney": 1, "ff": 0, "titles": 0},
    {"name": "UC Irvine",           "nickname": "Anteaters",   "city": "Irvine",        "state": "CA", "conference": "Big West", "home_court": "Bren Events Center",        "venue_rating": 44, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "UC Riverside",        "nickname": "Highlanders", "city": "Riverside",     "state": "CA", "conference": "Big West", "home_court": "Student Recreation Center", "venue_rating": 36, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "UC Santa Barbara",    "nickname": "Gauchos",     "city": "Santa Barbara", "state": "CA", "conference": "Big West", "home_court": "Events Center",             "venue_rating": 48, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Cal State Bakersfield","nickname": "Roadrunners","city": "Bakersfield",   "state": "CA", "conference": "Big West", "home_court": "Icardo Center",             "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},

    # CAA
    {"name": "Charleston",      "nickname": "Cougars",     "city": "Charleston",   "state": "SC", "conference": "CAA", "home_court": "TD Arena",                    "venue_rating": 52, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Drexel",          "nickname": "Dragons",     "city": "Philadelphia", "state": "PA", "conference": "CAA", "home_court": "Daskalakis Athletic Center",  "venue_rating": 44, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Elon",            "nickname": "Phoenix",     "city": "Elon",         "state": "NC", "conference": "CAA", "home_court": "Schar Center",                "venue_rating": 44, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Hampton",         "nickname": "Pirates",     "city": "Hampton",      "state": "VA", "conference": "CAA", "home_court": "Hampton Convocation Center",  "venue_rating": 44, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Hofstra",         "nickname": "Pride",       "city": "Hempstead",    "state": "NY", "conference": "CAA", "home_court": "Hofstra Arena",               "venue_rating": 46, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Monmouth",        "nickname": "Hawks",       "city": "West Long Branch","state": "NJ","conference": "CAA", "home_court": "OceanFirst Bank Center",    "venue_rating": 42, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Northeastern",    "nickname": "Huskies",     "city": "Boston",       "state": "MA", "conference": "CAA", "home_court": "Matthews Arena",              "venue_rating": 48, "tourney": 9,  "ff": 0, "titles": 0},
    {"name": "Stony Brook",     "nickname": "Seawolves",   "city": "Stony Brook",  "state": "NY", "conference": "CAA", "home_court": "Island Federal Credit Union Arena","venue_rating": 42, "tourney": 1, "ff": 0, "titles": 0},
    {"name": "Towson",          "nickname": "Tigers",      "city": "Towson",       "state": "MD", "conference": "CAA", "home_court": "SECU Arena",                  "venue_rating": 44, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "UNC Wilmington",  "nickname": "Seahawks",    "city": "Wilmington",   "state": "NC", "conference": "CAA", "home_court": "Trask Coliseum",              "venue_rating": 46, "tourney": 7,  "ff": 0, "titles": 0},

    # CONFERENCE USA
    {"name": "Delaware",        "nickname": "Fightin' Blue Hens","city": "Newark",  "state": "DE", "conference": "Conference USA", "home_court": "Bob Carpenter Center",        "venue_rating": 50, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Jacksonville State","nickname": "Gamecocks",   "city": "Jacksonville","state": "AL", "conference": "Conference USA", "home_court": "Pete Mathews Coliseum",        "venue_rating": 44, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Liberty",         "nickname": "Flames",        "city": "Lynchburg",   "state": "VA", "conference": "Conference USA", "home_court": "Liberty Arena",                "venue_rating": 50, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Louisiana Tech",  "nickname": "Bulldogs",      "city": "Ruston",      "state": "LA", "conference": "Conference USA", "home_court": "Thomas Assembly Center",       "venue_rating": 52, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Middle Tennessee","nickname": "Blue Raiders",  "city": "Murfreesboro","state": "TN", "conference": "Conference USA", "home_court": "Murphy Center",                "venue_rating": 50, "tourney": 9,  "ff": 0, "titles": 0},
    {"name": "Missouri State",  "nickname": "Bears",         "city": "Springfield", "state": "MO", "conference": "Conference USA", "home_court": "Great Southern Bank Arena",    "venue_rating": 56, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "New Mexico State","nickname": "Aggies",        "city": "Las Cruces",  "state": "NM", "conference": "Conference USA", "home_court": "Pan American Center",          "venue_rating": 58, "tourney": 26, "ff": 1, "titles": 0},
    {"name": "Sam Houston",     "nickname": "Bearkats",      "city": "Huntsville",  "state": "TX", "conference": "Conference USA", "home_court": "Bernard Johnson Coliseum",     "venue_rating": 44, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "UTEP",            "nickname": "Miners",        "city": "El Paso",     "state": "TX", "conference": "Conference USA", "home_court": "Don Haskins Center",           "venue_rating": 62, "tourney": 17, "ff": 1, "titles": 1},
    {"name": "Western Kentucky","nickname": "Hilltoppers",   "city": "Bowling Green","state": "KY", "conference": "Conference USA", "home_court": "E. A. Diddle Arena",           "venue_rating": 62, "tourney": 24, "ff": 1, "titles": 0},

    # HORIZON
    {"name": "Cleveland State", "nickname": "Vikings",       "city": "Cleveland",    "state": "OH", "conference": "Horizon", "home_court": "Wolstein Center",          "venue_rating": 52, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Detroit Mercy",   "nickname": "Titans",        "city": "Detroit",      "state": "MI", "conference": "Horizon", "home_court": "Calihan Hall",             "venue_rating": 50, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Green Bay",       "nickname": "Phoenix",       "city": "Green Bay",    "state": "WI", "conference": "Horizon", "home_court": "Resch Center",             "venue_rating": 50, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Milwaukee",       "nickname": "Panthers",      "city": "Milwaukee",    "state": "WI", "conference": "Horizon", "home_court": "Panther Arena",            "venue_rating": 50, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Northern Kentucky","nickname": "Norse",        "city": "Highland Heights","state": "KY","conference": "Horizon", "home_court": "Truist Arena",            "venue_rating": 46, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Oakland",         "nickname": "Golden Grizzlies","city": "Auburn Hills","state": "MI", "conference": "Horizon", "home_court": "O'rena",                  "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Robert Morris",   "nickname": "Colonials",     "city": "Moon Township","state": "PA", "conference": "Horizon", "home_court": "UPMC Events Center",       "venue_rating": 46, "tourney": 9,  "ff": 0, "titles": 0},
    {"name": "Wright State",    "nickname": "Raiders",       "city": "Dayton",       "state": "OH", "conference": "Horizon", "home_court": "Nutter Center",            "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},

    # IVY LEAGUE
    {"name": "Brown",           "nickname": "Bears",    "city": "Providence",   "state": "RI", "conference": "Ivy League", "home_court": "Pizzitola Sports Center",    "venue_rating": 40, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Columbia",        "nickname": "Lions",    "city": "New York",     "state": "NY", "conference": "Ivy League", "home_court": "Levien Gymnasium",           "venue_rating": 40, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Cornell",         "nickname": "Big Red",  "city": "Ithaca",       "state": "NY", "conference": "Ivy League", "home_court": "Newman Arena",               "venue_rating": 44, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Dartmouth",       "nickname": "Big Green","city": "Hanover",      "state": "NH", "conference": "Ivy League", "home_court": "Leede Arena",                "venue_rating": 38, "tourney": 7,  "ff": 2, "titles": 0},
    {"name": "Harvard",         "nickname": "Crimson",  "city": "Cambridge",    "state": "MA", "conference": "Ivy League", "home_court": "Lavietes Pavilion",          "venue_rating": 42, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Penn",            "nickname": "Quakers",  "city": "Philadelphia", "state": "PA", "conference": "Ivy League", "home_court": "Palestra",                   "venue_rating": 60, "tourney": 24, "ff": 1, "titles": 0},
    {"name": "Princeton",       "nickname": "Tigers",   "city": "Princeton",    "state": "NJ", "conference": "Ivy League", "home_court": "Jadwin Gymnasium",           "venue_rating": 52, "tourney": 26, "ff": 1, "titles": 0},
    {"name": "Yale",            "nickname": "Bulldogs", "city": "New Haven",    "state": "CT", "conference": "Ivy League", "home_court": "John J. Lee Amphitheater",   "venue_rating": 44, "tourney": 8,  "ff": 0, "titles": 0},

    # MAAC
    {"name": "Canisius",        "nickname": "Golden Griffins","city": "Buffalo",      "state": "NY", "conference": "MAAC", "home_court": "Koessler Athletic Center", "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Fairfield",       "nickname": "Stags",          "city": "Fairfield",    "state": "CT", "conference": "MAAC", "home_court": "Webster Bank Arena",      "venue_rating": 46, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Iona",            "nickname": "Gaels",          "city": "New Rochelle", "state": "NY", "conference": "MAAC", "home_court": "Hynes Athletic Center",   "venue_rating": 48, "tourney": 16, "ff": 0, "titles": 0},
    {"name": "Manhattan",       "nickname": "Jaspers",        "city": "Riverdale",    "state": "NY", "conference": "MAAC", "home_court": "Draddy Gymnasium",        "venue_rating": 42, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Marist",          "nickname": "Red Foxes",      "city": "Poughkeepsie", "state": "NY", "conference": "MAAC", "home_court": "McCann Field House",      "venue_rating": 40, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Niagara",         "nickname": "Purple Eagles",  "city": "Niagara University","state": "NY","conference": "MAAC", "home_court": "Gallagher Center",   "venue_rating": 40, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Quinnipiac",      "nickname": "Bobcats",        "city": "Hamden",       "state": "CT", "conference": "MAAC", "home_court": "TD Bank Sports Center",   "venue_rating": 44, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Rider",           "nickname": "Broncs",         "city": "Lawrenceville","state": "NJ", "conference": "MAAC", "home_court": "Alumni Gymnasium",        "venue_rating": 38, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Saint Peter's",   "nickname": "Peacocks",       "city": "Jersey City",  "state": "NJ", "conference": "MAAC", "home_court": "Run Baby Run Arena",      "venue_rating": 42, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Siena",           "nickname": "Saints",         "city": "Loudonville",  "state": "NY", "conference": "MAAC", "home_court": "MVP Arena",               "venue_rating": 52, "tourney": 6,  "ff": 0, "titles": 0},

    # MAC
    {"name": "Akron",           "nickname": "Zips",        "city": "Akron",        "state": "OH", "conference": "MAC", "home_court": "James A. Rhodes Arena",                  "venue_rating": 52, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Ball State",      "nickname": "Cardinals",   "city": "Muncie",       "state": "IN", "conference": "MAC", "home_court": "John E. Worthen Arena",                  "venue_rating": 48, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Bowling Green",   "nickname": "Falcons",     "city": "Bowling Green","state": "OH", "conference": "MAC", "home_court": "Stroh Center",                           "venue_rating": 46, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Buffalo",         "nickname": "Bulls",       "city": "Buffalo",      "state": "NY", "conference": "MAC", "home_court": "Alumni Arena",                           "venue_rating": 50, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Central Michigan","nickname": "Chippewas",   "city": "Mount Pleasant","state": "MI", "conference": "MAC", "home_court": "McGuirk Arena",                         "venue_rating": 46, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Eastern Michigan","nickname": "Eagles",      "city": "Ypsilanti",    "state": "MI", "conference": "MAC", "home_court": "Convocation Center",                     "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Kent State",      "nickname": "Golden Flashes","city": "Kent",       "state": "OH", "conference": "MAC", "home_court": "Memorial Athletic and Convocation Center","venue_rating": 50, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Miami (OH)",      "nickname": "RedHawks",    "city": "Oxford",       "state": "OH", "conference": "MAC", "home_court": "Millett Hall",                           "venue_rating": 52, "tourney": 17, "ff": 0, "titles": 0},
    {"name": "Northern Illinois","nickname": "Huskies",    "city": "DeKalb",       "state": "IL", "conference": "MAC", "home_court": "Convocation Center",                     "venue_rating": 46, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Ohio",            "nickname": "Bobcats",     "city": "Athens",       "state": "OH", "conference": "MAC", "home_court": "Convocation Center",                     "venue_rating": 50, "tourney": 14, "ff": 0, "titles": 0},
    {"name": "Toledo",          "nickname": "Rockets",     "city": "Toledo",       "state": "OH", "conference": "MAC", "home_court": "Savage Arena",                           "venue_rating": 52, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "UMass",           "nickname": "Minutemen",   "city": "Amherst",      "state": "MA", "conference": "MAC", "home_court": "Mullins Center",                         "venue_rating": 58, "tourney": 9,  "ff": 1, "titles": 0},
    {"name": "Western Michigan","nickname": "Broncos",     "city": "Kalamazoo",    "state": "MI", "conference": "MAC", "home_court": "University Arena",                       "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},

    # MEAC
    {"name": "Coppin State",        "nickname": "Eagles",   "city": "Baltimore",    "state": "MD", "conference": "MEAC", "home_court": "Physical Education Complex",      "venue_rating": 36, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Delaware State",      "nickname": "Hornets",  "city": "Dover",        "state": "DE", "conference": "MEAC", "home_court": "Memorial Hall",                   "venue_rating": 34, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Howard",              "nickname": "Bison",    "city": "Washington",   "state": "DC", "conference": "MEAC", "home_court": "Burr Gymnasium",                  "venue_rating": 38, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Morgan State",        "nickname": "Bears",    "city": "Baltimore",    "state": "MD", "conference": "MEAC", "home_court": "Hill Field House",                "venue_rating": 34, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Norfolk State",       "nickname": "Spartans", "city": "Norfolk",      "state": "VA", "conference": "MEAC", "home_court": "Joseph G. Echols Memorial Hall",  "venue_rating": 36, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "North Carolina A&T",  "nickname": "Aggies",   "city": "Greensboro",   "state": "NC", "conference": "MEAC", "home_court": "Corbett Sports Center",           "venue_rating": 40, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "North Carolina Central","nickname": "Eagles", "city": "Durham",       "state": "NC", "conference": "MEAC", "home_court": "McDougald Gymnasium",             "venue_rating": 38, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "South Carolina State","nickname": "Bulldogs", "city": "Orangeburg",   "state": "SC", "conference": "MEAC", "home_court": "SHM Memorial Center",             "venue_rating": 34, "tourney": 5,  "ff": 0, "titles": 0},

    # MISSOURI VALLEY
    {"name": "Belmont",         "nickname": "Bruins",      "city": "Nashville",    "state": "TN", "conference": "Missouri Valley", "home_court": "Curb Event Center",         "venue_rating": 52, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Bradley",         "nickname": "Braves",      "city": "Peoria",       "state": "IL", "conference": "Missouri Valley", "home_court": "Carver Arena",              "venue_rating": 56, "tourney": 9,  "ff": 2, "titles": 0},
    {"name": "Drake",           "nickname": "Bulldogs",    "city": "Des Moines",   "state": "IA", "conference": "Missouri Valley", "home_court": "Knapp Center",              "venue_rating": 60, "tourney": 8,  "ff": 1, "titles": 0},
    {"name": "Evansville",      "nickname": "Purple Aces", "city": "Evansville",   "state": "IN", "conference": "Missouri Valley", "home_court": "Ford Center",               "venue_rating": 58, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Illinois State",  "nickname": "Redbirds",    "city": "Normal",       "state": "IL", "conference": "Missouri Valley", "home_court": "Redbird Arena",             "venue_rating": 58, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Indiana State",   "nickname": "Sycamores",   "city": "Terre Haute",  "state": "IN", "conference": "Missouri Valley", "home_court": "Hulman Center",             "venue_rating": 56, "tourney": 4,  "ff": 1, "titles": 0},
    {"name": "Murray State",    "nickname": "Racers",      "city": "Murray",       "state": "KY", "conference": "Missouri Valley", "home_court": "CFSB Center",               "venue_rating": 54, "tourney": 18, "ff": 0, "titles": 0},
    {"name": "Northern Iowa",   "nickname": "Panthers",    "city": "Cedar Falls",  "state": "IA", "conference": "Missouri Valley", "home_court": "McLeod Center",             "venue_rating": 62, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Southern Illinois","nickname": "Salukis",    "city": "Carbondale",   "state": "IL", "conference": "Missouri Valley", "home_court": "Banterra Center",           "venue_rating": 60, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "UIC",             "nickname": "Flames",      "city": "Chicago",      "state": "IL", "conference": "Missouri Valley", "home_court": "Credit Union 1 Arena",      "venue_rating": 50, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Valparaiso",      "nickname": "Beacons",     "city": "Valparaiso",   "state": "IN", "conference": "Missouri Valley", "home_court": "Athletics-Recreation Center","venue_rating": 48, "tourney": 9,  "ff": 0, "titles": 0},

    # MOUNTAIN WEST
    {"name": "Air Force",       "nickname": "Falcons",      "city": "Colorado Springs","state": "CO", "conference": "Mountain West", "home_court": "Clune Arena",              "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Boise State",     "nickname": "Broncos",      "city": "Boise",          "state": "ID", "conference": "Mountain West", "home_court": "ExtraMile Arena",           "venue_rating": 60, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "Colorado State",  "nickname": "Rams",         "city": "Fort Collins",   "state": "CO", "conference": "Mountain West", "home_court": "Moby Arena",               "venue_rating": 60, "tourney": 13, "ff": 0, "titles": 0},
    {"name": "Fresno State",    "nickname": "Bulldogs",     "city": "Fresno",         "state": "CA", "conference": "Mountain West", "home_court": "Save Mart Center",          "venue_rating": 62, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Grand Canyon",    "nickname": "Antelopes",    "city": "Phoenix",        "state": "AZ", "conference": "Mountain West", "home_court": "Global Credit Union Arena", "venue_rating": 58, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Nevada",          "nickname": "Wolf Pack",    "city": "Reno",           "state": "NV", "conference": "Mountain West", "home_court": "Lawlor Events Center",      "venue_rating": 60, "tourney": 11, "ff": 0, "titles": 0},
    {"name": "New Mexico",      "nickname": "Lobos",        "city": "Albuquerque",    "state": "NM", "conference": "Mountain West", "home_court": "The Pit",                   "venue_rating": 74, "tourney": 17, "ff": 0, "titles": 0},
    {"name": "San Diego State", "nickname": "Aztecs",       "city": "San Diego",      "state": "CA", "conference": "Mountain West", "home_court": "Viejas Arena",              "venue_rating": 70, "tourney": 17, "ff": 1, "titles": 0},
    {"name": "San Jose State",  "nickname": "Spartans",     "city": "San Jose",       "state": "CA", "conference": "Mountain West", "home_court": "Provident Credit Union Event Center","venue_rating": 50, "tourney": 3, "ff": 0, "titles": 0},
    {"name": "UNLV",            "nickname": "Runnin' Rebels","city": "Las Vegas",     "state": "NV", "conference": "Mountain West", "home_court": "Thomas and Mack Center",    "venue_rating": 78, "tourney": 20, "ff": 4, "titles": 1},
    {"name": "Utah State",      "nickname": "Aggies",       "city": "Logan",          "state": "UT", "conference": "Mountain West", "home_court": "Smith Spectrum",            "venue_rating": 64, "tourney": 25, "ff": 0, "titles": 0},
    {"name": "Wyoming",         "nickname": "Cowboys",      "city": "Laramie",        "state": "WY", "conference": "Mountain West", "home_court": "Arena-Auditorium",          "venue_rating": 58, "tourney": 16, "ff": 1, "titles": 1},

    # NEC
    {"name": "Central Connecticut","nickname": "Blue Devils","city": "New Britain",  "state": "CT", "conference": "NEC", "home_court": "William H. Detrick Gymnasium", "venue_rating": 38, "tourney": 3, "ff": 0, "titles": 0},
    {"name": "Fairleigh Dickinson","nickname": "Knights",   "city": "Hackensack",    "state": "NJ", "conference": "NEC", "home_court": "Rothman Center",              "venue_rating": 38, "tourney": 7, "ff": 0, "titles": 0},
    {"name": "LIU",             "nickname": "Sharks",        "city": "Brookville",    "state": "NY", "conference": "NEC", "home_court": "Steinberg Wellness Center",    "venue_rating": 36, "tourney": 7, "ff": 0, "titles": 0},
    {"name": "Saint Francis (PA)","nickname": "Red Flash",  "city": "Loretto",       "state": "PA", "conference": "NEC", "home_court": "DeGol Arena",                 "venue_rating": 34, "tourney": 2, "ff": 0, "titles": 0},
    {"name": "Wagner",          "nickname": "Seahawks",      "city": "Staten Island", "state": "NY", "conference": "NEC", "home_court": "Spiro Sports Center",          "venue_rating": 34, "tourney": 2, "ff": 0, "titles": 0},

    # OHIO VALLEY
    {"name": "Eastern Illinois","nickname": "Panthers",     "city": "Charleston",   "state": "IL", "conference": "Ohio Valley", "home_court": "Lantz Arena",          "venue_rating": 40, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Morehead State",  "nickname": "Eagles",       "city": "Morehead",     "state": "KY", "conference": "Ohio Valley", "home_court": "Ellis Johnson Arena",  "venue_rating": 42, "tourney": 9,  "ff": 0, "titles": 0},
    {"name": "Southeast Missouri State","nickname": "Redhawks","city": "Cape Girardeau","state": "MO","conference": "Ohio Valley","home_court": "Show Me Center",      "venue_rating": 42, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Tennessee State", "nickname": "Tigers",       "city": "Nashville",    "state": "TN", "conference": "Ohio Valley", "home_court": "Gentry Complex",       "venue_rating": 40, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Tennessee Tech",  "nickname": "Golden Eagles","city": "Cookeville",   "state": "TN", "conference": "Ohio Valley", "home_court": "Eblen Center",         "venue_rating": 42, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "UT Martin",       "nickname": "Skyhawks",     "city": "Martin",       "state": "TN", "conference": "Ohio Valley", "home_court": "Elam Center",          "venue_rating": 38, "tourney": 0,  "ff": 0, "titles": 0},

    # PATRIOT LEAGUE
    {"name": "American",        "nickname": "Eagles",       "city": "Washington",   "state": "DC", "conference": "Patriot", "home_court": "Bender Arena",        "venue_rating": 44, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Army",            "nickname": "Black Knights","city": "West Point",   "state": "NY", "conference": "Patriot", "home_court": "Christl Arena",       "venue_rating": 40, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Boston University","nickname": "Terriers",    "city": "Boston",       "state": "MA", "conference": "Patriot", "home_court": "Case Gym",            "venue_rating": 44, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Bucknell",        "nickname": "Bison",        "city": "Lewisburg",    "state": "PA", "conference": "Patriot", "home_court": "Sojka Pavilion",      "venue_rating": 44, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Colgate",         "nickname": "Raiders",      "city": "Hamilton",     "state": "NY", "conference": "Patriot", "home_court": "Cotterell Court",      "venue_rating": 42, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Holy Cross",      "nickname": "Crusaders",    "city": "Worcester",    "state": "MA", "conference": "Patriot", "home_court": "Hart Center",          "venue_rating": 48, "tourney": 13, "ff": 2, "titles": 1},
    {"name": "Lafayette",       "nickname": "Leopards",     "city": "Easton",       "state": "PA", "conference": "Patriot", "home_court": "Kirby Sports Center",  "venue_rating": 40, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Lehigh",          "nickname": "Mountain Hawks","city": "Bethlehem",   "state": "PA", "conference": "Patriot", "home_court": "Stabler Arena",        "venue_rating": 44, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Loyola Maryland", "nickname": "Greyhounds",   "city": "Baltimore",    "state": "MD", "conference": "Patriot", "home_court": "Reitz Arena",          "venue_rating": 40, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Navy",            "nickname": "Midshipmen",   "city": "Annapolis",    "state": "MD", "conference": "Patriot", "home_court": "Alumni Hall",          "venue_rating": 42, "tourney": 11, "ff": 0, "titles": 0},

    # SEC
    {"name": "Alabama",         "nickname": "Crimson Tide", "city": "Tuscaloosa",   "state": "AL", "conference": "SEC", "home_court": "Coleman Coliseum",                        "venue_rating": 74, "tourney": 26, "ff": 1,  "titles": 0},
    {"name": "Arkansas",        "nickname": "Razorbacks",   "city": "Fayetteville", "state": "AR", "conference": "SEC", "home_court": "Bud Walton Arena",                        "venue_rating": 82, "tourney": 36, "ff": 6,  "titles": 1},
    {"name": "Auburn",          "nickname": "Tigers",       "city": "Auburn",       "state": "AL", "conference": "SEC", "home_court": "Neville Arena",                           "venue_rating": 74, "tourney": 14, "ff": 2,  "titles": 0},
    {"name": "Florida",         "nickname": "Gators",       "city": "Gainesville",  "state": "FL", "conference": "SEC", "home_court": "Exactech Arena",                          "venue_rating": 80, "tourney": 25, "ff": 5,  "titles": 3},
    {"name": "Georgia",         "nickname": "Bulldogs",     "city": "Athens",       "state": "GA", "conference": "SEC", "home_court": "Stegeman Coliseum",                       "venue_rating": 66, "tourney": 13, "ff": 1,  "titles": 0},
    {"name": "Kentucky",        "nickname": "Wildcats",     "city": "Lexington",    "state": "KY", "conference": "SEC", "home_court": "Rupp Arena",                              "venue_rating": 97, "tourney": 62, "ff": 17, "titles": 8},
    {"name": "LSU",             "nickname": "Tigers",       "city": "Baton Rouge",  "state": "LA", "conference": "SEC", "home_court": "Pete Maravich Assembly Center",           "venue_rating": 80, "tourney": 24, "ff": 4,  "titles": 0},
    {"name": "Ole Miss",        "nickname": "Rebels",       "city": "Oxford",       "state": "MS", "conference": "SEC", "home_court": "The Sandy and John Black Pavilion",       "venue_rating": 66, "tourney": 10, "ff": 0,  "titles": 0},
    {"name": "Mississippi State","nickname": "Bulldogs",    "city": "Starkville",   "state": "MS", "conference": "SEC", "home_court": "Humphrey Coliseum",                       "venue_rating": 68, "tourney": 14, "ff": 1,  "titles": 0},
    {"name": "Missouri",        "nickname": "Tigers",       "city": "Columbia",     "state": "MO", "conference": "SEC", "home_court": "Mizzou Arena",                            "venue_rating": 70, "tourney": 30, "ff": 0,  "titles": 0},
    {"name": "Oklahoma",        "nickname": "Sooners",      "city": "Norman",       "state": "OK", "conference": "SEC", "home_court": "Lloyd Noble Center",                      "venue_rating": 76, "tourney": 35, "ff": 5,  "titles": 0},
    {"name": "South Carolina",  "nickname": "Gamecocks",    "city": "Columbia",     "state": "SC", "conference": "SEC", "home_court": "Colonial Life Arena",                     "venue_rating": 72, "tourney": 10, "ff": 1,  "titles": 0},
    {"name": "Tennessee",       "nickname": "Volunteers",   "city": "Knoxville",    "state": "TN", "conference": "SEC", "home_court": "Thompson-Boling Arena",                   "venue_rating": 82, "tourney": 27, "ff": 0,  "titles": 0},
    {"name": "Texas",           "nickname": "Longhorns",    "city": "Austin",       "state": "TX", "conference": "SEC", "home_court": "Moody Center",                            "venue_rating": 82, "tourney": 39, "ff": 3,  "titles": 0},
    {"name": "Texas A&M",       "nickname": "Aggies",       "city": "College Station","state": "TX","conference": "SEC", "home_court": "Reed Arena",                             "venue_rating": 72, "tourney": 17, "ff": 0,  "titles": 0},
    {"name": "Vanderbilt",      "nickname": "Commodores",   "city": "Nashville",    "state": "TN", "conference": "SEC", "home_court": "Memorial Gymnasium",                      "venue_rating": 68, "tourney": 16, "ff": 0,  "titles": 0},

    # SOUTHERN CONFERENCE
    {"name": "Chattanooga",     "nickname": "Mocs",          "city": "Chattanooga",  "state": "TN", "conference": "Southern", "home_court": "McKenzie Arena",                  "venue_rating": 56, "tourney": 12, "ff": 0, "titles": 0},
    {"name": "The Citadel",     "nickname": "Bulldogs",      "city": "Charleston",   "state": "SC", "conference": "Southern", "home_court": "McAlister Field House",            "venue_rating": 38, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "East Tennessee State","nickname": "Buccaneers","city": "Johnson City", "state": "TN", "conference": "Southern", "home_court": "Freedom Hall Civic Center",        "venue_rating": 52, "tourney": 10, "ff": 0, "titles": 0},
    {"name": "Furman",          "nickname": "Paladins",      "city": "Greenville",   "state": "SC", "conference": "Southern", "home_court": "Timmons Arena",                   "venue_rating": 46, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Mercer",          "nickname": "Bears",         "city": "Macon",        "state": "GA", "conference": "Southern", "home_court": "Hawkins Arena",                   "venue_rating": 44, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Samford",         "nickname": "Bulldogs",      "city": "Birmingham",   "state": "AL", "conference": "Southern", "home_court": "Pete Hanna Center",               "venue_rating": 44, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "UNC Greensboro",  "nickname": "Spartans",      "city": "Greensboro",   "state": "NC", "conference": "Southern", "home_court": "Greensboro Coliseum",             "venue_rating": 50, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "VMI",             "nickname": "Keydets",       "city": "Lexington",    "state": "VA", "conference": "Southern", "home_court": "Cameron Hall",                    "venue_rating": 38, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Western Carolina","nickname": "Catamounts",    "city": "Cullowhee",    "state": "NC", "conference": "Southern", "home_court": "Ramsey Center",                   "venue_rating": 42, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Wofford",         "nickname": "Terriers",      "city": "Spartanburg",  "state": "SC", "conference": "Southern", "home_court": "Jerry Richardson Indoor Stadium", "venue_rating": 46, "tourney": 6,  "ff": 0, "titles": 0},

    # SOUTHLAND
    {"name": "Houston Christian","nickname": "Huskies",      "city": "Houston",      "state": "TX", "conference": "Southland", "home_court": "Sharp Gymnasium",              "venue_rating": 36, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Lamar",           "nickname": "Cardinals",     "city": "Beaumont",     "state": "TX", "conference": "Southland", "home_court": "Montagne Center",              "venue_rating": 44, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "McNeese",         "nickname": "Cowboys",       "city": "Lake Charles", "state": "LA", "conference": "Southland", "home_court": "The Legacy Center",            "venue_rating": 40, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "New Orleans",     "nickname": "Privateers",    "city": "New Orleans",  "state": "LA", "conference": "Southland", "home_court": "Lakefront Arena",              "venue_rating": 48, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Nicholls",        "nickname": "Colonels",      "city": "Thibodaux",    "state": "LA", "conference": "Southland", "home_court": "Stopher Gymnasium",            "venue_rating": 36, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Northwestern State","nickname": "Demons",      "city": "Natchitoches", "state": "LA", "conference": "Southland", "home_court": "Prather Coliseum",             "venue_rating": 38, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Southeastern Louisiana","nickname": "Lions",   "city": "Hammond",      "state": "LA", "conference": "Southland", "home_court": "University Center",            "venue_rating": 38, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Stephen F. Austin","nickname": "Lumberjacks",  "city": "Nacogdoches",  "state": "TX", "conference": "Southland", "home_court": "William R. Johnson Coliseum",  "venue_rating": 42, "tourney": 5,  "ff": 0, "titles": 0},

    # SWAC
    {"name": "Alabama A&M",         "nickname": "Bulldogs",  "city": "Huntsville",   "state": "AL", "conference": "SWAC", "home_court": "Alabama A&M Events Center",        "venue_rating": 34, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Alabama State",       "nickname": "Hornets",   "city": "Montgomery",   "state": "AL", "conference": "SWAC", "home_court": "Dunn-Oliver Acadome",              "venue_rating": 38, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Alcorn State",        "nickname": "Braves",    "city": "Lorman",       "state": "MS", "conference": "SWAC", "home_court": "Davey Whitney Complex",            "venue_rating": 32, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Arkansas-Pine Bluff", "nickname": "Golden Lions","city": "Pine Bluff", "state": "AR", "conference": "SWAC", "home_court": "K. L. Johnson Complex",            "venue_rating": 30, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Bethune-Cookman",     "nickname": "Wildcats",  "city": "Daytona Beach","state": "FL", "conference": "SWAC", "home_court": "Moore Gymnasium",                  "venue_rating": 30, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "Florida A&M",         "nickname": "Rattlers",  "city": "Tallahassee",  "state": "FL", "conference": "SWAC", "home_court": "Lawson Multipurpose Center",        "venue_rating": 34, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Grambling State",     "nickname": "Tigers",    "city": "Grambling",    "state": "LA", "conference": "SWAC", "home_court": "Fredrick C. Hobdy Assembly Center", "venue_rating": 32, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Jackson State",       "nickname": "Tigers",    "city": "Jackson",      "state": "MS", "conference": "SWAC", "home_court": "Williams Assembly Center",          "venue_rating": 34, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Mississippi Valley State","nickname": "Delta Devils","city": "Itta Bena","state": "MS","conference": "SWAC","home_court": "Harrison HPER Complex",             "venue_rating": 28, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Prairie View A&M",    "nickname": "Panthers",  "city": "Prairie View", "state": "TX", "conference": "SWAC", "home_court": "William Nicks Building",           "venue_rating": 30, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Southern",            "nickname": "Jaguars",   "city": "Baton Rouge",  "state": "LA", "conference": "SWAC", "home_court": "F. G. Clark Center",               "venue_rating": 36, "tourney": 9,  "ff": 0, "titles": 0},
    {"name": "Texas Southern",      "nickname": "Tigers",    "city": "Houston",      "state": "TX", "conference": "SWAC", "home_court": "Health and Physical Education Arena","venue_rating": 38, "tourney": 11, "ff": 0, "titles": 0},

    # SUMMIT LEAGUE
    {"name": "Kansas City",     "nickname": "Roos",          "city": "Kansas City",  "state": "MO", "conference": "Summit", "home_court": "Swinney Recreation Center",      "venue_rating": 40, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "North Dakota",    "nickname": "Fighting Hawks", "city": "Grand Forks",  "state": "ND", "conference": "Summit", "home_court": "Betty Engelstad Sioux Center",   "venue_rating": 44, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "North Dakota State","nickname": "Bison",        "city": "Fargo",        "state": "ND", "conference": "Summit", "home_court": "Bison Sports Arena",             "venue_rating": 46, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Omaha",           "nickname": "Mavericks",      "city": "Omaha",        "state": "NE", "conference": "Summit", "home_court": "Baxter Arena",                   "venue_rating": 52, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Oral Roberts",    "nickname": "Golden Eagles",  "city": "Tulsa",        "state": "OK", "conference": "Summit", "home_court": "Mabee Center",                   "venue_rating": 52, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "South Dakota",    "nickname": "Coyotes",        "city": "Vermillion",   "state": "SD", "conference": "Summit", "home_court": "Sanford Coyote Sports Center",   "venue_rating": 48, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "South Dakota State","nickname": "Jackrabbits",  "city": "Brookings",    "state": "SD", "conference": "Summit", "home_court": "Frost Arena",                    "venue_rating": 50, "tourney": 7,  "ff": 0, "titles": 0},

    # SUN BELT
    {"name": "Appalachian State","nickname": "Mountaineers",  "city": "Boone",        "state": "NC", "conference": "Sun Belt", "home_court": "Holmes Convocation Center",   "venue_rating": 50, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Arkansas State",  "nickname": "Red Wolves",     "city": "Jonesboro",    "state": "AR", "conference": "Sun Belt", "home_court": "First National Bank Arena",   "venue_rating": 48, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Coastal Carolina","nickname": "Chanticleers",   "city": "Conway",       "state": "SC", "conference": "Sun Belt", "home_court": "HTC Center",                  "venue_rating": 46, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "Georgia Southern","nickname": "Eagles",         "city": "Statesboro",   "state": "GA", "conference": "Sun Belt", "home_court": "Hanner Fieldhouse",           "venue_rating": 44, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Georgia State",   "nickname": "Panthers",       "city": "Atlanta",      "state": "GA", "conference": "Sun Belt", "home_court": "GSU Sports Arena",            "venue_rating": 50, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "James Madison",   "nickname": "Dukes",          "city": "Harrisonburg", "state": "VA", "conference": "Sun Belt", "home_court": "Atlantic Union Bank Center",  "venue_rating": 52, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Louisiana",       "nickname": "Ragin Cajuns",   "city": "Lafayette",    "state": "LA", "conference": "Sun Belt", "home_court": "Cajundome",                   "venue_rating": 58, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Louisiana-Monroe","nickname": "Warhawks",       "city": "Monroe",       "state": "LA", "conference": "Sun Belt", "home_court": "Fant-Ewing Coliseum",         "venue_rating": 44, "tourney": 7,  "ff": 0, "titles": 0},
    {"name": "Marshall",        "nickname": "Thundering Herd","city": "Huntington",   "state": "WV", "conference": "Sun Belt", "home_court": "Cam Henderson Center",        "venue_rating": 52, "tourney": 6,  "ff": 0, "titles": 0},
    {"name": "Old Dominion",    "nickname": "Monarchs",       "city": "Norfolk",      "state": "VA", "conference": "Sun Belt", "home_court": "Chartway Arena",              "venue_rating": 56, "tourney": 12, "ff": 0, "titles": 0},
    {"name": "South Alabama",   "nickname": "Jaguars",        "city": "Mobile",       "state": "AL", "conference": "Sun Belt", "home_court": "Mitchell Center",             "venue_rating": 50, "tourney": 8,  "ff": 0, "titles": 0},
    {"name": "Southern Miss",   "nickname": "Golden Eagles",  "city": "Hattiesburg",  "state": "MS", "conference": "Sun Belt", "home_court": "Reed Green Coliseum",         "venue_rating": 50, "tourney": 3,  "ff": 0, "titles": 0},
    {"name": "Texas State",     "nickname": "Bobcats",        "city": "San Marcos",   "state": "TX", "conference": "Sun Belt", "home_court": "Strahan Coliseum",            "venue_rating": 48, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Troy",            "nickname": "Trojans",        "city": "Troy",         "state": "AL", "conference": "Sun Belt", "home_court": "Trojan Arena",                "venue_rating": 44, "tourney": 3,  "ff": 0, "titles": 0},

    # WCC
    {"name": "Gonzaga",         "nickname": "Bulldogs",       "city": "Spokane",      "state": "WA", "conference": "WCC", "home_court": "McCarthey Athletic Center",        "venue_rating": 82, "tourney": 27, "ff": 2, "titles": 0},
    {"name": "Loyola Marymount","nickname": "Lions",          "city": "Los Angeles",  "state": "CA", "conference": "WCC", "home_court": "Gersten Pavilion",                "venue_rating": 50, "tourney": 5,  "ff": 0, "titles": 0},
    {"name": "Oregon State",    "nickname": "Beavers",        "city": "Corvallis",    "state": "OR", "conference": "WCC", "home_court": "Gill Coliseum",                   "venue_rating": 64, "tourney": 18, "ff": 2, "titles": 0},
    {"name": "Pacific",         "nickname": "Tigers",         "city": "Stockton",     "state": "CA", "conference": "WCC", "home_court": "Alex G. Spanos Center",           "venue_rating": 50, "tourney": 9,  "ff": 0, "titles": 0},
    {"name": "Pepperdine",      "nickname": "Waves",          "city": "Malibu",       "state": "CA", "conference": "WCC", "home_court": "Firestone Fieldhouse",            "venue_rating": 52, "tourney": 13, "ff": 0, "titles": 0},
    {"name": "Portland",        "nickname": "Pilots",         "city": "Portland",     "state": "OR", "conference": "WCC", "home_court": "Chiles Center",                   "venue_rating": 48, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Saint Mary's",    "nickname": "Gaels",          "city": "Moraga",       "state": "CA", "conference": "WCC", "home_court": "University Credit Union Pavilion","venue_rating": 62, "tourney": 14, "ff": 0, "titles": 0},
    {"name": "San Diego",       "nickname": "Toreros",        "city": "San Diego",    "state": "CA", "conference": "WCC", "home_court": "Jenny Craig Pavilion",            "venue_rating": 48, "tourney": 4,  "ff": 0, "titles": 0},
    {"name": "San Francisco",   "nickname": "Dons",           "city": "San Francisco","state": "CA", "conference": "WCC", "home_court": "The Sobrato Center",              "venue_rating": 52, "tourney": 16, "ff": 3, "titles": 2},
    {"name": "Santa Clara",     "nickname": "Broncos",        "city": "Santa Clara",  "state": "CA", "conference": "WCC", "home_court": "Leavey Center",                   "venue_rating": 50, "tourney": 11, "ff": 1, "titles": 0},
    {"name": "Seattle",         "nickname": "Redhawks",       "city": "Seattle",      "state": "WA", "conference": "WCC", "home_court": "Redhawk Center",                  "venue_rating": 46, "tourney": 11, "ff": 1, "titles": 0},
    {"name": "Washington State","nickname": "Cougars",        "city": "Pullman",      "state": "WA", "conference": "WCC", "home_court": "Beasley Coliseum",                "venue_rating": 60, "tourney": 7,  "ff": 1, "titles": 0},

    # WAC
    {"name": "Abilene Christian","nickname": "Wildcats",      "city": "Abilene",      "state": "TX", "conference": "WAC", "home_court": "Moody Coliseum",                  "venue_rating": 40, "tourney": 2,  "ff": 0, "titles": 0},
    {"name": "Southern Utah",   "nickname": "Thunderbirds",   "city": "Cedar City",   "state": "UT", "conference": "WAC", "home_court": "America First Event Center",      "venue_rating": 42, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Tarleton State",  "nickname": "Texans",         "city": "Stephenville", "state": "TX", "conference": "WAC", "home_court": "EECU Center",                     "venue_rating": 38, "tourney": 0,  "ff": 0, "titles": 0},
    {"name": "UT Arlington",    "nickname": "Mavericks",      "city": "Arlington",    "state": "TX", "conference": "WAC", "home_court": "College Park Center",             "venue_rating": 46, "tourney": 1,  "ff": 0, "titles": 0},
    {"name": "Utah Valley",     "nickname": "Wolverines",     "city": "Orem",         "state": "UT", "conference": "WAC", "home_court": "UCCU Center",                     "venue_rating": 44, "tourney": 0,  "ff": 0, "titles": 0},
]


def build_all_d1_programs():
    from program import create_program
    from coach import ARCHETYPE_WEIGHTS

    archetypes = list(ARCHETYPE_WEIGHTS.keys())
    weights    = list(ARCHETYPE_WEIGHTS.values())

    programs = []
    for data in ALL_D1_PROGRAMS:
        prestige = calc_prestige(data["tourney"], data["ff"], data["titles"], data["conference"])
        gravity  = get_gravity(prestige, data["conference"])

        # Pick archetype from the same weighted distribution used everywhere
        archetype = random.choices(archetypes, weights=weights, k=1)[0]

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
        )
        programs.append(p)
    return programs


if __name__ == "__main__":
    programs = build_all_d1_programs()

    print("Total D1 programs loaded: " + str(len(programs)))
    print("")

    elite   = [p for p in programs if p["prestige_current"] >= 80]
    good    = [p for p in programs if 60 <= p["prestige_current"] < 80]
    average = [p for p in programs if 40 <= p["prestige_current"] < 60]
    low     = [p for p in programs if 20 <= p["prestige_current"] < 40]
    bottom  = [p for p in programs if p["prestige_current"] < 20]

    print("Prestige distribution:")
    print("  Elite  (80+):    " + str(len(elite)))
    print("  Good   (60-79):  " + str(len(good)))
    print("  Average(40-59):  " + str(len(average)))
    print("  Low    (20-39):  " + str(len(low)))
    print("  Bottom (<20):    " + str(len(bottom)))
    print("")

    sorted_programs = sorted(programs, key=lambda p: p["prestige_current"], reverse=True)
    print("Top 25 by prestige:")
    for p in sorted_programs[:25]:
        print("  " + str(p["prestige_current"]) + " (" + p["prestige_grade"] + ")  " + p["name"] + " [" + p["conference"] + "]")

    print("")
    print("Bottom 10 by prestige:")
    for p in sorted_programs[-10:]:
        print("  " + str(p["prestige_current"]) + " (" + p["prestige_grade"] + ")  " + p["name"] + " [" + p["conference"] + "]")

    print("")
    osu = next(p for p in programs if p["name"] == "Oklahoma State")
    print("Oklahoma State: " + str(osu["prestige_current"]) + " (" + osu["prestige_grade"] + ")  Venue: " + str(osu["venue_rating"]) + "/100")
