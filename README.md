# Farmer Market PF

Farmer Market PF is a Flask-based farmer market web application that helps farmers view live vegetable prices, seasonal crop suggestions, weather-based price forecasts, and market insights in English and Kannada.

## Project Concept

The project is designed for farmers who need simple market guidance before selling crops. It collects public vegetable price data, shows Karnataka and all-India price information, highlights seasonal crops, and gives a simple forecast view based on current market price and weather conditions.

The application also includes Kannada translation and voice assistance for farmers who may prefer listening instead of reading.

## Technologies Used

- **Python**: Backend programming language
- **Flask**: Web framework for routes, templates, sessions, login, and dashboard
- **MongoDB**: Local database for storing registered users
- **PyMongo**: Python connector for MongoDB
- **HTML5**: Page structure
- **CSS3**: Responsive layout, dashboard styling, cards, charts, and visual design
- **JavaScript**: Language switching, voice assistance, and browser interaction
- **Web Speech API**: Browser-based text-to-speech for English and Kannada
- **Speech Recognition API**: Browser-based voice commands for search and chatbot questions
- **Groq / OpenRouter APIs**: Optional AI chatbot backend
- **Open-Meteo API**: Weather data for forecast signals
- **VegetableMarketPrice public pages**: Public vegetable price source used for live price scraping
- **Werkzeug Security**: Password hashing and verification

## Main Features

- Landing page
- Farmer registration page
- Login page
- Secure password hashing
- Session-based dashboard access
- Local MongoDB user storage
- Karnataka live vegetable price dashboard
- All-India vegetable price average dashboard
- Seasonal crop detection
- Hardcoded season override option
- Weather-based crop price forecast
- Pie chart price visualizations
- Crop images from live public price pages
- English and Kannada language support
- Dynamic vegetable name translation to Kannada
- Voice assistant for farmers
- Stop voice button
- Floating chatbot
- Voice-command chatbot
- Optional AI chatbot using Groq or OpenRouter
- Responsive UI for desktop and mobile

## Project Structure

```text
farmer_market_pf/
├── app.py
├── requirements.txt
├── README.md
├── static/
│   ├── app.js
│   ├── language_en.js
│   ├── language_kn.js
│   └── style.css
└── templates/
    ├── base.html
    ├── landing.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    └── partials/
        └── crop_card.html
```

## Database

The app uses local MongoDB.

```text
Database: farmer_market_db
Collection: users
```

User data stored:

- Name
- Email
- Hashed password
- Role

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
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

Open in browser:

```text
http://127.0.0.1:5002
```

## Optional Weather Location

By default, the app uses Bengaluru coordinates for weather.

You can change the farm location:

```bash
export FARM_LATITUDE=12.9716
export FARM_LONGITUDE=77.5946
python app.py
```

## Optional AI Chatbot

The chatbot works locally from dashboard data even without an AI key. You can optionally enable Groq or OpenRouter for smarter chatbot answers.

Groq:

```bash
export AI_PROVIDER=groq
export GROQ_API_KEY=your_groq_api_key
export GROQ_MODEL=llama-3.1-8b-instant
python app.py
```

OpenRouter:

```bash
export AI_PROVIDER=openrouter
export OPENROUTER_API_KEY=your_openrouter_api_key
export OPENROUTER_MODEL=openai/gpt-4o-mini
python app.py
```

## Season Override

The app can automatically detect the season by month. You can also force a season in `app.py`:

```python
SEASON_OVERRIDE = "Summer"
```

Supported values:

```text
Summer
Monsoon
Winter
```

Keep it empty for automatic detection:

```python
SEASON_OVERRIDE = ""
```

## Author

**SRIHARSHA N**

GitHub: [SRIHARSHA2108](https://github.com/SRIHARSHA2108)

## Author Contributions

- Designed and developed the Flask web application
- Built landing, register, login, and dashboard pages
- Integrated MongoDB for user registration and login
- Added live public vegetable price scraping
- Added Karnataka and all-India market views
- Implemented weather-based price forecasting
- Added seasonal crop recommendation logic
- Designed responsive dashboard UI
- Added crop images, visual cards, and pie charts
- Added English and Kannada translation modules
- Added browser-based voice assistance for farmers
- Added floating voice-command chatbot

## Notes

This project uses public vegetable price pages for live price data. If the source website changes its HTML structure, the scraper may need updates.

This app is built for educational and project demonstration purposes.
