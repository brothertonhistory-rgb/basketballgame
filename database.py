# -----------------------------------------
# COLLEGE HOOPS SIM -- Database Layer v1.0
#
# Single module that owns ALL database reads and writes.
# The rest of the codebase never touches SQL directly.
# The sim engine runs in memory exactly as before.
# This module is the write layer at season end.
#
# SAVE FILE LOCATION:
#   Dev path:  C:\Users\ootpe\OneDrive\Desktop\College Basketball Universe\saves\
#   Each save: saves\<save_name>\world.db
#   TODO Phase 5: replace dev path with Documents\CollegeHoopsSim\saves\ for distribution
#
# USAGE:
#   from database import init_db, commit_season_to_db, load_world_state, save_world_state
#
#   # On new game:
#   db_path = init_db("my_save")
#
#   # At end of every season (called from season.py):
#   commit_season_to_db(db_path, all_programs, tournament_results,
#                       season_year, free_agent_pool)
#
#   # Save/load active world state between sessions:
#   save_world_state(db_path, all_programs, season_year, free_agent_pool)
#   all_programs, season_year, free_agent_pool = load_world_state(db_path)
#
# PLAY BY PLAY RETENTION RULES:
#   keep_pbp = TRUE  when: either team is user team, OR game is NCAA tournament
#   keep_pbp = FALSE when: regular season, neither team is user team
#   Possessions with keep_pbp=FALSE are purged at season end after box scores committed.
#   Box scores (player_game_stats) are NEVER purged -- permanent record always.
#
# ARCHITECTURE RULES (never violate these):
#   - All IDs in Python are integers. player_id, coach_id, program_id.
#   - Name strings are display only. Never use as a join key in SQL.
#   - attr_snapshot stored as JSON blob. kept forever (even post-retirement).
#   - world_state table holds ONE row -- the active sim state as JSON.
#     Overwritten every save. History is in the history tables, not here.
#   - Never call sqlite3 directly outside this file.
# -----------------------------------------

import sqlite3
import json
import os
import shutil
from datetime import datetime

# -----------------------------------------
# PATH CONFIGURATION
# Dev path -- replace this in Phase 5 distribution build
# -----------------------------------------

DEV_SAVES_ROOT = r"C:\Users\ootpe\OneDrive\Desktop\College Basketball Universe\saves"


def get_save_path(save_name):
    """Returns the full path to a save's directory."""
    return os.path.join(DEV_SAVES_ROOT, save_name)


def get_db_path(save_name):
    """Returns the full path to a save's world.db file."""
    return os.path.join(get_save_path(save_name), "world.db")


# -----------------------------------------
# INITIALIZATION
# -----------------------------------------

def init_db(save_name, overwrite=False):
    """
    Creates a new save directory and initializes world.db with full schema.
    Returns the db_path string for use in all subsequent calls.

    save_name   -- folder name for this save (e.g. "dynasty_run_1")
    overwrite   -- if True, deletes existing save with same name first

    Raises FileExistsError if save already exists and overwrite=False.
    """
    save_dir = get_save_path(save_name)
    db_path  = get_db_path(save_name)

    if os.path.exists(save_dir):
        if overwrite:
            shutil.rmtree(save_dir)
        else:
            raise FileExistsError(
                "Save '" + save_name + "' already exists. "
                "Use overwrite=True to replace it."
            )

    os.makedirs(save_dir, exist_ok=True)

    conn = _connect(db_path)
    _create_schema(conn)
    conn.close()

    print("Database initialized: " + db_path)
    return db_path


def _connect(db_path):
    """Opens a connection with standard settings."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe concurrent writes
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL") # faster than FULL, safe with WAL
    return conn


def _create_schema(conn):
    """Creates all tables. Safe to call on existing db -- uses IF NOT EXISTS."""
    conn.executescript("""

    -- =============================================
    -- CORE ENTITIES
    -- =============================================

    CREATE TABLE IF NOT EXISTS conferences (
        conference_id   INTEGER PRIMARY KEY,
        name            TEXT NOT NULL UNIQUE,
        tier            TEXT NOT NULL,
        prestige_floor  REAL NOT NULL DEFAULT 1.0,
        prestige_ceiling REAL NOT NULL DEFAULT 100.0
    );

    CREATE TABLE IF NOT EXISTS programs (
        program_id      INTEGER PRIMARY KEY,
        name            TEXT NOT NULL UNIQUE,
        conference_id   INTEGER NOT NULL REFERENCES conferences(conference_id),
        home_state      TEXT,
        prestige_gravity REAL NOT NULL DEFAULT 50.0,
        is_user_team    INTEGER NOT NULL DEFAULT 0  -- 0=false 1=true, only one row ever=1
    );

    CREATE TABLE IF NOT EXISTS players (
        player_id       INTEGER PRIMARY KEY,
        name            TEXT NOT NULL,
        position        TEXT NOT NULL,
        home_state      TEXT,
        arc_type        TEXT,
        recruited_by    INTEGER REFERENCES coaches(coach_id),
        coach_loyalty   INTEGER NOT NULL DEFAULT 10,
        spike_type      TEXT,
        created_season  INTEGER,
        retired_season  INTEGER    -- NULL while active
    );

    CREATE TABLE IF NOT EXISTS coaches (
        coach_id        INTEGER PRIMARY KEY,
        name            TEXT NOT NULL,
        archetype       TEXT,
        age             INTEGER,
        retirement_season INTEGER,  -- NULL while active
        career_wins     INTEGER NOT NULL DEFAULT 0,
        career_losses   INTEGER NOT NULL DEFAULT 0
    );

    -- =============================================
    -- SEASON RECORDS
    -- =============================================

    CREATE TABLE IF NOT EXISTS program_seasons (
        program_season_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id          INTEGER NOT NULL REFERENCES programs(program_id),
        season              INTEGER NOT NULL,
        coach_id            INTEGER REFERENCES coaches(coach_id),
        wins                INTEGER NOT NULL DEFAULT 0,
        losses              INTEGER NOT NULL DEFAULT 0,
        conf_wins           INTEGER NOT NULL DEFAULT 0,
        conf_losses         INTEGER NOT NULL DEFAULT 0,
        prestige_start      REAL,
        prestige_end        REAL,
        prestige_gravity    REAL,
        tournament_result   TEXT,    -- 'r64','r32','sweet_16','elite_8','final_four','champion', NULL
        conf_finish_pct     REAL,
        job_security_end    REAL,
        net_score           REAL,
        UNIQUE(program_id, season)
    );

    CREATE TABLE IF NOT EXISTS player_seasons (
        player_season_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id           INTEGER NOT NULL REFERENCES players(player_id),
        program_id          INTEGER NOT NULL REFERENCES programs(program_id),
        season              INTEGER NOT NULL,
        year_in_school      TEXT,   -- 'Freshman','Sophomore','Junior','Senior'
        games               INTEGER NOT NULL DEFAULT 0,
        minutes             REAL NOT NULL DEFAULT 0.0,
        points              INTEGER NOT NULL DEFAULT 0,
        rebounds            INTEGER NOT NULL DEFAULT 0,
        assists             INTEGER NOT NULL DEFAULT 0,
        steals              INTEGER NOT NULL DEFAULT 0,
        blocks              INTEGER NOT NULL DEFAULT 0,
        turnovers           INTEGER NOT NULL DEFAULT 0,
        fouls               INTEGER NOT NULL DEFAULT 0,
        fg_made             INTEGER NOT NULL DEFAULT 0,
        fg_att              INTEGER NOT NULL DEFAULT 0,
        three_made          INTEGER NOT NULL DEFAULT 0,
        three_att           INTEGER NOT NULL DEFAULT 0,
        ft_made             INTEGER NOT NULL DEFAULT 0,
        ft_att              INTEGER NOT NULL DEFAULT 0,
        ppg                 REAL,
        rpg                 REAL,
        apg                 REAL,
        spg                 REAL,
        bpg                 REAL,
        topg                REAL,
        mpg                 REAL,
        fg_pct              REAL,
        three_pct           REAL,
        ft_pct              REAL,
        attr_snapshot       TEXT,   -- JSON blob of all 21 attributes. kept forever.
        is_active_season    INTEGER NOT NULL DEFAULT 1,
        UNIQUE(player_id, season)
    );

    CREATE TABLE IF NOT EXISTS coach_seasons (
        coach_season_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        coach_id            INTEGER NOT NULL REFERENCES coaches(coach_id),
        program_id          INTEGER NOT NULL REFERENCES programs(program_id),
        season              INTEGER NOT NULL,
        role                TEXT NOT NULL DEFAULT 'head_coach', -- 'head_coach','assistant','grad_assistant'
        wins                INTEGER NOT NULL DEFAULT 0,
        losses              INTEGER NOT NULL DEFAULT 0,
        job_security        REAL,
        salary              REAL,
        contract_years_remaining INTEGER,
        UNIQUE(coach_id, season, role)
    );

    -- =============================================
    -- GAME RECORDS
    -- =============================================

    CREATE TABLE IF NOT EXISTS games (
        game_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        season              INTEGER NOT NULL,
        home_program_id     INTEGER NOT NULL REFERENCES programs(program_id),
        away_program_id     INTEGER NOT NULL REFERENCES programs(program_id),
        home_score          INTEGER,
        away_score          INTEGER,
        game_type           TEXT NOT NULL DEFAULT 'regular', -- 'regular','conference_tourney','ncaa_tourney'
        neutral_site        INTEGER NOT NULL DEFAULT 0,
        tournament_round    TEXT,   -- 'r64','r32','sweet_16','elite_8','final_four','championship', NULL
        keep_pbp            INTEGER NOT NULL DEFAULT 0  -- 0=purge at season end, 1=keep forever
    );

    CREATE TABLE IF NOT EXISTS player_game_stats (
        stat_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id             INTEGER NOT NULL REFERENCES games(game_id),
        player_id           INTEGER NOT NULL REFERENCES players(player_id),
        program_id          INTEGER NOT NULL REFERENCES programs(program_id),
        minutes             REAL NOT NULL DEFAULT 0.0,
        points              INTEGER NOT NULL DEFAULT 0,
        rebounds            INTEGER NOT NULL DEFAULT 0,
        assists             INTEGER NOT NULL DEFAULT 0,
        steals              INTEGER NOT NULL DEFAULT 0,
        blocks              INTEGER NOT NULL DEFAULT 0,
        turnovers           INTEGER NOT NULL DEFAULT 0,
        fouls               INTEGER NOT NULL DEFAULT 0,
        fg_made             INTEGER NOT NULL DEFAULT 0,
        fg_att              INTEGER NOT NULL DEFAULT 0,
        three_made          INTEGER NOT NULL DEFAULT 0,
        three_att           INTEGER NOT NULL DEFAULT 0,
        ft_made             INTEGER NOT NULL DEFAULT 0,
        ft_att              INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS season_awards (
        award_id            INTEGER PRIMARY KEY AUTOINCREMENT,
        season              INTEGER NOT NULL,
        award_type          TEXT NOT NULL,  -- 'player_of_year','coach_of_year','all_conference', etc
        player_id           INTEGER REFERENCES players(player_id),
        coach_id            INTEGER REFERENCES coaches(coach_id),
        program_id          INTEGER REFERENCES programs(program_id),
        conference_id       INTEGER REFERENCES conferences(conference_id),
        notes               TEXT
    );

    -- =============================================
    -- PLAY BY PLAY
    -- Selectively retained -- see keep_pbp on games table.
    -- Purged at season end for games where keep_pbp=0.
    -- Box scores in player_game_stats are NEVER purged.
    -- =============================================

    CREATE TABLE IF NOT EXISTS possessions (
        possession_id       INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id             INTEGER NOT NULL REFERENCES games(game_id),
        possession_num      INTEGER NOT NULL,
        offense_program_id  INTEGER NOT NULL REFERENCES programs(program_id),
        shooter_id          INTEGER REFERENCES players(player_id),
        defender_id         INTEGER REFERENCES players(player_id),
        shot_type           TEXT,
        outcome             TEXT,   -- 'score','miss','foul','turnover'
        points              INTEGER NOT NULL DEFAULT 0,
        is_three            INTEGER NOT NULL DEFAULT 0,
        rebounder_id        INTEGER REFERENCES players(player_id),
        home_score_before   INTEGER NOT NULL DEFAULT 0,
        away_score_before   INTEGER NOT NULL DEFAULT 0
    );

    -- =============================================
    -- EVENTS
    -- =============================================

    CREATE TABLE IF NOT EXISTS recruiting_events (
        event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id           INTEGER NOT NULL REFERENCES players(player_id),
        program_id          INTEGER NOT NULL REFERENCES programs(program_id),
        season              INTEGER NOT NULL,
        event_type          TEXT NOT NULL,  -- 'offer','commit','sign','decommit'
        true_talent         REAL,
        spike_type          TEXT
    );

    CREATE TABLE IF NOT EXISTS transfer_events (
        event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id           INTEGER NOT NULL REFERENCES players(player_id),
        from_program_id     INTEGER REFERENCES programs(program_id),
        to_program_id       INTEGER REFERENCES programs(program_id),
        season              INTEGER NOT NULL,
        reason              TEXT    -- 'portal','coaching_change','decommit'
    );

    CREATE TABLE IF NOT EXISTS coaching_moves (
        move_id             INTEGER PRIMARY KEY AUTOINCREMENT,
        coach_id            INTEGER NOT NULL REFERENCES coaches(coach_id),
        from_program_id     INTEGER REFERENCES programs(program_id),
        to_program_id       INTEGER REFERENCES programs(program_id),
        season              INTEGER NOT NULL,
        reason              TEXT,   -- 'fired','resigned','poached','retired'
        salary_new          REAL,
        was_buyout          INTEGER NOT NULL DEFAULT 0
    );

    -- =============================================
    -- ANALYTICS
    -- One row per program per season. Populated at season end.
    -- Queryable forever -- this is the KenPom-style ratings page.
    -- =============================================

    CREATE TABLE IF NOT EXISTS team_efficiency_ratings (
        rating_id           INTEGER PRIMARY KEY AUTOINCREMENT,
        program_id          INTEGER NOT NULL REFERENCES programs(program_id),
        season              INTEGER NOT NULL,
        offensive_rating    REAL,   -- points per 100 possessions, offense
        defensive_rating    REAL,   -- points per 100 possessions, defense
        net_rating          REAL,   -- offensive_rating - defensive_rating
        tempo               REAL,   -- possessions per game
        luck_rating         REAL,   -- performance vs expected from efficiency
        adj_offensive_rating REAL,  -- adjusted for opponent strength
        adj_defensive_rating REAL,
        adj_net_rating      REAL,
        national_rank       INTEGER,
        UNIQUE(program_id, season)
    );

    -- =============================================
    -- SEASON SNAPSHOTS
    -- One row per season. The almanac index page.
    -- JSON blobs for things that are display-only (final four, leaders).
    -- =============================================

    CREATE TABLE IF NOT EXISTS season_snapshots (
        snapshot_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        season              INTEGER NOT NULL UNIQUE,
        champion_id         INTEGER REFERENCES programs(program_id),
        final_four          TEXT,   -- JSON: [program_id, ...]
        cinderellas         TEXT,   -- JSON: [{name, seed, round}, ...]
        tier_distribution   TEXT,   -- JSON: {blue_blood: 4, elite: 18, ...}
        stat_leaders        TEXT,   -- JSON: {ppg: {player_id, name, value}, ...}
        carousel_summary    TEXT,   -- JSON: {fired: N, resigned: N, retired: N}
        total_programs      INTEGER,
        total_games         INTEGER
    );

    -- =============================================
    -- WORLD STATE
    -- Single row. Active sim state as JSON.
    -- Overwritten every save. NOT the history record.
    -- =============================================

    CREATE TABLE IF NOT EXISTS world_state (
        state_id            INTEGER PRIMARY KEY DEFAULT 1,  -- always row 1
        current_season      INTEGER NOT NULL,
        sim_state           TEXT NOT NULL,  -- JSON blob: full all_programs list
        free_agent_pool     TEXT NOT NULL,  -- JSON blob: coach free agent pool
        last_saved          TEXT NOT NULL   -- ISO datetime string
    );

    -- =============================================
    -- INDEXES
    -- Added for the queries that will be run most often.
    -- =============================================

    CREATE INDEX IF NOT EXISTS idx_program_seasons_program
        ON program_seasons(program_id);
    CREATE INDEX IF NOT EXISTS idx_program_seasons_season
        ON program_seasons(season);
    CREATE INDEX IF NOT EXISTS idx_player_seasons_player
        ON player_seasons(player_id);
    CREATE INDEX IF NOT EXISTS idx_player_seasons_program
        ON player_seasons(program_id);
    CREATE INDEX IF NOT EXISTS idx_player_seasons_season
        ON player_seasons(season);
    CREATE INDEX IF NOT EXISTS idx_coach_seasons_coach
        ON coach_seasons(coach_id);
    CREATE INDEX IF NOT EXISTS idx_games_season
        ON games(season);
    CREATE INDEX IF NOT EXISTS idx_games_home
        ON games(home_program_id);
    CREATE INDEX IF NOT EXISTS idx_games_away
        ON games(away_program_id);
    CREATE INDEX IF NOT EXISTS idx_player_game_stats_game
        ON player_game_stats(game_id);
    CREATE INDEX IF NOT EXISTS idx_player_game_stats_player
        ON player_game_stats(player_id);
    CREATE INDEX IF NOT EXISTS idx_possessions_game
        ON possessions(game_id);
    CREATE INDEX IF NOT EXISTS idx_efficiency_season
        ON team_efficiency_ratings(season);
    CREATE INDEX IF NOT EXISTS idx_efficiency_program
        ON team_efficiency_ratings(program_id);

    """)
    conn.commit()


# -----------------------------------------
# SEED STATIC DATA
# Write conferences and programs once at world build.
# These are permanent -- never re-seeded.
# -----------------------------------------

def seed_conferences_and_programs(db_path, all_programs):
    """
    Seeds conferences and programs tables from the in-memory world.
    Called ONCE at new game creation after init_db().
    Safe to call again -- uses INSERT OR IGNORE so no duplicates.

    Assigns and returns program_id_map: {program_name: program_id}
    and conference_id_map: {conference_name: conference_id}
    so the rest of the session can look up IDs without hitting the db.
    """
    from programs_data import get_conference_tier, get_conference_ceiling, get_conference_floor

    conn = _connect(db_path)

    # Build unique conference list
    conferences_seen = {}
    for p in all_programs:
        conf_name = p["conference"]
        if conf_name not in conferences_seen:
            tier_obj  = get_conference_tier(conf_name)
            floor_val = get_conference_floor(conf_name)
            ceil_val  = get_conference_ceiling(conf_name)
            conferences_seen[conf_name] = {
                "name":    conf_name,
                "tier":    tier_obj["tier"],
                "floor":   floor_val,
                "ceiling": ceil_val,
            }

    # Insert conferences
    for conf in conferences_seen.values():
        conn.execute("""
            INSERT OR IGNORE INTO conferences
                (name, tier, prestige_floor, prestige_ceiling)
            VALUES (?, ?, ?, ?)
        """, (conf["name"], conf["tier"], conf["floor"], conf["ceiling"]))
    conn.commit()

    # Build conference_id_map
    rows = conn.execute("SELECT conference_id, name FROM conferences").fetchall()
    conference_id_map = {row["name"]: row["conference_id"] for row in rows}

    # Insert programs
    for p in all_programs:
        conf_id = conference_id_map[p["conference"]]
        conn.execute("""
            INSERT OR IGNORE INTO programs
                (program_id, name, conference_id, home_state,
                 prestige_gravity, is_user_team)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            p.get("program_id"),
            p["name"],
            conf_id,
            p.get("home_state", ""),
            p.get("prestige_gravity", 50.0),
            1 if p.get("is_user_team") else 0,
        ))
    conn.commit()

    # Build program_id_map
    rows = conn.execute("SELECT program_id, name FROM programs").fetchall()
    program_id_map = {row["name"]: row["program_id"] for row in rows}

    conn.close()
    print("Seeded " + str(len(conference_id_map)) + " conferences, " +
          str(len(program_id_map)) + " programs.")
    return program_id_map, conference_id_map


def seed_coaches(db_path, all_programs):
    """
    Seeds coaches table from all head coaches at world build.
    Called ONCE after seed_conferences_and_programs().
    Returns coach_id_map: {coach_id_in_memory: db_coach_id}

    Note: coach_id in the sim dicts is the primary key we use directly.
    This function ensures the row exists in the db.
    """
    conn = _connect(db_path)

    for p in all_programs:
        coach = p.get("coach", {})
        if not coach:
            continue
        cid = coach.get("coach_id")
        if cid is None:
            continue
        conn.execute("""
            INSERT OR IGNORE INTO coaches
                (coach_id, name, archetype, age,
                 career_wins, career_losses)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            cid,
            coach.get("name", "Unknown"),
            coach.get("archetype", ""),
            coach.get("age", 40),
            coach.get("career_wins", 0),
            coach.get("career_losses", 0),
        ))

        # Also seed assistants and GAs
        for staff_list_key in ("assistant_coaches", "grad_assistants"):
            for staff in p.get(staff_list_key, []):
                scid = staff.get("coach_id")
                if scid is None:
                    continue
                conn.execute("""
                    INSERT OR IGNORE INTO coaches
                        (coach_id, name, archetype, age,
                         career_wins, career_losses)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    scid,
                    staff.get("name", "Unknown"),
                    staff.get("archetype", ""),
                    staff.get("age", 30),
                    0, 0,
                ))

    conn.commit()
    conn.close()
    print("Coaches seeded.")


def seed_players(db_path, all_programs):
    """
    Seeds players table from all active roster players at world build.
    Called ONCE after seed_coaches().
    player_id in the sim dict is the primary key -- used directly.
    """
    conn = _connect(db_path)

    for p in all_programs:
        for player in p.get("roster", []):
            pid = player.get("player_id")
            if pid is None:
                continue
            conn.execute("""
                INSERT OR IGNORE INTO players
                    (player_id, name, position, home_state,
                     arc_type, recruited_by, coach_loyalty, spike_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid,
                player.get("name", "Unknown"),
                player.get("position", "SF"),
                player.get("home_state", ""),
                player.get("arc_type", "steady"),
                player.get("recruited_by"),
                player.get("coach_loyalty", 10),
                player.get("spike", {}).get("label") if player.get("spike") else None,
            ))

    conn.commit()
    conn.close()
    print("Players seeded.")


# -----------------------------------------
# SEASON COMMIT
# The main entry point called from season.py at season end.
# -----------------------------------------

def commit_season_to_db(db_path, all_programs, tournament_results,
                        season_year, free_agent_pool,
                        carousel_report=None, verbose=True):
    """
    Writes the completed season to the database.
    Called once per season from simulate_world_season() after all
    simulation steps are complete.

    Pipeline:
      1. Ensure any new players/coaches exist in the db
      2. Write program_seasons (one row per program)
      3. Write player_seasons (one row per player who played)
      4. Write coach_seasons (one row per coach)
      5. Write games + player_game_stats (box scores)
      6. Write season_snapshot (almanac index row)
      7. Write coaching_moves from carousel_report
      8. Purge play by play for games where keep_pbp=0
      9. Update team_efficiency_ratings

    Does NOT write possessions -- those are written during game simulation
    by write_possession() when pbp tracking is active. (Future hook.)
    """
    conn = _connect(db_path)

    if verbose:
        print("  [DB] Committing season " + str(season_year) + " to database...")

    # Step 1: ensure new players and coaches exist
    _ensure_players_exist(conn, all_programs)
    _ensure_coaches_exist(conn, all_programs, free_agent_pool)

    # Step 2: program_seasons
    _write_program_seasons(conn, all_programs, season_year, tournament_results)

    # Step 3: player_seasons
    _write_player_seasons(conn, all_programs, season_year)

    # Step 4: coach_seasons
    _write_coach_seasons(conn, all_programs, season_year)

    # Step 5: games + box scores
    _write_games_and_box_scores(conn, all_programs, season_year)

    # Step 6: season snapshot
    _write_season_snapshot(conn, all_programs, tournament_results,
                           season_year, carousel_report)

    # Step 7: coaching moves
    if carousel_report:
        _write_coaching_moves(conn, carousel_report, season_year)

    # Step 8: purge non-retained play by play
    _purge_pbp(conn, season_year)

    # Step 9: efficiency ratings
    _write_efficiency_ratings(conn, all_programs, season_year)

    conn.commit()
    conn.close()

    if verbose:
        print("  [DB] Season " + str(season_year) + " committed.")


# -----------------------------------------
# INTERNAL WRITE FUNCTIONS
# -----------------------------------------

def _ensure_players_exist(conn, all_programs):
    """Inserts any players not yet in the players table."""
    for p in all_programs:
        for player in p.get("roster", []):
            pid = player.get("player_id")
            if pid is None:
                continue
            existing = conn.execute(
                "SELECT 1 FROM players WHERE player_id=?", (pid,)
            ).fetchone()
            if not existing:
                conn.execute("""
                    INSERT OR IGNORE INTO players
                        (player_id, name, position, home_state,
                         arc_type, recruited_by, coach_loyalty, spike_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pid,
                    player.get("name", "Unknown"),
                    player.get("position", "SF"),
                    player.get("home_state", ""),
                    player.get("arc_type", "steady"),
                    player.get("recruited_by"),
                    player.get("coach_loyalty", 10),
                    player.get("spike", {}).get("label") if player.get("spike") else None,
                ))


def _ensure_coaches_exist(conn, all_programs, free_agent_pool):
    """Inserts any coaches not yet in the coaches table."""
    all_coaches = []
    for p in all_programs:
        coach = p.get("coach")
        if coach:
            all_coaches.append(coach)
        for staff_list_key in ("assistant_coaches", "grad_assistants"):
            all_coaches.extend(p.get(staff_list_key, []))
    all_coaches.extend(free_agent_pool or [])

    for coach in all_coaches:
        cid = coach.get("coach_id")
        if cid is None:
            continue
        existing = conn.execute(
            "SELECT 1 FROM coaches WHERE coach_id=?", (cid,)
        ).fetchone()
        if not existing:
            conn.execute("""
                INSERT OR IGNORE INTO coaches
                    (coach_id, name, archetype, age,
                     career_wins, career_losses)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                cid,
                coach.get("name", "Unknown"),
                coach.get("archetype", ""),
                coach.get("age", 40),
                coach.get("career_wins", 0),
                coach.get("career_losses", 0),
            ))


def _write_program_seasons(conn, all_programs, season_year, tournament_results):
    """Writes one row per program to program_seasons."""
    champ_name = tournament_results.get("champion") if tournament_results else None

    for p in all_programs:
        prog_id  = p.get("program_id")
        coach    = p.get("coach", {})
        coach_id = coach.get("coach_id") if coach else None

        # Get tournament result for this program
        tourney_result = None
        ncaa = p.get("ncaa_tournament_result", {})
        if ncaa.get("seed") is not None:
            tourney_result = ncaa.get("result", "r64")

        # Get prestige history for this season
        history = p.get("season_history", [])
        this_season = next(
            (h for h in history if h.get("year") == season_year), {}
        )

        conn.execute("""
            INSERT OR REPLACE INTO program_seasons
                (program_id, season, coach_id,
                 wins, losses, conf_wins, conf_losses,
                 prestige_start, prestige_end, prestige_gravity,
                 tournament_result, conf_finish_pct,
                 job_security_end, net_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prog_id,
            season_year,
            coach_id,
            p.get("wins", 0),
            p.get("losses", 0),
            p.get("conf_wins", 0),
            p.get("conf_losses", 0),
            this_season.get("prestige_end", p.get("prestige_current")),
            p.get("prestige_current"),
            p.get("prestige_gravity"),
            tourney_result,
            p.get("conf_finish_percentile"),
            p.get("job_security"),
            None,  # net_score populated in step 9
        ))


def _write_player_seasons(conn, all_programs, season_year):
    """Writes one row per player per program to player_seasons."""
    ATTR_KEYS = [
        "catch_and_shoot", "off_dribble", "mid_range", "three_point",
        "free_throw", "finishing", "post_scoring", "passing",
        "ball_handling", "court_vision", "decision_making",
        "on_ball_defense", "help_defense", "rebounding", "shot_blocking",
        "steal_tendency", "foul_tendency", "speed", "lateral_quickness",
        "strength", "vertical", "endurance",
    ]

    for p in all_programs:
        prog_id     = p.get("program_id")
        season_data = p.get("season_stats", {})

        for player in p.get("roster", []):
            pid  = player.get("player_id")
            name = player.get("name", "")
            if pid is None:
                continue

            stats = season_data.get(name, {})
            games = stats.get("games", 0)
            if games == 0:
                continue

            # Attribute snapshot -- all 21 attributes as JSON
            attr_snap = {k: player.get(k, 0) for k in ATTR_KEYS}
            attr_json = json.dumps(attr_snap)

            conn.execute("""
                INSERT OR REPLACE INTO player_seasons
                    (player_id, program_id, season, year_in_school,
                     games, minutes, points, rebounds, assists,
                     steals, blocks, turnovers, fouls,
                     fg_made, fg_att, three_made, three_att,
                     ft_made, ft_att,
                     ppg, rpg, apg, spg, bpg, topg, mpg,
                     fg_pct, three_pct, ft_pct,
                     attr_snapshot, is_active_season)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid, prog_id, season_year,
                player.get("year", "Freshman"),
                games,
                stats.get("minutes", 0.0),
                stats.get("points", 0),
                stats.get("rebounds", 0),
                stats.get("assists", 0),
                stats.get("steals", 0),
                stats.get("blocks", 0),
                stats.get("turnovers", 0),
                stats.get("fouls", 0),
                stats.get("fg_made", 0),
                stats.get("fg_att", 0),
                stats.get("three_made", 0),
                stats.get("three_att", 0),
                stats.get("ft_made", 0),
                stats.get("ft_att", 0),
                stats.get("ppg", 0.0),
                stats.get("rpg", 0.0),
                stats.get("apg", 0.0),
                stats.get("spg", 0.0),
                stats.get("bpg", 0.0),
                stats.get("topg", 0.0),
                stats.get("mpg", 0.0),
                stats.get("fg_pct", 0.0),
                stats.get("three_pct", 0.0),
                stats.get("ft_pct", 0.0),
                attr_json,
                1,
            ))


def _write_coach_seasons(conn, all_programs, season_year):
    """Writes coach_seasons for all head coaches and staff."""
    for p in all_programs:
        prog_id = p.get("program_id")
        coach   = p.get("coach", {})
        if coach and coach.get("coach_id"):
            conn.execute("""
                INSERT OR REPLACE INTO coach_seasons
                    (coach_id, program_id, season, role,
                     wins, losses, job_security, salary,
                     contract_years_remaining)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                coach["coach_id"], prog_id, season_year,
                "head_coach",
                p.get("wins", 0),
                p.get("losses", 0),
                p.get("job_security"),
                coach.get("salary_current"),
                coach.get("contract_years_remaining", 0),
            ))

        for staff in p.get("assistant_coaches", []):
            if staff.get("coach_id"):
                conn.execute("""
                    INSERT OR REPLACE INTO coach_seasons
                        (coach_id, program_id, season, role,
                         wins, losses, salary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    staff["coach_id"], prog_id, season_year,
                    "assistant",
                    p.get("wins", 0),
                    p.get("losses", 0),
                    staff.get("salary_current"),
                ))


def _write_games_and_box_scores(conn, all_programs, season_year):
    """
    Writes games and player_game_stats from season_results on each program.

    DEDUPLICATION: each game appears in two programs' season_results
    (home and away). We use a seen_pairs set to write each game once.

    keep_pbp logic:
      TRUE  if either team is user team OR game has tournament_round
      FALSE otherwise (possessions purged at season end)
    """
    # Build lookup maps
    prog_by_name = {p["name"]: p for p in all_programs}
    user_team_names = {
        p["name"] for p in all_programs if p.get("is_user_team")
    }

    seen_pairs = set()  # (home_name, away_name) already written

    for p in all_programs:
        prog_id = p.get("program_id")

        for result in p.get("season_results", []):
            opp_name = result.get("opponent", "")
            is_home  = result.get("is_home", True)

            if is_home:
                home_name = p["name"]
                away_name = opp_name
                home_score = result.get("score", 0)
                away_score = result.get("opp_score", 0)
            else:
                home_name = opp_name
                away_name = p["name"]
                home_score = result.get("opp_score", 0)
                away_score = result.get("score", 0)

            pair = (home_name, away_name)
            rev  = (away_name, home_name)
            if pair in seen_pairs or rev in seen_pairs:
                continue
            seen_pairs.add(pair)

            home_prog = prog_by_name.get(home_name)
            away_prog = prog_by_name.get(away_name)
            if not home_prog or not away_prog:
                continue

            home_prog_id = home_prog.get("program_id")
            away_prog_id = away_prog.get("program_id")

            is_conf    = result.get("is_conference", False)
            game_type  = "conference" if is_conf else "regular"
            tourney_round = result.get("tournament_round")
            if tourney_round:
                game_type = "ncaa_tourney"

            keep_pbp = 1 if (
                home_name in user_team_names or
                away_name in user_team_names or
                tourney_round is not None
            ) else 0

            cursor = conn.execute("""
                INSERT INTO games
                    (season, home_program_id, away_program_id,
                     home_score, away_score,
                     game_type, neutral_site,
                     tournament_round, keep_pbp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                season_year,
                home_prog_id, away_prog_id,
                home_score, away_score,
                game_type,
                1 if result.get("neutral_site") else 0,
                tourney_round,
                keep_pbp,
            ))
            game_id = cursor.lastrowid

            # Box scores -- write for both teams from season_stats
            for team_prog in [home_prog, away_prog]:
                team_prog_id  = team_prog.get("program_id")
                team_stats    = team_prog.get("season_stats", {})
                team_roster   = team_prog.get("roster", [])

                for player in team_roster:
                    pid  = player.get("player_id")
                    pname = player.get("name", "")
                    if pid is None:
                        continue
                    gs = player.get("game_stats", {})
                    if gs.get("minutes", 0) < 0.5:
                        continue

                    conn.execute("""
                        INSERT INTO player_game_stats
                            (game_id, player_id, program_id,
                             minutes, points, rebounds, assists,
                             steals, blocks, turnovers, fouls,
                             fg_made, fg_att,
                             three_made, three_att,
                             ft_made, ft_att)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                ?, ?, ?, ?)
                    """, (
                        game_id, pid, team_prog_id,
                        gs.get("minutes", 0.0),
                        gs.get("points", 0),
                        gs.get("rebounds", 0),
                        gs.get("assists", 0),
                        gs.get("steals", 0),
                        gs.get("blocks", 0),
                        gs.get("turnovers", 0),
                        gs.get("fouls", 0),
                        gs.get("fg_made", 0),
                        gs.get("fg_att", 0),
                        gs.get("three_made", 0),
                        gs.get("three_att", 0),
                        gs.get("ft_made", 0),
                        gs.get("ft_att", 0),
                    ))


def _write_season_snapshot(conn, all_programs, tournament_results,
                           season_year, carousel_report):
    """Writes one almanac row for the completed season."""
    champ_name = tournament_results.get("champion") if tournament_results else None
    champ_prog = next(
        (p for p in all_programs if p["name"] == champ_name), None
    ) if champ_name else None
    champ_id = champ_prog.get("program_id") if champ_prog else None

    ff_names = tournament_results.get("final_four", []) if tournament_results else []
    ff_ids   = []
    for name in ff_names:
        prog = next((p for p in all_programs if p["name"] == name), None)
        if prog:
            ff_ids.append(prog.get("program_id"))

    cinderellas = tournament_results.get("cinderellas", []) if tournament_results else []
    cin_data    = [{"name": c[0], "seed": c[1], "round": c[2]}
                   for c in cinderellas if len(c) >= 3]

    # Tier distribution count
    from season import UNIVERSE_TIERS
    tier_dist = {}
    for tier_name, p_min, p_max, target in UNIVERSE_TIERS:
        actual = sum(
            1 for p in all_programs
            if p_min <= p["prestige_current"] <= p_max
        )
        tier_dist[tier_name] = actual

    # Carousel summary
    car_summary = {}
    if carousel_report:
        changes = carousel_report.get("changes", [])
        car_summary = {
            "fired":   sum(1 for c in changes if c.get("reason") == "fired"),
            "resigned": sum(1 for c in changes
                           if c.get("reason") in ("resigned", "poached")),
            "retired": sum(1 for c in changes
                          if c.get("trigger") == "retirement"),
        }

    conn.execute("""
        INSERT OR REPLACE INTO season_snapshots
            (season, champion_id, final_four, cinderellas,
             tier_distribution, carousel_summary,
             total_programs, total_games)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        season_year,
        champ_id,
        json.dumps(ff_ids),
        json.dumps(cin_data),
        json.dumps(tier_dist),
        json.dumps(car_summary),
        len(all_programs),
        None,  # total_games populated after game writes
    ))


def _write_coaching_moves(conn, carousel_report, season_year):
    """Writes coaching_moves rows from the carousel report."""
    changes = carousel_report.get("changes", [])
    for change in changes:
        coach_id = change.get("coach_id")
        if coach_id is None:
            continue

        from_prog_name = change.get("from_program")
        to_prog_name   = change.get("to_program")

        from_id = conn.execute(
            "SELECT program_id FROM programs WHERE name=?",
            (from_prog_name,)
        ).fetchone()
        to_id = conn.execute(
            "SELECT program_id FROM programs WHERE name=?",
            (to_prog_name,)
        ).fetchone()

        conn.execute("""
            INSERT INTO coaching_moves
                (coach_id, from_program_id, to_program_id,
                 season, reason, salary_new, was_buyout)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            coach_id,
            from_id["program_id"] if from_id else None,
            to_id["program_id"]   if to_id   else None,
            season_year,
            change.get("reason"),
            change.get("salary_new"),
            1 if change.get("was_buyout") else 0,
        ))


def _purge_pbp(conn, season_year):
    """
    Deletes possessions rows for games where keep_pbp=0.
    Called at season end after all box scores are committed.
    Box scores in player_game_stats are NEVER touched.
    """
    conn.execute("""
        DELETE FROM possessions
        WHERE game_id IN (
            SELECT game_id FROM games
            WHERE season=? AND keep_pbp=0
        )
    """, (season_year,))


def _write_efficiency_ratings(conn, all_programs, season_year):
    """
    Calculates and writes KenPom-style efficiency ratings for every program.
    Uses season_results to calculate possessions and points.

    offensive_rating  = points scored per 100 possessions
    defensive_rating  = points allowed per 100 possessions
    net_rating        = offensive - defensive
    tempo             = possessions per game
    """
    prog_by_name = {p["name"]: p for p in all_programs}

    for p in all_programs:
        prog_id  = p.get("program_id")
        results  = p.get("season_results", [])
        if not results:
            continue

        total_poss_off = 0
        total_poss_def = 0
        total_pts_off  = 0
        total_pts_def  = 0
        games_counted  = 0

        for result in results:
            poss         = result.get("possessions", 68)
            pts_scored   = result.get("score", 0)
            pts_allowed  = result.get("opp_score", 0)
            total_poss_off += poss
            total_poss_def += poss
            total_pts_off  += pts_scored
            total_pts_def  += pts_allowed
            games_counted  += 1

        if games_counted == 0:
            continue

        off_rtg  = round(total_pts_off  / max(1, total_poss_off) * 100, 1)
        def_rtg  = round(total_pts_def  / max(1, total_poss_def) * 100, 1)
        net_rtg  = round(off_rtg - def_rtg, 1)
        tempo    = round(total_poss_off / max(1, games_counted), 1)

        conn.execute("""
            INSERT OR REPLACE INTO team_efficiency_ratings
                (program_id, season,
                 offensive_rating, defensive_rating, net_rating, tempo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (prog_id, season_year, off_rtg, def_rtg, net_rtg, tempo))

    # Assign national ranks by net_rating
    conn.execute("""
        UPDATE team_efficiency_ratings
        SET national_rank = (
            SELECT COUNT(*) + 1
            FROM team_efficiency_ratings t2
            WHERE t2.season = team_efficiency_ratings.season
            AND t2.net_rating > team_efficiency_ratings.net_rating
        )
        WHERE season = ?
    """, (season_year,))


# -----------------------------------------
# WORLD STATE -- SAVE / LOAD
# -----------------------------------------

def save_world_state(db_path, all_programs, season_year, free_agent_pool):
    """
    Saves the complete active world state to the world_state table.
    Overwrites the single existing row (or inserts if first save).
    Called at the end of every session so the user can resume.

    The JSON blob is the full in-memory all_programs list.
    This is NOT the history record -- it's the live scratchpad.
    """
    conn = _connect(db_path)

    sim_json  = json.dumps(all_programs)
    pool_json = json.dumps(free_agent_pool)
    now       = datetime.now().isoformat()

    conn.execute("""
        INSERT INTO world_state
            (state_id, current_season, sim_state, free_agent_pool, last_saved)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(state_id) DO UPDATE SET
            current_season  = excluded.current_season,
            sim_state       = excluded.sim_state,
            free_agent_pool = excluded.free_agent_pool,
            last_saved      = excluded.last_saved
    """, (season_year, sim_json, pool_json, now))

    conn.commit()
    conn.close()
    print("  [DB] World state saved. Season: " + str(season_year) +
          "  (" + now[:19] + ")")


def load_world_state(db_path):
    """
    Loads the active world state from the database.
    Returns (all_programs, season_year, free_agent_pool).
    Returns (None, None, None) if no saved state exists.
    """
    conn = _connect(db_path)
    row  = conn.execute(
        "SELECT * FROM world_state WHERE state_id=1"
    ).fetchone()
    conn.close()

    if not row:
        return None, None, None

    all_programs    = json.loads(row["sim_state"])
    free_agent_pool = json.loads(row["free_agent_pool"])
    season_year     = row["current_season"]

    print("  [DB] World state loaded. Season: " + str(season_year) +
          "  Last saved: " + row["last_saved"][:19])
    return all_programs, season_year, free_agent_pool


# -----------------------------------------
# READ FUNCTIONS
# These will grow as the UI is built.
# Every Sports Reference style page is a function here.
# -----------------------------------------

def get_program_history(db_path, program_name):
    """
    Returns year-by-year history for a program.
    The program history page.
    """
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT
            ps.season, ps.wins, ps.losses, ps.conf_wins, ps.conf_losses,
            ps.prestige_end, ps.prestige_gravity, ps.tournament_result,
            ps.conf_finish_pct, ps.job_security_end,
            c.name AS coach_name
        FROM program_seasons ps
        JOIN programs p ON ps.program_id = p.program_id
        LEFT JOIN coaches c ON ps.coach_id = c.coach_id
        WHERE p.name = ?
        ORDER BY ps.season
    """, (program_name,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_player_career(db_path, player_id):
    """
    Returns season-by-season career stats for a player.
    The player career page.
    Includes school name for each season (handles transfers).
    """
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT
            ps.season, ps.year_in_school, pr.name AS school,
            ps.games, ps.ppg, ps.rpg, ps.apg, ps.spg, ps.bpg, ps.topg,
            ps.mpg, ps.fg_pct, ps.three_pct, ps.ft_pct,
            ps.fg_made, ps.fg_att, ps.three_made, ps.three_att,
            ps.ft_made, ps.ft_att,
            ps.attr_snapshot
        FROM player_seasons ps
        JOIN programs pr ON ps.program_id = pr.program_id
        WHERE ps.player_id = ?
        ORDER BY ps.season
    """, (player_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_coach_history(db_path, coach_id):
    """
    Returns year-by-year coaching history.
    Mirrors Sports Reference coach pages:
    each season listed with school, record.
    Career totals and per-school totals calculated from rows.
    """
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT
            cs.season, cs.role, pr.name AS school,
            cs.wins, cs.losses, cs.salary, cs.job_security
        FROM coach_seasons cs
        JOIN programs pr ON cs.program_id = pr.program_id
        WHERE cs.coach_id = ?
        ORDER BY cs.season
    """, (coach_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_season_efficiency_rankings(db_path, season):
    """
    Returns all teams ranked by adjusted net rating for a season.
    The KenPom-style analytics page.
    """
    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT
            ter.national_rank,
            p.name AS program,
            c.name AS conference,
            ter.offensive_rating, ter.defensive_rating,
            ter.net_rating, ter.tempo,
            ps.wins, ps.losses, ps.tournament_result
        FROM team_efficiency_ratings ter
        JOIN programs p ON ter.program_id = p.program_id
        JOIN conferences c ON p.conference_id = c.conference_id
        LEFT JOIN program_seasons ps
            ON ter.program_id = ps.program_id
            AND ter.season = ps.season
        WHERE ter.season = ?
        ORDER BY ter.national_rank
    """, (season,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_season_snapshot(db_path, season):
    """Returns the almanac index row for a given season."""
    conn = _connect(db_path)
    row  = conn.execute(
        "SELECT * FROM season_snapshots WHERE season=?", (season,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    for key in ("final_four", "cinderellas", "tier_distribution",
                "carousel_summary", "stat_leaders"):
        if result.get(key):
            result[key] = json.loads(result[key])
    return result


def get_stat_leaders(db_path, season, stat="ppg", limit=25):
    """
    Returns top players by a given stat for a season.
    stat must be a column in player_seasons (ppg, rpg, apg, etc.)
    """
    allowed = {"ppg", "rpg", "apg", "spg", "bpg", "topg",
               "fg_pct", "three_pct", "ft_pct", "mpg"}
    if stat not in allowed:
        raise ValueError("stat must be one of: " + str(allowed))

    conn = _connect(db_path)
    rows = conn.execute("""
        SELECT
            pl.name AS player_name, pl.position,
            pr.name AS school,
            ps.year_in_school, ps.games,
            ps.{stat}
        FROM player_seasons ps
        JOIN players pl ON ps.player_id = pl.player_id
        JOIN programs pr ON ps.program_id = pr.program_id
        WHERE ps.season = ? AND ps.games >= 10
        ORDER BY ps.{stat} DESC
        LIMIT ?
    """.format(stat=stat), (season, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -----------------------------------------
# UTILITIES
# -----------------------------------------

def get_db_size_mb(db_path):
    """Returns database file size in MB."""
    if not os.path.exists(db_path):
        return 0.0
    return round(os.path.getsize(db_path) / (1024 * 1024), 2)


def get_save_info(save_name):
    """Returns basic info about a save without loading it."""
    db_path = get_db_path(save_name)
    if not os.path.exists(db_path):
        return None
    conn  = _connect(db_path)
    state = conn.execute(
        "SELECT current_season, last_saved FROM world_state WHERE state_id=1"
    ).fetchone()
    seasons = conn.execute(
        "SELECT COUNT(*) as n FROM season_snapshots"
    ).fetchone()
    conn.close()
    return {
        "save_name":      save_name,
        "db_path":        db_path,
        "size_mb":        get_db_size_mb(db_path),
        "current_season": state["current_season"] if state else None,
        "last_saved":     state["last_saved"][:19] if state else None,
        "seasons_stored": seasons["n"] if seasons else 0,
    }


def list_saves():
    """Returns a list of all available saves."""
    if not os.path.exists(DEV_SAVES_ROOT):
        return []
    saves = []
    for name in os.listdir(DEV_SAVES_ROOT):
        info = get_save_info(name)
        if info:
            saves.append(info)
    return saves


# -----------------------------------------
# TEST
# -----------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  DATABASE LAYER v1.0 -- INIT TEST")
    print("=" * 60)

    TEST_SAVE = "test_save_001"

    print("")
    print("Testing init_db()...")
    try:
        db_path = init_db(TEST_SAVE, overwrite=True)
        print("  PASS: database created at " + db_path)
    except Exception as e:
        print("  FAIL: " + str(e))
        exit(1)

    print("")
    print("Testing schema...")
    conn = _connect(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()
    expected = [
        "coach_seasons", "coaching_moves", "coaches",
        "conferences", "games", "player_game_stats",
        "player_seasons", "players", "possessions",
        "program_seasons", "programs", "recruiting_events",
        "season_awards", "season_snapshots",
        "team_efficiency_ratings", "transfer_events", "world_state",
    ]
    found = [t["name"] for t in tables]
    for t in expected:
        status = "PASS" if t in found else "FAIL"
        print("  " + status + ": " + t)

    print("")
    print("Testing world build seed...")
    from programs_data import build_all_d1_programs
    all_programs = build_all_d1_programs()

    # Assign program_ids if not already set
    for i, p in enumerate(all_programs, start=1):
        if "program_id" not in p:
            p["program_id"] = i

    prog_map, conf_map = seed_conferences_and_programs(db_path, all_programs)
    seed_coaches(db_path, all_programs)
    seed_players(db_path, all_programs)

    print("")
    print("DB size after seed: " + str(get_db_size_mb(db_path)) + " MB")

    print("")
    print("Testing save_world_state / load_world_state...")
    save_world_state(db_path, all_programs, 2024, [])
    loaded_programs, loaded_season, loaded_pool = load_world_state(db_path)
    print("  Loaded " + str(len(loaded_programs)) + " programs, season " +
          str(loaded_season))

    print("")
    print("Testing list_saves()...")
    saves = list_saves()
    for s in saves:
        print("  " + s["save_name"] + "  |  season: " +
              str(s["current_season"]) + "  |  " +
              str(s["size_mb"]) + " MB")

    print("")
    print("=" * 60)
    print("  ALL TESTS COMPLETE")
    print("=" * 60)
