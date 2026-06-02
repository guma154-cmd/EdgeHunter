import uuid
from src.edgehunter.core.advanced_calibration_models import ReliabilityLevel, TrendStatus, _check_operational_language

def calculate_reliability_scores(
    segment_metrics: dict,
    trend_report: dict | None = None,
    *,
    min_sample_size: int = 10,
) -> dict:
    
    if min_sample_size < 1:
        raise ValueError("min_sample_size must be >= 1")
        
    _check_operational_language(str(segment_metrics))
    if trend_report:
        _check_operational_language(str(trend_report))

    sample_size = segment_metrics.get("sample_size", 0)
    segment_key = segment_metrics.get("segment_key")

    trend_status = TrendStatus.STABLE
    if trend_report:
        t_val = trend_report.get("trend_status", TrendStatus.STABLE)
        if isinstance(t_val, str):
            trend_status = TrendStatus(t_val)
        else:
            trend_status = t_val

    if sample_size < min_sample_size:
        return {
            "score_id": f"SCORE-{uuid.uuid4().hex[:8]}",
            "segment_key": segment_key,
            "score": 0.0,
            "reliability_level": ReliabilityLevel.RELIABILITY_INSUFFICIENT_SAMPLE,
            "confidence": 0.0,
            "sample_size": sample_size,
            "reason": f"Sample size {sample_size} below minimum {min_sample_size}",
            "is_simulated": True,
            "actionable": False
        }

    conf_rate = segment_metrics.get("confirmation_rate", 0.0)
    avg_assertiveness = segment_metrics.get("average_calibrated_assertiveness", 0.0)
    avg_confidence = segment_metrics.get("average_confidence", 0.0)
    
    not_confirmed_rate = segment_metrics.get("not_confirmed_rate", 0.0)
    false_pos_rate = segment_metrics.get("false_positive_rate", 0.0)

    # Base stability factor
    stability_factor = 0.5
    if trend_status == TrendStatus.IMPROVING:
        stability_factor = 1.0
    elif trend_status == TrendStatus.STABLE:
        stability_factor = 0.8
    elif trend_status == TrendStatus.VOLATILE:
        stability_factor = 0.4
    elif trend_status == TrendStatus.DECLINING:
        stability_factor = 0.0

    # Base score
    score = (conf_rate * 0.50) + (avg_assertiveness * 0.20) + (avg_confidence * 0.15) + (stability_factor * 0.15)
    
    # Penalizações
    if not_confirmed_rate > 0.30:
        score -= 0.15
    elif not_confirmed_rate > 0.15:
        score -= 0.05
        
    if false_pos_rate > 0.20:
        score -= 0.20
    elif false_pos_rate > 0.10:
        score -= 0.10
        
    if trend_status == TrendStatus.DECLINING:
        score -= 0.15
    elif trend_status == TrendStatus.VOLATILE:
        score -= 0.05
        
    # Cap between 0 and 1
    score = max(0.0, min(1.0, score))
    
    if score >= 0.75:
        level = ReliabilityLevel.RELIABILITY_HIGH
    elif score >= 0.55:
        level = ReliabilityLevel.RELIABILITY_MEDIUM
    else:
        level = ReliabilityLevel.RELIABILITY_LOW
        
    return {
        "score_id": f"SCORE-{uuid.uuid4().hex[:8]}",
        "segment_key": segment_key,
        "score": score,
        "reliability_level": level,
        "confidence": score * 0.9,  # synthetic confidence bound
        "sample_size": sample_size,
        "reason": f"Calculated technical score based on confirmation rate and {trend_status.value} trend",
        "is_simulated": True,
        "actionable": False
    }
