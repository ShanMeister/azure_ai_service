from zoneinfo import ZoneInfo
from datetime import datetime

TAIPEI_ZONEINFO = ZoneInfo("Asia/Taipei")


def get_current_time() -> datetime:
    return datetime.now(TAIPEI_ZONEINFO)
