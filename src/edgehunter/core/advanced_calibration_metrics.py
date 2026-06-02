from src.edgehunter.core.advanced_calibration_models import _check_operational_language

def calculate_segment_calibration_metrics(
    segmented_data: dict,
    *,
    min_sample_size: int = 10,
) -> dict:
    if min_sample_size < 1:
        raise ValueError("min_sample_size must be >= 1")

    # Safety check
    _check_operational_language(str(segmented_data))

    result_segments = []

    for seg in segmented_data.get("segments", []):
        sample_size = seg.get("sample_size", 0)
        resolved_total = seg.get("resolved_total", 0)
        unresolved_total = seg.get("unresolved_total", 0)
        invalidated_total = seg.get("invalidated_total", 0)
        
        green_pos = 0
        green_neg = 0
        red_pos = 0
        red_neg = 0
        
        total_assertiveness = 0.0
        total_confidence = 0.0
        
        classifications = seg.get("classifications", [])
        outcomes = seg.get("outcomes", [])
        
        for cls in classifications:
            ast = cls.get("calibrated_assertiveness", cls.get("assertiveness", 0.0))
            cnf = cls.get("confidence", 0.0)
            total_assertiveness += float(ast)
            total_confidence += float(cnf)
            
            # Find matching outcome
            sid = cls.get("signal_id")
            cid = cls.get("classification_id")
            oid = cls.get("opportunity_id")
            
            matching_out = None
            for out in outcomes:
                if out.get("signal_id") == sid and sid is not None:
                    matching_out = out
                    break
                elif out.get("classification_id") == cid and cid is not None:
                    matching_out = out
                    break
                elif out.get("opportunity_id") == oid and oid is not None:
                    matching_out = out
                    break
            
            if matching_out:
                status = matching_out.get("result_status")
                sim_label = str(cls.get("simulation_label", "UNKNOWN")).upper()
                
                # Treat "RESOLVED_POSITIVE" as "POSITIVE_OBSERVED" for matching purposes if legacy names exist
                if status in ["POSITIVE_OBSERVED", "RESOLVED_POSITIVE"]:
                    if "GREEN" in sim_label:
                        green_pos += 1
                    elif "RED" in sim_label:
                        red_pos += 1
                elif status in ["NEGATIVE_OBSERVED", "RESOLVED_NEGATIVE"]:
                    if "GREEN" in sim_label:
                        green_neg += 1
                    elif "RED" in sim_label:
                        red_neg += 1
                        
        confirmed_total = green_pos + red_neg
        not_confirmed_total = green_neg + red_pos
        
        # In case there are outcomes we didn't account for but were marked resolved, 
        # let's be strict with denominators based on what we captured.
        # The true resolved total should be the sum of these 4 if they were all either GREEN/RED and POS/NEG.
        # But we'll use the tracked resolved_total for global rates to be safe.
        
        confirmation_rate = confirmed_total / resolved_total if resolved_total > 0 else 0.0
        not_confirmed_rate = not_confirmed_total / resolved_total if resolved_total > 0 else 0.0
        
        green_resolved = green_pos + green_neg
        red_resolved = red_pos + red_neg
        
        green_confirmation_rate = green_pos / green_resolved if green_resolved > 0 else 0.0
        green_not_confirmed_rate = green_neg / green_resolved if green_resolved > 0 else 0.0
        
        red_rejection_confirmation_rate = red_neg / red_resolved if red_resolved > 0 else 0.0
        red_missed_positive_rate = red_pos / red_resolved if red_resolved > 0 else 0.0
        
        false_positive_rate = green_neg / resolved_total if resolved_total > 0 else 0.0
        false_negative_rate = red_pos / resolved_total if resolved_total > 0 else 0.0
        
        average_calibrated_assertiveness = total_assertiveness / sample_size if sample_size > 0 else 0.0
        average_confidence = total_confidence / sample_size if sample_size > 0 else 0.0
        
        metrics = {
            "segment_key": seg.get("segment_key"),
            "sample_size": sample_size,
            "resolved_total": resolved_total,
            "unresolved_total": unresolved_total,
            "invalidated_total": invalidated_total,
            "confirmed_total": confirmed_total,
            "not_confirmed_total": not_confirmed_total,
            "confirmation_rate": confirmation_rate,
            "not_confirmed_rate": not_confirmed_rate,
            "green_confirmation_rate": green_confirmation_rate,
            "green_not_confirmed_rate": green_not_confirmed_rate,
            "red_rejection_confirmation_rate": red_rejection_confirmation_rate,
            "red_missed_positive_rate": red_missed_positive_rate,
            "average_calibrated_assertiveness": average_calibrated_assertiveness,
            "average_confidence": average_confidence,
            "false_positive_rate": false_positive_rate,
            "false_negative_rate": false_negative_rate,
            "minimum_sample_met": sample_size >= min_sample_size,
            "is_simulated": True,
            "actionable": False
        }
        
        result_segments.append(metrics)

    return {
        "metrics_by_segment": result_segments,
        "is_simulated": True,
        "actionable": False
    }
