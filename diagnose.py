from programs_data import build_all_d1_programs
from calendar import SeasonCalendar, get_conference_format
from scheduler import (build_conference_schedule, schedule_noncon,
                       get_noncon_slots, _estimate_conf_games,
                       _get_scheduled_opponents, get_scheduling_profile)

print("Building programs...")
all_programs = build_all_d1_programs()
print(f"Loaded {len(all_programs)} programs")

cal = SeasonCalendar(2024)
conferences = {}
for p in all_programs:
    conferences.setdefault(p['conference'], []).append(p)

print("Building conference schedules...")
for cn, cp in conferences.items():
    if len(cp) >= 2:
        build_conference_schedule(cal, cn, cp)

conf_total = cal.total_games()
print(f"Conference games placed: {conf_total}")

print("Building non-conference schedules...")

# Patch road_count to be inspectable after scheduling
import scheduler as sched_mod
original_place = sched_mod._place_noncon_game
road_count_tracker = {}

def tracked_place(calendar, home, away, noncon_dates, noncon_count, road_count,
                  is_neutral=False, neutral_site=None, event_name=None, series_id=None):
    result = original_place(calendar, home, away, noncon_dates, noncon_count, road_count,
                            is_neutral=is_neutral, neutral_site=neutral_site,
                            event_name=event_name, series_id=series_id)
    if result and not is_neutral:
        road_count_tracker[away['name']] = road_count_tracker.get(away['name'], 0) + 1
    return result

sched_mod._place_noncon_game = tracked_place
schedule_noncon(cal, all_programs, 2024)
sched_mod._place_noncon_game = original_place

total = cal.total_games()
print(f"Total after noncon: {total}")

# Check Vermont specifically
vt = next(p for p in all_programs if p['name'] == 'Vermont')
profile = get_scheduling_profile(vt)
print(f"\nVermont profile:")
print(f"  aggression={vt.get('scheduling_aggression')}  conf_tier={vt.get('conference')}")
print(f"  max_road_games={profile['max_road_games']}  paycheck_road={profile['paycheck_road']}")

sched = cal.get_team_schedule('Vermont')
conf_g = len([s for s in sched if s.game_type == 'conference'])
noncon_slots = [s for s in sched if s.game_type == 'noncon']
road_g = len([s for s in noncon_slots if not s.is_neutral and not s.is_home_game('Vermont')])
print(f"  conf={conf_g}  noncon={len(noncon_slots)}  road={road_g}")
print(f"  road_count_tracker={road_count_tracker.get('Vermont', 0)}")
print(f"  Road opponents:")
for s in noncon_slots:
    if not s.is_neutral and not s.is_home_game('Vermont'):
        opp = s.get_opponent('Vermont')
        opp_name = opp['name'] if opp else '?'
        opp_tier = get_scheduling_profile(opp)['max_road_games'] if opp else '?'
        print(f"    vs {opp_name} (their max_road={opp_tier})")

# Sample breakdown
print("\nSample team breakdown:")
conf_counts = _estimate_conf_games(all_programs, cal)
for name in ['Oklahoma State', 'Vermont', 'Kansas', 'Albany', 'Prairie View A&M']:
    p = next((x for x in all_programs if x['name'] == name), None)
    if not p: continue
    sched    = cal.get_team_schedule(name)
    conf_g   = len([s for s in sched if s.game_type == 'conference'])
    noncon_g = len([s for s in sched if s.game_type == 'noncon'])
    road_g   = len([s for s in sched if s.game_type == 'noncon'
                    and not s.is_neutral and not s.is_home_game(name)])
    agg      = p.get('scheduling_aggression', '?')
    print(f"  {name:<22} conf={conf_g}  noncon={noncon_g}  road={road_g}  total={conf_g+noncon_g}  agg={agg}")
