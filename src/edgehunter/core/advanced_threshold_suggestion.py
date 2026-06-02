from src.edgehunter.core.advanced_calibration_models import ReliabilityLevel, TrendStatus, _check_operational_language

def generate_advanced_threshold_suggestion(
    reliability_report: dict,
    *,
    current_threshold: float = 0.70,
    min_sample_size: int = 30,
) -> dict:
    
    if min_sample_size < 1:
        raise ValueError("min_sample_size must be >= 1")
    if not (0.50 <= current_threshold <= 0.95):
        raise ValueError("current_threshold must be between 0.50 and 0.95")

    _check_operational_language(str(reliability_report))

    scores = reliability_report.get("scores", [])
    metrics = reliability_report.get("segments_metrics", [])
    
    global_sample = sum(s.get("sample_size", 0) for s in scores)
    
    if global_sample < min_sample_size:
        return {
            "suggested_action": "REQUIRE_MORE_SAMPLE",
            "suggested_threshold": current_threshold,
            "reason": f"Global sample size {global_sample} is below minimum {min_sample_size}.",
            "auto_apply": False,
            "is_simulated": True,
            "actionable": False
        }

    high_count = 0
    low_count = 0
    declining_count = 0
    
    # Analyze reliability levels
    for s in scores:
        lvl = s.get("reliability_level")
        if lvl == ReliabilityLevel.RELIABILITY_HIGH:
            high_count += 1
        elif lvl == ReliabilityLevel.RELIABILITY_LOW:
            low_count += 1
            
    # Analyze green/red false rates across metrics
    green_false_positives = 0.0
    red_false_negatives = 0.0
    green_count = 0
    red_count = 0
    
    for m in metrics:
        trend = m.get("trend_status")
        if trend == TrendStatus.DECLINING:
            declining_count += 1
            
        key = m.get("segment_key", {})
        label = key.get("simulation_label", "").upper()
        
        if "GREEN" in label:
            green_false_positives += m.get("false_positive_rate", 0.0)
            green_count += 1
        elif "RED" in label:
            # missed positive is false negative in green perspective
            red_false_negatives += m.get("false_negative_rate", 0.0)
            red_count += 1
            
    avg_green_fp = green_false_positives / green_count if green_count > 0 else 0.0
    avg_red_fn = red_false_negatives / red_count if red_count > 0 else 0.0
    
    action = "KEEP_THRESHOLD"
    new_threshold = current_threshold
    reason = "System is stable and well calibrated."

    if low_count > high_count or declining_count > len(metrics) / 3:
        action = "RAISE_THRESHOLD"
        new_threshold = current_threshold + 0.05
        reason = "Many segments are showing low reliability or declining trends."
        
    elif avg_green_fp > 0.15:
        action = "RAISE_THRESHOLD"
        new_threshold = current_threshold + 0.05
        reason = "Green false positive rate is too high."
        
    elif avg_red_fn > 0.15 and avg_green_fp < 0.05 and high_count > low_count:
        action = "LOWER_THRESHOLD"
        new_threshold = current_threshold - 0.05
        reason = "Green signals are highly reliable, but many positive scenarios are missed by red signals."

    # Clamp the suggested threshold between 0.50 and 0.95
    new_threshold = max(0.50, min(0.95, new_threshold))
    
    if new_threshold == current_threshold and action in ["RAISE_THRESHOLD", "LOWER_THRESHOLD"]:
        action = "KEEP_THRESHOLD"
        reason = "Threshold capped by safety bounds."

    return {
        "suggested_action": action,
        "suggested_threshold": float(f"{new_threshold:.2f}"),
        "reason": reason,
        "auto_apply": False,
        "is_simulated": True,
        "actionable": False
    }
