import math
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
PARIS_LAT, PARIS_LON = 48.8566, 2.3522

SYNODIC_MONTH = 29.530588853
NEW_MOON_EPOCH_JD = 2451550.26
MOON_PHASES = "🌑🌒🌓🌔🌕🌖🌗🌘"


@dataclass(frozen=True)
class Day:
    sunrise: datetime
    sunset: datetime
    utc_offset: int
    moon: str


def _julian(dt: datetime) -> float:
    return dt.timestamp() / 86400 + 2440587.5


def _from_julian(jd: float, tz: ZoneInfo) -> datetime:
    return datetime.fromtimestamp((jd - 2440587.5) * 86400, tz=timezone.utc).astimezone(tz)


def _sun_times(d: date, lat: float, lon: float) -> tuple[float, float]:
    """Sunrise and sunset as Julian dates (NOAA sunrise equation, about one minute accurate)."""
    sin, cos, rad = math.sin, math.cos, math.radians
    n = math.ceil(_julian(datetime.combine(d, time(12), timezone.utc)) - 2451545.0 + 0.0008)
    mean_noon = n - lon / 360
    anomaly = (357.5291 + 0.98560028 * mean_noon) % 360
    centre = 1.9148 * sin(rad(anomaly)) + 0.02 * sin(rad(2 * anomaly)) + 0.0003 * sin(rad(3 * anomaly))
    longitude = (anomaly + centre + 180 + 102.9372) % 360
    transit = 2451545.0 + mean_noon + 0.0053 * sin(rad(anomaly)) - 0.0069 * sin(rad(2 * longitude))
    declination = math.asin(sin(rad(longitude)) * sin(rad(23.4397)))
    hour_angle = math.degrees(math.acos(
        (sin(rad(-0.833)) - sin(rad(lat)) * sin(declination)) / (cos(rad(lat)) * cos(declination))
    ))
    return transit - hour_angle / 360, transit + hour_angle / 360


def _moon(d: date, tz: ZoneInfo) -> str:
    age = ((_julian(datetime.combine(d, time(12), tz)) - NEW_MOON_EPOCH_JD) / SYNODIC_MONTH) % 1
    return MOON_PHASES[round(age * 8) % 8]


def paris_day(d: date) -> Day:
    rise, set_ = _sun_times(d, PARIS_LAT, PARIS_LON)
    offset = datetime.combine(d, time(12), PARIS).utcoffset()
    return Day(
        sunrise=_from_julian(rise, PARIS),
        sunset=_from_julian(set_, PARIS),
        utc_offset=int(offset.total_seconds() // 3600),
        moon=_moon(d, PARIS),
    )
