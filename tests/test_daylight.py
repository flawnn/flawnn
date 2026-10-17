from datetime import date

from daylight import paris_day


def test_known_october_day():
    day = paris_day(date(2026, 10, 17))
    assert day.sunrise.strftime("%H:%M") in {"08:12", "08:13", "08:14"}
    assert day.sunset.strftime("%H:%M") in {"18:56", "18:57", "18:58"}
    assert day.utc_offset == 2
    assert day.moon == "🌓"


def test_offset_follows_daylight_saving():
    assert paris_day(date(2026, 10, 25)).utc_offset == 1
    assert paris_day(date(2026, 7, 1)).utc_offset == 2


def test_midsummer_is_longer_than_midwinter():
    june, december = paris_day(date(2026, 6, 21)), paris_day(date(2026, 12, 21))
    assert june.sunset - june.sunrise > december.sunset - december.sunrise


def test_new_and_full_moon():
    assert paris_day(date(2026, 10, 10)).moon == "🌑"
    assert paris_day(date(2026, 10, 26)).moon == "🌕"
