# Centralized Municipal Action Catalog for AI Enforcement Engine

MUNICIPAL_ACTIONS = {
    "Vehicular Emissions": [
        {
            "type": "Traffic Control",
            "action": "Restrict entry of diesel commercial trucks and heavy vehicles along active corridors.",
            "expected_impact": "High",
            "difficulty": "High"
        },
        {
            "type": "Traffic Flow",
            "action": "Synchronize major intersection signal timing patterns to reduce vehicle idling.",
            "expected_impact": "Medium",
            "difficulty": "Low"
        },
        {
            "type": "Public Transport",
            "action": "Deploy feeder shuttle busses to discourage personal passenger car commutes.",
            "expected_impact": "Medium",
            "difficulty": "Medium"
        }
    ],
    "Industrial Emissions": [
        {
            "type": "Compliance Audit",
            "action": "Dispatch inspector teams to Peenya industrial factories to review boiler logbooks.",
            "expected_impact": "High",
            "difficulty": "Medium"
        },
        {
            "type": "Emission Caps",
            "action": "Temporarily mandate a 30% production reduction for non-compliant manufacturing boilers.",
            "expected_impact": "High",
            "difficulty": "High"
        },
        {
            "type": "Fuel Verification",
            "action": "Audit coal and petcoke consumption logs to enforce ban on unapproved fuels.",
            "expected_impact": "High",
            "difficulty": "Medium"
        }
    ],
    "Construction Dust": [
        {
            "type": "Construction Stop",
            "action": "Issue temporary stop-work directives for excavation and dry concrete mixing activities.",
            "expected_impact": "High",
            "difficulty": "High"
        },
        {
            "type": "Dust Suppression",
            "action": "Deploy roadside mist water sprinklers and mechanical sweeping routines along corridors.",
            "expected_impact": "High",
            "difficulty": "Low"
        },
        {
            "type": "Site Shielding",
            "action": "Inspect construction boundaries to verify dust barrier sheets are completely intact.",
            "expected_impact": "Medium",
            "difficulty": "Low"
        }
    ],
    "Biomass Burning": [
        {
            "type": "Waste Patrol",
            "action": "Increase municipal warden patrols to penalize biomass heating and garbage burning.",
            "expected_impact": "High",
            "difficulty": "Medium"
        },
        {
            "type": "Shelter Support",
            "action": "Distribute clean heating blankets to night shelter workers to prevent wood combustion.",
            "expected_impact": "Medium",
            "difficulty": "Low"
        }
    ],
    "Crop Burning": [
        {
            "type": "Cross-Border Coordinating",
            "action": "Coordinate state board alerts to suppress regional agricultural smoke transport corridors.",
            "expected_impact": "High",
            "difficulty": "High"
        },
        {
            "type": "Early Warning",
            "action": "Broadcast alerts across agricultural wards to stop agricultural waste burning.",
            "expected_impact": "Medium",
            "difficulty": "Medium"
        }
    ],
    "Waste Burning": [
        {
            "type": "Landfill Inspections",
            "action": "Deploy fire teams to inspect local landfills for spontaneous trash combustion hotspots.",
            "expected_impact": "High",
            "difficulty": "Medium"
        },
        {
            "type": "Penalties",
            "action": "Enforce strict fines on open residential garden and plastic garbage burning.",
            "expected_impact": "Medium",
            "difficulty": "Low"
        }
    ],
    "Natural Dust": [
        {
            "type": "Road Misting",
            "action": "Deploy mobile dust suppression spray trucks along high-traffic arterial dirt roads.",
            "expected_impact": "Medium",
            "difficulty": "Low"
        }
    ],
    "Mixed Sources": [
        {
            "type": "General Patrol",
            "action": "Increase generalized road sweeping and water sprinkling frequencies in the area.",
            "expected_impact": "Medium",
            "difficulty": "Low"
        }
    ],
    "Unknown": [
        {
            "type": "Monitoring Deployment",
            "action": "Deploy a mobile AQI monitoring van to identify transient particulate sources.",
            "expected_impact": "Medium",
            "difficulty": "Medium"
        }
    ]
}
