from backend.app.services.enforcement.context import EnforcementContext
from backend.app.config.action_catalog import MUNICIPAL_ACTIONS

def analyze(context: EnforcementContext, priority_results: dict) -> list:
    """
    Stateless Intervention Engine. Resolves source categories against the
    centralized catalog configurations to fetch actions, difficulty ratings, and impact metrics.
    """
    source_attr = context.source_attribution
    primary_source = source_attr.get("primary", {}).get("source", "Mixed Sources")
    priority = priority_results.get("priority", "Low")
    conf = context.confidence.get("score", 0.85)
    
    # Lookup actions from central catalog
    catalog_actions = MUNICIPAL_ACTIONS.get(primary_source, MUNICIPAL_ACTIONS["Mixed Sources"])
    
    recommendations = []
    for item in catalog_actions:
        recommendations.append({
            "category": item["type"],
            "action": item["action"],
            "expected_impact": item["expected_impact"],
            "implementation_difficulty": item["difficulty"],
            "urgency": priority,
            "confidence": conf
        })
        
    return recommendations
