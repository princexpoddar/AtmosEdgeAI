from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.core.database import Ward, Advisory, Reading, Station, StationReading
from backend.app.services.enforcement.station_profiles import get_station_profile

def get_aqi_category(pm25: float) -> str:
    """
    Returns the CPCB air quality category index for a given PM2.5 concentration.
    """
    if pm25 <= 30:
        return "Good"
    elif pm25 <= 60:
        return "Satisfactory"
    elif pm25 <= 90:
        return "Moderate"
    elif pm25 <= 120:
        return "Poor"
    elif pm25 <= 250:
        return "Very Poor"
    else:
        return "Severe"


REGIONAL_TEMPLATES: Dict[str, Dict[str, str]] = {
    "kn": {  # Kannada (Bengaluru)
        "Good": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಉತ್ತಮವಾಗಿದೆ (Good). ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳಿಗೆ ಸುರಕ್ಷಿತವಾಗಿದೆ.",
        "Satisfactory": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ತೃಪ್ತಿಕರವಾಗಿದೆ (Satisfactory).",
        "Moderate": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಮಧ್ಯಮವಾಗಿದೆ (Moderate). ಶಾಲಾ ಮಕ್ಕಳು ಮತ್ತು ಹಿರಿಯ ನಾಗರಿಕರು ದೀರ್ಘಕಾಲದ ಹೊರಾಂಗಣ ಮಾನ್ಯತೆಯನ್ನು ಮಿತಿಗೊಳಿಸಿ.",
        "Poor": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಕಳಪೆಯಾಗಿದೆ (Poor). ಹೊರಾಂಗಣದಲ್ಲಿ N95 ಮಾಸ್ಕ್ ಧರಿಸಲು ಸಲಹೆ ನೀಡಲಾಗಿದೆ.",
        "Very Poor": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಅತ್ಯಂತ ಕಳಪೆಯಾಗಿದೆ (Very Poor). ತುರ್ತು ಹೊರತುಪಡಿಸಿ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ತಪ್ಪಿಸಿ.",
        "Severe": "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಗಂಭೀರವಾಗಿದೆ (Severe). ಸಾರ್ವಜನಿಕ ಆರೋಗ್ಯ ತುರ್ತುಸ್ಥಿತಿ ಘೋಷಿಸಲಾಗಿದೆ."
    },
    "ta": {  # Tamil (Chennai)
        "Good": "காற்றின் தரம் மிகவும் நன்று (Good). வெளிப்புற நடவடிக்கைகளுக்கு பாதுகாப்பானது.",
        "Satisfactory": "காற்றின் தரம் திருப்திகரமாக உள்ளது (Satisfactory).",
        "Moderate": "காற்றின் தரம் மிதமான நிலையில் உள்ளது (Moderate). முதியவர்கள் மற்றும் குழந்தைகள் கவனமாக இருக்கவும்.",
        "Poor": "காற்றின் தரம் மோசமாக உள்ளது (Poor). வெளியே செல்லும்போது N95 முகக்கவசம் அணியவும்.",
        "Very Poor": "காற்றின் தரம் மிகவும் மோசமாக உள்ளது (Very Poor). தேவையற்ற வெளிப்புற பயணங்களை தவிர்க்கவும்.",
        "Severe": "காற்றின் தரம் மிகவும் ஆபத்தான நிலையில் உள்ளது (Severe). சுகாதார எச்சரிக்கை விடுக்கப்பட்டுள்ளது."
    },
    "mr": {  # Marathi (Mumbai)
        "Good": "हवेची गुणवत्ता उत्तम आहे (Good). बाहेर फिरण्यासाठी सुरक्षित.",
        "Satisfactory": "हवेची गुणवत्ता समाधानकारक आहे (Satisfactory).",
        "Moderate": "हवेची गुणवत्ता मध्यम आहे (Moderate). लहान मुले आणि ज्येष्ठांनी काळजी घ्यावी.",
        "Poor": "हवेची गुणवत्ता वाईट आहे (Poor). बाहेर पडताना N95 मास्क वापरा.",
        "Very Poor": "हवेची गुणवत्ता अत्यंत वाईट आहे (Very Poor). बाहेरील व्यायाम टाळा.",
        "Severe": "हवेची गुणवत्ता गंभीर आहे (Severe). आरोग्य आणीबाणी इशारा जारी."
    },
    "bn": {  # Bengali (Kolkata)
        "Good": "বাতাসের গুণমান ভালো (Good)। বাইরের কাজকর্মের জন্য নিরাপদ।",
        "Satisfactory": "বাতাসের গুণমান সন্তোষজনক (Satisfactory)।",
        "Moderate": "বাতাসের গুণমান মাঝারি (Moderate)। শিশু ও প্রবীণদের দীর্ঘক্ষণ বাইরে থাকা এড়িয়ে চলা উচিত।",
        "Poor": "বাতাসের গুণমান খারাপ (Poor)। বাইরে বের হলে N95 মাস্ক ব্যবহার করুন।",
        "Very Poor": "বাতাসের গুণমান খুব খারাপ (Very Poor)। বাইরের শারীরিক ব্যায়াম বন্ধ রাখুন।",
        "Severe": "বাতাসের গুণমান আশঙ্কাজনক (Severe)। জরুরি স্বাস্থ্য সতর্কতা জারি।"
    },
    "hi": {  # Hindi (Delhi / UP / MP / Rajasthan / Punjab)
        "Good": "वायु गुणवत्ता अच्छी है (Good)। बाहरी गतिविधियों के लिए पूरी तरह सुरक्षित।",
        "Satisfactory": "वायु गुणवत्ता संतोषजनक है (Satisfactory)।",
        "Moderate": "वायु गुणवत्ता मध्यम है (Moderate)। स्कूली बच्चों और बुजुर्गों को सावधानी बरतनी चाहिए।",
        "Poor": "वायु गुणवत्ता खराब है (Poor)। बाहर निकलने पर N95 मास्क पहनें।",
        "Very Poor": "वायु गुणवत्ता बहुत खराब है (Very Poor)। बाहरी व्यायाम से बचें।",
        "Severe": "वायु गुणवत्ता गंभीर है (Severe)। आपातकालीन स्वास्थ्य सलाह लागू।"
    },
    "en": {  # English
        "Good": "Air quality is Good. Safe for all outdoor activities.",
        "Satisfactory": "Air quality is Satisfactory. Acceptable for general public.",
        "Moderate": "Air quality is Moderate. Sensitive receptors (schools & hospitals) should limit outdoor exposure.",
        "Poor": "Air quality is Poor. N95 masks recommended for outdoor commuters.",
        "Very Poor": "Air quality is Very Poor. Avoid strenuous outdoor physical exercise.",
        "Severe": "Air quality is Severe. Public health emergency advisory active."
    }
}


def generate_regional_advisory(station_id: str, lang: str = None, db: Session = None) -> Dict[str, Any]:
    """
    Generates ward/station level multi-lingual health advisories mapping population vulnerability
    (schools, hospitals, outdoor workers) against forecast AQI in regional languages.
    """
    s_id = str(station_id)
    station = db.query(Station).filter(Station.id == s_id).first() if db else None
    
    if not station:
        station_name = f"Station {s_id}"
        city = "Delhi"
        state = "Delhi"
        pm25 = 75.0
        no2 = 30.0
    else:
        station_name = station.name
        city = station.city or "Delhi"
        state = station.state or "Delhi"
        latest = (
            db.query(StationReading)
            .filter(StationReading.station_id == s_id, StationReading.pm25 != None)
            .order_by(StationReading.timestamp.desc())
            .first()
        )
        pm25 = latest.pm25 if (latest and latest.pm25 is not None) else 75.0
        no2  = latest.no2  if (latest and latest.no2  is not None) else 30.0

    category = get_aqi_category(pm25)
    profile = get_station_profile(s_id, station_name, city, state)
    
    selected_lang = lang or profile.get("native_lang", "hi")
    if selected_lang not in REGIONAL_TEMPLATES:
        selected_lang = "en"

    template = REGIONAL_TEMPLATES.get(selected_lang, REGIONAL_TEMPLATES["en"])
    regional_msg = template.get(category, template["Moderate"])
    english_msg = REGIONAL_TEMPLATES["en"].get(category, REGIONAL_TEMPLATES["en"]["Moderate"])

    receptors = profile.get("receptors", {})
    schools = receptors.get("schools", 10)
    hospitals = receptors.get("hospitals", 3)

    return {
        "station_id": s_id,
        "station_name": station_name,
        "city": city,
        "state": state,
        "category": category,
        "pm25": round(pm25, 1),
        "no2": round(no2, 1),
        "language": selected_lang,
        "advisory_message_regional": regional_msg,
        "advisory_message_english": english_msg,
        "sensitive_receptors_summary": f"{schools} schools and {hospitals} hospitals located within 2km catchment of {station_name}.",
        "vulnerability_level": receptors.get("vulnerability_level", "Medium"),
        "spcb_authority": profile.get("spcb_authority", "SPCB")
    }


def generate_chat_response(query: str, ward_id: int, db: Session, gemini_api_key: str = None) -> str:
    """
    Chatbot assistant that answers citizen queries based on real-time ward data.
    If gemini_api_key is provided, uses Gemini; otherwise falls back to rule-based responses.
    """
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    latest = db.query(Reading).filter(Reading.ward_id == ward_id).order_by(Reading.timestamp.desc()).first()
    
    if not ward or not latest:
        return "Hello! I do not have enough air quality data to provide recommendations for this ward at this moment."
        
    pm25 = latest.pm25
    category = get_aqi_category(pm25)
    
    if gemini_api_key:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
        headers = {"Content-Type": "application/json"}
        prompt = (
            f"You are AtmosEdgeAI, an intelligent air quality health assistant.\n"
            f"User is asking: '{query}'\n"
            f"Here is the real-time air quality data for their location ({ward.name}):\n"
            f"- PM2.5: {pm25} ug/m3 (CPCB Category: {category})\n"
            f"- NO2: {latest.no2} ug/m3\n"
            f"- Temperature: {latest.temp} °C\n"
            f"- Humidity: {latest.humidity} %\n"
            f"- Wind Speed: {latest.wind_speed} km/h\n"
            f"- Atmospheric Stagnation: {latest.stagnation} (scale 0-1, high means pollution is trapped)\n\n"
            f"Please write a concise, friendly, and helpful response directly addressing their question. "
            f"Give practical safety/health recommendations (like whether they should wear a mask, do outdoor exercise, protect children, etc.) based on these conditions."
        )
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code == 200:
                res_data = r.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            else:
                print(f"[Gemini API Error] Status: {r.status_code}, Response: {r.text}")
        except Exception as e:
            print(f"[Gemini Exception] {e}")

    query_lower = query.lower()
    
    if "mask" in query_lower or "wear" in query_lower or "protect" in query_lower:
        if pm25 > 90:
            return f"The current PM2.5 level in {ward.name} is {pm25} ug/m3 ({category}). It is highly recommended to wear an N95 mask if you go outdoors to protect yourself."
        else:
            return f"The air quality in {ward.name} is currently {category} (PM2.5: {pm25} ug/m3). General population does not need masks, but sensitive individuals should monitor conditions."
            
    elif "exercise" in query_lower or "run" in query_lower or "outside" in query_lower or "outdoor" in query_lower:
        if pm25 > 90:
            return f"With PM2.5 levels at {pm25} ug/m3 ({category}) in {ward.name}, outdoor physical activities and running should be avoided. Exercise indoors instead."
        else:
            return f"Outdoor conditions in {ward.name} are {category} (PM2.5: {pm25} ug/m3). It is safe to perform outdoor sports and exercise."
            
    elif "children" in query_lower or "kid" in query_lower or "elderly" in query_lower or "asthma" in query_lower:
        if pm25 > 60:
            return f"Caution: The air quality in {ward.name} is {category} (PM2.5: {pm25} ug/m3). Children, the elderly, and asthmatics should limit prolonged outdoor exposure."
        else:
            return f"The air quality in {ward.name} is {category} (PM2.5: {pm25} ug/m3), which is safe for children and senior citizens."
            
    else:
        return f"Hello! The current air quality in {ward.name} is {category} (PM2.5 level: {pm25} ug/m3, Temperature: {latest.temp}C, Humidity: {latest.humidity}%). Let me know if you need specific advice on mask usage, outdoor exercise, or health precautions."


def generate_ward_advisories(db: Session):
    """
    Analyzes latest readings and generates health advice advisories for all wards.
    """
    wards = db.query(Ward).all()
    for w in wards:
        latest = db.query(Reading).filter(Reading.ward_id == w.id).order_by(Reading.timestamp.desc()).first()
        if not latest:
            continue
            
        pm25 = latest.pm25
        category = get_aqi_category(pm25)
        
        exists = db.query(Advisory).filter(
            Advisory.ward_id == w.id,
            Advisory.level == category
        ).first()
        
        if not exists:
            message_en = f"Air quality in {w.name} is {category}. PM2.5 is {pm25} ug/m3."
            message_hi = f"{w.name} में हवा की गुणवत्ता {category} है। PM2.5 का स्तर {pm25} है।"
            message_local = message_en
            
            adv = Advisory(
                ward_id=w.id,
                timestamp=datetime.utcnow(),
                level=category,
                message_en=message_en,
                message_hi=message_hi,
                message_local=message_local
            )
            db.add(adv)
    db.commit()
