from flask import Flask, Response
import requests
import os

app = Flask(__name__)

ICAL_URL = os.environ.get("ICAL_URL", "")
DRIVER_NAME = os.environ.get("DRIVER_NAME", "Chase Sweat")
EXCLUDE_WORDS = os.environ.get("EXCLUDE_WORDS", "AVAILABLE,UNAVAILABLE,Vacation,OFF")

SCHOOL_ICAL_URL = "https://www.forsyth.k12.ga.us/fs/calendar-manager/events.ics?calendar_ids=21"
SCHOOL_KEEP_WORDS = ["break", "early release", "no school", "first day", "last day", "workday", "recess", "dismiss", "student holiday", "staff holiday"]

CRLF = "\r\n"

def filter_ical(text, name, exclude_words):
    exclude = [w.strip().lower() for w in exclude_words.split(",") if w.strip()]
    name_lower = name.lower()
    events = text.split("BEGIN:VEVENT")
    header = events[0]
    kept = []
    for block in events[1:]:
        full = "BEGIN:VEVENT" + block
        unfolded = full.replace(CRLF + " ", "").replace("\n ", "")
        lower = unfolded.lower()
        is_mine = False
        if "attendee" in lower and name_lower in lower:
            is_mine = True
        if "organizer" in lower and name_lower in lower:
            is_mine = True
        if not is_mine:
            continue
        summary_line = ""
        for line in unfolded.splitlines():
            if line.upper().startswith("SUMMARY:"):
                summary_line = line.lower()
                break
        if any(w in summary_line for w in exclude):
            continue
        kept.append(full.strip())
    body = CRLF.join(kept)
    end = "END:VCALENDAR"
    if end in header:
        header = header.replace(end, "").strip()
    return header.strip() + CRLF + body + CRLF + "END:VCALENDAR"

def filter_school_ical(text, keep_words):
    events = text.split("BEGIN:VEVENT")
    header = events[0]
    kept = []
    for block in events[1:]:
        full = "BEGIN:VEVENT" + block
        unfolded = full.replace(CRLF + " ", "").replace("\n ", "")
        summary_line = ""
        for line in unfolded.splitlines():
            if line.upper().startswith("SUMMARY:"):
                summary_line = line.lower()
                break
        if any(w in summary_line for w in keep_words):
            kept.append(full.strip())
    body = CRLF.join(kept)
    end = "END:VCALENDAR"
    if end in header:
        header = header.replace(end, "").strip()
    return header.strip() + CRLF + body + CRLF + "END:VCALENDAR"

@app.route("/feed")
def feed():
    if not ICAL_URL:
        return Response("ICAL_URL not configured", status=500)
    try:
        r = requests.get(ICAL_URL, timeout=15)
        r.raise_for_status()
    except Exception as e:
        return Response("Failed to fetch calendar: " + str(e), status=502)
    filtered = filter_ical(r.text, DRIVER_NAME, EXCLUDE_WORDS)
    return Response(filtered, mimetype="text/calendar")

@app.route("/school")
def school():
    try:
        r = requests.get(SCHOOL_ICAL_URL, timeout=15)
        r.raise_for_status()
    except Exception as e:
        return Response("Failed to fetch school calendar: " + str(e), status=502)
    filtered = filter_school_ical(r.text, SCHOOL_KEEP_WORDS)
    return Response(filtered, mimetype="text/calendar")

@app.route("/")
def index():
    return "Ride filter running. Feeds: /feed (rides) | /school (school calendar)"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
