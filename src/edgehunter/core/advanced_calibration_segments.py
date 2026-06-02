import math
from src.edgehunter.core.advanced_calibration_models import CalibrationSegmentKey, _check_operational_language

def get_bucket_label(assertiveness: float, bucket_size: float) -> str:
    if not isinstance(assertiveness, (int, float)) or not (0.0 <= assertiveness <= 1.0):
        raise ValueError("assertiveness must be between 0.0 and 1.0")
    if not isinstance(bucket_size, float) or bucket_size <= 0.0 or bucket_size >= 1.0:
        raise ValueError("bucket_size must be a float between 0.0 and 1.0 (exclusive bounds)")

    # Handle the maximum bound specifically so it doesn't spill over to the next bucket
    if assertiveness == 1.0:
        lower = 1.0 - bucket_size
        return f"{lower:.2f}-1.00"

    bucket_index = math.floor(assertiveness / bucket_size)
    lower_bound = bucket_index * bucket_size
    upper_bound = min(1.0, lower_bound + bucket_size)
    
    # Just visually correct the string to avoid things like 0.70-0.80 overlapping with 0.80-0.90
    # Usually we say 0.70-0.79 or similar, but the exact string doesn't matter for the key as long as it's deterministic.
    upper_display = upper_bound - 0.01 if upper_bound < 1.0 else 1.00
    
    return f"{lower_bound:.2f}-{upper_display:.2f}"

def segment_historical_calibration_data(
    classifications: list[dict],
    outcomes: list[dict],
    *,
    bucket_size: float = 0.10,
) -> dict:
    if bucket_size <= 0.0 or bucket_size >= 1.0:
        raise ValueError("bucket_size must be strictly between 0.0 and 1.0")
        
    _check_operational_language(str(classifications))
    _check_operational_language(str(outcomes))

    # Link outcomes
    # Priority: signal_id > classification_id > opportunity_id
    linked_outcomes = {}
    for out in outcomes:
        sid = out.get("signal_id")
        cid = out.get("classification_id")
        oid = out.get("opportunity_id")
        if sid:
            linked_outcomes[f"sid_{sid}"] = out
        if cid:
            linked_outcomes[f"cid_{cid}"] = out
        if oid:
            linked_outcomes[f"oid_{oid}"] = out

    segments_data = {}
    
    global_totals = {
        "sample_size": 0,
        "resolved_total": 0,
        "unresolved_total": 0,
        "invalidated_total": 0
    }

    for cls in classifications:
        source = str(cls.get("source", "UNKNOWN"))
        detection_method = str(cls.get("detection_method", "UNKNOWN"))
        simulation_label = str(cls.get("simulation_label", "UNKNOWN"))
        market = str(cls.get("market", "UNKNOWN"))
        selection = str(cls.get("selection", "UNKNOWN"))
        
        assertiveness = cls.get("calibrated_assertiveness")
        if assertiveness is None:
            assertiveness = cls.get("assertiveness", 0.0)
            
        bucket_label = get_bucket_label(assertiveness, bucket_size)
        
        key = CalibrationSegmentKey(
            source=source,
            detection_method=detection_method,
            simulation_label=simulation_label,
            market=market,
            selection=selection,
            assertiveness_bucket=bucket_label
        )
        key_tuple = (source, detection_method, simulation_label, market, selection, bucket_label)

        if key_tuple not in segments_data:
            segments_data[key_tuple] = {
                "segment_key": key,
                "classifications": [],
                "outcomes": [],
                "sample_size": 0,
                "resolved_total": 0,
                "unresolved_total": 0,
                "invalidated_total": 0
            }
            
        seg = segments_data[key_tuple]
        seg["classifications"].append(cls)
        seg["sample_size"] += 1
        global_totals["sample_size"] += 1
        
        # Find matching outcome
        sid = cls.get("signal_id")
        cid = cls.get("classification_id")
        oid = cls.get("opportunity_id")
        
        matching_outcome = None
        if sid and f"sid_{sid}" in linked_outcomes:
            matching_outcome = linked_outcomes[f"sid_{sid}"]
        elif cid and f"cid_{cid}" in linked_outcomes:
            matching_outcome = linked_outcomes[f"cid_{cid}"]
        elif oid and f"oid_{oid}" in linked_outcomes:
            matching_outcome = linked_outcomes[f"oid_{oid}"]
            
        if matching_outcome:
            seg["outcomes"].append(matching_outcome)
            status = matching_outcome.get("result_status")
            if status == "INVALIDATED":
                seg["invalidated_total"] += 1
                global_totals["invalidated_total"] += 1
            elif status in ["RESOLVED", "RESOLVED_POSITIVE", "RESOLVED_NEGATIVE", "POSITIVE_OBSERVED", "NEGATIVE_OBSERVED"]:
                seg["resolved_total"] += 1
                global_totals["resolved_total"] += 1
            else:
                seg["unresolved_total"] += 1
                global_totals["unresolved_total"] += 1
        else:
            seg["unresolved_total"] += 1
            global_totals["unresolved_total"] += 1
            
    # Prepare result
    result_segments = []
    # Sort keys for deterministic output
    sorted_keys = sorted(segments_data.keys())
    for k in sorted_keys:
        result_segments.append(segments_data[k])

    return {
        "total_segments": len(result_segments),
        "segments": result_segments,
        "global_totals": global_totals,
        "is_simulated": True,
        "actionable": False
    }
