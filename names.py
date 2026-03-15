import random

# -----------------------------------------
# COLLEGE HOOPS SIM -- Name Generator v0.1
# Heritage-based name pools for realistic
# player name generation
# Heritage is a hidden attribute -- drives
# names now, image generation later
# -----------------------------------------

# Heritage options
HERITAGE_TYPES = [
    "african_american",
    "white_european",
    "latino",
    "asian_pacific",
    "mixed",
]

# Default D1 weighting -- reflects real college basketball demographics
DEFAULT_WEIGHTS = {
    "african_american": 58,
    "white_european":   26,
    "latino":           10,
    "asian_pacific":     2,
    "mixed":             4,
}

# Conference-specific weightings
CONFERENCE_WEIGHTS = {
    # SWAC and MEAC -- historically Black conferences
    "SWAC": {"african_american": 82, "white_european": 6,  "latino": 7,  "asian_pacific": 1, "mixed": 4},
    "MEAC": {"african_american": 80, "white_european": 8,  "latino": 7,  "asian_pacific": 1, "mixed": 4},
    # Big Sky -- largely rural/mountain west, skews whiter
    "Big Sky":    {"african_american": 38, "white_european": 46, "latino": 10, "asian_pacific": 2, "mixed": 4},
    # Ivy League -- diverse but more white/international
    "Ivy League": {"african_american": 42, "white_european": 38, "latino": 10, "asian_pacific": 6, "mixed": 4},
    # Patriot League -- similar to Ivy
    "Patriot":    {"african_american": 40, "white_european": 40, "latino": 10, "asian_pacific": 4, "mixed": 6},
    # WAC -- Southwest schools, higher Latino
    "WAC":        {"african_american": 44, "white_european": 28, "latino": 20, "asian_pacific": 3, "mixed": 5},
    # Southland -- Gulf Coast, higher Latino
    "Southland":  {"african_american": 48, "white_european": 24, "latino": 20, "asian_pacific": 2, "mixed": 6},
    # WCC -- West Coast, more Asian/Pacific and Latino
    "WCC":        {"african_american": 48, "white_european": 28, "latino": 14, "asian_pacific": 5, "mixed": 5},
    # Mountain West -- Southwest mix
    "Mountain West": {"african_american": 50, "white_european": 30, "latino": 14, "asian_pacific": 2, "mixed": 4},
    # Big West -- California schools, diverse
    "Big West":   {"african_american": 46, "white_european": 26, "latino": 16, "asian_pacific": 6, "mixed": 6},
}

# -----------------------------------------
# NAME POOLS
# -----------------------------------------

FIRST_NAMES = {
    "african_american": [
        "Marcus", "DeShawn", "Malik", "Jamal", "Darius", "Tre", "Kendall",
        "Jaylen", "Trayvon", "Deon", "Rasheed", "Antwon", "Keyshawn",
        "Lamar", "Tyrese", "Devonte", "Marques", "Darnell", "Javon",
        "Terrell", "Quincy", "Dashawn", "Jalen", "Corey", "Darryl",
        "DeAndre", "Kevon", "Tyreke", "Rodney", "Darius", "Elijah",
        "Isaiah", "Jordan", "Trevon", "Devin", "Marquise", "Jamari",
        "Keyon", "Nate", "Reggie", "Kareem", "Hakeem", "Shareef",
        "Dwayne", "Lebron", "Kyrie", "Kawhi", "Zion", "Trae", "Ja",
        "Anfernee", "Latrell", "Stephon", "Alonzo", "Vince", "Caron",
        "Carmelo", "Amar'e", "Dwight", "Kevin", "LaMarcus", "Al",
        "Tobias", "Justise", "Thaddeus", "Bismack", "Festus", "Ekpe",
        "Brandon", "Chris", "James", "Damon", "Antonio", "Andre",
        "Antwan", "Cedric", "Darrell", "Dominique", "Eldridge", "Floyd",
        "Gerald", "Harold", "Irvin", "Jerome", "Kenneth", "Leonard",
        "Maurice", "Nathan", "Orlando", "Percy", "Raymond", "Samuel",
        "Thomas", "Ulysses", "Vernon", "Walter", "Xavier", "Yusuf",
    ],
    "white_european": [
        "Tyler", "Ryan", "Kyle", "Connor", "Brady", "Chase", "Cody",
        "Derek", "Evan", "Grant", "Hunter", "Jake", "Kevin", "Logan",
        "Matt", "Nick", "Owen", "Parker", "Quinn", "Reed", "Scott",
        "Travis", "Wes", "Alex", "Ben", "Blake", "Bryce", "Caleb",
        "Drew", "Dylan", "Eric", "Frank", "Garrett", "Hayden", "Ian",
        "Jason", "Justin", "Liam", "Mason", "Nathan", "Noah", "Oliver",
        "Patrick", "Peyton", "Robbie", "Sam", "Seth", "Shane", "Spencer",
        "Tanner", "Tim", "Todd", "Tom", "Trevor", "Troy", "Tucker",
        "Wade", "Will", "Zach", "Adam", "Aaron", "Austin", "Brent",
        "Brett", "Brian", "Cameron", "Chad", "Christian", "Colton",
        "Craig", "Curtis", "Dale", "Danny", "David", "Dean", "Derrick",
        "Doug", "Edward", "Ethan", "Finn", "Gavin", "Glen", "Greg",
        "Heath", "Jack", "Jeff", "Joel", "John", "Jonathan", "Jordan",
        "Josh", "Keith", "Kirk", "Lance", "Lars", "Lee", "Luke",
        "Mark", "Michael", "Miles", "Mitchell", "Paul", "Peter", "Phil",
        "Randy", "Rich", "Rob", "Roger", "Ross", "Sean", "Stephen",
        "Steve", "Stuart", "Taylor", "Ted", "Terry", "Theo", "Wade",
    ],
    "latino": [
        "Carlos", "Miguel", "Jose", "Juan", "Luis", "Diego", "Andres",
        "Roberto", "Ricardo", "Emmanuel", "Sergio", "Fernando", "Alejandro",
        "Marco", "Pablo", "Rafael", "Angel", "Victor", "Eduardo", "Manuel",
        "Hector", "Cesar", "Oscar", "Rodrigo", "Alvaro", "Ernesto",
        "Gustavo", "Ignacio", "Joaquin", "Lorenzo", "Marcos", "Nicolas",
        "Orlando", "Pedro", "Raul", "Sebastian", "Tomas", "Ulises",
        "Valentin", "Xavier", "Yohan", "Zacharias", "Adrian", "Bruno",
        "Cristian", "Daniel", "Enrique", "Felipe", "Gabriel", "Hugo",
        "Ivan", "Javier", "Kevin", "Leonardo", "Mario", "Nelson",
        "Omar", "Patricio", "Quentin", "Ramon", "Santiago", "Teodoro",
        "Uriel", "Vicente", "Wilfredo", "Alex", "Benito", "Camilo",
        "David", "Esteban", "Francisco", "Gerardo", "Hernan", "Israel",
        "Jorge", "Julio", "Leonel", "Mauricio", "Noel", "Octavio",
    ],
    "asian_pacific": [
        "Kai", "Koa", "Kenji", "Hiro", "Ryu", "Jin", "Wei", "Tae",
        "Sung", "Yong", "Min", "Jun", "Park", "Kim", "Lee", "Choi",
        "Joon", "Dae", "Hyun", "Soo", "Kang", "Bong", "Chan", "Dong",
        "Eun", "Fong", "Gang", "Han", "Il", "Jae", "Kong", "Liang",
        "Ming", "Ning", "Pang", "Qing", "Ren", "Sheng", "Tang",
        "Uong", "Vang", "Wang", "Xing", "Yang", "Zeng", "Akira",
        "Daiki", "Hayato", "Isamu", "Jiro", "Kazuki", "Makoto",
        "Naoki", "Osamu", "Riku", "Satoshi", "Takashi", "Yuki",
        "Tonga", "Sione", "Filipo", "Amani", "Tevita", "Latu",
    ],
}

LAST_NAMES = {
    "african_american": [
        "Johnson", "Williams", "Jackson", "Davis", "Brown", "Jones",
        "Wilson", "Taylor", "Thomas", "Moore", "Harris", "Martin",
        "Thompson", "White", "Robinson", "Walker", "Lewis", "Allen",
        "Young", "King", "Wright", "Scott", "Green", "Baker", "Adams",
        "Nelson", "Carter", "Mitchell", "Perez", "Roberts", "Turner",
        "Phillips", "Campbell", "Parker", "Evans", "Edwards", "Collins",
        "Stewart", "Sanchez", "Morris", "Rogers", "Reed", "Cook",
        "Morgan", "Bell", "Murphy", "Bailey", "Rivera", "Cooper",
        "Richardson", "Cox", "Howard", "Ward", "Torres", "Peterson",
        "Gray", "Ramirez", "James", "Watson", "Brooks", "Kelly",
        "Sanders", "Price", "Bennett", "Wood", "Barnes", "Ross",
        "Henderson", "Coleman", "Jenkins", "Perry", "Powell", "Long",
        "Patterson", "Hughes", "Flores", "Washington", "Butler",
        "Simmons", "Foster", "Gonzales", "Bryant", "Alexander",
        "Russell", "Griffin", "Diggs", "Durant", "Irving", "Curry",
        "Wade", "Paul", "George", "Leonard", "Westbrook", "Harden",
        "Booker", "Ingram", "Ball", "Morant", "Williamson", "Young",
        "Tatum", "Brown", "Smart", "Holiday", "Middleton", "Beal",
    ],
    "white_european": [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller",
        "Davis", "Wilson", "Anderson", "Taylor", "Thomas", "Moore",
        "Martin", "Thompson", "White", "Harris", "Robinson", "Walker",
        "Lewis", "Allen", "Young", "King", "Wright", "Scott", "Green",
        "Baker", "Adams", "Nelson", "Carter", "Mitchell", "Roberts",
        "Turner", "Phillips", "Campbell", "Parker", "Evans", "Edwards",
        "Collins", "Stewart", "Morris", "Rogers", "Reed", "Cook",
        "Morgan", "Bell", "Bailey", "Cooper", "Richardson", "Cox",
        "Peterson", "Gray", "Watson", "Brooks", "Kelly", "Price",
        "Bennett", "Wood", "Barnes", "Ross", "Henderson", "Jenkins",
        "Powell", "Long", "Patterson", "Hughes", "Butler", "Foster",
        "Russell", "Griffin", "Hayes", "Myers", "Ford", "Hamilton",
        "Graham", "Sullivan", "Wallace", "Woods", "Cole", "West",
        "Jordan", "Owens", "Reynolds", "Fisher", "Ellis", "Harrison",
        "Gibson", "Mcdonald", "Cruz", "Marshall", "Ortiz", "Gomez",
        "Murray", "Freeman", "Wells", "Webb", "Simpson", "Stevens",
        "Tucker", "Porter", "Hunter", "Hicks", "Crawford", "Henry",
        "Boyd", "Mason", "Morales", "Kennedy", "Warren", "Dixon",
        "Ramos", "Reyes", "Burns", "Gordon", "Shaw", "Holmes", "Rice",
        "Robertson", "Hunt", "Black", "Daniels", "Palmer", "Mills",
        "Nichols", "Grant", "Knight", "Ferguson", "Rose", "Stone",
        "Hawkins", "Dunn", "Perkins", "Hudson", "Spencer", "Gardner",
        "Stephens", "Payne", "Pierce", "Berry", "Matthews", "Arnold",
        "Wagner", "Willis", "Ray", "Watkins", "Olson", "Carroll",
        "Duncan", "Snyder", "Hart", "Cunningham", "Bradley", "Lane",
        "Andrews", "Ruiz", "Harper", "Fox", "Riley", "Armstrong",
        "Carpenter", "Weaver", "Greene", "Lawrence", "Elliott", "Chavez",
        "Sims", "Austin", "Peters", "Kelley", "Franklin", "Lawson",
        "Fields", "Gutierrez", "Ryan", "Schmidt", "Carr", "Vasquez",
        "Castillo", "Wheeler", "Chapman", "Oliver", "Montgomery",
        "Richards", "Williamson", "Johnston", "Banks", "Meyer", "Bishop",
        "Mccoy", "Howell", "Alvarez", "Morrison", "Hansen", "Fernandez",
        "Garza", "Harvey", "Little", "Burton", "Stanley", "Nguyen",
        "George", "Jacobs", "Reid", "Kim", "Fuller", "Lynch", "Dean",
        "Gilbert", "Garrett", "Romero", "Welch", "Larson", "Frazier",
        "Burke", "Hanson", "Day", "Mendoza", "Moreno", "Bowman",
        "Medina", "Fowler", "Brewer", "Hoffman", "Carlson", "Silva",
        "Pearson", "Holland", "Douglas", "Fleming", "Jensen", "Vargas",
        "Byrd", "Davidson", "Hopkins", "May", "Terry", "Herrera",
        "Wade", "Soto", "Walters", "Curtis", "Neal", "Caldwell",
        "Lowe", "Jennings", "Barnett", "Graves", "Jimenez", "Horton",
        "Shelton", "Barrett", "Obrien", "Castro", "Sutton", "Gregory",
        "Mckinney", "Lucas", "Miles", "Craig", "Rodriquez", "Chambers",
        "Holt", "Lambert", "Fletcher", "Watts", "Bates", "Hale",
        "Rhodes", "Pena", "Beck", "Newman", "Haynes", "Mcdaniel",
        "Mendez", "Bush", "Vaughn", "Parks", "Dawson", "Santiago",
        "Norris", "Hardy", "Love", "Steele", "Curry", "Cannon",
        "Ballard", "Strickland", "Dennis", "Burnett", "Hogan", "Walton",
    ],
    "latino": [
        "Garcia", "Martinez", "Rodriguez", "Lopez", "Hernandez", "Gonzalez",
        "Perez", "Sanchez", "Ramirez", "Torres", "Flores", "Rivera",
        "Gomez", "Diaz", "Reyes", "Morales", "Cruz", "Ortiz", "Gutierrez",
        "Chavez", "Ramos", "Mendoza", "Castillo", "Vargas", "Romero",
        "Herrera", "Medina", "Aguilar", "Vega", "Cabrera", "Guerrero",
        "Jimenez", "Moreno", "Soto", "Alvarez", "Castaneda", "Cervantes",
        "Contreras", "Delgado", "Espinoza", "Fuentes", "Guzman",
        "Ibarra", "Juarez", "Lara", "Leiva", "Luna", "Maldonado",
        "Marin", "Mejia", "Mendez", "Miranda", "Molina", "Montes",
        "Montoya", "Munoz", "Navarro", "Nunez", "Ochoa", "Orozco",
        "Pacheco", "Padilla", "Palacios", "Paredes", "Pena", "Pineda",
        "Quintero", "Rangel", "Rivas", "Robles", "Rocha", "Rosales",
        "Ruiz", "Salazar", "Salinas", "Santiago", "Serrano", "Sierra",
        "Silva", "Solis", "Tapia", "Trejo", "Valdez", "Valencia",
        "Valenzuela", "Vasquez", "Vega", "Velasco", "Velazquez",
        "Villanueva", "Villarreal", "Zavala", "Zuniga",
    ],
    "asian_pacific": [
        "Kim", "Lee", "Park", "Choi", "Jung", "Kang", "Cho", "Yoon",
        "Chang", "Lim", "Han", "Oh", "Shin", "Yang", "Kwon", "Song",
        "Hong", "Jeon", "Hwang", "Ahn", "Wang", "Chen", "Liu", "Zhang",
        "Li", "Wu", "Zhou", "Sun", "Ma", "Hu", "Guo", "Lin", "He",
        "Gao", "Luo", "Zheng", "Xie", "Tang", "Xu", "Deng", "Feng",
        "Nguyen", "Tran", "Le", "Pham", "Hoang", "Phan", "Vu", "Dang",
        "Bui", "Do", "Ho", "Ngo", "Duong", "Ly", "Satou", "Suzuki",
        "Tanaka", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kobayashi",
        "Kato", "Yoshida", "Tonga", "Faleolo", "Tuilagi", "Fifita",
        "Havili", "Latu", "Nonu", "Rokocoko", "Slade", "Smith",
    ],
}


def get_heritage(conference=""):
    """
    Assigns a heritage to a player based on conference weighting.
    Returns one of the HERITAGE_TYPES strings.
    """
    weights = CONFERENCE_WEIGHTS.get(conference, DEFAULT_WEIGHTS)
    population = []
    for heritage, weight in weights.items():
        population.extend([heritage] * weight)
    return random.choice(population)


def get_name(heritage=None, conference=""):
    """
    Generates a full player name based on heritage.
    If heritage is None, assigns one based on conference.
    Mixed heritage pulls first name from one pool, last from another.
    Returns: (first_name, last_name, heritage)
    """
    if heritage is None:
        heritage = get_heritage(conference)

    if heritage == "mixed":
        # Pull from two different pools
        pools = ["african_american", "white_european", "latino", "asian_pacific"]
        first_pool = random.choice(pools)
        last_pool  = random.choice([p for p in pools if p != first_pool])
        first_name = random.choice(FIRST_NAMES[first_pool])
        last_name  = random.choice(LAST_NAMES[last_pool])
    else:
        first_name = random.choice(FIRST_NAMES[heritage])
        last_name  = random.choice(LAST_NAMES[heritage])

    return first_name, last_name, heritage


def generate_player_name(conference=""):
    """
    Main entry point for player name generation.
    Returns: (full_name, heritage)
    """
    first, last, heritage = get_name(conference=conference)
    full_name = first + " " + last
    return full_name, heritage


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":

    print("=== Name Generator Test ===")
    print("")

    # Generate 20 random players with no conference specified
    print("20 random D1 players (default weighting):")
    for _ in range(20):
        name, heritage = generate_player_name()
        print("  " + name + "  (" + heritage + ")")

    print("")
    print("10 players from a SWAC school:")
    for _ in range(10):
        name, heritage = generate_player_name(conference="SWAC")
        print("  " + name + "  (" + heritage + ")")

    print("")
    print("10 players from a Big Sky school:")
    for _ in range(10):
        name, heritage = generate_player_name(conference="Big Sky")
        print("  " + name + "  (" + heritage + ")")

    print("")
    print("10 players from a Southland school:")
    for _ in range(10):
        name, heritage = generate_player_name(conference="Southland")
        print("  " + name + "  (" + heritage + ")")

    print("")
    print("10 players from a WCC school:")
    for _ in range(10):
        name, heritage = generate_player_name(conference="WCC")
        print("  " + name + "  (" + heritage + ")")

    print("")
    # Show some mixed heritage examples
    print("10 mixed heritage players (cross-pool names):")
    for _ in range(10):
        name, heritage = generate_player_name()
        if heritage == "mixed":
            print("  " + name + "  (mixed)")
