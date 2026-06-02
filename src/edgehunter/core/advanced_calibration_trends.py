from src.edgehunter.core.advanced_calibration_models import TrendStatus, _check_operational_language

def detect_segment_trends(
    current_metrics: dict,
    previous_metrics: dict | None = None,
    *,
    min_sample_size: int = 10,
    improvement_delta: float = 0.05,
    degradation_delta: float = 0.05,
) -> dict:
    
    if min_sample_size < 1:
        raise ValueError("min_sample_size must be >= 1")
    if improvement_delta <= 0.0 or degradation_delta <= 0.0:
        raise ValueError("deltas must be strictly positive")

    _check_operational_language(str(current_metrics))
    if previous_metrics:
        _check_operational_language(str(previous_metrics))

    sample_size = current_metrics.get("sample_size", 0)
    
    if sample_size < min_sample_size:
        return {
            "trend_status": TrendStatus.INSUFFICIENT_SAMPLE,
            "reason": f"Sample size {sample_size} is below minimum {min_sample_size}",
            "is_simulated": True,
            "actionable": False
        }
        
    if not previous_metrics:
        return {
            "trend_status": TrendStatus.STABLE,
            "reason": "No previous period metrics to compare, defaulting to STABLE",
            "is_simulated": True,
            "actionable": False
        }
        
    curr_conf = current_metrics.get("confirmation_rate", 0.0)
    prev_conf = previous_metrics.get("confirmation_rate", 0.0)
    
    curr_err = current_metrics.get("false_positive_rate", 0.0)
    prev_err = previous_metrics.get("false_positive_rate", 0.0)
    
    conf_diff = curr_conf - prev_conf
    err_diff = curr_err - prev_err
    
    # Se confirmação subiu >= improvement_delta e erro não subiu: IMPROVING.
    if conf_diff >= improvement_delta and err_diff <= 0.0:
        status = TrendStatus.IMPROVING
        reason = f"Confirmation rate improved by {conf_diff:.2f} and error rate did not increase"
        
    # Se confirmação e erro subiram juntos (ambos acima de 0): VOLATILE.
    # Note: the prompt says "Se confirmação e erro subiram juntos: VOLATILE."
    # Let's consider "subiram" as strictly positive difference.
    elif conf_diff > 0.0 and err_diff > 0.0:
        status = TrendStatus.VOLATILE
        reason = f"Both confirmation rate and error rate increased"
        
    # Se confirmação caiu >= degradation_delta ou erro subiu >= degradation_delta: DECLINING.
    elif conf_diff <= -degradation_delta or err_diff >= degradation_delta:
        status = TrendStatus.DECLINING
        reason = f"Confirmation rate degraded or error rate increased significantly"
        
    # Caso contrário: STABLE.
    else:
        status = TrendStatus.STABLE
        reason = "Changes are within stable thresholds"
        
    return {
        "trend_status": status,
        "reason": reason,
        "is_simulated": True,
        "actionable": False
    }
