import os
import re
import json
import shutil
import time
from datetime import datetime, timedelta

# Full year of history by default, but ratchet retention down one rung per
# day while disk stays under pressure (365 -> 180 -> 90 -> 60 -> 30), giving
# each cut time to actually free space before cutting further, and ratchet
# back up one rung per day once usage recovers. This is what keeps a burst
# of traffic from being the thing that fills the disk and takes MongoDB down
# with it (see bash-tools/repair-mongodb.sh).
RETENTION_LADDER = [365, 180, 90, 60, 30]
PRESSURE_PERCENT = int(os.environ.get('LIBERTEA_DISK_PRESSURE_PERCENT', 80))

# run.sh's loop calls this script every 5 minutes; only do real work once an
# hour so a single deletion pass has time to matter before the next one.
RUN_INTERVAL_SECONDS = int(os.environ.get('LIBERTEA_EVICT_INTERVAL_SECONDS', 3600))

PARSED_LOGS_PATH = '/data/parsed-logs'
USAGES_PATH = '/data/usages'
# Must live on a mounted volume; /data itself is not one, so state kept there
# would be lost every time the container is recreated.
STATE_PATH = os.path.join(PARSED_LOGS_PATH, '.eviction-state.json')


def disk_used_percent(path):
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return 0
    if usage.total == 0:
        return 0
    return usage.used / usage.total * 100


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    # A full disk is exactly when this runs and exactly when writing can fail;
    # losing the state only costs an extra pass, so never let it stop eviction.
    try:
        with open(STATE_PATH, 'w') as f:
            json.dump(state, f)
    except OSError as e:
        print(f'Could not save eviction state: {e}')


def effective_retention_days(state):
    days = state['days'] if state.get('days') in RETENTION_LADDER else RETENTION_LADDER[0]
    today = datetime.now().strftime('%Y-%m-%d')
    if state.get('last_step') == today:
        return days

    idx = RETENTION_LADDER.index(days)
    used_percent = disk_used_percent(PARSED_LOGS_PATH)
    if used_percent >= PRESSURE_PERCENT and idx < len(RETENTION_LADDER) - 1:
        idx += 1
        days = RETENTION_LADDER[idx]
        state['days'], state['last_step'] = days, today
        print(f'Disk usage at {used_percent:.0f}%, stepping retention down to {days} days')
    elif used_percent < PRESSURE_PERCENT and idx > 0:
        idx -= 1
        days = RETENTION_LADDER[idx]
        state['days'], state['last_step'] = days, today
        print(f'Disk usage at {used_percent:.0f}%, stepping retention back up to {days} days')

    return days


def delete_file(path):
    try:
        os.remove(path)
        return True
    except OSError as e:
        print(f'Could not delete {path}: {e}')
        return False


def evict_parsed_logs(cutoff_date):
    if not os.path.isdir(PARSED_LOGS_PATH):
        return

    deleted = 0
    for file in os.listdir(PARSED_LOGS_PATH):
        if not file.startswith('endpoints-event.json-'):
            continue

        # file name is either ...-yyyymmdd.json or ...-yyyymmdd-hh.json
        date_part = file.split('-')[2].split('.')[0]
        try:
            file_date = datetime.strptime(date_part, '%Y%m%d')
        except ValueError:
            continue

        if file_date < cutoff_date:
            if delete_file(os.path.join(PARSED_LOGS_PATH, file)):
                deleted += 1

    if deleted:
        print(f'Evicted {deleted} old file(s) from parsed-logs')


def evict_usages_day_and_month(cutoff_date):
    for resolution, date_format in (('day', '%Y-%m-%d'), ('month', '%Y-%m')):
        dir_path = os.path.join(USAGES_PATH, resolution)
        if not os.path.isdir(dir_path):
            continue

        deleted = 0
        for file in os.listdir(dir_path):
            name = file[:-len('.json')] if file.endswith('.json') else None
            if name is None:
                continue
            try:
                file_date = datetime.strptime(name, date_format)
            except ValueError:
                continue

            if file_date < cutoff_date:
                if delete_file(os.path.join(dir_path, file)):
                    deleted += 1

        if deleted:
            print(f'Evicted {deleted} old file(s) from usages/{resolution}')


def evict_usages_week():
    # Nothing reads the "week" resolution (checked the panel), it's pure
    # dead weight; keep wiping it in case summarize.py ever starts writing
    # it again.
    dir_path = os.path.join(USAGES_PATH, 'week')
    if not os.path.isdir(dir_path):
        return

    deleted = 0
    for file in os.listdir(dir_path):
        if delete_file(os.path.join(dir_path, file)):
            deleted += 1

    if deleted:
        print(f'Evicted {deleted} unused usages/week file(s)')


if __name__ == '__main__':
    state = load_state()
    now = time.time()
    if now - state.get('last_run', 0) < RUN_INTERVAL_SECONDS:
        raise SystemExit(0)

    retention_days = effective_retention_days(state)
    state['last_run'] = now
    save_state(state)

    cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=retention_days)
    evict_parsed_logs(cutoff)
    evict_usages_day_and_month(cutoff)
    evict_usages_week()
