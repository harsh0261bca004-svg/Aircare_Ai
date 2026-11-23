import os
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

POLLUTANTS = {
    "pm2_5": ("PM2.5", "μg/m³"),
    "pm10": ("PM10", "μg/m³"),
    "carbon_monoxide": ("Carbon monoxide", "μg/m³"),
    "nitrogen_dioxide": ("Nitrogen dioxide", "μg/m³"),
    "sulphur_dioxide": ("Sulphur dioxide", "μg/m³"),
    "ozone": ("Ozone", "μg/m³"),
}

def aqi_label(value):
    if value is None:
        return {"label": "Unavailable", "level": "unknown", "advice": "Air-quality index is not available."}
    value = float(value)
    if value <= 50:
        return {"label": "Good", "level": "good", "advice": "Air quality is satisfactory for most people."}
    if value <= 100:
        return {"label": "Moderate", "level": "moderate", "advice": "Most people can continue normal activities. Sensitive people should monitor symptoms."}
    if value <= 150:
        return {"label": "Unhealthy for sensitive groups", "level": "sensitive", "advice": "Children and people with respiratory or heart conditions should reduce prolonged outdoor exertion."}
    if value <= 200:
        return {"label": "Unhealthy", "level": "unhealthy", "advice": "Consider reducing prolonged or heavy outdoor activity."}
    if value <= 300:
        return {"label": "Very unhealthy", "level": "very-unhealthy", "advice": "Avoid strenuous outdoor activity and follow local public-health guidance."}
    return {"label": "Hazardous", "level": "hazardous", "advice": "Avoid outdoor exertion where possible and follow official local advisories."}

def get_json(url, params):
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()

def find_city(name):
    data = get_json(GEOCODING_URL, {"name": name, "count": 1, "language": "en", "format": "json"})
    results = data.get("results") or []
    if not results:
        raise ValueError(f"Couldn't find '{name}'. Try another city name.")
    return results[0]

def fetch_air_quality(city):
    params = {
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "current": ",".join(POLLUTANTS.keys()) + ",us_aqi",
        "hourly": "us_aqi,pm2_5,pm10",
        "forecast_days": 1,
        "timezone": "auto"
    }
    data = get_json(AIR_QUALITY_URL, params)
    current = data.get("current", {})
    us_aqi = current.get("us_aqi")
    pollutants = []
    for key, (label, unit) in POLLUTANTS.items():
        val = current.get(key)
        pollutants.append({"key": key, "name": label, "value": val, "unit": unit})
    hourly = data.get("hourly", {})
    chart = []
    times = hourly.get("time", [])
    aqi_values = hourly.get("us_aqi", [])
    for t, val in list(zip(times, aqi_values))[:24]:
        chart.append({"time": t[11:16], "aqi": val})
    return {
        "city": city.get("name"),
        "region": city.get("admin1", ""),
        "country": city.get("country", ""),
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "timezone": data.get("timezone", ""),
        "updated": current.get("time", "Not available"),
        "aqi": us_aqi,
        "status": aqi_label(us_aqi),
        "pollutants": pollutants,
        "chart": chart,
        "source": "Open-Meteo Air Quality API"
    }

def local_assistant(question, city_data=None):
    q = question.lower()
    if city_data:
        status = city_data["status"]["label"]
        aqi = city_data["aqi"]
        city = city_data["city"]
    else:
        status, aqi, city = "unknown", None, "your area"

    if any(word in q for word in ["pm2.5", "pm 2.5", "fine particle"]):
        answer = "PM2.5 means very small airborne particles that can travel deep into the lungs. Check the PM2.5 reading on the dashboard and follow local health advisories."
    elif any(word in q for word in ["pm10", "pm 10"]):
        answer = "PM10 refers to inhalable particles such as dust and pollen. Its level is shown in the pollutant readings."
    elif any(word in q for word in ["good", "safe", "go outside", "outdoor", "exercise"]):
        answer = f"For {city}, the current US AQI is {aqi if aqi is not None else 'unavailable'} ({status}). {city_data['status']['advice'] if city_data else 'Search for a city to see current air quality.'}"
    elif any(word in q for word in ["protect", "precaution", "health", "mask"]):
        answer = "Check the latest local AQI before outdoor activity. On polluted days, reduce prolonged strenuous outdoor exertion, keep indoor spaces well ventilated when outdoor air is cleaner, and follow advice from local health authorities. People with health concerns should follow their clinician's guidance."
    elif any(word in q for word in ["aqi", "index", "meaning"]):
        answer = "AQI is an index used to communicate air pollution levels. Lower values generally indicate cleaner air; higher values indicate greater pollution. This dashboard uses the US AQI scale."
    else:
        answer = f"I can help explain AQI, PM2.5, PM10 and general precautions. {('The current reading for ' + city + ' is ' + str(aqi) + ' (' + status + ').') if aqi is not None else 'Search for a city to load its latest readings first.'}"
    return answer

def gemini_answer(question, city_data=None):
    if not GEMINI_API_KEY:
        return local_assistant(question, city_data), "Built-in assistant (Gemini API key not configured)"
    context = "No city data loaded."
    if city_data:
        context = f"City: {city_data['city']}, US AQI: {city_data['aqi']}, category: {city_data['status']['label']}, pollutants: " + ", ".join(
            f"{p['name']}={p['value']} {p['unit']}" for p in city_data["pollutants"] if p["value"] is not None
        )
    prompt = (
        "You are AirCare AI, an educational air-quality information assistant. "
        "Answer in clear, concise language. Do not diagnose or claim to provide medical advice. "
        "Encourage users to follow official local health guidance. "
        f"Current dashboard context: {context}\nUser question: {question}"
    )
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        response = requests.post(
            url, params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.4, "maxOutputTokens": 350}},
            timeout=20
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload["candidates"][0]["content"]["parts"][0]["text"]
        return answer, "Google Gemini 2.5 Flash"
    except Exception:
        return local_assistant(question, city_data), "Built-in assistant (Gemini temporarily unavailable)"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/air-quality")
def air_quality():
    city_name = request.args.get("city", "New Delhi").strip()
    if not city_name:
        return jsonify({"error": "Please enter a city name."}), 400
    try:
        city = find_city(city_name)
        return jsonify(fetch_air_quality(city))
    except requests.RequestException:
        return jsonify({"error": "The air-quality service is temporarily unavailable. Please try again."}), 502
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except (KeyError, TypeError):
        return jsonify({"error": "The service returned incomplete air-quality data. Please try again."}), 502

@app.route("/api/compare")
def compare():
    names = [x.strip() for x in request.args.get("cities", "").split(",") if x.strip()]
    if len(names) < 2 or len(names) > 4:
        return jsonify({"error": "Enter between 2 and 4 city names."}), 400
    results = []
    try:
        for name in names:
            results.append(fetch_air_quality(find_city(name)))
        return jsonify({"cities": results})
    except Exception as exc:
        return jsonify({"error": str(exc) if isinstance(exc, ValueError) else "Could not compare cities right now."}), 502

@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(silent=True) or {}
    question = (body.get("message") or "").strip()
    city_data = body.get("city_data")
    if not question:
        return jsonify({"error": "Please type a question."}), 400
    if len(question) > 700:
        return jsonify({"error": "Please keep your question under 700 characters."}), 400
    answer, provider = gemini_answer(question, city_data)
    return jsonify({"answer": answer, "provider": provider})

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
