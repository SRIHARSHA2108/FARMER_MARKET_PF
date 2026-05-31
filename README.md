# Farmer Market Flask App

Simple Flask app with landing, register, login, and dashboard pages using local MongoDB.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start MongoDB locally:

```bash
mongod
```

Run the Flask app:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5002
```

The app stores users in:

```text
Database: farmer_market_db
Collection: users
```

## Automatic Crop Forecasts

The dashboard automatically shows Karnataka and all-India vegetable price
forecasts. Prices are loaded from public VegetableMarketPrice.com pages without
a government API key. Weather is loaded from the free Open-Meteo API.

Optional farm location settings:

```bash
export FARM_LATITUDE=12.9716
export FARM_LONGITUDE=77.5946
python app.py
```
