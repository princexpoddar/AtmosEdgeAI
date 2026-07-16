from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.core.database import Ward, Advisory, Reading

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
    
    # Try using Gemini if API key is provided
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

    # Fallback to Rule-based response
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
        
        # Check if an advisory already exists for the latest timestamp
        exists = db.query(Advisory).filter(
            Advisory.ward_id == w.id,
            Advisory.level == category
        ).first()
        
        if not exists:
            message_en = f"Air quality in {w.name} is {category}. PM2.5 is {pm25} ug/m3."
            message_hi = f"{w.name} में हवा की गुणवत्ता {category} है। PM2.5 का स्तर {pm25} है।"
            message_local = message_en # default local
            
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
