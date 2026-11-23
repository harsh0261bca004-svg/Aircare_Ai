# AirCare AI — Urban Air Quality Assistant

A responsive Flask web app for exploring current air-quality readings, pollutant concentrations, hourly AQI forecasts, city comparisons and an AI assistant.

## Features
- Search for cities worldwide (including Indian cities such as Meerut, Delhi, Mumbai and Lucknow).
- Current US AQI and category-based general guidance.
- PM2.5, PM10, CO, NO₂, SO₂ and O₃ readings.
- Hourly AQI trend chart.
- Compare 2–4 cities.
- Air-quality Q&A assistant with optional Google Gemini integration.
- Responsive dashboard for desktop and mobile.

## Data and AI
- **Air-quality data:** Open-Meteo Geocoding API and Open-Meteo Air Quality API.
- **Generative AI:** Optional Google Gemini 2.5 Flash API integration. If `GEMINI_API_KEY` is not configured, a built-in rule-based assistant responds instead. Do not claim Gemini was actively used in a demo unless a valid key is configured and the Gemini provider is shown in the chat header.
- The dashboard uses the **US AQI** field supplied by Open-Meteo. AQI scales differ by country; do not interpret this as India's CPCB AQI.

## Run locally
1. Install Python 3.10 or newer.
2. Extract this folder and open a terminal inside it.
3. Create and activate a virtual environment:
   - Windows: `python -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`.
6. Optional: add your Google Gemini API key to `.env` as `GEMINI_API_KEY=your_key`.
7. Start: `python app.py`
8. Open `http://127.0.0.1:5000`.

Internet access is required for live city and air-quality data. If the external API is unavailable, the app displays an error rather than inventing readings.

## Deploy
### Render
1. Push the project to a **public GitHub repository**.
2. Create a new Web Service on Render and connect the repository.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add `GEMINI_API_KEY` as an environment variable only if you have a key and want Gemini enabled.
6. Deploy and open the generated HTTPS URL.

Never commit `.env` or expose API keys in frontend JavaScript, GitHub, screenshots or demo videos.

## Suggested public repository structure
```
AirCare_AI/
├── app.py
├── templates/index.html
├── static/css/style.css
├── static/js/app.js
├── requirements.txt
├── .env.example
├── .gitignore
├── Procfile
└── README.md
```

## Testing checklist
- [ ] Search for Meerut and another city.
- [ ] Confirm AQI and pollutant readings load.
- [ ] Confirm chart renders.
- [ ] Compare 2–4 cities.
- [ ] Ask the assistant a question.
- [ ] Test on a phone-sized screen.
- [ ] Confirm errors are shown when a city cannot be found or the API is unavailable.
- [ ] If using Gemini, verify the provider label says Google Gemini 2.5 Flash.

## Important note
This is an educational awareness project, not a medical device or official government monitoring service. Data may be delayed or unavailable. Follow official local advisories for health decisions.
