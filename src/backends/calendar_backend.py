import os
import sqlite3
import json
import re
import stat
import html
from datetime import datetime, date, timedelta
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal, Slot, Property, QDateTime, QByteArray
try:
    from paths import get_writable_appdata_dir
except ImportError:
    from src.paths import get_writable_appdata_dir

def get_calendar_db_path():
    dir_path = get_writable_appdata_dir()
    return os.path.join(dir_path, "calendar.db")

def get_legacy_json_path():
    dir_path = get_writable_appdata_dir()
    return os.path.join(dir_path, "events.json")


class CalendarBackend(QAbstractListModel):
    eventsChanged = Signal()
    selectedDayChanged = Signal()

    IdRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    DescriptionRole = Qt.UserRole + 3
    StartTimeRole = Qt.UserRole + 4
    EndTimeRole = Qt.UserRole + 5
    ColorRole = Qt.UserRole + 6
    EventTypeRole = Qt.UserRole + 7
    IsAllDayRole = Qt.UserRole + 8
    DateStrRole = Qt.UserRole + 9
    TimeStrRole = Qt.UserRole + 10
    TimeLabelRole = Qt.UserRole + 11

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_path = get_calendar_db_path()
        self._events = []
        self._init_db()
        self._reload_data()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    start_time TEXT NOT NULL,
                    end_time TEXT DEFAULT '',
                    color TEXT DEFAULT '#0a84ff',
                    event_type TEXT DEFAULT 'Event',
                    is_all_day INTEGER DEFAULT 0
                )
            """)
            conn.commit()

            # Check if database is empty
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM events")
            count = cur.fetchone()[0]

            if count == 0:
                self._seed_initial_events(conn)

        # Enforce restricted file permissions on calendar.db (read/write by current user only)
        try:
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            print(f"[CalendarBackend] File permission notice: {e}")

    def _seed_initial_events(self, conn):
        # 1. Try importing from legacy events.json if present
        legacy_path = get_legacy_json_path()
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, "r", encoding="utf-8") as f:
                    legacy_events = json.load(f)
                    if legacy_events and isinstance(legacy_events, list):
                        for ev in legacy_events:
                            t_str = ev.get("time", "09:00")
                            d_str = ev.get("date", datetime.now().strftime("%Y-%m-%d"))
                            start_iso = f"{d_str}T{t_str}:00"
                            is_all_day = 1 if ev.get("isAllDay") else 0
                            conn.execute("""
                                INSERT INTO events (title, description, start_time, end_time, color, event_type, is_all_day)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                ev.get("title", "Event"),
                                ev.get("description", ""),
                                start_iso,
                                "",
                                ev.get("eventColor", "#0a84ff"),
                                ev.get("eventType", "Event"),
                                is_all_day
                            ))
                        conn.commit()
                        print(f"[CalendarBackend] Migrated {len(legacy_events)} events from legacy JSON.")
                        return
            except Exception as e:
                print(f"[CalendarBackend] Error migrating legacy JSON: {e}")

        # 2. Seed default Glass-styled events
        now = datetime.now()
        d0 = now.strftime("%Y-%m-%d")
        d1 = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        d2 = (now + timedelta(days=3)).strftime("%Y-%m-%d")
        d3 = (now + timedelta(days=7)).strftime("%Y-%m-%d")

        seeds = [
            ("Design & UI Review", "Glass Widgets on Windows 11", f"{d0}T14:00:00", f"{d0}T15:00:00", "#0a84ff", "Event", 0),
            ("Qt 6 Quick Direct3D Sync", "Hardware acceleration performance pass", f"{d0}T16:30:00", f"{d0}T17:15:00", "#34C759", "Event", 0),
            ("Release Day & Packaging", "Publish standalone Windows desktop widget suite", f"{d1}T10:00:00", f"{d1}T12:00:00", "#FF9500", "Event", 0),
            ("Weekend Planning", "Upcoming events & travel", f"{d2}T09:00:00", f"{d2}T10:00:00", "#AF52DE", "Event", 1),
            ("Team Showcase", "GlassWidgets desktop showcase", f"{d3}T15:00:00", f"{d3}T16:00:00", "#4B9EFF", "Event", 0),
        ]

        conn.executemany("""
            INSERT INTO events (title, description, start_time, end_time, color, event_type, is_all_day)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, seeds)
        conn.commit()
        print("[CalendarBackend] Seeded SQLite calendar with default events.")

    def _reload_data(self):
        self.beginResetModel()
        self._events = []
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, title, description, start_time, end_time, color, event_type, is_all_day
                    FROM events
                    ORDER BY start_time ASC
                """)
                rows = cur.fetchall()
                for r in rows:
                    st = r["start_time"]
                    date_part = st[:10] if len(st) >= 10 else datetime.now().strftime("%Y-%m-%d")
                    time_part = st[11:16] if len(st) >= 16 else "00:00"
                    is_all = bool(r["is_all_day"])

                    if is_all:
                        t_lbl = "All day"
                    else:
                        try:
                            hh, mm = map(int, time_part.split(":"))
                            ampm = "AM" if hh < 12 else "PM"
                            h12 = hh % 12
                            if h12 == 0:
                                h12 = 12
                            t_lbl = f"{h12}:{mm:02d} {ampm}"
                        except Exception:
                            t_lbl = time_part

                    self._events.append({
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"] or "",
                        "startTime": st,
                        "endTime": r["end_time"] or "",
                        "color": r["color"] or "#0a84ff",
                        "eventType": r["event_type"] or "Event",
                        "isAllDay": is_all,
                        "dateStr": date_part,
                        "timeStr": time_part,
                        "timeLabel": t_lbl
                    })
        except Exception as e:
            print(f"[CalendarBackend] Error reloading data: {e}")
        self.endResetModel()
        self.eventsChanged.emit()

    # --- QAbstractListModel Overrides ---
    def rowCount(self, parent=QModelIndex()):
        return len(self._events)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._events):
            return None
        ev = self._events[index.row()]
        if role == self.IdRole:
            return ev["id"]
        elif role == self.TitleRole or role == Qt.DisplayRole:
            return ev["title"]
        elif role == self.DescriptionRole:
            return ev["description"]
        elif role == self.StartTimeRole:
            return ev["startTime"]
        elif role == self.EndTimeRole:
            return ev["endTime"]
        elif role == self.ColorRole:
            return ev["color"]
        elif role == self.EventTypeRole:
            return ev["eventType"]
        elif role == self.IsAllDayRole:
            return ev["isAllDay"]
        elif role == self.DateStrRole:
            return ev["dateStr"]
        elif role == self.TimeStrRole:
            return ev["timeStr"]
        elif role == self.TimeLabelRole:
            return ev["timeLabel"]
        return None

    def roleNames(self):
        return {
            self.IdRole: QByteArray(b"eventId"),
            self.TitleRole: QByteArray(b"title"),
            self.DescriptionRole: QByteArray(b"description"),
            self.StartTimeRole: QByteArray(b"startTime"),
            self.EndTimeRole: QByteArray(b"endTime"),
            self.ColorRole: QByteArray(b"eventColor"),
            self.EventTypeRole: QByteArray(b"eventType"),
            self.IsAllDayRole: QByteArray(b"isAllDay"),
            self.DateStrRole: QByteArray(b"dateStr"),
            self.TimeStrRole: QByteArray(b"timeStr"),
            self.TimeLabelRole: QByteArray(b"timeLabel")
        }

    # --- CRUD Slots for QML ---
    @Slot(str, str, str, bool, str, str, str, str, result=int)
    @Slot(str, str, str, bool, str, str, result=int)
    @Slot(str, str, str, bool, str, result=int)
    @Slot(str, str, str, bool, result=int)
    @Slot(str, str, result=int)
    def addEvent(self, title, date_str, time_str="09:00", is_all_day=False, color="#0a84ff", event_type="Event", description="", end_time=""):
        if not title:
            return -1

        # Sanitize & clamp lengths to prevent database pollution or layout breaks
        title = html.escape(str(title).strip())[:200]
        description = html.escape(str(description).strip())[:2000] if description else ""

        # Validate date_str (YYYY-MM-DD)
        date_clean = str(date_str).strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_clean):
            date_clean = datetime.now().strftime("%Y-%m-%d")

        # Validate time_str (HH:MM)
        time_clean = str(time_str).strip()
        if not re.match(r"^\d{1,2}:\d{2}$", time_clean):
            time_clean = "00:00"
        if len(time_clean) == 4 and time_clean[1] == ":":
            time_clean = "0" + time_clean
        start_iso = f"{date_clean}T{time_clean}:00"

        # Validate color
        color_clean = str(color).strip()
        if not re.match(r"^#[0-9a-fA-F]{3,8}$", color_clean):
            color_clean = "#0a84ff"

        if event_type not in ["Event", "Todo", "Holiday", "Journal"]:
            event_type = "Event"

        is_all_day_int = 1 if is_all_day else 0
        new_id = -1
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO events (title, description, start_time, end_time, color, event_type, is_all_day)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (title, description, start_iso, end_time, color_clean, event_type, is_all_day_int))
                conn.commit()
                new_id = cur.lastrowid
        except Exception as e:
            print(f"[CalendarBackend] Error adding event: {e}")
            return -1

        self._reload_data()
        return new_id

    @Slot(int, result=bool)
    def deleteEvent(self, event_id):
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
                conn.commit()
            self._reload_data()
            return True
        except Exception as e:
            print(f"[CalendarBackend] Error deleting event {event_id}: {e}")
            return False

    @Slot(int, str, str, str, bool, str, str, str, str, result=bool)
    def updateEvent(self, event_id, title, date_str, time_str="09:00", is_all_day=False, color="#0a84ff", event_type="Event", description="", end_time=""):
        if not title:
            return False

        # Sanitize & clamp lengths
        title = html.escape(str(title).strip())[:200]
        description = html.escape(str(description).strip())[:2000] if description else ""

        # Validate date_str (YYYY-MM-DD)
        date_clean = str(date_str).strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_clean):
            date_clean = datetime.now().strftime("%Y-%m-%d")

        # Validate time_str (HH:MM)
        time_clean = str(time_str).strip()
        if not re.match(r"^\d{1,2}:\d{2}$", time_clean):
            time_clean = "00:00"
        if len(time_clean) == 4 and time_clean[1] == ":":
            time_clean = "0" + time_clean
        start_iso = f"{date_clean}T{time_clean}:00"

        # Validate color
        color_clean = str(color).strip()
        if not re.match(r"^#[0-9a-fA-F]{3,8}$", color_clean):
            color_clean = "#0a84ff"

        if event_type not in ["Event", "Todo", "Holiday", "Journal"]:
            event_type = "Event"

        is_all_day_int = 1 if is_all_day else 0

        try:
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE events
                    SET title = ?, description = ?, start_time = ?, end_time = ?, color = ?, event_type = ?, is_all_day = ?
                    WHERE id = ?
                """, (title, description, start_iso, end_time, color_clean, event_type, is_all_day_int, event_id))
                conn.commit()
            self._reload_data()
            return True
        except Exception as e:
            print(f"[CalendarBackend] Error updating event {event_id}: {e}")
            return False

    # --- Query Slots for QML Calendar Components ---
    @Slot("QVariant", result="QVariant")
    def getEventsForDate(self, qdate_or_js):
        """Returns events formatted for KDE Calendar compatibility with QDateTime objects."""
        target_str = ""
        try:
            if hasattr(qdate_or_js, "toPython"):
                py_dt = qdate_or_js.toPython()
                if isinstance(py_dt, (datetime, date)):
                    target_str = py_dt.strftime("%Y-%m-%d")
            elif hasattr(qdate_or_js, "getFullYear"):
                y = qdate_or_js.getFullYear()
                m = qdate_or_js.getMonth() + 1
                d = qdate_or_js.getDate()
                target_str = f"{y:04d}-{m:02d}-{d:02d}"
            elif hasattr(qdate_or_js, "year"):
                target_str = f"{qdate_or_js.year():04d}-{qdate_or_js.month():02d}-{qdate_or_js.day():02d}"
            else:
                s = str(qdate_or_js)
                if len(s) >= 10 and s[4] == '-' and s[7] == '-':
                    target_str = s[:10]
                else:
                    dt = datetime.fromisoformat(s)
                    target_str = dt.strftime("%Y-%m-%d")
        except Exception:
            target_str = datetime.now().strftime("%Y-%m-%d")

        results = []
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, title, description, start_time, end_time, color, event_type, is_all_day
                    FROM events
                    WHERE substr(start_time, 1, 10) = ?
                    ORDER BY is_all_day DESC, start_time ASC
                """, (target_str,))
                rows = cur.fetchall()

                for r in rows:
                    st = r["start_time"]
                    t_str = st[11:16] if len(st) >= 16 else "00:00"
                    try:
                        dt = datetime.strptime(f"{target_str} {t_str}", "%Y-%m-%d %H:%M")
                    except Exception:
                        dt = datetime.now()

                    end_dt = dt + timedelta(minutes=60)
                    q_start = QDateTime.fromSecsSinceEpoch(int(dt.timestamp()))
                    q_end = QDateTime.fromSecsSinceEpoch(int(end_dt.timestamp()))

                    results.append({
                        "id": r["id"],
                        "title": r["title"],
                        "description": r["description"] or "",
                        "startDateTime": q_start,
                        "endDateTime": q_end,
                        "isAllDay": bool(r["is_all_day"]),
                        "eventColor": r["color"] or "#0a84ff",
                        "eventType": r["event_type"] or "Event"
                    })
        except Exception as e:
            print(f"[CalendarBackend] Error fetching events for {target_str}: {e}")

        return results

    @Slot(int, int, result="QVariant")
    def getEventDaysForMonth(self, year, month):
        """Returns list of day numbers (1..31) in the given year and month that have at least one event."""
        month_prefix = f"{year:04d}-{month:02d}"
        days = []
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT substr(start_time, 9, 2)
                    FROM events
                    WHERE substr(start_time, 1, 7) = ?
                """, (month_prefix,))
                rows = cur.fetchall()
                for r in rows:
                    try:
                        days.append(int(r[0]))
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            print(f"[CalendarBackend] Error fetching event days for {month_prefix}: {e}")
        return sorted(days)

    @Slot(int, int, int, result=bool)
    def hasEventsOnDate(self, year, month, day):
        """Fast check for event presence on specific year, month (1-based), day."""
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM events WHERE substr(start_time, 1, 10) = ? LIMIT 1", (date_str,))
                return cur.fetchone() is not None
        except Exception:
            return False

    @Slot(result="QVariant")
    def getAllEvents(self):
        """Returns all events as raw dictionaries for QML."""
        return self._events

    @Slot(str)
    def importIcs(self, ics_path):
        if not os.path.exists(ics_path):
            return
        try:
            with open(ics_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            current_event = None
            for line in lines:
                line = line.strip()
                if line == "BEGIN:VEVENT":
                    current_event = {"eventType": "Event", "isAllDay": False, "eventColor": "#4B9EFF", "description": ""}
                elif line == "END:VEVENT" and current_event:
                    if "title" in current_event and "date" in current_event:
                        t = current_event.get("time", "09:00")
                        self.addEvent(
                            current_event["title"],
                            current_event["date"],
                            t,
                            current_event.get("isAllDay", False),
                            current_event.get("eventColor", "#4B9EFF"),
                            current_event.get("eventType", "Event"),
                            current_event.get("description", "")
                        )
                    current_event = None
                elif current_event:
                    if line.startswith("SUMMARY:"):
                        current_event["title"] = line[8:].strip()
                    elif line.startswith("DESCRIPTION:"):
                        current_event["description"] = line[12:].strip()
                    elif line.startswith("DTSTART"):
                        val = line.split(":")[-1].strip()
                        if len(val) >= 8:
                            current_event["date"] = f"{val[0:4]}-{val[4:6]}-{val[6:8]}"
                            if len(val) >= 13 and "T" in val:
                                current_event["time"] = f"{val[9:11]}:{val[11:13]}"
                            else:
                                current_event["isAllDay"] = True
                                current_event["time"] = "00:00"
        except Exception as e:
            print(f"[CalendarBackend] Error importing ICS {ics_path}: {e}")
