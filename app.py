import json
import math
import os
import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import wraps
from html import unescape
from statistics import mean
from urllib.error import URLError
from urllib.request import Request, urlopen

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = "change-this-secret-key"

client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)
db = client["farmer_market_db"]
users = db["users"]

PUBLIC_PRICE_BASE_URL = "https://www.vegetablemarketprice.com/market"
AI_PROVIDER = os.environ.get("AI_PROVIDER", "").lower()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
PUBLIC_PRICE_STATES = {
    "andhra-pradesh": "Andhra Pradesh",
    "delhi": "Delhi",
    "gujarat": "Gujarat",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "maharashtra": "Maharashtra",
    "tamil-nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "uttar-pradesh": "Uttar Pradesh",
    "west-bengal": "West Bengal",
}

# Set this to "Summer", "Monsoon", or "Winter" to force a season.
# Keep it empty to detect the season automatically from the current month.
SEASON_OVERRIDE = ""

SEASON_CROPS = {
    "Summer": {
        "months": {3, 4, 5},
        "crops": {
            "cucumber",
            "lemon",
            "mint",
            "watermelon",
            "muskmelon",
            "pumpkin",
            "bottle gourd",
            "ridge gourd",
            "snake gourd",
            "ash gourd",
            "mango",
            "raw mango",
        },
        "note": "Heat-tolerant and water-rich crops usually perform better in summer.",
    },
    "Monsoon": {
        "months": {6, 7, 8, 9},
        "crops": {
            "brinjal",
            "okra",
            "ladies finger",
            "green chilli",
            "chilli",
            "beans",
            "cluster beans",
            "corn",
            "coriander",
            "spinach",
            "amaranth",
            "drumsticks",
        },
        "note": "Monsoon favors rain-fed vegetables, but heavy rain can affect transport and quality.",
    },
    "Winter": {
        "months": {10, 11, 12, 1, 2},
        "crops": {
            "carrot",
            "cauliflower",
            "cabbage",
            "beetroot",
            "radish",
            "green peas",
            "fenugreek",
            "potato",
            "onion",
            "tomato",
            "capsicum",
            "garlic",
        },
        "note": "Cool-season vegetables usually have better quality and supply in winter.",
    },
}


def fetch_weather_signal():
    latitude = os.environ.get("FARM_LATITUDE", "12.9716")
    longitude = os.environ.get("FARM_LONGITUDE", "77.5946")
    api_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        "&current=temperature_2m,rain,precipitation"
    )

    try:
        with urlopen(api_url, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
        current = data.get("current", {})
        rain_mm = float(current.get("rain") or current.get("precipitation") or 0)
        temperature = round(float(current.get("temperature_2m", 28)))
        source = "Live Open-Meteo API"
    except (URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError):
        rain_mm = 0
        temperature = 28
        source = "Offline sample weather"

    if rain_mm >= 10:
        rain_level = "heavy"
    elif rain_mm >= 1:
        rain_level = "normal"
    else:
        rain_level = "low"

    return {
        "temperature": temperature,
        "rain_mm": rain_mm,
        "rain_level": rain_level,
        "source": source,
        "updated_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }


def get_current_season():
    if SEASON_OVERRIDE in SEASON_CROPS:
        details = SEASON_CROPS[SEASON_OVERRIDE]
        return {
            "name": SEASON_OVERRIDE,
            "month": "Hardcoded",
            "crops": sorted(details["crops"]),
            "note": details["note"],
        }

    current_month = datetime.now().month
    for season_name, details in SEASON_CROPS.items():
        if current_month in details["months"]:
            return {
                "name": season_name,
                "month": datetime.now().strftime("%B"),
                "crops": sorted(details["crops"]),
                "note": details["note"],
            }
    return {
        "name": "Mixed",
        "month": datetime.now().strftime("%B"),
        "crops": [],
        "note": "Mixed seasonal conditions are active.",
    }


def get_season_match(commodity, season):
    commodity_name = commodity.lower()
    for crop in season["crops"]:
        if crop in commodity_name or commodity_name in crop:
            return crop.title()
    return None


def parse_price(value):
    try:
        clean_value = re.sub(r"[^\d.]", "", str(value))
        return float(clean_value)
    except (TypeError, ValueError):
        return None


def strip_tags(value):
    return unescape(re.sub(r"<[^>]+>", " ", value)).strip()


def parse_retail_range(value):
    prices = [parse_price(part) for part in re.split(r"\s*-\s*", value)]
    prices = [price for price in prices if price is not None]
    if len(prices) >= 2:
        return prices[0], prices[1]
    if len(prices) == 1:
        return prices[0], prices[0]
    return None, None


def parse_public_price_page(html, state_name):
    date_match = re.search(r'data-current-date="([^"]+)"', html)
    latest_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    rows = re.findall(
        r'<tr class="todayVegetableTableRows"[^>]*>(.*?)</tr>',
        html,
        flags=re.DOTALL,
    )

    records = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.DOTALL)
        if len(cells) < 5:
            continue

        commodity = strip_tags(cells[1])
        wholesale_price = parse_price(strip_tags(cells[2]))
        retail_min, retail_max = parse_retail_range(strip_tags(cells[3]))
        unit = strip_tags(cells[4]).replace("1", "1 ")
        image_match = re.search(r'<img[^>]+src="([^"]+)"', cells[0])
        image_url = image_match.group(1) if image_match else ""
        if image_url.startswith("/"):
            image_url = f"https://www.vegetablemarketprice.com{image_url}"

        if not commodity or wholesale_price is None:
            continue

        records.append(
            {
                "commodity": commodity,
                "state": state_name,
                "current_price": wholesale_price,
                "min_price": retail_min or wholesale_price,
                "max_price": retail_max or wholesale_price,
                "unit": unit,
                "latest_date": latest_date,
                "image_url": image_url,
            }
        )

    return records


def fetch_public_price_records(state_slug="karnataka", state_name="Karnataka"):
    api_url = f"{PUBLIC_PRICE_BASE_URL}/{state_slug}/today"
    try:
        with urlopen(api_url, timeout=5) as response:
            html = response.read().decode("utf-8", errors="replace")
    except (URLError, TimeoutError, socket.timeout) as error:
        return {
            "records": [],
            "source": "VegetableMarketPrice.com public pages",
            "error": f"Could not load public prices for {state_name}: {error}",
        }

    records = parse_public_price_page(html, state_name)
    if not records:
        return {
            "records": [],
            "source": "VegetableMarketPrice.com public pages",
            "error": f"No public prices found for {state_name}.",
        }

    return {
        "records": records,
        "source": "VegetableMarketPrice.com public pages",
        "error": None,
    }


def fetch_all_india_public_prices():
    all_records = []
    errors = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_public_price_records, state_slug, state_name)
            for state_slug, state_name in PUBLIC_PRICE_STATES.items()
        ]
        for future in as_completed(futures):
            result = future.result()
            all_records.extend(result["records"])
            if result["error"]:
                errors.append(result["error"])

    return {
        "records": all_records,
        "source": "VegetableMarketPrice.com public pages",
        "error": "; ".join(errors) if not all_records and errors else None,
    }


def summarize_commodity_prices(records, max_items=30):
    grouped = {}
    for record in records:
        commodity = record.get("commodity")
        current_price = parse_price(record.get("current_price"))
        min_price = parse_price(record.get("min_price"))
        max_price = parse_price(record.get("max_price"))

        if not commodity or current_price is None:
            continue

        grouped.setdefault(
            commodity,
            {
                "commodity": commodity,
                "state": record.get("state", ""),
                "states": set(),
                "latest_dates": set(),
                "current_prices": [],
                "min_prices": [],
                "max_prices": [],
                "units": set(),
                "image_url": "",
            },
        )
        item = grouped[commodity]
        item["states"].add(record.get("state", ""))
        item["latest_dates"].add(record.get("latest_date", ""))
        item["current_prices"].append(current_price)
        item["units"].add(record.get("unit", "1 kg"))
        if record.get("image_url") and not item["image_url"]:
            item["image_url"] = record["image_url"]
        if min_price is not None:
            item["min_prices"].append(min_price)
        if max_price is not None:
            item["max_prices"].append(max_price)

    summaries = []
    for item in grouped.values():
        modal_average = round(mean(item["current_prices"]), 2)
        min_average = round(mean(item["min_prices"]), 2) if item["min_prices"] else modal_average
        max_average = round(mean(item["max_prices"]), 2) if item["max_prices"] else modal_average
        state_count = len([state for state in item["states"] if state])
        record_count = len(item["current_prices"])

        summaries.append(
            {
                "commodity": item["commodity"],
                "state": item["state"],
                "unit": sorted(item["units"])[0],
                "current_price": modal_average,
                "min_price": min_average,
                "max_price": max_average,
                "state_count": state_count,
                "record_count": record_count,
                "latest_date": sorted(item["latest_dates"])[-1] if item["latest_dates"] else "",
                "image_url": item["image_url"],
            }
        )

    summaries.sort(key=lambda item: item["record_count"], reverse=True)
    return summaries[:max_items]


def build_market_prediction(price_item, weather, season):
    rain_level = weather["rain_level"]
    temperature = weather["temperature"]
    current_price = price_item["current_price"]
    min_price = price_item["min_price"]
    max_price = price_item["max_price"]
    season_match = get_season_match(price_item["commodity"], season)

    rain_effects = {
        "low": -0.01,
        "normal": 0.0,
        "heavy": 0.08,
    }
    temp_effect = 0
    if temperature >= 34:
        temp_effect = 0.04
    elif temperature <= 18:
        temp_effect = 0.02

    weekly_movement = (
        0.015
        + rain_effects.get(rain_level, 0)
        + temp_effect
    )

    future = []
    predicted_price = current_price
    for week in range(1, 5):
        open_price = predicted_price
        predicted_price = predicted_price * (1 + weekly_movement)
        close_price = predicted_price
        spread = max((max_price - min_price) * (0.35 + week * 0.04), current_price * 0.04)
        future.append(
            {
                "label": f"Week {week}",
                "price": round(close_price, 2),
                "open": round(open_price, 2),
                "close": round(close_price, 2),
                "high": round(max(open_price, close_price) + spread / 2, 2),
                "low": round(max(0, min(open_price, close_price) - spread / 2), 2),
                "type": "future",
            }
        )

    past_candles = []
    estimated_close = current_price
    volatility = max(max_price - min_price, current_price * 0.08)
    for day in range(6, 0, -1):
        movement = ((day % 3) - 1) * 0.012 - weekly_movement / 5
        open_price = estimated_close / (1 + movement)
        close_price = estimated_close
        spread = volatility * (0.45 + day * 0.03)
        past_candles.insert(
            0,
            {
                "label": f"Past {day}",
                "open": round(open_price, 2),
                "close": round(close_price, 2),
                "high": round(max(open_price, close_price) + spread / 2, 2),
                "low": round(max(0, min(open_price, close_price) - spread / 2), 2),
                "type": "history",
            },
        )
        estimated_close = open_price

    current_candle = {
        "label": "Today",
        "open": round((min_price + current_price) / 2, 2),
        "close": round(current_price, 2),
        "high": round(max(max_price, min_price, current_price), 2),
        "low": round(min(max_price, min_price, current_price), 2),
        "type": "current",
    }
    chart_candles = past_candles + [current_candle] + future
    chart_low = min(candle["low"] for candle in chart_candles)
    chart_high = max(candle["high"] for candle in chart_candles)
    chart_range = chart_high - chart_low or 1

    for candle in chart_candles:
        high_offset = ((chart_high - candle["high"]) / chart_range) * 100
        low_offset = ((chart_high - candle["low"]) / chart_range) * 100
        open_offset = ((chart_high - candle["open"]) / chart_range) * 100
        close_offset = ((chart_high - candle["close"]) / chart_range) * 100
        body_top = min(open_offset, close_offset)
        body_bottom = max(open_offset, close_offset)
        candle["wick_top"] = round(high_offset, 2)
        candle["wick_height"] = round(max(low_offset - high_offset, 2), 2)
        candle["body_top"] = round(body_top, 2)
        candle["body_height"] = round(max(body_bottom - body_top, 3), 2)
        candle["trend"] = "up" if candle["close"] >= candle["open"] else "down"
        candle["volume_height"] = round(
            22 + (abs(candle["close"] - candle["open"]) / chart_range) * 160,
            2,
        )

    current_price_top = round(((chart_high - current_price) / chart_range) * 100, 2)
    chart_width = 620
    chart_height = 280
    plot_left = 34
    plot_right = 86
    plot_top = 26
    plot_bottom = 64
    plot_width = chart_width - plot_left - plot_right
    plot_height = chart_height - plot_top - plot_bottom
    candle_gap = plot_width / max(len(chart_candles) - 1, 1)
    candle_width = max(12, min(22, candle_gap * 0.48))

    def y_for_price(price):
        return plot_top + ((chart_high - price) / chart_range) * plot_height

    for index, candle in enumerate(chart_candles):
        x = plot_left + index * candle_gap
        open_y = y_for_price(candle["open"])
        close_y = y_for_price(candle["close"])
        high_y = y_for_price(candle["high"])
        low_y = y_for_price(candle["low"])
        body_y = min(open_y, close_y)
        body_height = max(abs(close_y - open_y), 3)
        volume_height = min(34, max(8, candle["volume_height"]))
        candle["svg"] = {
            "x": round(x, 2),
            "wick_y1": round(high_y, 2),
            "wick_y2": round(low_y, 2),
            "body_x": round(x - candle_width / 2, 2),
            "body_y": round(body_y, 2),
            "body_width": round(candle_width, 2),
            "body_height": round(body_height, 2),
            "volume_x": round(x - candle_width / 2, 2),
            "volume_y": round(chart_height - plot_bottom + 42 - volume_height, 2),
            "volume_height": round(volume_height, 2),
        }

    current_price_y = round(y_for_price(current_price), 2)
    price_ticks = [
        {"price": round(chart_high, 2), "y": round(y_for_price(chart_high), 2)},
        {"price": round((chart_high + current_price) / 2, 2), "y": round(y_for_price((chart_high + current_price) / 2), 2)},
        {"price": round(current_price, 2), "y": current_price_y},
        {"price": round((current_price + chart_low) / 2, 2), "y": round(y_for_price((current_price + chart_low) / 2), 2)},
        {"price": round(chart_low, 2), "y": round(y_for_price(chart_low), 2)},
    ]
    forecast_price = future[-1]["price"]
    forecast_change = abs(forecast_price - current_price)
    max_range = max(abs(max_price - current_price), 1)
    min_range = max(abs(current_price - min_price), 1)
    pie_values = [
        {"label": "Current", "value": max(current_price, 1), "class": "current"},
        {"label": "Min Gap", "value": min_range, "class": "min"},
        {"label": "Max Gap", "value": max_range, "class": "max"},
        {"label": "Forecast", "value": max(forecast_change, 1), "class": "forecast"},
    ]
    total_pie_value = sum(item["value"] for item in pie_values)
    start_angle = -90
    pie_slices = []

    for item in pie_values:
        sweep_angle = (item["value"] / total_pie_value) * 360
        end_angle = start_angle + sweep_angle
        large_arc = 1 if sweep_angle > 180 else 0
        start_radians = math.radians(start_angle)
        end_radians = math.radians(end_angle)
        radius = 78
        center = 100
        start_x = center + radius * math.cos(start_radians)
        start_y = center + radius * math.sin(start_radians)
        end_x = center + radius * math.cos(end_radians)
        end_y = center + radius * math.sin(end_radians)
        pie_slices.append(
            {
                "label": item["label"],
                "value": round(item["value"], 2),
                "percent": round((item["value"] / total_pie_value) * 100, 1),
                "class": item["class"],
                "path": (
                    f"M {center} {center} "
                    f"L {start_x:.2f} {start_y:.2f} "
                    f"A {radius} {radius} 0 {large_arc} 1 {end_x:.2f} {end_y:.2f} Z"
                ),
            }
        )
        start_angle = end_angle

    direction = "increase" if future[-1]["price"] >= current_price else "decrease"

    return {
        "commodity": price_item["commodity"],
        "unit": price_item["unit"],
        "current_price": current_price,
        "min_price": price_item["min_price"],
        "max_price": price_item["max_price"],
        "state_count": price_item["state_count"],
        "record_count": price_item["record_count"],
        "latest_date": price_item["latest_date"],
        "image_url": price_item.get("image_url", ""),
        "future": future,
        "chart_candles": chart_candles,
        "chart_high": round(chart_high, 2),
        "chart_low": round(chart_low, 2),
        "current_price_top": current_price_top,
        "current_price_y": current_price_y,
        "price_ticks": price_ticks,
        "chart_width": chart_width,
        "chart_height": chart_height,
        "plot_left": plot_left,
        "plot_top": plot_top,
        "plot_width": plot_width,
        "plot_height": plot_height,
        "pie_slices": pie_slices,
        "is_seasonal": bool(season_match),
        "season_match": season_match,
        "season_name": season["name"],
        "direction": direction,
        "rain_level": rain_level,
        "temperature": temperature,
    }


def build_all_predictions(price_items, weather, season):
    predictions = [
        build_market_prediction(price_item, weather, season)
        for price_item in price_items
    ]
    predictions.sort(
        key=lambda item: (
            not item["is_seasonal"],
            -item["record_count"],
            item["commodity"],
        )
    )
    return predictions


def ensure_database():
    users.create_index("email", unique=True)


def get_ai_settings():
    if AI_PROVIDER == "openrouter" and OPENROUTER_API_KEY:
        return {
            "api_key": OPENROUTER_API_KEY,
            "model": OPENROUTER_MODEL,
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "provider": "openrouter",
        }
    if AI_PROVIDER == "groq" and GROQ_API_KEY:
        return {
            "api_key": GROQ_API_KEY,
            "model": GROQ_MODEL,
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "provider": "groq",
        }
    return None


def ask_ai_assistant(question, language, context):
    settings = get_ai_settings()
    if not settings:
        return None

    language_name = "Kannada" if language == "kn" else "English"
    system_prompt = (
        "You are a helpful farmer market assistant. Answer briefly and clearly. "
        "Use only the provided dashboard context for crop prices and forecasts. "
        f"Reply in {language_name}. Do not invent live prices."
    )
    user_prompt = {
        "question": question,
        "dashboard_context": context,
    }
    payload = {
        "model": settings["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "temperature": 0.3,
        "max_tokens": 220,
    }
    headers = {
        "Authorization": f"Bearer {settings['api_key']}",
        "Content-Type": "application/json",
    }
    if settings["provider"] == "openrouter":
        headers["HTTP-Referer"] = "http://127.0.0.1:5002"
        headers["X-Title"] = "Farmer Market PF"

    try:
        api_request = Request(
            settings["url"],
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(api_request, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, URLError, TimeoutError, socket.timeout, json.JSONDecodeError):
        return None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_email" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "Customer")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        user = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password, method="pbkdf2:sha256"),
            "role": role,
        }

        try:
            ensure_database()
            users.insert_one(user)
        except DuplicateKeyError:
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("register"))
        except PyMongoError:
            flash("MongoDB is not running. Start MongoDB and try again.", "danger")
            return redirect(url_for("register"))

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            ensure_database()
            user = users.find_one({"email": email})
        except PyMongoError:
            flash("MongoDB is not running. Start MongoDB and try again.", "danger")
            return redirect(url_for("login"))

        if user and check_password_hash(user["password"], password):
            session["user_email"] = user["email"]
            session["user_name"] = user["name"]
            session["user_role"] = user.get("role", "Customer")
            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    weather = fetch_weather_signal()
    season = get_current_season()
    karnataka_result = fetch_public_price_records("karnataka", "Karnataka")
    india_result = fetch_all_india_public_prices()
    karnataka_prices = summarize_commodity_prices(karnataka_result["records"])
    india_prices = summarize_commodity_prices(india_result["records"])
    karnataka_predictions = build_all_predictions(karnataka_prices, weather, season)
    india_predictions = build_all_predictions(india_prices, weather, season)
    seasonal_predictions = [
        prediction for prediction in karnataka_predictions if prediction["is_seasonal"]
    ][:6]

    return render_template(
        "dashboard.html",
        name=session["user_name"],
        email=session["user_email"],
        role=session["user_role"],
        karnataka_predictions=karnataka_predictions,
        india_predictions=india_predictions,
        karnataka_error=karnataka_result["error"],
        india_error=india_result["error"],
        price_source=karnataka_result["source"],
        weather=weather,
        season=season,
        seasonal_predictions=seasonal_predictions,
    )


@app.route("/api/chatbot", methods=["POST"])
def chatbot_api():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    language = payload.get("language", "en")
    context = payload.get("context", {})

    if not question:
        return jsonify({"answer": "", "ai_used": False})

    answer = ask_ai_assistant(question, language, context)
    return jsonify(
        {
            "answer": answer or "",
            "ai_used": bool(answer),
            "provider": AI_PROVIDER if answer else "",
        }
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("landing"))


if __name__ == "__main__":
    app.run(debug=True, port=5002)
