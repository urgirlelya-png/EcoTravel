import requests
import json
import hashlib
import os
import math
from datetime import datetime, timedelta
from flask import session


class CarbonCalculator:
    EMISSION_FACTORS = {
        "plane": 0.25,
        "car": 0.18,
        "train": 0.04,
    }

    def __init__(self, transport_type, distance):
        self.transport_type = transport_type.lower()
        self.distance = distance
        self.co2 = self.calculate_footprint()

    def calculate_footprint(self):
        factor = self.EMISSION_FACTORS.get(self.transport_type, 0.18)
        return round(factor * self.distance, 2)

    def get_eco_rating(self):
        if self.co2 <= 20:
            return "A"
        elif self.co2 <= 60:
            return "B"
        elif self.co2 <= 150:
            return "C"
        elif self.co2 <= 400:
            return "D"
        return "F"

    def suggest_alternatives(self):
        suggestions = {
            "plane": "Consider traveling by train to cut CO2 emissions by about 6x. If distance allows, choose an electric car or a high-speed train.",
            "car": "Try taking a train or bus. A train emits about 4.5x less CO2 than a car. Also consider carpooling to reduce impact.",
            "train": "Great choice!  Trains are among the most eco-friendly options. For an even lower footprint, consider biking or walking for short trips.",
        }
        return suggestions.get(self.transport_type, "Choose public transport and plan routes efficiently.")


class TravelProfile:
    def __init__(self, username):
        self.username = username
        if "trips" not in session:
            session["trips"] = []

    def add_trip(self, trip_data):
        trips = session.get("trips", [])
        trips.append(trip_data)
        session["trips"] = trips

    def get_total_co2(self):
        trips = session.get("trips", [])
        return round(sum(t.get("co2", 0) for t in trips), 2)

    def get_badge(self):
        total = self.get_total_co2()
        if total == 0:
            return "Eco Travel Beginner"
        elif total <= 30:
            return "Greta Thunberg"
        elif total <= 100:
            return "Forest Guardian"
        elif total <= 300:
            return "Green Traveler"
        elif total <= 700:
            return "Occasional Ecologist"
        return "Oil Tycoon"


class UserAuth:
    USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")

    def __init__(self):
        if not os.path.exists(self.USERS_FILE):
            with open(self.USERS_FILE, "w") as f:
                json.dump({}, f)

    def _load(self):
        with open(self.USERS_FILE, "r") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.USERS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _hash(self, password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def register(self, username, password):
        users = self._load()
        if username.lower() in {k.lower() for k in users}:
            return False
        users[username] = {
            "password": self._hash(password),
            "joined": datetime.now().strftime("%Y-%m-%d"),
        }
        self._save(users)
        return True

    def login(self, username, password):
        users = self._load()
        user = users.get(username)
        if not user:
            return False
        return user["password"] == self._hash(password)

    def user_exists(self, username):
        users = self._load()
        return username in users


def fetch_weather_data(city, api_key="demo"):
    if api_key == "demo":
        weather = {
            "city": city,
            "temperature": 18,
            "description": "partly cloudy",
            "humidity": 65,
            "wind_speed": 4.2,
            "icon": "02d",
            "feels_like": 16,
        }
        air_quality = {
            "aqi": 2,
            "aqi_label": "Good",
            "co": 201.94,
            "no2": 0.81,
            "pm2_5": 4.73,
        }
        return weather, air_quality

    base_url = "https://api.openweathermap.org/data/2.5"

    try:
        weather_resp = requests.get(
            f"{base_url}/weather",
            params={"q": city, "appid": api_key, "units": "metric", "lang": "en"},
            timeout=5,
        )
        weather_resp.raise_for_status()
        w_data = weather_resp.json()

        lat = w_data["coord"]["lat"]
        lon = w_data["coord"]["lon"]

        weather = {
            "city": w_data.get("name", city),
            "temperature": round(w_data["main"]["temp"], 1),
            "description": w_data["weather"][0]["description"],
            "humidity": w_data["main"]["humidity"],
            "wind_speed": w_data["wind"]["speed"],
            "icon": w_data["weather"][0]["icon"],
            "feels_like": round(w_data["main"]["feels_like"], 1),
        }

        air_resp = requests.get(
            "https://api.openweathermap.org/data/2.5/air_pollution",
            params={"lat": lat, "lon": lon, "appid": api_key},
            timeout=5,
        )
        air_resp.raise_for_status()
        a_data = air_resp.json()

        aqi_labels = {1: "Excellent", 2: "Good", 3: "Moderate", 4: "Poor", 5: "Very poor"}
        aqi_value = a_data["list"][0]["main"]["aqi"]
        components = a_data["list"][0]["components"]

        air_quality = {
            "aqi": aqi_value,
            "aqi_label": aqi_labels.get(aqi_value, "Unknown"),
            "co": components.get("co", 0),
            "no2": components.get("no2", 0),
            "pm2_5": components.get("pm2_5", 0),
        }

        return weather, air_quality

    except requests.RequestException:
        weather = {
            "city": city,
            "temperature": "n/a",
            "description": "data unavailable",
            "humidity": "n/a",
            "wind_speed": "n/a",
            "icon": "01d",
            "feels_like": "n/a",
        }
        air_quality = {
            "aqi": 0,
            "aqi_label": "No data",
            "co": "n/a",
            "no2": "n/a",
            "pm2_5": "n/a",
        }
        return weather, air_quality


def fetch_forecast_data(city, api_key="demo"):
    today = datetime.now()

    if api_key == "demo":
        scenarios = [
            (14, 22, "clear sky",        "01d", 48, 3.1, 5),
            (12, 19, "few clouds",        "02d", 54, 4.0, 10),
            (9,  15, "scattered clouds",  "03d", 65, 5.5, 35),
            (7,  12, "light rain",        "10d", 82, 6.8, 80),
            (11, 17, "broken clouds",     "04d", 60, 4.3, 20),
        ]
        days = []
        for i, (t_min, t_max, desc, icon, hum, wind, rain_chance) in enumerate(scenarios):
            d = today + timedelta(days=i)
            days.append({
                "date":         d.strftime("%Y-%m-%d"),
                "day_name":     d.strftime("%A"),
                "date_display": d.strftime("%b %d"),
                "temp_min":     t_min,
                "temp_max":     t_max,
                "description":  desc,
                "icon":         icon,
                "humidity":     hum,
                "wind_speed":   wind,
                "rain_chance":  rain_chance,
            })

        hours = []
        for h in range(0, 24, 3):
            temp = round(14 + 6 * math.sin((h - 6) * math.pi / 12), 1)
            ico = "01d" if 6 <= h < 20 else "01n"
            hours.append({
                "time":        f"{h:02d}:00",
                "temp":        temp,
                "icon":        ico,
                "rain_chance": 5 if h < 15 else 10,
            })

        return {"city": city, "days": days, "hours": hours}

    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"q": city, "appid": api_key, "units": "metric", "cnt": 40},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        city_name = data["city"]["name"]

        grouped = {}
        for item in data["list"]:
            date_str = item["dt_txt"].split(" ")[0]
            grouped.setdefault(date_str, []).append(item)

        days = []
        for date_str, items in list(grouped.items())[:5]:
            temps = [it["main"]["temp"] for it in items]
            mid = items[len(items) // 2]
            d = datetime.strptime(date_str, "%Y-%m-%d")
            days.append({
                "date":         date_str,
                "day_name":     d.strftime("%A"),
                "date_display": d.strftime("%b %d"),
                "temp_min":     round(min(temps), 1),
                "temp_max":     round(max(temps), 1),
                "description":  mid["weather"][0]["description"],
                "icon":         mid["weather"][0]["icon"],
                "humidity":     round(sum(it["main"]["humidity"] for it in items) / len(items)),
                "wind_speed":   round(sum(it["wind"]["speed"] for it in items) / len(items), 1),
                "rain_chance":  round(max(it.get("pop", 0) for it in items) * 100),
            })

        today_str = today.strftime("%Y-%m-%d")
        today_items = grouped.get(today_str, list(grouped.values())[0])
        hours = []
        for it in today_items[:8]:
            hours.append({
                "time":        it["dt_txt"].split(" ")[1][:5],
                "temp":        round(it["main"]["temp"], 1),
                "icon":        it["weather"][0]["icon"],
                "rain_chance": round(it.get("pop", 0) * 100),
            })

        return {"city": city_name, "days": days, "hours": hours}

    except requests.RequestException:
        return {"city": city, "days": [], "hours": [], "error": True}

