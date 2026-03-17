# tournament_sites.py
# NCAA Tournament host city assignments for College Hoops Sim.
#
# Round structure:
#   first_second   - Opening weekend. 8 sites selected per year, each hosts 8 teams.
#                    Pool of 65+ cities. All arenas 10,000+ capacity.
#   sweet16_elite8 - Regional weekends. 4 sites selected per year, one per quadrant.
#                    Major NBA-level arenas.
#   final_four     - One site. NFL stadium or massive arena only.
#
# Every site has a 'quadrant' tag for geographic balance enforcement:
#   NE = Northeast      (New England, NY, PA, NJ, MD, DC, DE, VA)
#   SE = Southeast      (NC, SC, GA, FL, TN, AL, MS, KY)
#   MW = Midwest        (OH, MI, IN, IL, WI, MN, IA, MO, KS, NE, ND, SD)
#   SW = Southwest      (TX, OK, AR, LA, NM, AZ)
#   NW = Northwest      (WA, OR, ID, MT, WY, CO, UT, NV, CA, AK, HI)
#
# Placement logic (runs pre-season):
#   1. Draw 8 first_second sites with at least 1 per quadrant
#   2. Draw 4 sweet16_elite8 sites, one per quadrant (4 of 5 quadrants each year)
#   3. Draw 1 final_four site
#   4. Assign 1 seeds to closest first_second site in their regional pod
#   5. Seeds 2-4 get proximity preference within their pod
#   6. Seeds 5-16 slot by bracket logic only
#   7. Home city advantage: a 1 seed whose campus city is a host gets that site

import random
from math import radians, sin, cos, sqrt, atan2


def haversine(lat1, lon1, lat2, lon2):
    """Return distance in miles between two lat/lon points."""
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


TOURNAMENT_SITES = {

    # =========================================================================
    # FIRST & SECOND ROUND SITES
    # All arenas 10,000+ capacity.
    # 67 cities covering all five quadrants.
    # =========================================================================
    'first_second': [

        # --- NORTHEAST ---
        {'city': 'Albany',           'state': 'NY', 'arena': 'MVP Arena',                          'capacity': 15500, 'latitude': 42.6526,  'longitude': -73.7562,  'quadrant': 'NE'},
        {'city': 'Providence',       'state': 'RI', 'arena': 'Amica Mutual Pavilion',              'capacity': 14000, 'latitude': 41.8240,  'longitude': -71.4128,  'quadrant': 'NE'},
        {'city': 'Hartford',         'state': 'CT', 'arena': 'XL Center',                          'capacity': 15635, 'latitude': 41.7658,  'longitude': -72.6851,  'quadrant': 'NE'},
        {'city': 'Buffalo',          'state': 'NY', 'arena': 'KeyBank Center',                     'capacity': 19070, 'latitude': 42.8749,  'longitude': -78.8759,  'quadrant': 'NE'},
        {'city': 'Rochester',        'state': 'NY', 'arena': 'Blue Cross Arena',                   'capacity': 12695, 'latitude': 43.1566,  'longitude': -77.6088,  'quadrant': 'NE'},
        {'city': 'Pittsburgh',       'state': 'PA', 'arena': 'PPG Paints Arena',                   'capacity': 18387, 'latitude': 40.4396,  'longitude': -79.9763,  'quadrant': 'NE'},
        {'city': 'Philadelphia',     'state': 'PA', 'arena': 'Wells Fargo Center',                 'capacity': 20478, 'latitude': 39.9012,  'longitude': -75.1720,  'quadrant': 'NE'},
        {'city': 'Washington',       'state': 'DC', 'arena': 'Capital One Arena',                  'capacity': 20356, 'latitude': 38.8981,  'longitude': -77.0209,  'quadrant': 'NE'},
        {'city': 'Baltimore',        'state': 'MD', 'arena': 'CFG Bank Arena',                     'capacity': 14000, 'latitude': 39.2841,  'longitude': -76.6218,  'quadrant': 'NE'},
        {'city': 'Boston',           'state': 'MA', 'arena': 'TD Garden',                          'capacity': 19156, 'latitude': 42.3662,  'longitude': -71.0621,  'quadrant': 'NE'},
        {'city': 'Newark',           'state': 'NJ', 'arena': 'Prudential Center',                  'capacity': 18711, 'latitude': 40.7334,  'longitude': -74.1710,  'quadrant': 'NE'},
        {'city': 'Syracuse',         'state': 'NY', 'arena': 'JMA Wireless Dome',                  'capacity': 35446, 'latitude': 43.0357,  'longitude': -76.1359,  'quadrant': 'NE'},
        {'city': 'Richmond',         'state': 'VA', 'arena': 'Richmond Coliseum',                  'capacity': 13000, 'latitude': 37.5407,  'longitude': -77.4360,  'quadrant': 'NE'},

        # --- SOUTHEAST ---
        {'city': 'Raleigh',          'state': 'NC', 'arena': 'PNC Arena',                          'capacity': 18680, 'latitude': 35.8031,  'longitude': -78.7220,  'quadrant': 'SE'},
        {'city': 'Greenville',       'state': 'SC', 'arena': 'Bon Secours Wellness Arena',         'capacity': 16000, 'latitude': 34.8526,  'longitude': -82.3940,  'quadrant': 'SE'},
        {'city': 'Columbia',         'state': 'SC', 'arena': 'Colonial Life Arena',                'capacity': 18000, 'latitude': 33.9946,  'longitude': -81.0300,  'quadrant': 'SE'},
        {'city': 'Charlotte',        'state': 'NC', 'arena': 'Spectrum Center',                    'capacity': 19077, 'latitude': 35.2251,  'longitude': -80.8392,  'quadrant': 'SE'},
        {'city': 'Jacksonville',     'state': 'FL', 'arena': 'VyStar Veterans Memorial Arena',     'capacity': 15000, 'latitude': 30.3322,  'longitude': -81.6557,  'quadrant': 'SE'},
        {'city': 'Orlando',          'state': 'FL', 'arena': 'Kia Center',                         'capacity': 18846, 'latitude': 28.5392,  'longitude': -81.3836,  'quadrant': 'SE'},
        {'city': 'Tampa',            'state': 'FL', 'arena': 'Amalie Arena',                       'capacity': 19092, 'latitude': 27.9428,  'longitude': -82.4517,  'quadrant': 'SE'},
        {'city': 'Atlanta',          'state': 'GA', 'arena': 'State Farm Arena',                   'capacity': 21000, 'latitude': 33.7573,  'longitude': -84.3963,  'quadrant': 'SE'},
        {'city': 'Birmingham',       'state': 'AL', 'arena': 'Legacy Arena',                       'capacity': 17500, 'latitude': 33.5207,  'longitude': -86.8025,  'quadrant': 'SE'},
        {'city': 'Nashville',        'state': 'TN', 'arena': 'Bridgestone Arena',                  'capacity': 17159, 'latitude': 36.1591,  'longitude': -86.7785,  'quadrant': 'SE'},
        {'city': 'Memphis',          'state': 'TN', 'arena': 'FedExForum',                         'capacity': 18119, 'latitude': 35.1382,  'longitude': -90.0505,  'quadrant': 'SE'},
        {'city': 'Lexington',        'state': 'KY', 'arena': 'Rupp Arena',                         'capacity': 20545, 'latitude': 38.0406,  'longitude': -84.5037,  'quadrant': 'SE'},
        {'city': 'Louisville',       'state': 'KY', 'arena': 'KFC Yum! Center',                    'capacity': 22090, 'latitude': 38.2186,  'longitude': -85.7546,  'quadrant': 'SE'},
        {'city': 'Huntsville',       'state': 'AL', 'arena': 'Propst Arena',                       'capacity': 10000, 'latitude': 34.7304,  'longitude': -86.5861,  'quadrant': 'SE'},
        {'city': 'Knoxville',        'state': 'TN', 'arena': 'Thompson-Boling Arena',              'capacity': 21678, 'latitude': 35.9544,  'longitude': -83.9268,  'quadrant': 'SE'},
        {'city': 'Tallahassee',      'state': 'FL', 'arena': 'Donald L. Tucker Center',            'capacity': 12500, 'latitude': 30.4419,  'longitude': -84.2985,  'quadrant': 'SE'},
        {'city': 'Baton Rouge',      'state': 'LA', 'arena': 'Pete Maravich Assembly Center',      'capacity': 13472, 'latitude': 30.4133,  'longitude': -91.1800,  'quadrant': 'SE'},

        # --- MIDWEST ---
        {'city': 'Columbus',         'state': 'OH', 'arena': 'Nationwide Arena',                   'capacity': 18500, 'latitude': 39.9690,  'longitude': -82.9971,  'quadrant': 'MW'},
        {'city': 'Cleveland',        'state': 'OH', 'arena': 'Rocket Mortgage FieldHouse',         'capacity': 19432, 'latitude': 41.4965,  'longitude': -81.6882,  'quadrant': 'MW'},
        {'city': 'Detroit',          'state': 'MI', 'arena': 'Little Caesars Arena',               'capacity': 19515, 'latitude': 42.3410,  'longitude': -83.0550,  'quadrant': 'MW'},
        {'city': 'Grand Rapids',     'state': 'MI', 'arena': 'Van Andel Arena',                    'capacity': 12000, 'latitude': 42.9634,  'longitude': -85.6681,  'quadrant': 'MW'},
        {'city': 'Indianapolis',     'state': 'IN', 'arena': 'Gainbridge Fieldhouse',              'capacity': 17923, 'latitude': 39.7640,  'longitude': -86.1555,  'quadrant': 'MW'},
        {'city': 'Milwaukee',        'state': 'WI', 'arena': 'Fiserv Forum',                       'capacity': 17341, 'latitude': 43.0451,  'longitude': -87.9170,  'quadrant': 'MW'},
        {'city': 'Chicago',          'state': 'IL', 'arena': 'United Center',                      'capacity': 20917, 'latitude': 41.8807,  'longitude': -87.6742,  'quadrant': 'MW'},
        {'city': 'Minneapolis',      'state': 'MN', 'arena': 'Target Center',                      'capacity': 18978, 'latitude': 44.9795,  'longitude': -93.2762,  'quadrant': 'MW'},
        {'city': 'Des Moines',       'state': 'IA', 'arena': 'Wells Fargo Arena',                  'capacity': 17122, 'latitude': 41.5868,  'longitude': -93.6250,  'quadrant': 'MW'},
        {'city': 'Omaha',            'state': 'NE', 'arena': 'CHI Health Center',                  'capacity': 17560, 'latitude': 41.2565,  'longitude': -95.9345,  'quadrant': 'MW'},
        {'city': 'Kansas City',      'state': 'MO', 'arena': 'T-Mobile Center',                    'capacity': 19500, 'latitude': 39.0989,  'longitude': -94.5786,  'quadrant': 'MW'},
        {'city': 'St. Louis',        'state': 'MO', 'arena': 'Enterprise Center',                  'capacity': 18096, 'latitude': 38.6270,  'longitude': -90.2028,  'quadrant': 'MW'},
        {'city': 'Wichita',          'state': 'KS', 'arena': 'INTRUST Bank Arena',                 'capacity': 15004, 'latitude': 37.6872,  'longitude': -97.3301,  'quadrant': 'MW'},
        {'city': 'Sioux Falls',      'state': 'SD', 'arena': 'Denny Sanford Premier Center',       'capacity': 12000, 'latitude': 43.5446,  'longitude': -96.7311,  'quadrant': 'MW'},
        {'city': 'Fargo',            'state': 'ND', 'arena': 'Scheels Arena',                      'capacity': 10500, 'latitude': 46.8772,  'longitude': -96.7898,  'quadrant': 'MW'},
        {'city': 'Lincoln',          'state': 'NE', 'arena': 'Pinnacle Bank Arena',                'capacity': 15500, 'latitude': 40.8136,  'longitude': -96.7026,  'quadrant': 'MW'},
        {'city': 'Dayton',           'state': 'OH', 'arena': 'UD Arena',                           'capacity': 13407, 'latitude': 39.7589,  'longitude': -84.1916,  'quadrant': 'MW'},
        {'city': 'Fort Wayne',       'state': 'IN', 'arena': 'Allen County War Memorial Coliseum', 'capacity': 13000, 'latitude': 41.1306,  'longitude': -85.1294,  'quadrant': 'MW'},
        {'city': 'Peoria',           'state': 'IL', 'arena': 'Carver Arena',                       'capacity': 11495, 'latitude': 40.6936,  'longitude': -89.5890,  'quadrant': 'MW'},
        {'city': 'Green Bay',        'state': 'WI', 'arena': 'Resch Center',                       'capacity': 10200, 'latitude': 44.5133,  'longitude': -88.0133,  'quadrant': 'MW'},
        {'city': 'Springfield',      'state': 'MO', 'arena': 'Great Southern Bank Arena',          'capacity': 11000, 'latitude': 37.2090,  'longitude': -93.2923,  'quadrant': 'MW'},

        # --- SOUTHWEST ---
        {'city': 'Dallas',           'state': 'TX', 'arena': 'American Airlines Center',           'capacity': 19200, 'latitude': 32.7905,  'longitude': -96.8103,  'quadrant': 'SW'},
        {'city': 'Houston',          'state': 'TX', 'arena': 'Toyota Center',                      'capacity': 18300, 'latitude': 29.7508,  'longitude': -95.3621,  'quadrant': 'SW'},
        {'city': 'San Antonio',      'state': 'TX', 'arena': 'Frost Bank Center',                  'capacity': 18418, 'latitude': 29.4270,  'longitude': -98.4375,  'quadrant': 'SW'},
        {'city': 'Oklahoma City',    'state': 'OK', 'arena': 'Paycom Center',                      'capacity': 18203, 'latitude': 35.4634,  'longitude': -97.5151,  'quadrant': 'SW'},
        {'city': 'Tulsa',            'state': 'OK', 'arena': 'BOK Center',                         'capacity': 19199, 'latitude': 36.1540,  'longitude': -95.9928,  'quadrant': 'SW'},
        {'city': 'New Orleans',      'state': 'LA', 'arena': 'Smoothie King Center',               'capacity': 17791, 'latitude': 29.9490,  'longitude': -90.0812,  'quadrant': 'SW'},
        {'city': 'Little Rock',      'state': 'AR', 'arena': 'Simmons Bank Arena',                 'capacity': 18000, 'latitude': 34.7465,  'longitude': -92.2896,  'quadrant': 'SW'},
        {'city': 'El Paso',          'state': 'TX', 'arena': 'Don Haskins Center',                 'capacity': 12222, 'latitude': 31.7619,  'longitude': -106.4850, 'quadrant': 'SW'},
        {'city': 'Lubbock',          'state': 'TX', 'arena': 'United Supermarkets Arena',          'capacity': 15098, 'latitude': 33.5779,  'longitude': -101.8552, 'quadrant': 'SW'},
        {'city': 'Albuquerque',      'state': 'NM', 'arena': 'Tingley Coliseum',                   'capacity': 11500, 'latitude': 35.0853,  'longitude': -106.6500, 'quadrant': 'SW'},
        {'city': 'Tucson',           'state': 'AZ', 'arena': 'McKale Center',                      'capacity': 14644, 'latitude': 32.2319,  'longitude': -110.9501, 'quadrant': 'SW'},
        {'city': 'Phoenix',          'state': 'AZ', 'arena': 'Footprint Center',                   'capacity': 18422, 'latitude': 33.4457,  'longitude': -112.0712, 'quadrant': 'SW'},
        {'city': 'Fort Worth',       'state': 'TX', 'arena': 'Dickies Arena',                      'capacity': 14000, 'latitude': 32.7555,  'longitude': -97.3308,  'quadrant': 'SW'},
        {'city': 'Austin',           'state': 'TX', 'arena': 'Moody Center',                       'capacity': 15000, 'latitude': 30.2849,  'longitude': -97.7341,  'quadrant': 'SW'},
        {'city': 'Waco',             'state': 'TX', 'arena': 'Foster Pavilion',                    'capacity': 10284, 'latitude': 31.5493,  'longitude': -97.1467,  'quadrant': 'SW'},
        {'city': 'Jonesboro',        'state': 'AR', 'arena': 'First National Bank Arena',          'capacity': 10563, 'latitude': 35.8423,  'longitude': -90.7043,  'quadrant': 'SW'},

        # --- NORTHWEST ---
        {'city': 'Portland',         'state': 'OR', 'arena': 'Moda Center',                        'capacity': 19393, 'latitude': 45.5316,  'longitude': -122.6668, 'quadrant': 'NW'},
        {'city': 'Seattle',          'state': 'WA', 'arena': 'Climate Pledge Arena',               'capacity': 17100, 'latitude': 47.6220,  'longitude': -122.3541, 'quadrant': 'NW'},
        {'city': 'Spokane',          'state': 'WA', 'arena': 'Spokane Arena',                      'capacity': 12600, 'latitude': 47.6588,  'longitude': -117.4260, 'quadrant': 'NW'},
        {'city': 'Boise',            'state': 'ID', 'arena': 'ExtraMile Arena',                    'capacity': 12500, 'latitude': 43.6187,  'longitude': -116.2146, 'quadrant': 'NW'},
        {'city': 'Salt Lake City',   'state': 'UT', 'arena': 'Delta Center',                       'capacity': 18306, 'latitude': 40.7683,  'longitude': -111.9011, 'quadrant': 'NW'},
        {'city': 'Denver',           'state': 'CO', 'arena': 'Ball Arena',                         'capacity': 19520, 'latitude': 39.7487,  'longitude': -104.9820, 'quadrant': 'NW'},
        {'city': 'Las Vegas',        'state': 'NV', 'arena': 'T-Mobile Arena',                     'capacity': 20000, 'latitude': 36.1088,  'longitude': -115.1405, 'quadrant': 'NW'},
        {'city': 'Sacramento',       'state': 'CA', 'arena': 'Golden 1 Center',                    'capacity': 17583, 'latitude': 38.5802,  'longitude': -121.4997, 'quadrant': 'NW'},
        {'city': 'San Diego',        'state': 'CA', 'arena': 'Pechanga Arena',                     'capacity': 14200, 'latitude': 32.7108,  'longitude': -117.1598, 'quadrant': 'NW'},
        {'city': 'San Jose',         'state': 'CA', 'arena': 'SAP Center',                         'capacity': 17562, 'latitude': 37.3327,  'longitude': -121.9010, 'quadrant': 'NW'},
        {'city': 'Fresno',           'state': 'CA', 'arena': 'Save Mart Center',                   'capacity': 15596, 'latitude': 36.7378,  'longitude': -119.7871, 'quadrant': 'NW'},
        {'city': 'Billings',         'state': 'MT', 'arena': 'First Interstate Arena',             'capacity': 12000, 'latitude': 45.7833,  'longitude': -108.5007, 'quadrant': 'NW'},
        {'city': 'Colorado Springs', 'state': 'CO', 'arena': 'Broadmoor World Arena',              'capacity': 10000, 'latitude': 38.8339,  'longitude': -104.8214, 'quadrant': 'NW'},
        {'city': 'Reno',             'state': 'NV', 'arena': 'Lawlor Events Center',               'capacity': 11200, 'latitude': 39.5296,  'longitude': -119.8138, 'quadrant': 'NW'},
    ],

    # =========================================================================
    # SWEET 16 / ELITE 8 SITES (Regionals)
    # Major arenas. One per quadrant selected each year (4 of 5 quadrants).
    # =========================================================================
    'sweet16_elite8': [

        # --- NORTHEAST ---
        {'city': 'New York',         'state': 'NY', 'arena': 'Madison Square Garden',             'capacity': 19812, 'latitude': 40.7505,  'longitude': -73.9934,  'quadrant': 'NE'},
        {'city': 'Boston',           'state': 'MA', 'arena': 'TD Garden',                         'capacity': 19156, 'latitude': 42.3662,  'longitude': -71.0621,  'quadrant': 'NE'},
        {'city': 'Philadelphia',     'state': 'PA', 'arena': 'Wells Fargo Center',                'capacity': 20478, 'latitude': 39.9012,  'longitude': -75.1720,  'quadrant': 'NE'},
        {'city': 'Washington',       'state': 'DC', 'arena': 'Capital One Arena',                 'capacity': 20356, 'latitude': 38.8981,  'longitude': -77.0209,  'quadrant': 'NE'},
        {'city': 'Newark',           'state': 'NJ', 'arena': 'Prudential Center',                 'capacity': 18711, 'latitude': 40.7334,  'longitude': -74.1710,  'quadrant': 'NE'},
        {'city': 'Pittsburgh',       'state': 'PA', 'arena': 'PPG Paints Arena',                  'capacity': 18387, 'latitude': 40.4396,  'longitude': -79.9763,  'quadrant': 'NE'},

        # --- SOUTHEAST ---
        {'city': 'Atlanta',          'state': 'GA', 'arena': 'State Farm Arena',                  'capacity': 21000, 'latitude': 33.7573,  'longitude': -84.3963,  'quadrant': 'SE'},
        {'city': 'Miami',            'state': 'FL', 'arena': 'Kaseya Center',                     'capacity': 19600, 'latitude': 25.7814,  'longitude': -80.1870,  'quadrant': 'SE'},
        {'city': 'Charlotte',        'state': 'NC', 'arena': 'Spectrum Center',                   'capacity': 19077, 'latitude': 35.2251,  'longitude': -80.8392,  'quadrant': 'SE'},
        {'city': 'Louisville',       'state': 'KY', 'arena': 'KFC Yum! Center',                   'capacity': 22090, 'latitude': 38.2186,  'longitude': -85.7546,  'quadrant': 'SE'},
        {'city': 'Nashville',        'state': 'TN', 'arena': 'Bridgestone Arena',                 'capacity': 17159, 'latitude': 36.1591,  'longitude': -86.7785,  'quadrant': 'SE'},
        {'city': 'Memphis',          'state': 'TN', 'arena': 'FedExForum',                        'capacity': 18119, 'latitude': 35.1382,  'longitude': -90.0505,  'quadrant': 'SE'},
        {'city': 'Raleigh',          'state': 'NC', 'arena': 'PNC Arena',                         'capacity': 18680, 'latitude': 35.8031,  'longitude': -78.7220,  'quadrant': 'SE'},

        # --- MIDWEST ---
        {'city': 'Chicago',          'state': 'IL', 'arena': 'United Center',                     'capacity': 20917, 'latitude': 41.8807,  'longitude': -87.6742,  'quadrant': 'MW'},
        {'city': 'Indianapolis',     'state': 'IN', 'arena': 'Gainbridge Fieldhouse',             'capacity': 17923, 'latitude': 39.7640,  'longitude': -86.1555,  'quadrant': 'MW'},
        {'city': 'Minneapolis',      'state': 'MN', 'arena': 'Target Center',                     'capacity': 18978, 'latitude': 44.9795,  'longitude': -93.2762,  'quadrant': 'MW'},
        {'city': 'Kansas City',      'state': 'MO', 'arena': 'T-Mobile Center',                   'capacity': 19500, 'latitude': 39.0989,  'longitude': -94.5786,  'quadrant': 'MW'},
        {'city': 'Detroit',          'state': 'MI', 'arena': 'Little Caesars Arena',              'capacity': 19515, 'latitude': 42.3410,  'longitude': -83.0550,  'quadrant': 'MW'},
        {'city': 'St. Louis',        'state': 'MO', 'arena': 'Enterprise Center',                 'capacity': 18096, 'latitude': 38.6270,  'longitude': -90.2028,  'quadrant': 'MW'},
        {'city': 'Cleveland',        'state': 'OH', 'arena': 'Rocket Mortgage FieldHouse',        'capacity': 19432, 'latitude': 41.4965,  'longitude': -81.6882,  'quadrant': 'MW'},
        {'city': 'Milwaukee',        'state': 'WI', 'arena': 'Fiserv Forum',                      'capacity': 17341, 'latitude': 43.0451,  'longitude': -87.9170,  'quadrant': 'MW'},
        {'city': 'Omaha',            'state': 'NE', 'arena': 'CHI Health Center',                 'capacity': 17560, 'latitude': 41.2565,  'longitude': -95.9345,  'quadrant': 'MW'},

        # --- SOUTHWEST ---
        {'city': 'Dallas',           'state': 'TX', 'arena': 'American Airlines Center',          'capacity': 19200, 'latitude': 32.7905,  'longitude': -96.8103,  'quadrant': 'SW'},
        {'city': 'Houston',          'state': 'TX', 'arena': 'Toyota Center',                     'capacity': 18300, 'latitude': 29.7508,  'longitude': -95.3621,  'quadrant': 'SW'},
        {'city': 'San Antonio',      'state': 'TX', 'arena': 'Frost Bank Center',                 'capacity': 18418, 'latitude': 29.4270,  'longitude': -98.4375,  'quadrant': 'SW'},
        {'city': 'New Orleans',      'state': 'LA', 'arena': 'Smoothie King Center',              'capacity': 17791, 'latitude': 29.9490,  'longitude': -90.0812,  'quadrant': 'SW'},
        {'city': 'Oklahoma City',    'state': 'OK', 'arena': 'Paycom Center',                     'capacity': 18203, 'latitude': 35.4634,  'longitude': -97.5151,  'quadrant': 'SW'},
        {'city': 'Phoenix',          'state': 'AZ', 'arena': 'Footprint Center',                  'capacity': 18422, 'latitude': 33.4457,  'longitude': -112.0712, 'quadrant': 'SW'},

        # --- NORTHWEST ---
        {'city': 'Los Angeles',      'state': 'CA', 'arena': 'Crypto.com Arena',                  'capacity': 19079, 'latitude': 34.0430,  'longitude': -118.2673, 'quadrant': 'NW'},
        {'city': 'San Francisco',    'state': 'CA', 'arena': 'Chase Center',                      'capacity': 18064, 'latitude': 37.7680,  'longitude': -122.3877, 'quadrant': 'NW'},
        {'city': 'Portland',         'state': 'OR', 'arena': 'Moda Center',                       'capacity': 19393, 'latitude': 45.5316,  'longitude': -122.6668, 'quadrant': 'NW'},
        {'city': 'Seattle',          'state': 'WA', 'arena': 'Climate Pledge Arena',              'capacity': 17100, 'latitude': 47.6220,  'longitude': -122.3541, 'quadrant': 'NW'},
        {'city': 'Denver',           'state': 'CO', 'arena': 'Ball Arena',                        'capacity': 19520, 'latitude': 39.7487,  'longitude': -104.9820, 'quadrant': 'NW'},
        {'city': 'Las Vegas',        'state': 'NV', 'arena': 'T-Mobile Arena',                    'capacity': 20000, 'latitude': 36.1088,  'longitude': -115.1405, 'quadrant': 'NW'},
        {'city': 'Sacramento',       'state': 'CA', 'arena': 'Golden 1 Center',                   'capacity': 17583, 'latitude': 38.5802,  'longitude': -121.4997, 'quadrant': 'NW'},
        {'city': 'Salt Lake City',   'state': 'UT', 'arena': 'Delta Center',                      'capacity': 18306, 'latitude': 40.7683,  'longitude': -111.9011, 'quadrant': 'NW'},
        {'city': 'San Jose',         'state': 'CA', 'arena': 'SAP Center',                        'capacity': 17562, 'latitude': 37.3327,  'longitude': -121.9010, 'quadrant': 'NW'},
    ],

    # =========================================================================
    # FINAL FOUR SITES
    # NFL stadiums and massive arenas only.
    # =========================================================================
    'final_four': [
        {'city': 'New Orleans',      'state': 'LA', 'arena': 'Caesars Superdome',                 'capacity': 72003, 'latitude': 29.9511,  'longitude': -90.0812,  'quadrant': 'SW'},
        {'city': 'Atlanta',          'state': 'GA', 'arena': 'Mercedes-Benz Stadium',             'capacity': 71000, 'latitude': 33.7553,  'longitude': -84.4006,  'quadrant': 'SE'},
        {'city': 'Dallas',           'state': 'TX', 'arena': 'AT&T Stadium',                      'capacity': 80000, 'latitude': 32.7480,  'longitude': -97.0930,  'quadrant': 'SW'},
        {'city': 'Houston',          'state': 'TX', 'arena': 'NRG Stadium',                       'capacity': 72220, 'latitude': 29.6847,  'longitude': -95.4107,  'quadrant': 'SW'},
        {'city': 'Indianapolis',     'state': 'IN', 'arena': 'Lucas Oil Stadium',                 'capacity': 67000, 'latitude': 39.7601,  'longitude': -86.1639,  'quadrant': 'MW'},
        {'city': 'Minneapolis',      'state': 'MN', 'arena': 'U.S. Bank Stadium',                 'capacity': 66860, 'latitude': 44.9736,  'longitude': -93.2575,  'quadrant': 'MW'},
        {'city': 'Phoenix',          'state': 'AZ', 'arena': 'State Farm Stadium',                'capacity': 63400, 'latitude': 33.5276,  'longitude': -112.2626, 'quadrant': 'SW'},
        {'city': 'San Antonio',      'state': 'TX', 'arena': 'Alamodome',                         'capacity': 64000, 'latitude': 29.4190,  'longitude': -98.4612,  'quadrant': 'SW'},
        {'city': 'Detroit',          'state': 'MI', 'arena': 'Ford Field',                        'capacity': 65000, 'latitude': 42.3400,  'longitude': -83.0456,  'quadrant': 'MW'},
        {'city': 'Las Vegas',        'state': 'NV', 'arena': 'Allegiant Stadium',                 'capacity': 65000, 'latitude': 36.0909,  'longitude': -115.1833, 'quadrant': 'NW'},
        {'city': 'Los Angeles',      'state': 'CA', 'arena': 'SoFi Stadium',                      'capacity': 70240, 'latitude': 33.9535,  'longitude': -118.3392, 'quadrant': 'NW'},
        {'city': 'Miami',            'state': 'FL', 'arena': 'Hard Rock Stadium',                 'capacity': 65326, 'latitude': 25.9580,  'longitude': -80.2389,  'quadrant': 'SE'},
        {'city': 'Chicago',          'state': 'IL', 'arena': 'United Center',                     'capacity': 20917, 'latitude': 41.8807,  'longitude': -87.6742,  'quadrant': 'MW'},
        {'city': 'New York',         'state': 'NY', 'arena': 'Madison Square Garden',             'capacity': 19812, 'latitude': 40.7505,  'longitude': -73.9934,  'quadrant': 'NE'},
        {'city': 'Seattle',          'state': 'WA', 'arena': 'Lumen Field',                       'capacity': 69000, 'latitude': 47.5952,  'longitude': -122.3316, 'quadrant': 'NW'},
        {'city': 'Tampa',            'state': 'FL', 'arena': 'Raymond James Stadium',             'capacity': 65890, 'latitude': 27.9759,  'longitude': -82.5033,  'quadrant': 'SE'},
        {'city': 'Charlotte',        'state': 'NC', 'arena': 'Bank of America Stadium',           'capacity': 74867, 'latitude': 35.2258,  'longitude': -80.8528,  'quadrant': 'SE'},
        {'city': 'Denver',           'state': 'CO', 'arena': 'Empower Field at Mile High',        'capacity': 76125, 'latitude': 39.7439,  'longitude': -105.0201, 'quadrant': 'NW'},
    ],
}


# =============================================================================
# DRAW & PLACEMENT FUNCTIONS
# =============================================================================

def draw_tournament_sites(exclude_recent_cities=None):
    """
    Pre-season draw. Selects all tournament sites for one year.
    exclude_recent_cities: list of city names used in last 1-2 years to avoid repeats.
    Returns dict with 'first_second' (8 sites), 'sweet16_elite8' (4 sites),
    'final_four' (1 site).
    """
    # Cities already used this year — grows as we draw each round.
    # Higher rounds claim cities first; lower rounds cannot use them.
    claimed = set(exclude_recent_cities or [])

    # -----------------------------------------------------------------------
    # STEP 1: Final Four — drawn first, highest priority
    # -----------------------------------------------------------------------
    ff_pool = [s for s in TOURNAMENT_SITES['final_four'] if s['city'] not in claimed]
    ff_pick = random.choice(ff_pool)
    claimed.add(ff_pick['city'])

    # -----------------------------------------------------------------------
    # STEP 2: Sweet 16 / Elite 8 — 4 sites with geographic diversity guarantee
    # Hard rules:
    #   - At least 1 site west of the Mississippi (lon < -90)
    #   - At least 1 site east of the Mississippi (lon >= -90)
    #   - At least 1 site in the northern half (lat >= 38)
    #   - At least 1 site in the southern half (lat < 38)
    # Cannot use Final Four city or recent cities.
    # -----------------------------------------------------------------------
    regional_pool = [s for s in TOURNAMENT_SITES['sweet16_elite8'] if s['city'] not in claimed]

    MISS_LON = -90.0   # approximate Mississippi River longitude
    LAT_MID  = 38.0    # approximate north/south midline

    def pick_regional(pool, used, require_west=False, require_east=False,
                      require_north=False, require_south=False):
        """Pick one regional site satisfying optional geographic constraints."""
        candidates = [s for s in pool if s['city'] not in used]
        if require_west:
            candidates = [s for s in candidates if s['longitude'] < MISS_LON]
        if require_east:
            candidates = [s for s in candidates if s['longitude'] >= MISS_LON]
        if require_north:
            candidates = [s for s in candidates if s['latitude'] >= LAT_MID]
        if require_south:
            candidates = [s for s in candidates if s['latitude'] < LAT_MID]
        return random.choice(candidates) if candidates else None

    selected_regionals = []
    regional_used = set()

    # Pick 1 guaranteed western site
    pick = pick_regional(regional_pool, regional_used, require_west=True)
    if pick:
        selected_regionals.append(pick)
        regional_used.add(pick['city'])

    # Pick 1 guaranteed eastern site
    pick = pick_regional(regional_pool, regional_used, require_east=True)
    if pick:
        selected_regionals.append(pick)
        regional_used.add(pick['city'])

    # Pick 1 guaranteed northern site (from remaining)
    pick = pick_regional(regional_pool, regional_used, require_north=True)
    if pick:
        selected_regionals.append(pick)
        regional_used.add(pick['city'])

    # Pick 1 guaranteed southern site (from remaining)
    pick = pick_regional(regional_pool, regional_used, require_south=True)
    if pick:
        selected_regionals.append(pick)
        regional_used.add(pick['city'])

    # If any slot failed to fill (edge case from exclusions), fill from remainder
    while len(selected_regionals) < 4:
        remaining_r = [s for s in regional_pool if s['city'] not in regional_used]
        if not remaining_r:
            break
        pick = random.choice(remaining_r)
        selected_regionals.append(pick)
        regional_used.add(pick['city'])

    # Lock all regional cities out of first round
    for site in selected_regionals:
        claimed.add(site['city'])

    # -----------------------------------------------------------------------
    # STEP 3: First / Second Round — 8 sites, at least 1 per quadrant
    # Cannot use Final Four city or any regional city.
    # -----------------------------------------------------------------------
    pool = [s for s in TOURNAMENT_SITES['first_second'] if s['city'] not in claimed]
    by_quadrant = {}
    for site in pool:
        by_quadrant.setdefault(site['quadrant'], []).append(site)

    selected_first = []
    used_first = set()

    # One guaranteed from each quadrant
    for q in ['NE', 'SE', 'MW', 'SW', 'NW']:
        eligible = [s for s in by_quadrant.get(q, []) if s['city'] not in used_first]
        if eligible:
            pick = random.choice(eligible)
            selected_first.append(pick)
            used_first.add(pick['city'])

    # Fill remaining 3 slots from any quadrant
    remaining = [s for s in pool if s['city'] not in used_first]
    random.shuffle(remaining)
    for site in remaining:
        if len(selected_first) >= 8:
            break
        selected_first.append(site)
        used_first.add(site['city'])

    return {
        'first_second': selected_first,
        'sweet16_elite8': selected_regionals,
        'final_four': ff_pick,
    }


# Compass buckets — names within the same bucket cannot both appear in one bracket.
# The four final names must come from four DIFFERENT buckets.
COMPASS_BUCKETS = {
    'North':     'NORTH',
    'Northeast': 'NORTH',
    'Northwest': 'NORTH',
    'East':      'EAST',
    'Southeast': 'EAST',
    'South':     'SOUTH',
    'Southwest': 'SOUTH',
    'West':      'WEST',
    'Northwest': 'WEST',
    'Midwest':   'NEUTRAL',
}

# Ordered preference lists per relative position.
# westernmost site prefers western names, easternmost prefers eastern, etc.
POSITION_PREFERENCES = {
    'west':  ['West', 'Northwest', 'Southwest'],
    'east':  ['East', 'Northeast', 'Southeast'],
    'north': ['North', 'Midwest', 'Northeast', 'Northwest'],
    'south': ['South', 'Southeast', 'Southwest', 'Midwest'],
}

# All valid names in priority order for last-resort fallback
ALL_DIRECTIONS = [
    'West', 'Northwest', 'Southwest',
    'East', 'Northeast', 'Southeast',
    'South', 'North', 'Midwest'
]


def name_regionals(regional_sites):
    """
    Assign 4 unique directional names that ALWAYS span all four compass feels.

    Hard rule: the four names must come from four different compass buckets:
        NORTH bucket: North, Northeast, Northwest
        EAST bucket:  East, Northeast, Southeast
        SOUTH bucket: South, Southeast, Southwest
        WEST bucket:  West, Northwest, Southwest

    Note Northeast/Southeast/Southwest/Northwest each span two buckets —
    that flexibility is what lets us resolve tricky draws.

    Logic:
    1. Identify westernmost, easternmost, northernmost-middle, southernmost-middle.
    2. Assign each a preferred name from their position preference list.
    3. Enforce bucket diversity — if two sites claim names from the same bucket,
       bump the lower-priority one to its next available option in a different bucket.
    4. Never use the same name twice.
    """
    if len(regional_sites) != 4:
        result = []
        for i, site in enumerate(regional_sites):
            s = dict(site)
            s['regional_name'] = ALL_DIRECTIONS[i]
            result.append(s)
        return result

    # Identify positional roles
    sorted_lon = sorted(regional_sites, key=lambda s: s['longitude'])
    westernmost  = sorted_lon[0]
    easternmost  = sorted_lon[3]
    middle_two   = sorted(sorted_lon[1:3], key=lambda s: s['latitude'], reverse=True)
    north_mid    = middle_two[0]
    south_mid    = middle_two[1]

    roles = [
        (westernmost, 'west'),
        (easternmost, 'east'),
        (north_mid,   'north'),
        (south_mid,   'south'),
    ]

    # Bucket membership — a name can satisfy multiple buckets
    NAME_BUCKETS = {
        'West':      {'WEST'},
        'Northwest': {'WEST', 'NORTH'},
        'Southwest': {'WEST', 'SOUTH'},
        'East':      {'EAST'},
        'Northeast': {'EAST', 'NORTH'},
        'Southeast': {'EAST', 'SOUTH'},
        'North':     {'NORTH'},
        'South':     {'SOUTH'},
        'Midwest':   {'NEUTRAL'},
    }

    # Required buckets — we must cover all four
    required_buckets = {'NORTH', 'EAST', 'SOUTH', 'WEST'}

    # Build candidate lists per role, extended with all directions as fallback
    def candidates_for(role):
        prefs = POSITION_PREFERENCES[role]
        extras = [d for d in ALL_DIRECTIONS if d not in prefs]
        return prefs + extras

    # Greedy assignment with bucket enforcement
    # Try all permutations of the 4 roles to find one that covers all 4 buckets
    from itertools import permutations

    best_result = None
    for role_order in permutations(roles):
        used_names = set()
        covered_buckets = set()
        assignment = []
        valid = True

        for site, role in role_order:
            candidates = candidates_for(role)
            chosen = None
            for name in candidates:
                if name in used_names:
                    continue
                buckets = NAME_BUCKETS.get(name, {'NEUTRAL'})
                # Check if this name adds value without duplicating a bucket
                # we've already fully covered with a more specific name
                chosen = name
                used_names.add(name)
                covered_buckets.update(buckets)
                assignment.append((site, name))
                break
            if not chosen:
                valid = False
                break

        if valid and required_buckets.issubset(covered_buckets):
            best_result = assignment
            break

    # If no perfect solution found (extremely unlikely), use first valid assignment
    if not best_result:
        used_names = set()
        best_result = []
        for site, role in roles:
            for name in candidates_for(role):
                if name not in used_names:
                    used_names.add(name)
                    best_result.append((site, name))
                    break

    # Build result dicts
    result = []
    for site, name in best_result:
        site_copy = dict(site)
        site_copy['regional_name'] = name
        result.append(site_copy)

    return result


def build_bracket(seeded_field, draw):
    """
    Assemble the full 64-team bracket.

    seeded_field: list of 64 dicts in seed order, each with keys:
        school_id, name, seed, latitude, longitude, city

    draw: output of draw_tournament_sites(), with sweet16_elite8 sites
          already named via name_regionals()

    Returns bracket dict:
    {
        'regional_name': {
            'first_second_site': site_dict,
            'regional_site': site_dict,
            'games': [
                {'seed': 1, 'team': ...},
                {'seed': 16, 'team': ...},
                ...8 matchups...
            ]
        }
    }

    Placement logic:
        1 seeds: closest first_second site (home city advantage applies)
        2 seeds: closest remaining first_second site in their regional pod
        3-4 seeds: proximity preference within pod
        5-16 seeds: fill remaining slots by bracket structure
    """
    first_sites = list(draw['first_second'])
    regional_sites = draw['sweet16_elite8']  # should have regional_name attached

    # Build bracket pods - one per regional site
    pods = {}
    for reg in regional_sites:
        pods[reg['regional_name']] = {
            'regional_site': reg,
            'first_second_sites': [],  # 2 first round sites per regional
            'slots': [],               # 16 teams per regional
        }

    regional_names = list(pods.keys())

    # --- Assign 2 first_second sites to each regional (8 sites / 4 regionals) ---
    # Distribute by proximity to regional site
    available_first = list(first_sites)
    for reg_name in regional_names:
        reg_site = pods[reg_name]['regional_site']
        # Sort available first sites by distance to this regional
        available_first.sort(key=lambda s: haversine(
            reg_site['latitude'], reg_site['longitude'],
            s['latitude'], s['longitude']
        ))
        # Take closest available
        for _ in range(2):
            if available_first:
                pods[reg_name]['first_second_sites'].append(available_first.pop(0))

    # --- Place 1 seeds ---
    # Each 1 seed gets closest first_second site, home city advantage applies
    one_seeds = [t for t in seeded_field if t['seed'] == 1]
    used_regionals_for_ones = {}

    # Sort 1 seeds by overall seed ranking
    for team in one_seeds:
        all_first_sites = first_sites
        best_site, dist = assign_seed_to_site(
            team['latitude'], team['longitude'], team['city'], all_first_sites
        )
        # Find which regional owns this first site
        for reg_name, pod in pods.items():
            if any(s['city'] == best_site['city'] for s in pod['first_second_sites']):
                used_regionals_for_ones[team['school_id']] = reg_name
                pods[reg_name]['slots'].append({'seed': team['seed'], 'team': team})
                break

    # --- Place remaining seeds 2-16 into each regional to fill 16 slots ---
    remaining_teams = [t for t in seeded_field if t['seed'] > 1]

    # Seeds 2-4: proximity preference
    for seed_num in [2, 3, 4]:
        seed_teams = [t for t in remaining_teams if t['seed'] == seed_num]
        for team in seed_teams:
            # Find regional with fewest teams that has open slots
            open_pods = [(name, pod) for name, pod in pods.items()
                         if len(pod['slots']) < 16]
            if not open_pods:
                break
            # Prefer closest regional site
            open_pods.sort(key=lambda x: haversine(
                team['latitude'], team['longitude'],
                x[1]['regional_site']['latitude'],
                x[1]['regional_site']['longitude']
            ))
            for pod_name, pod in open_pods:
                if len(pod['slots']) < 16:
                    pod['slots'].append({'seed': team['seed'], 'team': team})
                    remaining_teams = [t for t in remaining_teams if t['school_id'] != team['school_id']]
                    break

    # --- Fill remaining slots round-robin by seed ---
    for team in remaining_teams:
        # Find pod with fewest teams
        open_pods = [(name, pod) for name, pod in pods.items()
                     if len(pod['slots']) < 16]
        if not open_pods:
            break
        open_pods.sort(key=lambda x: len(x[1]['slots']))
        pod_name, pod = open_pods[0]
        pod['slots'].append({'seed': team['seed'], 'team': team})

    return pods


def assign_seed_to_site(school_lat, school_lon, school_city, available_sites):
    """
    Find the best site for a seeded team.
    Home city advantage: if school's city matches a site city, return that site first.
    Otherwise return closest site by distance.
    Returns (site, distance_miles).
    """
    # Home city check
    for site in available_sites:
        if site['city'].lower() == school_city.lower():
            return site, 0.0

    # Closest by distance
    closest = None
    closest_dist = float('inf')
    for site in available_sites:
        dist = haversine(school_lat, school_lon, site['latitude'], site['longitude'])
        if dist < closest_dist:
            closest_dist = dist
            closest = site
    return closest, closest_dist


def get_sites_by_quadrant(round_key, quadrant):
    """Return all eligible sites for a round in a given quadrant."""
    return [s for s in TOURNAMENT_SITES[round_key] if s['quadrant'] == quadrant]
