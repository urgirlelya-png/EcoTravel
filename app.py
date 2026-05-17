from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from utils import CarbonCalculator, TravelProfile, UserAuth, fetch_weather_data, fetch_forecast_data

app = Flask(__name__)
app.secret_key = "ecotrip-secret-key-2024"

OWM_API_KEY = "dfe39e12c246e653195259ffe54a7341"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        origin        = request.form.get("origin", "").strip()
        destination   = request.form.get("destination", "").strip()
        transport_type = request.form.get("transport_type", "car")

        try:
            distance = int(request.form.get("distance", 0))
        except ValueError:
            distance = 0

        calc = CarbonCalculator(transport_type, distance)

        trip_data = {
            "origin":         origin,
            "destination":    destination,
            "distance":       distance,
            "transport_type": transport_type,
            "co2":            calc.co2,
            "rating":         calc.get_eco_rating(),
        }

        username = session.get("user", "guest")
        profile  = TravelProfile(username)
        profile.add_trip(trip_data)

        return redirect(url_for("calculate", transport=transport_type, distance=distance))

    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/destination/<city>")
def destination(city):
    weather, air_quality = fetch_weather_data(city, OWM_API_KEY)

    aqi = air_quality.get("aqi", 0)
    if aqi <= 2:
        aqi_class = "success"
    elif aqi == 3:
        aqi_class = "warning"
    else:
        aqi_class = "danger"

    return render_template(
        "destination.html",
        weather=weather,
        air_quality=air_quality,
        aqi_class=aqi_class,
        city=city,
    )


@app.route("/weather", methods=["GET", "POST"])
def weather():
    if request.method == "POST":
        city = request.form.get("city", "").strip()
        if city:
            return redirect(url_for("forecast", city=city))
    return render_template("weather.html")


@app.route("/forecast/<city>")
def forecast(city):
    data = fetch_forecast_data(city, OWM_API_KEY)
    return render_template("forecast.html", data=data, city=city)


@app.route("/calculate/<transport>/<int:distance>")
def calculate(transport, distance):
    calc         = CarbonCalculator(transport, distance)
    rating       = calc.get_eco_rating()
    suggestion   = calc.suggest_alternatives()

    rating_classes = {"A": "success", "B": "success", "C": "warning", "D": "warning", "F": "danger"}

    transport_labels = {"plane": "Plane", "car": "Car", "train": "Train"}

    return render_template(
        "calculate.html",
        co2=calc.co2,
        rating=rating,
        rating_class=rating_classes.get(rating, "secondary"),
        suggestion=suggestion,
        transport=transport_labels.get(transport.lower(), transport),
        distance=distance,
    )


@app.route("/profile")
@login_required
def profile():
    username      = session["user"]
    travel_profile = TravelProfile(username)
    trips         = session.get("trips", [])
    total_co2     = travel_profile.get_total_co2()
    badge         = travel_profile.get_badge()

    transport_labels = {"plane": "Plane", "car": "Car", "train": "Train"}

    return render_template(
        "profile.html",
        username=username,
        trips=trips,
        total_co2=total_co2,
        badge=badge,
        transport_labels=transport_labels,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user" in session:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm",  "")

        if len(username) < 3:
            error = "Username must be at least 3 characters."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            auth = UserAuth()
            if auth.register(username, password):
                session["user"]  = username
                session["trips"] = []
                return redirect(url_for("index"))
            else:
                error = "That username is already taken."

    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        auth = UserAuth()
        if auth.login(username, password):
            session["user"] = username
            session.setdefault("trips", [])
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
