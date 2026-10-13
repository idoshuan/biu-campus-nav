# Builds a weekly-repeating .ics from a semester timetable (JSON list of classes).
# usage: python3 tools/make_ics.py private/ori-schedule.json private/ori-2027a.ics
import json, sys, uuid, datetime as dt

DAY = {"ראשון": 0, "שני": 1, "שלישי": 2, "רביעי": 3, "חמישי": 4, "שישי": 5}
ICS_DAY = ["SU", "MO", "TU", "WE", "TH", "FR"]
VTZ = """BEGIN:VTIMEZONE
TZID:Asia/Jerusalem
BEGIN:STANDARD
DTSTART:19701025T020000
TZOFFSETFROM:+0300
TZOFFSETTO:+0200
TZNAME:IST
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
BEGIN:DAYLIGHT
DTSTART:19700327T020000
TZOFFSETFROM:+0200
TZOFFSETTO:+0300
TZNAME:IDT
RRULE:FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=23,24,25,26,27,28,29;BYDAY=FR
END:DAYLIGHT
END:VTIMEZONE"""

def esc(s): return s.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")
def fold(line):  # RFC 5545: lines of at most 75 octets
    out, cur = [], b""
    for ch in line:
        c = ch.encode()
        if len(cur) + len(c) > (75 if not out else 74): out.append(cur); cur = b""
        cur += c
    out.append(cur)
    return "\r\n ".join(x.decode() for x in out)

spec = json.load(open(sys.argv[1]))
week0 = dt.date.fromisoformat(spec["week_of_sunday"]); until = spec["until"]
lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//biu-campus-nav//timetable//HE", "CALSCALE:GREGORIAN",
         "X-WR-CALNAME:" + esc(spec["name"]), "X-WR-TIMEZONE:Asia/Jerusalem", *VTZ.split("\n")]
stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
for c in spec["classes"]:
    d = week0 + dt.timedelta(days=DAY[c["day"]])
    s, e = c["start"].replace(":", ""), c["end"].replace(":", "")
    loc = (f"בניין {c['building']}" + (f", חדר {c['room']}" if c.get("room") else "")) if c.get("building") else c.get("place", "")
    desc = " · ".join(x for x in (f"קורס {c['code']}", c.get("teacher")) if x)
    lines += ["BEGIN:VEVENT", f"UID:{uuid.uuid5(uuid.NAMESPACE_URL, c['code'] + c['day'] + c['start'])}@biu-campus-nav", f"DTSTAMP:{stamp}",
              f"DTSTART;TZID=Asia/Jerusalem:{d:%Y%m%d}T{s}00", f"DTEND;TZID=Asia/Jerusalem:{d:%Y%m%d}T{e}00",
              f"RRULE:FREQ=WEEKLY;BYDAY={ICS_DAY[DAY[c['day']]]};UNTIL={until}",
              "SUMMARY:" + esc(c["title"]), "LOCATION:" + esc(loc), "DESCRIPTION:" + esc(desc), "END:VEVENT"]
lines.append("END:VCALENDAR")
open(sys.argv[2], "w", newline="").write("\r\n".join(fold(l) for l in lines) + "\r\n")
print(len(spec["classes"]), "classes ->", sys.argv[2])
