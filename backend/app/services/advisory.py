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


LANG_MAP = {
    "kn": ("Kannada", "Use Kannada script (ಕನ್ನಡ ಲಿಪಿ)"),
    "ta": ("Tamil", "Use Tamil script (தமிழ் எழுத்துகள்)"),
    "hi": ("Hindi", "Use Devanagari Hindi script (हिंदी देवनागरी लिपि)"),
    "mr": ("Marathi", "Use Devanagari Marathi script (मराठी देवनागरी लिपि)"),
    "bn": ("Bengali", "Use Bengali script (বাংলা হরফ)"),
    "en": ("English", "Use English language"),
}

# ── Multi-Lingual Fallback Templates ──────────────────────────────────────
# Used when Gemini API is unavailable (rate-limit, key revoked, network down)

FALLBACK_TEMPLATES = {
    "outdoor": {
        "en": "With PM2.5 at {pm25:.1f} µg/m³ ({category}) near {station}, outdoor exercise should be {advice}. {mask_note} Children, elderly, and asthma patients should {vulnerable_advice}.",
        "hi": "{station} के पास PM2.5 {pm25:.1f} µg/m³ ({category}) है। बाहरी व्यायाम {advice_hi}। {mask_hi} बच्चों, बुज़ुर्गों और अस्थमा रोगियों को {vulnerable_hi}।",
        "kn": "{station} ಬಳಿ PM2.5 {pm25:.1f} µg/m³ ({category}) ಇದೆ. ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ {advice_kn}. {mask_kn} ಮಕ್ಕಳು, ವೃದ್ಧರು ಮತ್ತು ಆಸ್ತಮಾ ರೋಗಿಗಳು {vulnerable_kn}.",
        "ta": "{station} அருகே PM2.5 {pm25:.1f} µg/m³ ({category}) உள்ளது. வெளிப்புற உடற்பயிற்சி {advice_ta}. {mask_ta} குழந்தைகள், முதியோர் மற்றும் ஆஸ்துமா நோயாளிகள் {vulnerable_ta}.",
        "mr": "{station} जवळ PM2.5 {pm25:.1f} µg/m³ ({category}) आहे. बाहेरील व्यायाम {advice_mr}. {mask_mr} लहान मुले, ज्येष्ठ नागरिक आणि दमा रुग्णांनी {vulnerable_mr}.",
        "bn": "{station} এর কাছে PM2.5 {pm25:.1f} µg/m³ ({category}) আছে। বাইরের ব্যায়াম {advice_bn}। {mask_bn} শিশু, বয়স্ক এবং হাঁপানি রোগীদের {vulnerable_bn}।",
    },
    "mask": {
        "en": "Current PM2.5 is {pm25:.1f} µg/m³ ({category}) at {station}. {mask_recommendation} Especially important near {hotspots}.",
        "hi": "{station} पर PM2.5 {pm25:.1f} µg/m³ ({category}) है। {mask_hi} विशेषकर {hotspots} के पास।",
        "kn": "{station} ನಲ್ಲಿ PM2.5 {pm25:.1f} µg/m³ ({category}) ಇದೆ. {mask_kn} ವಿಶೇಷವಾಗಿ {hotspots} ಬಳಿ.",
        "ta": "{station} இல் PM2.5 {pm25:.1f} µg/m³ ({category}) உள்ளது. {mask_ta} குறிப்பாக {hotspots} அருகே.",
        "mr": "{station} येथे PM2.5 {pm25:.1f} µg/m³ ({category}) आहे. {mask_mr} विशेषत: {hotspots} जवळ.",
        "bn": "{station} এ PM2.5 {pm25:.1f} µg/m³ ({category}) আছে। {mask_bn} বিশেষত {hotspots} এর কাছে।",
    },
    "children": {
        "en": "Air quality near {station} is {category} (PM2.5: {pm25:.1f} µg/m³). {children_advice} There are {schools} schools and {hospitals} hospitals within 2km. {precaution}",
        "hi": "{station} के पास वायु गुणवत्ता {category} (PM2.5: {pm25:.1f} µg/m³) है। {children_hi} 2 किमी के भीतर {schools} स्कूल और {hospitals} अस्पताल हैं। {precaution_hi}",
        "kn": "{station} ಬಳಿ ವಾಯು ಗುಣಮಟ್ಟ {category} (PM2.5: {pm25:.1f} µg/m³) ಇದೆ. {children_kn} 2 ಕಿಮೀ ಒಳಗೆ {schools} ಶಾಲೆಗಳು ಮತ್ತು {hospitals} ಆಸ್ಪತ್ರೆಗಳಿವೆ. {precaution_kn}",
        "ta": "{station} அருகே காற்றின் தரம் {category} (PM2.5: {pm25:.1f} µg/m³) உள்ளது. {children_ta} 2 கிமீ சுற்றளவில் {schools} பள்ளிகள் மற்றும் {hospitals} மருத்துவமனைகள் உள்ளன. {precaution_ta}",
        "mr": "{station} जवळ हवेची गुणवत्ता {category} (PM2.5: {pm25:.1f} µg/m³) आहे. {children_mr} 2 किमी परिसरात {schools} शाळा आणि {hospitals} रुग्णालये आहेत. {precaution_mr}",
        "bn": "{station} এর কাছে বাতাসের মান {category} (PM2.5: {pm25:.1f} µg/m³)। {children_bn} 2 কিমির মধ্যে {schools}টি স্কুল এবং {hospitals}টি হাসপাতাল আছে। {precaution_bn}",
    },
    "general": {
        "en": "Air quality near {station} ({city}) is currently {category}. PM2.5: {pm25:.1f} µg/m³, NO2: {no2:.1f} µg/m³. {general_advice} {schools} schools and {hospitals} hospitals are within the 2km catchment ({vulnerability} vulnerability). Stay updated with real-time monitoring.",
        "hi": "{station} ({city}) के पास वायु गुणवत्ता {category} है। PM2.5: {pm25:.1f} µg/m³, NO2: {no2:.1f} µg/m³। {general_hi} 2 किमी दायरे में {schools} स्कूल और {hospitals} अस्पताल हैं ({vulnerability} जोखिम)। वास्तविक समय निगरानी के साथ अपडेट रहें।",
        "kn": "{station} ({city}) ಬಳಿ ವಾಯು ಗುಣಮಟ್ಟ {category} ಇದೆ. PM2.5: {pm25:.1f} µg/m³, NO2: {no2:.1f} µg/m³. {general_kn} 2 ಕಿಮೀ ವ್ಯಾಪ್ತಿಯಲ್ಲಿ {schools} ಶಾಲೆಗಳು ಮತ್ತು {hospitals} ಆಸ್ಪತ್ರೆಗಳಿವೆ ({vulnerability} ಅಪಾಯ). ನೈಜ-ಸಮಯದ ಮೇಲ್ವಿಚಾರಣೆಯೊಂದಿಗೆ ನವೀಕೃತವಾಗಿರಿ.",
        "ta": "{station} ({city}) அருகே காற்றின் தரம் {category} உள்ளது. PM2.5: {pm25:.1f} µg/m³, NO2: {no2:.1f} µg/m³. {general_ta} 2 கிமீ சுற்றளவில் {schools} பள்ளிகள் மற்றும் {hospitals} மருத்துவமனைகள் உள்ளன ({vulnerability} ஆபத்து). நிகழ்நேர கண்காணிப்புடன் புதுப்பித்த நிலையில் இருங்கள்.",
        "mr": "{station} ({city}) जवळ हवेची गुणवत्ता {category} आहे. PM2.5: {pm25:.1f} µg/m³, NO2: {no2:.1f} µg/m³. {general_mr} 2 किमी परिसरात {schools} शाळा आणि {hospitals} रुग्णालये आहेत ({vulnerability} जोखीम). रिअल-टाइम मॉनिटरिंगसह अपडेट रहा.",
        "bn": "{station} ({city}) এর কাছে বাতাসের মান {category}। PM2.5: {pm25:.1f} µg/m³, NO2: {no2:.1f} µg/m³। {general_bn} 2 কিমির মধ্যে {schools}টি স্কুল এবং {hospitals}টি হাসপাতাল আছে ({vulnerability} ঝুঁকি)। রিয়েল-টাইম মনিটরিংয়ের সাথে আপডেট থাকুন।",
    }
}


def _get_severity_phrases(category: str, lang: str) -> Dict[str, str]:
    """Returns context-appropriate phrases for a given AQI category and language."""
    is_safe = category in ("Good", "Satisfactory")
    is_moderate = category == "Moderate"

    phrases = {
        "en": {
            "advice": "safe for most people" if is_safe else ("best limited to light activities" if is_moderate else "strongly discouraged"),
            "mask_note": "N95 masks are not required." if is_safe else ("An N95 mask is recommended for sensitive individuals." if is_moderate else "N95 masks are strongly recommended for everyone outdoors."),
            "mask_recommendation": "N95 masks are not needed at this level." if is_safe else ("Consider wearing an N95 mask, especially if sensitive." if is_moderate else "Wearing an N95 mask is strongly recommended for outdoor commutes."),
            "vulnerable_advice": "enjoy outdoor activities freely." if is_safe else ("limit prolonged outdoor exposure." if is_moderate else "strictly avoid outdoor activities."),
            "children_advice": "Children can play outdoors safely." if is_safe else ("Children should limit outdoor playtime." if is_moderate else "Children should stay indoors."),
            "precaution": "No special precautions needed." if is_safe else ("Carry rescue inhalers if asthmatic." if is_moderate else "Close windows, use air purifiers, and avoid outdoor exposure."),
            "general_advice": "Conditions are favorable for outdoor activities." if is_safe else ("Sensitive groups should take precautions." if is_moderate else "Minimize outdoor exposure for all age groups."),
        },
        "hi": {
            "advice_hi": "सुरक्षित है" if is_safe else ("सीमित रखें" if is_moderate else "से बचें"),
            "mask_hi": "N95 मास्क की ज़रूरत नहीं।" if is_safe else ("संवेदनशील लोगों के लिए N95 मास्क उचित है।" if is_moderate else "बाहर N95 मास्क अनिवार्य है।"),
            "vulnerable_hi": "बाहर खेल-कूद कर सकते हैं।" if is_safe else ("लंबे समय तक बाहर न रहें।" if is_moderate else "बाहर जाने से बचें।"),
            "children_hi": "बच्चे बाहर सुरक्षित रूप से खेल सकते हैं।" if is_safe else ("बच्चों को बाहर कम समय बिताना चाहिए।" if is_moderate else "बच्चों को घर के अंदर ही रहना चाहिए।"),
            "precaution_hi": "कोई विशेष सावधानी ज़रूरी नहीं।" if is_safe else ("अस्थमा रोगी इनहेलर साथ रखें।" if is_moderate else "खिड़कियाँ बंद रखें, एयर प्यूरीफायर चलाएं।"),
            "general_hi": "बाहरी गतिविधियों के लिए अनुकूल।" if is_safe else ("संवेदनशील वर्ग सावधानी बरतें।" if is_moderate else "सभी आयु वर्ग बाहरी संपर्क कम करें।"),
        },
        "kn": {
            "advice_kn": "ಸುರಕ್ಷಿತವಾಗಿದೆ" if is_safe else ("ಸೀಮಿತವಾಗಿರಲಿ" if is_moderate else "ತಪ್ಪಿಸಿ"),
            "mask_kn": "N95 ಮಾಸ್ಕ್ ಅಗತ್ಯವಿಲ್ಲ." if is_safe else ("ಸೂಕ್ಷ್ಮ ವ್ಯಕ್ತಿಗಳಿಗೆ N95 ಮಾಸ್ಕ್ ಶಿಫಾರಸು." if is_moderate else "ಎಲ್ಲರಿಗೂ N95 ಮಾಸ್ಕ್ ಕಡ್ಡಾಯ."),
            "vulnerable_kn": "ಹೊರಾಂಗಣದಲ್ಲಿ ಆಡಬಹುದು." if is_safe else ("ದೀರ್ಘಕಾಲ ಹೊರಗೆ ಇರಬೇಡಿ." if is_moderate else "ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ತಪ್ಪಿಸಿ."),
            "children_kn": "ಮಕ್ಕಳು ಹೊರಗೆ ಆಡಬಹುದು." if is_safe else ("ಮಕ್ಕಳ ಹೊರಾಂಗಣ ಸಮಯವನ್ನು ಸೀಮಿತಗೊಳಿಸಿ." if is_moderate else "ಮಕ್ಕಳು ಒಳಾಂಗಣದಲ್ಲೇ ಇರಬೇಕು."),
            "precaution_kn": "ವಿಶೇಷ ಮುನ್ನೆಚ್ಚರಿಕೆ ಅಗತ್ಯವಿಲ್ಲ." if is_safe else ("ಆಸ್ತಮಾ ರೋಗಿಗಳು ಇನ್ಹೇಲರ್ ಇಟ್ಟುಕೊಳ್ಳಿ." if is_moderate else "ಕಿಟಕಿ ಮುಚ್ಚಿ, ಏರ್ ಪ್ಯೂರಿಫೈಯರ್ ಬಳಸಿ."),
            "general_kn": "ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳಿಗೆ ಅನುಕೂಲಕರ." if is_safe else ("ಸೂಕ್ಷ್ಮ ಗುಂಪುಗಳು ಎಚ್ಚರಿಕೆ ವಹಿಸಬೇಕು." if is_moderate else "ಎಲ್ಲಾ ವಯಸ್ಸಿನವರೂ ಹೊರಾಂಗಣ ಸಂಪರ್ಕ ಕಡಿಮೆ ಮಾಡಿ."),
        },
        "ta": {
            "advice_ta": "பாதுகாப்பானது" if is_safe else ("குறைக்கவும்" if is_moderate else "தவிர்க்கவும்"),
            "mask_ta": "N95 முகக்கவசம் தேவையில்லை." if is_safe else ("உணர்திறன் உள்ளவர்களுக்கு N95 பரிந்துரைக்கப்படுகிறது." if is_moderate else "அனைவருக்கும் N95 கட்டாயம்."),
            "vulnerable_ta": "வெளியே விளையாடலாம்." if is_safe else ("நீண்ட நேரம் வெளியே இருக்க வேண்டாம்." if is_moderate else "வெளிப்புற நடவடிக்கைகளை தவிர்க்கவும்."),
            "children_ta": "குழந்தைகள் வெளியே பாதுகாப்பாக விளையாடலாம்." if is_safe else ("குழந்தைகள் வெளிப்புற நேரத்தை குறைக்க வேண்டும்." if is_moderate else "குழந்தைகள் வீட்டிற்குள்ளேயே இருக்க வேண்டும்."),
            "precaution_ta": "சிறப்பு முன்னெச்சரிக்கை தேவையில்லை." if is_safe else ("ஆஸ்துமா நோயாளிகள் இன்ஹேலர் வைத்திருக்கவும்." if is_moderate else "ஜன்னல்களை மூடுங்கள், ஏர் ப்யூரிஃபையர் பயன்படுத்துங்கள்."),
            "general_ta": "வெளிப்புற நடவடிக்கைகளுக்கு ஏற்றது." if is_safe else ("உணர்திறன் குழுக்கள் முன்னெச்சரிக்கை எடுக்கவும்." if is_moderate else "அனைத்து வயதினரும் வெளிப்புற தொடர்பைக் குறைக்கவும்."),
        },
        "mr": {
            "advice_mr": "सुरक्षित आहे" if is_safe else ("मर्यादित ठेवा" if is_moderate else "टाळा"),
            "mask_mr": "N95 मास्कची गरज नाही." if is_safe else ("संवेदनशील व्यक्तींसाठी N95 मास्क शिफारसीय." if is_moderate else "सर्वांसाठी N95 मास्क अनिवार्य."),
            "vulnerable_mr": "बाहेर खेळू शकतात." if is_safe else ("दीर्घ काळ बाहेर राहू नका." if is_moderate else "बाहेरील क्रियाकलाप टाळा."),
            "children_mr": "मुले बाहेर सुरक्षितपणे खेळू शकतात." if is_safe else ("मुलांनी बाहेरील वेळ कमी करावा." if is_moderate else "मुलांनी घरातच राहावे."),
            "precaution_mr": "विशेष काळजी आवश्यक नाही." if is_safe else ("दम्याच्या रुग्णांनी इनहेलर सोबत ठेवा." if is_moderate else "खिडक्या बंद ठेवा, एअर प्युरिफायर वापरा."),
            "general_mr": "बाहेरील क्रियाकलापांसाठी अनुकूल." if is_safe else ("संवेदनशील गटांनी काळजी घ्यावी." if is_moderate else "सर्व वयोगटांनी बाहेरील संपर्क कमी करा."),
        },
        "bn": {
            "advice_bn": "নিরাপদ" if is_safe else ("সীমিত রাখুন" if is_moderate else "এড়িয়ে চলুন"),
            "mask_bn": "N95 মাস্কের প্রয়োজন নেই।" if is_safe else ("সংবেদনশীলদের জন্য N95 মাস্ক সুপারিশ করা হয়।" if is_moderate else "সবার জন্য N95 মাস্ক বাধ্যতামূলক।"),
            "vulnerable_bn": "বাইরে খেলতে পারে।" if is_safe else ("দীর্ঘক্ষণ বাইরে থাকবেন না।" if is_moderate else "বাইরের কাজকর্ম এড়িয়ে চলুন।"),
            "children_bn": "শিশুরা বাইরে নিরাপদে খেলতে পারে।" if is_safe else ("শিশুদের বাইরের সময় কমান।" if is_moderate else "শিশুদের ঘরেই থাকা উচিত।"),
            "precaution_bn": "বিশেষ সতর্কতার প্রয়োজন নেই।" if is_safe else ("হাঁপানি রোগীরা ইনহেলার সঙ্গে রাখুন।" if is_moderate else "জানালা বন্ধ রাখুন, এয়ার পিউরিফায়ার ব্যবহার করুন।"),
            "general_bn": "বাইরের কার্যকলাপের জন্য অনুকূল।" if is_safe else ("সংবেদনশীল গোষ্ঠী সতর্কতা অবলম্বন করুন।" if is_moderate else "সব বয়সীদের বাইরের সংস্পর্শ কমান।"),
        },
    }
    return phrases.get(lang, phrases["en"])


def _build_fallback_reply(query: str, lang: str, pm25: float, no2: float,
                          category: str, station_name: str, city: str,
                          schools: int, hospitals: int, vulnerability: str,
                          hotspots_str: str) -> str:
    """Build a rich multi-lingual fallback reply when Gemini API is unavailable."""
    phrases = _get_severity_phrases(category, lang)
    fmt = dict(
        pm25=pm25, no2=no2, category=category, station=station_name,
        city=city, schools=schools, hospitals=hospitals,
        vulnerability=vulnerability, hotspots=hotspots_str,
        **phrases
    )

    q = query.lower()
    if any(w in q for w in ("run", "exercise", "outdoor", "walk", "jog", "sport", "ಓಡ", "ஓட", "दौड", "व्यायाम")):
        template_key = "outdoor"
    elif any(w in q for w in ("mask", "n95", "wear", "commute", "मास्क", "முகக்கவசம்", "ಮಾಸ್ಕ್", "মাস্ক")):
        template_key = "mask"
    elif any(w in q for w in ("child", "kid", "elder", "old", "senior", "school", "baby", "बच्च", "முதிய", "குழந்தை", "ಮಕ್ಕಳ", "শিশু", "বয়স্ক")):
        template_key = "children"
    else:
        template_key = "general"

    template = FALLBACK_TEMPLATES.get(template_key, FALLBACK_TEMPLATES["general"])
    lang_template = template.get(lang, template["en"])

    try:
        return lang_template.format(**fmt)
    except KeyError:
        # Safe fallback to English if a format key is missing
        return template["en"].format(**fmt)


import os

def generate_chat_response(
    query: str,
    station_id: str,
    lang: str = "en",
    db: Session = None,
    gemini_api_key: str = None
) -> Dict[str, Any]:
    """
    Multi-Lingual Citizen AI Chatbot powered by Google Gemini 2.5 Flash API.
    Reads API key from GEMINI_API_KEY env var. Falls back to rich multi-lingual
    rule-based templates when the API is unavailable.
    """
    s_id = str(station_id)
    station = db.query(Station).filter(Station.id == s_id).first() if db else None

    if not station:
        station_name = f"Station {s_id}"
        city = "Delhi"
        state = "Delhi"
        pm25 = 75.0
        no2 = 30.0
        temp = 26.0
        humidity = 55.0
        wind = 12.0
        stagnation = 0.4
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
        temp = latest.temp if (latest and latest.temp is not None) else 26.0
        humidity = latest.humidity if (latest and latest.humidity is not None) else 55.0
        wind = latest.wind_speed if (latest and latest.wind_speed is not None) else 12.0
        stagnation = latest.stagnation if (latest and latest.stagnation is not None) else 0.4

    category = get_aqi_category(pm25)
    profile = get_station_profile(s_id, station_name, city, state)

    selected_lang = lang if lang in LANG_MAP else profile.get("native_lang", "en")
    lang_name, lang_instructions = LANG_MAP.get(selected_lang, LANG_MAP["en"])

    receptors = profile.get("receptors", {})
    schools = receptors.get("schools", 10)
    hospitals = receptors.get("hospitals", 3)
    vuln_level = receptors.get("vulnerability_level", "Medium")
    spcb_auth = profile.get("spcb_authority", "SPCB")
    spcb_framework = profile.get("spcb_framework", "NCAP Directive")
    land_use = profile.get("land_use", "Urban Catchment")
    zone_type = profile.get("zone_type", "Residential/Commercial")
    hotspots = profile.get("registered_hotspots", [])
    hotspots_str = ", ".join(hotspots) if hotspots else "Local Catchment"

    # ── Resolve API Key: argument > env var ──
    key_to_use = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")

    if key_to_use:
        prompt = f"""You are AtmosEdgeAI's Multi-Lingual Citizen Environmental & Health Assistant.
A citizen is asking you a direct question regarding local air quality, health precautions, or outdoor safety.

Target Location & Live Telemetry Context:
- Monitoring Station: {station_name} ({city}, {state})
- Current Air Quality: PM2.5 = {pm25:.1f} µg/m³, NO2 = {no2:.1f} µg/m³ (CPCB Category: {category})
- Meteorological Dispersion: Temp = {temp}°C, Humidity = {humidity}%, Wind Speed = {wind} km/h, Stagnation Index = {stagnation} (0-1 scale)
- Station Land-Use Profile: {land_use} ({zone_type})
- Statutory SPCB Authority: {spcb_auth} ({spcb_framework})
- Sensitive Receptors within 2km: {schools} Schools, {hospitals} Hospitals ({vuln_level} Vulnerability)
- Registered Hotspots: {hotspots_str}

Citizen Query: "{query}"

CRITICAL INSTRUCTIONS:
1. Answer directly, empathetically, and accurately addressing the citizen's specific doubt.
2. YOU MUST ANSWER ENTIRELY IN {lang_name.upper()} ({lang_instructions}).
3. Cover practical safety advice: N95 mask necessity, outdoor exercise/running feasibility, protecting children, elderly, and respiratory patients.
4. Keep response clear, well-structured, and concise (under 150 words).
"""
        import requests

        for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key_to_use}"
            headers = {"Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=15)
                if r.status_code == 200:
                    res_data = r.json()
                    reply_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return {
                        "reply": reply_text,
                        "station_id": s_id,
                        "station_name": station_name,
                        "city": city,
                        "category": category,
                        "pm25": round(pm25, 1),
                        "lang": selected_lang,
                        "model_used": model_name
                    }
                else:
                    print(f"[Gemini {model_name}] HTTP {r.status_code}: {r.text[:200]}")
            except Exception as exc:
                print(f"[Gemini Exception {model_name}] {exc}")

    # ── Multi-Lingual Fallback (native script) ──
    fallback_msg = _build_fallback_reply(
        query=query, lang=selected_lang, pm25=pm25, no2=no2,
        category=category, station_name=station_name, city=city,
        schools=schools, hospitals=hospitals, vulnerability=vuln_level,
        hotspots_str=hotspots_str
    )

    return {
        "reply": fallback_msg,
        "station_id": s_id,
        "station_name": station_name,
        "city": city,
        "category": category,
        "pm25": round(pm25, 1),
        "lang": selected_lang,
        "model_used": "AtmosEdgeAI Local Engine"
    }



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
