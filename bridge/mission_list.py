"""Read-only presentation helpers for device missions."""
import math
from datetime import datetime

def numeric(value):
    try:value=float(value)
    except (TypeError,ValueError):return None
    return value if math.isfinite(value) and value>=0 else None

def timestamp(value):
    value=numeric(value)
    if not value:return None
    return value/1000 if value>100_000_000_000 else value

def sort_rows(rows,mode,label):
    field,reverse={'name-asc':('name',False),'name-desc':('name',True),'date-desc':('updated',True),'date-asc':('updated',False),'distance-asc':('distance',False),'distance-desc':('distance',True),'points-asc':('waypoints',False),'points-desc':('waypoints',True)}.get(mode,(None,False))
    if field is None:return rows
    def value(entry):
        i,m=entry
        return label(i,m).casefold() if field=='name' else timestamp(m.get(field)) if field=='updated' else numeric(m.get(field))
    known=[entry for entry in rows if value(entry) is not None];unknown=[entry for entry in rows if value(entry) is None]
    return sorted(known,key=value,reverse=reverse)+unknown

def archive_state(mission,archive_rows,connected):
    # Only an exact match of the current file against the loaded library counts.
    if not connected or not mission.get('sha256'):return 'unknown'
    return 'saved' if any(m.get('sha256')==mission['sha256'] for m in archive_rows) else 'missing'

def metadata(mission):
    out=[];distance=numeric(mission.get('distance'));date=timestamp(mission.get('updated'))
    if distance is not None:out.append(f'{distance/1000:.2f} km')
    if date:
        try:out.append(datetime.fromtimestamp(date).strftime('%d.%m.%Y'))
        except (OverflowError,OSError,ValueError):pass
    return ' · '.join(out)
