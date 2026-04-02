import random

def run_business_simulation(label, action, current_revenue=10000):
    """
    Simulates the business impact of applying a specific strategy (action) to a customer segment (label).
    Returns ROI estimate, Risk level, Confidence score, and simulated revenue impact.
    """
    base_confidence = random.uniform(0.70, 0.95)
    
    # Simple deterministic logic for demonstration
    if action == 'High Discount':
        if "Sensible" in label or "Careless" in label:
            roi_pct = 15.5
            risk = "Medium"
        else:
            roi_pct = 5.0
            risk = "High"
            
    elif action == 'Loyalty Program':
        if "Target" in label or "Careful" in label:
            roi_pct = 22.0
            risk = "Low"
        else:
            roi_pct = 8.5
            risk = "Medium"
            
    elif action == 'Aggressive Marketing':
        roi_pct = 12.0
        risk = "High"
        base_confidence -= 0.1
        
    else:
        roi_pct = 10.0
        risk = "Medium"
        
    # Introduce slight jitter
    roi_pct += random.uniform(-2.0, 2.0)
    
    simulated_revenue_increase = (roi_pct / 100) * current_revenue
    
    return {
        "strategy_applied": action,
        "roi_estimate": f"+{roi_pct:.1f}%",
        "risk_level": risk,
        "confidence_score": f"{base_confidence * 100:.1f}%",
        "simulated_revenue_increase": f"${simulated_revenue_increase:,.2f}"
    }
