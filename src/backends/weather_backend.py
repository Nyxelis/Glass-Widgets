import os
import json
import time
import ssl
import urllib.request
import urllib.parse
import threading
from datetime import datetime, timezone
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QMetaObject, Qt
try:
    from paths import get_writable_appdata_dir
except ImportError:
    from src.paths import get_writable_appdata_dir

def get_weather_cache_file():
    path = get_writable_appdata_dir()
    return os.path.join(path, "weather_cache.json")


class WeatherBackend(QObject):
    weatherDataChanged = Signal()
    coordinatesChanged = Signal()
    loadingChanged = Signal()
    errorChanged = Signal()

    _fetchSuccess = Signal(dict)
    _fetchError = Signal(str)
    _geocodeSuccess = Signal(str, float, float)
    _geocodeError = Signal(str)

    def __init__(self, config_mgr=None, parent=None):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.cache_file = get_weather_cache_file()

        # Connect background worker signals
        self._fetchSuccess.connect(self._on_fetch_success)
        self._fetchError.connect(self._on_fetch_error)
        self._geocodeSuccess.connect(self._on_geocode_success)
        self._geocodeError.connect(self._on_geocode_error)

        # Default coordinates (e.g. New York)
        self._lat = 40.7128
        self._lon = -74.0060
        self._location_name = "New York"
        self._temp_unit = 0 # 0 = Celsius, 1 = Fahrenheit

        # Weather state
        self._current_temp = "--"
        self._high_temp = "--"
        self._low_temp = "--"
        self._weather_code = 0
        self._condition_text = "Loading…"
        self._icon_name = "sunny"
        self._wind_speed = "--"
        self._wind_direction = "N"
        self._humidity = "--"
        self._is_night = False
        self._gradient_category = "clear"
        self._hourly_slots = []
        self._daily_forecast = []
        self._overall_low = 0.0
        self._overall_high = 100.0

        self._is_loading = False
        self._error_message = ""
        self._last_updated = ""
        self._last_fetch_timestamp = 0

        # Load saved coordinates from config if available
        if self.config_mgr:
            cfg = self.config_mgr.get_widget_config("weather")
            lat_val = getattr(cfg, "latitude", None)
            lon_val = getattr(cfg, "longitude", None)
            loc_val = getattr(cfg, "location", None)
            if lat_val is not None and lat_val != 0.0:
                self._lat = float(lat_val)
            if lon_val is not None and lon_val != 0.0:
                self._lon = float(lon_val)
            if loc_val:
                self._location_name = str(loc_val)

        # 30-minute auto refresh timer (started when weather widget is active)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1800000) # 30 mins
        self._refresh_timer.timeout.connect(self.refreshWeather)

        # Initial load: load cache immediately
        self._load_cache()

    @Slot()
    def pause_polling(self):
        if self._refresh_timer.isActive():
            print("[WeatherBackend] Pausing weather refresh timer (no active weather widgets)", flush=True)
            self._refresh_timer.stop()

    @Slot()
    def resume_polling(self):
        if not self._refresh_timer.isActive():
            print("[WeatherBackend] Resuming weather refresh timer", flush=True)
            self._refresh_timer.start()
            now = time.time()
            if now - self._last_fetch_timestamp > 1800:
                self.refreshWeather()

    # --- Property Getters ---
    @Property(float, notify=coordinatesChanged)
    def latitude(self):
        return self._lat

    @Property(float, notify=coordinatesChanged)
    def longitude(self):
        return self._lon

    @Property(str, notify=coordinatesChanged)
    def locationName(self):
        return self._location_name

    @Property(str, notify=weatherDataChanged)
    def currentTemp(self):
        return self._current_temp

    @Property(str, notify=weatherDataChanged)
    def highTemp(self):
        return self._high_temp

    @Property(str, notify=weatherDataChanged)
    def lowTemp(self):
        return self._low_temp

    @Property(int, notify=weatherDataChanged)
    def weatherCode(self):
        return self._weather_code

    @Property(str, notify=weatherDataChanged)
    def condition(self):
        return self._condition_text

    @Property(str, notify=weatherDataChanged)
    def iconName(self):
        return self._icon_name

    @Property(str, notify=weatherDataChanged)
    def windSpeed(self):
        return self._wind_speed

    @Property(str, notify=weatherDataChanged)
    def windDirection(self):
        return self._wind_direction

    @Property(str, notify=weatherDataChanged)
    def humidity(self):
        return self._humidity

    @Property(bool, notify=weatherDataChanged)
    def isNight(self):
        return self._is_night

    @Property(str, notify=weatherDataChanged)
    def gradientCategory(self):
        return self._gradient_category

    @Property("QVariantList", notify=weatherDataChanged)
    def hourlySlots(self):
        return self._hourly_slots

    @Property("QVariantList", notify=weatherDataChanged)
    def dailyForecast(self):
        return self._daily_forecast

    @Property(float, notify=weatherDataChanged)
    def overallLow(self):
        return self._overall_low

    @Property(float, notify=weatherDataChanged)
    def overallHigh(self):
        return self._overall_high

    @Property(bool, notify=loadingChanged)
    def isLoading(self):
        return self._is_loading

    @Property(str, notify=errorChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=weatherDataChanged)
    def lastUpdated(self):
        return self._last_updated

    # --- WMO Weather Code Mappings ---
    @staticmethod
    def map_icon_for_code(code, night=False):
        if code == 0:
            return "clearnight" if night else "sunny"
        if code in (1, 2):
            return "partlycloudynight" if night else "partlysunny"
        if code == 3:
            return "cloudy"
        if code in (45, 48):
            return "fog"
        if code in (51, 53, 55):
            return "nightdrizzle" if night else "drizzle"
        if code in (56, 57):
            return "sleet"
        if code in (61, 63):
            return "rain"
        if code == 65:
            return "heavyrain"
        if code in (66, 67):
            return "sleet"
        if code in (71, 73, 75):
            return "snow"
        if code == 77:
            return "scatteredsnow"
        if code in (80, 81):
            return "rain"
        if code == 82:
            return "heavyrain"
        if code in (85, 86):
            return "scatteredsnow"
        if code in (95, 96, 99):
            return "thunderbolt"
        return "clearnight" if night else "sunny"

    @staticmethod
    def map_condition_for_code(code):
        conditions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Freezing drizzle",
            57: "Heavy freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return conditions.get(code, "Clear")

    @staticmethod
    def map_gradient_category(code, night=False):
        if code in (0, 1):
            return "nightclear" if night else "clear"
        if code == 2:
            return "nightcloudy" if night else "clear"
        if code == 3:
            return "cloudy"
        if code in (45, 48):
            return "fog"
        if (51 <= code <= 67) or (80 <= code <= 82):
            return "rain"
        if (71 <= code <= 77) or code in (85, 86):
            return "snow"
        if code >= 95:
            return "storm"
        return "nightclear" if night else "clear"

    @staticmethod
    def compass_direction(degrees):
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int(round(degrees / 45.0)) % 8
        return dirs[idx]

    # --- Cache Management ---
    def _load_cache(self):
        if not os.path.exists(self.cache_file):
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_lat = cached.get("latitude")
            cached_lon = cached.get("longitude")
            # Only use if coordinates match
            if cached_lat is not None and cached_lon is not None:
                if abs(cached_lat - self._lat) < 0.01 and abs(cached_lon - self._lon) < 0.01:
                    raw_data = cached.get("data")
                    if raw_data:
                        self._process_api_payload(raw_data)
                        self._last_fetch_timestamp = cached.get("timestamp", 0)
        except Exception as e:
            print(f"[WeatherBackend] Error loading cache: {e}")

    def _save_cache(self, raw_data):
        try:
            cache_obj = {
                "latitude": self._lat,
                "longitude": self._lon,
                "timestamp": time.time(),
                "data": raw_data
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_obj, f)
        except Exception as e:
            print(f"[WeatherBackend] Error saving cache: {e}")

    # --- Public Slots for UI Interaction ---
    @Slot(float, float)
    def setCoordinates(self, lat, lon):
        self.updateLocation(self._location_name, lat, lon)

    @Slot(str)
    def setLocationName(self, name):
        self.updateLocation(name, self._lat, self._lon)

    @Slot(str, float, float)
    def updateLocation(self, name, lat, lon):
        if lat < -90.0 or lat > 90.0:
            self._error_message = "Latitude must be between -90 and 90"
            self.errorChanged.emit()
            return
        if lon < -180.0 or lon > 180.0:
            self._error_message = "Longitude must be between -180 and 180"
            self.errorChanged.emit()
            return

        coords_changed = (self._lat != lat or self._lon != lon or self._location_name != name)
        self._lat = float(lat)
        self._lon = float(lon)
        self._location_name = name.strip() or f"{lat:.2f}, {lon:.2f}"
        self._error_message = ""
        self.errorChanged.emit()

        if coords_changed:
            self.coordinatesChanged.emit()
            # Persist in config
            if self.config_mgr:
                self.config_mgr.set_widget_config("weather", "latitude", self._lat)
                self.config_mgr.set_widget_config("weather", "longitude", self._lon)
                self.config_mgr.set_widget_config("weather", "location", self._location_name)
                # Sync weather-panel as well
                self.config_mgr.set_widget_config("weather-panel", "latitude", self._lat)
                self.config_mgr.set_widget_config("weather-panel", "longitude", self._lon)
                self.config_mgr.set_widget_config("weather-panel", "location", self._location_name)
            self.refreshWeather(force=True)

    def _on_fetch_success(self, payload):
        self._process_api_payload(payload)
        self._is_loading = False
        self._error_message = ""
        self.loadingChanged.emit()
        self.errorChanged.emit()

    def _on_fetch_error(self, err_msg):
        self._error_message = err_msg
        self._is_loading = False
        self.loadingChanged.emit()
        self.errorChanged.emit()

    def _on_geocode_success(self, name, lat, lon):
        self.updateLocation(name, lat, lon)

    def _on_geocode_error(self, err_msg):
        self._error_message = err_msg
        self._is_loading = False
        self.loadingChanged.emit()
        self.errorChanged.emit()

    @Slot(str)
    def searchCityAndSet(self, query):
        clean = query.strip()
        if not clean:
            return

        # Check if user typed coordinates like "35.68, 139.76"
        if "," in clean:
            parts = clean.split(",")
            try:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                self.updateLocation(f"{lat:.2f}, {lon:.2f}", lat, lon)
                return
            except ValueError:
                pass

        def search_thread():
            self._is_loading = True
            QTimer.singleShot(0, lambda: self.loadingChanged.emit())
            try:
                enc = urllib.parse.quote(clean)
                url = f"https://geocoding-api.open-meteo.com/v1/search?name={enc}&count=1&language=en&format=json"
                req = urllib.request.Request(url, headers={"User-Agent": "GlassWidgets/1.0"})
                ssl_ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    results = data.get("results")
                    if results and len(results) > 0:
                        top = results[0]
                        c_name = top.get("name", clean)
                        c_lat = float(top.get("latitude"))
                        c_lon = float(top.get("longitude"))
                        c_country = top.get("country", "")
                        disp_name = f"{c_name}, {c_country}" if c_country else c_name
                        self._geocodeSuccess.emit(disp_name, c_lat, c_lon)
                    else:
                        self._geocodeError.emit(f"City '{clean}' not found")
            except Exception as e:
                self._geocodeError.emit(f"Geocoding error: {e}")

        threading.Thread(target=search_thread, daemon=True).start()

    @Slot()
    def refreshWeather(self, force=False):
        now = time.time()
        # Respect 30-min cache unless force=True
        if not force and (now - self._last_fetch_timestamp < 1800) and self._current_temp != "--":
            return

        def fetch_worker():
            self._is_loading = True
            QTimer.singleShot(0, lambda: self.loadingChanged.emit())

            api_unit = "celsius" if self._temp_unit == 0 else "fahrenheit"
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={self._lat}&longitude={self._lon}"
                f"&current=temperature_2m,weather_code,wind_speed_10m,wind_direction_10m,relative_humidity_2m"
                f"&hourly=temperature_2m,weather_code"
                f"&daily=temperature_2m_max,temperature_2m_min,weather_code,sunrise,sunset"
                f"&temperature_unit={api_unit}"
                f"&wind_speed_unit=kmh"
                f"&timezone=auto"
                f"&forecast_days=7"
            )

            try:
                req = urllib.request.Request(url, headers={"User-Agent": "GlassWidgets/1.0"})
                ssl_ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
                    if resp.status == 200:
                        payload = json.loads(resp.read().decode("utf-8"))
                        self._save_cache(payload)
                        self._last_fetch_timestamp = time.time()
                        self._fetchSuccess.emit(payload)
                    else:
                        self._fetchError.emit(f"Weather server returned HTTP {resp.status}")
            except urllib.error.URLError as e:
                self._fetchError.emit(f"Network offline or timeout: {e.reason}")
            except Exception as e:
                self._fetchError.emit(f"Failed to parse weather: {e}")

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _process_api_payload(self, data):
        cur = data.get("current", {})
        daily = data.get("daily", {})
        hourly = data.get("hourly", {})

        # Current temperature & weather code
        raw_temp = cur.get("temperature_2m")
        if raw_temp is not None:
            self._current_temp = str(int(round(raw_temp)))

        self._weather_code = int(cur.get("weather_code", 0))
        self._condition_text = self.map_condition_for_code(self._weather_code)

        raw_wind = cur.get("wind_speed_10m")
        self._wind_speed = str(int(round(raw_wind))) if raw_wind is not None else "--"
        self._wind_direction = self.compass_direction(cur.get("wind_direction_10m", 0))

        raw_hum = cur.get("relative_humidity_2m")
        self._humidity = f"{int(round(raw_hum))}%" if raw_hum is not None else "--"

        # Day/Night check based on sunrise/sunset
        now_dt = datetime.now()
        is_night = False
        if daily.get("sunrise") and daily.get("sunset"):
            try:
                sunrise_dt = datetime.fromisoformat(daily["sunrise"][0])
                sunset_dt = datetime.fromisoformat(daily["sunset"][0])
                is_night = (now_dt < sunrise_dt or now_dt >= sunset_dt)
            except Exception:
                h = now_dt.hour
                is_night = (h < 7 or h >= 19)
        else:
            h = now_dt.hour
            is_night = (h < 7 or h >= 19)

        self._is_night = is_night
        self._icon_name = self.map_icon_for_code(self._weather_code, is_night)
        self._gradient_category = self.map_gradient_category(self._weather_code, is_night)

        # High & Low for today
        d_max = daily.get("temperature_2m_max", [])
        d_min = daily.get("temperature_2m_min", [])
        if d_max and len(d_max) > 0 and d_max[0] is not None:
            self._high_temp = str(int(round(d_max[0])))
        if d_min and len(d_min) > 0 and d_min[0] is not None:
            self._low_temp = str(int(round(d_min[0])))

        # 7-day Daily forecast
        days_out = []
        lows = []
        highs = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        time_list = daily.get("time", [])
        code_list = daily.get("weather_code", [])

        for i in range(len(time_list)):
            try:
                date_obj = datetime.fromisoformat(time_list[i])
                day_label = "Today" if i == 0 else day_names[date_obj.weekday()]
                mx = int(round(d_max[i])) if i < len(d_max) else 0
                mn = int(round(d_min[i])) if i < len(d_min) else 0
                wc = int(code_list[i]) if i < len(code_list) else 0
                lows.append(mn)
                highs.append(mx)
                days_out.append({
                    "day": day_label,
                    "high": str(mx),
                    "low": str(mn),
                    "weatherCode": wc,
                    "iconName": self.map_icon_for_code(wc, False)
                })
            except Exception:
                pass

        self._daily_forecast = days_out
        self._overall_low = float(min(lows)) if lows else 0.0
        self._overall_high = float(max(highs)) if highs else 100.0

        # Next 24 hours Hourly forecast
        h_times = hourly.get("time", [])
        h_temps = hourly.get("temperature_2m", [])
        h_codes = hourly.get("weather_code", [])
        hourly_out = []

        cur_hour_str = now_dt.strftime("%Y-%m-%dT%H:00")
        start_idx = 0
        for idx, t_str in enumerate(h_times):
            if t_str >= cur_hour_str:
                start_idx = idx
                break

        for j in range(start_idx, min(start_idx + 12, len(h_times))):
            try:
                dt_hour = datetime.fromisoformat(h_times[j])
                disp_time = "Now" if j == start_idx else dt_hour.strftime("%I %p").lstrip("0")
                h_temp = str(int(round(h_temps[j])))
                h_code = int(h_codes[j])
                h_night = (dt_hour.hour < 7 or dt_hour.hour >= 19)
                hourly_out.append({
                    "displayTime": disp_time,
                    "temp": h_temp,
                    "weatherCode": h_code,
                    "iconName": self.map_icon_for_code(h_code, h_night),
                    "isSunEvent": False,
                    "sunEventType": ""
                })
            except Exception:
                pass

        self._hourly_slots = hourly_out
        self._last_updated = now_dt.strftime("%H:%M")
        self.weatherDataChanged.emit()
