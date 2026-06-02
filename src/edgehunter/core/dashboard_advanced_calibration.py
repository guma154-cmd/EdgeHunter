import uuid
from datetime import datetime, timezone
from src.edgehunter.core.advanced_calibration_models import _check_operational_language
from src.edgehunter.core.advanced_calibration_segments import segment_historical_calibration_data
from src.edgehunter.core.advanced_calibration_metrics import calculate_segment_calibration_metrics
from src.edgehunter.core.advanced_calibration_trends import detect_segment_trends
from src.edgehunter.core.advanced_reliability_score import calculate_reliability_scores
from src.edgehunter.core.advanced_threshold_suggestion import generate_advanced_threshold_suggestion

def generate_advanced_calibration_dashboard(
    current_metrics: list[dict],
    current_outcomes: list[dict],
    previous_metrics: list[dict] | None = None,
    previous_outcomes: list[dict] | None = None,
    *,
    min_sample_size: int = 10,
    current_threshold: float = 0.70
) -> dict:
    
    _check_operational_language(str(current_metrics))
    _check_operational_language(str(current_outcomes))
    
    if previous_metrics and previous_outcomes:
        _check_operational_language(str(previous_metrics))
        _check_operational_language(str(previous_outcomes))
        
    current_segments = segment_historical_calibration_data(current_metrics, current_outcomes)
    
    prev_seg_map = {}
    if previous_metrics and previous_outcomes:
        prev_segments = segment_historical_calibration_data(previous_metrics, previous_outcomes)
        prev_calc = calculate_segment_calibration_metrics(prev_segments, min_sample_size=1)
        for pm in prev_calc["metrics_by_segment"]:
            prev_seg_map[str(pm["segment_key"])] = pm

    current_calc = calculate_segment_calibration_metrics(current_segments, min_sample_size=1)
    
    scores = []
    final_metrics = []
    
    for cm in current_calc["metrics_by_segment"]:
        s_key_str = str(cm["segment_key"])
        pm = prev_seg_map.get(s_key_str)
        
        trend = detect_segment_trends(cm, pm, min_sample_size=min_sample_size)
        cm["trend_status"] = trend["trend_status"]
        
        score = calculate_reliability_scores(cm, trend, min_sample_size=min_sample_size)
        scores.append(score)
        final_metrics.append(cm)

    report = {
        "report_id": f"ADV-CALIB-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scores": scores,
        "segments_metrics": final_metrics,
        "is_simulated": True,
        "actionable": False
    }
    
    suggestion = generate_advanced_threshold_suggestion(
        report, 
        current_threshold=current_threshold, 
        min_sample_size=min_sample_size
    )
    
    report["threshold_suggestion"] = suggestion
    
    _check_operational_language(str(report))
    
    return report
