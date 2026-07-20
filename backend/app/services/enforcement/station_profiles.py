"""
enforcement/station_profiles.py
================================
Geospatial Registry for Station Land-Use Profiles, Sensitive Receptors,
SPCB Regulatory Mandates, and Registered Emission Hotspots.
"""

from typing import Dict, Any, List

# Standard SPCB regulatory mapping by state / city
SPCB_REGISTRY: Dict[str, Dict[str, str]] = {
    "Delhi": {
        "authority": "DPCC (Delhi Pollution Control Committee)",
        "framework": "GRAP IV (Graded Response Action Plan) & CAAQMS Directive 2024",
        "region_code": "DL-NCR",
        "lang": "hi"
    },
    "Karnataka": {
        "authority": "KSPCB (Karnataka State Pollution Control Board)",
        "framework": "NCAP Bengaluru City Clean Air Action Plan 2024",
        "region_code": "KA-SOU",
        "lang": "kn"
    },
    "Tamil Nadu": {
        "authority": "TNPCB (Tamil Nadu Pollution Control Board)",
        "framework": "Greater Chennai Coastal Industrial & Urban Clean Air Plan",
        "region_code": "TN-SOU",
        "lang": "ta"
    },
    "Maharashtra": {
        "authority": "MPCB (Maharashtra Pollution Control Board)",
        "framework": "MMR Mumbai Metropolitan Region Air Action Plan",
        "region_code": "MH-WEST",
        "lang": "mr"
    },
    "Uttar Pradesh": {
        "authority": "UPPCB (Uttar Pradesh Pollution Control Board)",
        "framework": "UP State NCAP Non-Attainment City Mitigation Protocol",
        "region_code": "UP-NORTH",
        "lang": "hi"
    },
    "Rajasthan": {
        "authority": "RSPCB (Rajasthan State Pollution Control Board)",
        "framework": "NCAP Rajasthan Industrial Belt Clean Air Action Plan",
        "region_code": "RJ-WEST",
        "lang": "hi"
    },
    "West Bengal": {
        "authority": "WBPCB (West Bengal Pollution Control Board)",
        "framework": "KMC Kolkata Metropolitan Air Quality Directive 2024",
        "region_code": "WB-EAST",
        "lang": "bn"
    },
    "Punjab": {
        "authority": "PPCB (Punjab Pollution Control Board)",
        "framework": "Punjab Agricultural Stubble & Stagnant Haze Action Plan",
        "region_code": "PB-NORTH",
        "lang": "hi"
    },
    "Madhya Pradesh": {
        "authority": "MPPCB (Madhya Pradesh Pollution Control Board)",
        "framework": "MP State NCAP Industrial Stack Compliance Directive",
        "region_code": "MP-CENTRAL",
        "lang": "hi"
    }
}

# Known station profiles keyed by station ID or partial matching rules
STATION_DOSSIER_DATABASE: Dict[str, Dict[str, Any]] = {
    # 860: Sanjay Palace, Agra
    "860": {
        "land_use": "Commercial & Construction Corridor",
        "zone_type": "Heritage & Commercial Zone",
        "topographic_type": "Indo-Gangetic Basin Sink",
        "receptors": {"schools": 12, "hospitals": 3, "elderly_care": 2, "outdoor_markets": 6, "vulnerability_level": "High"},
        "registered_hotspots": [
            "MG Road Commercial Construction Belt",
            "Sanjay Palace Multi-Story Parking Complex",
            "Bypass Road Heavy Diesel Freight Passage"
        ],
    },
    # 5657: Punjabi Bagh, Delhi
    "5657": {
        "land_use": "High-Density Traffic Corridor",
        "zone_type": "Arterial Transit & Mixed Zone",
        "topographic_type": "Stagnant Urban Basin",
        "receptors": {"schools": 18, "hospitals": 5, "elderly_care": 3, "outdoor_markets": 8, "vulnerability_level": "Critical"},
        "registered_hotspots": [
            "Ring Road & Rohtak Road Flyover Interchange",
            "Punjabi Bagh Bus Terminal Idle Corridor",
            "Rajouri Garden Commercial Freight Hub"
        ],
    },
    # 5548: BTM Layout, Bengaluru
    "5548": {
        "land_use": "High-Density Traffic Corridor",
        "zone_type": "Urban Transit Corridor",
        "topographic_type": "Deccan Plateau Elevated Basin",
        "receptors": {"schools": 14, "hospitals": 4, "elderly_care": 2, "outdoor_markets": 5, "vulnerability_level": "High"},
        "registered_hotspots": [
            "Silk Board Junction Traffic Bottleneck",
            "Outer Ring Road BTM Flyover Bay",
            "Madiwala Market Diesel Transit Hub"
        ],
    },
    # 5547: BWSSB Kadabesanahalli, Bengaluru
    "5547": {
        "land_use": "Commercial & Construction Zone",
        "zone_type": "IT Tech Park & Construction Corridor",
        "topographic_type": "Deccan Plateau Elevated Basin",
        "receptors": {"schools": 9, "hospitals": 3, "elderly_care": 1, "outdoor_markets": 4, "vulnerability_level": "Medium"},
        "registered_hotspots": [
            "Outer Ring Road Metro Rail Construction Site",
            "Kadabesanahalli Flyover Diesel Bus Corridor",
            "Bellandur Lake Buffer Waste Hotspot"
        ],
    },
    # 5576: Moti Doongri, Alwar
    "5576": {
        "land_use": "Industrial Stack Cluster",
        "zone_type": "Heavy Industrial & Mining Corridor",
        "topographic_type": "Semi-Arid Valley Sink",
        "receptors": {"schools": 7, "hospitals": 2, "elderly_care": 1, "outdoor_markets": 3, "vulnerability_level": "Medium"},
        "registered_hotspots": [
            "MIA Industrial Area Phase-1 Boiler Stacks",
            "Matsya Industrial Area Foundry Belt",
            "Alwar Bypass Heavy Transport Corridor"
        ],
    },
    # 5551: Golden Temple, Amritsar
    "5551": {
        "land_use": "Biomass & Commercial Zone",
        "zone_type": "Heritage & High Footfall Zone",
        "topographic_type": "Indo-Gangetic Plain Sink",
        "receptors": {"schools": 11, "hospitals": 4, "elderly_care": 2, "outdoor_markets": 10, "vulnerability_level": "High"},
        "registered_hotspots": [
            "Heritage Street Commercial Cooking Stacks",
            "Grand Trunk Road Bus Stand Transit Corridor",
            "Outskirt Agricultural Stubble Plume Entry Point"
        ],
    },
    # 5667: Bhopal Chauraha, Dewas
    "5667": {
        "land_use": "Industrial Stack Cluster",
        "zone_type": "Chemical & Manufacturing Hub",
        "topographic_type": "Malwa Plateau Basin",
        "receptors": {"schools": 8, "hospitals": 2, "elderly_care": 1, "outdoor_markets": 4, "vulnerability_level": "Medium"},
        "registered_hotspots": [
            "Bank Note Press Industrial Stack Belt",
            "Dewas Industrial Area Sector-2 Boiler Units",
            "Bhopal Road Highway Freight Junction"
        ],
    },
    # 2456: Talkatora, Lucknow
    "2456": {
        "land_use": "Industrial Stack Cluster",
        "zone_type": "Manufacturing & Freight Hub",
        "topographic_type": "Gomti River Basin Sink",
        "receptors": {"schools": 13, "hospitals": 3, "elderly_care": 2, "outdoor_markets": 6, "vulnerability_level": "High"},
        "registered_hotspots": [
            "Talkatora Industrial Estate Foundry & Electroplating Stacks",
            "Lucknow Railway Yard Freight Clearing Bay",
            "Kanpur Road Heavy Transport Interchange"
        ],
    }
}


def get_station_profile(station_id: str, station_name: str = "", city: str = "", state: str = "") -> Dict[str, Any]:
    """
    Retrieves or generates a station-specific land-use & receptor dossier.
    Combines static database lookup with dynamic heuristic defaults for any CPCB station.
    """
    s_id = str(station_id)
    if s_id in STATION_DOSSIER_DATABASE:
        profile = STATION_DOSSIER_DATABASE[s_id].copy()
    else:
        # Dynamic heuristic profile generation for unlisted stations based on name/city
        name_lower = (station_name or "").lower()
        if "industrial" in name_lower or "estate" in name_lower or "sector" in name_lower or "phase" in name_lower:
            land_use = "Industrial Stack Cluster"
            zone_type = "Heavy Industrial & Manufacturing Belt"
            receptors = {"schools": 6, "hospitals": 2, "elderly_care": 1, "outdoor_markets": 3, "vulnerability_level": "Medium"}
            hotspots = ["Local Industrial Stack Cluster", "Boiler House Corridor", "Heavy Freight Transit Bay"]
        elif "road" in name_lower or "chowk" in name_lower or "junction" in name_lower or "bus" in name_lower or "highway" in name_lower or "bypass" in name_lower:
            land_use = "High-Density Traffic Corridor"
            zone_type = "Arterial Freight & Transit Hub"
            receptors = {"schools": 15, "hospitals": 4, "elderly_care": 2, "outdoor_markets": 7, "vulnerability_level": "High"}
            hotspots = ["Arterial Intersection Freight Bottleneck", "Bus Terminal Idle Bay", "High-Volume Transit Corridor"]
        elif "park" in name_lower or "colony" in name_lower or "nagar" in name_lower or "puram" in name_lower or "vihar" in name_lower:
            land_use = "Commercial & Construction Zone"
            zone_type = "Mixed Residential & Commercial Zone"
            receptors = {"schools": 12, "hospitals": 3, "elderly_care": 2, "outdoor_markets": 5, "vulnerability_level": "Medium"}
            hotspots = ["Local Construction Permit Site", "Commercial Heating Stacks", "Neighborhood Unpaved Road Dust"]
        else:
            land_use = "Mixed Residential & Institutional"
            zone_type = "Urban Residential Zone"
            receptors = {"schools": 10, "hospitals": 3, "elderly_care": 1, "outdoor_markets": 4, "vulnerability_level": "Medium"}
            hotspots = ["Neighborhood Generator Sets", "Local Biomass Stoves", "Urban Traffic Access Feeder"]

        topography = "Coastal Marine Corridor" if city.lower() in ["mumbai", "chennai", "kolkata"] else "Indo-Gangetic Basin Sink"
        profile = {
            "land_use": land_use,
            "zone_type": zone_type,
            "topographic_type": topography,
            "receptors": receptors,
            "registered_hotspots": hotspots
        }

    # Attach SPCB Regulatory Authority
    state_key = state if state in SPCB_REGISTRY else city
    spcb = SPCB_REGISTRY.get(state_key, SPCB_REGISTRY.get(city, {
        "authority": f"{state or city} Pollution Control Authority",
        "framework": "National Clean Air Programme (NCAP) Statutory Directive",
        "region_code": "IN-GENERIC",
        "lang": "hi"
    }))

    profile["spcb_authority"] = spcb["authority"]
    profile["spcb_framework"] = spcb["framework"]
    profile["region_code"]    = spcb["region_code"]
    profile["native_lang"]    = spcb["lang"]

    return profile
