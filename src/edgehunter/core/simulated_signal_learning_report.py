from typing import Optional

FORBIDDEN_FIELDS = {
    "stake", "kelly", "kelly_criterion", "bankroll", "bet_amount", 
    "wager", "suggested_bet", "recommended_bet", "recommendation", 
    "execute", "execution", "place_bet"
}

def generate_simulated_signal_learning_report(
    classifications: list[dict],
    outcomes: Optional[dict[str, bool]] = None
) -> dict:
    if outcomes is None:
        outcomes = {}
        
    total_classifications = len(classifications)
    green_total = 0
    red_total = 0
    resolved_total = 0
    unresolved_total = 0
    
    green_success = 0
    green_fp = 0
    red_success = 0
    red_fn = 0
    
    sum_calibrated_assertiveness = 0.0
    sum_confidence = 0.0
    
    by_label = {
        "GREEN_SIM": {
            "total": 0,
            "resolved": 0,
            "unresolved": 0,
            "success": 0,
            "false_positive": 0,
            "average_calibrated_assertiveness": 0.0,
            "average_confidence": 0.0,
        },
        "RED_SIM": {
            "total": 0,
            "resolved": 0,
            "unresolved": 0,
            "success": 0,
            "false_negative": 0,
            "average_calibrated_assertiveness": 0.0,
            "average_confidence": 0.0,
        }
    }
    
    for c in classifications:
        # Security checks
        if c.get("actionable") or c.get("bet_placed") or c.get("alerted"):
            raise ValueError("Operational flags (actionable, bet_placed, alerted) must be False")
            
        for key in c.keys():
            if key.lower() in FORBIDDEN_FIELDS:
                raise ValueError(f"Forbidden financial field found: {key}")
                
        label = c.get("simulation_label")
        signal_id = c.get("signal_id")
        
        ca = float(c.get("calibrated_assertiveness", 0.0))
        conf = float(c.get("confidence", 0.0))
        
        sum_calibrated_assertiveness += ca
        sum_confidence += conf
        
        if label == "GREEN_SIM":
            green_total += 1
            by_label["GREEN_SIM"]["total"] += 1
            by_label["GREEN_SIM"]["average_calibrated_assertiveness"] += ca
            by_label["GREEN_SIM"]["average_confidence"] += conf
            
            if signal_id in outcomes:
                resolved_total += 1
                by_label["GREEN_SIM"]["resolved"] += 1
                outcome = outcomes[signal_id]
                if outcome:
                    green_success += 1
                    by_label["GREEN_SIM"]["success"] += 1
                else:
                    green_fp += 1
                    by_label["GREEN_SIM"]["false_positive"] += 1
            else:
                unresolved_total += 1
                by_label["GREEN_SIM"]["unresolved"] += 1
                
        elif label == "RED_SIM":
            red_total += 1
            by_label["RED_SIM"]["total"] += 1
            by_label["RED_SIM"]["average_calibrated_assertiveness"] += ca
            by_label["RED_SIM"]["average_confidence"] += conf
            
            if signal_id in outcomes:
                resolved_total += 1
                by_label["RED_SIM"]["resolved"] += 1
                outcome = outcomes[signal_id]
                # RED_SIM success means the signal failed (outcome False)
                if not outcome:
                    red_success += 1
                    by_label["RED_SIM"]["success"] += 1
                else:
                    red_fn += 1
                    by_label["RED_SIM"]["false_negative"] += 1
            else:
                unresolved_total += 1
                by_label["RED_SIM"]["unresolved"] += 1
                
    if green_total > 0:
        by_label["GREEN_SIM"]["average_calibrated_assertiveness"] /= green_total
        by_label["GREEN_SIM"]["average_confidence"] /= green_total
        
    if red_total > 0:
        by_label["RED_SIM"]["average_calibrated_assertiveness"] /= red_total
        by_label["RED_SIM"]["average_confidence"] /= red_total
        
    green_resolved = by_label["GREEN_SIM"]["resolved"]
    red_resolved = by_label["RED_SIM"]["resolved"]
    
    return {
        "total_classifications": total_classifications,
        "green_total": green_total,
        "red_total": red_total,
        "resolved_total": resolved_total,
        "unresolved_total": unresolved_total,
        "green_success_rate": green_success / green_resolved if green_resolved > 0 else 0.0,
        "red_success_rate": red_success / red_resolved if red_resolved > 0 else 0.0,
        "green_false_positive_rate": green_fp / green_resolved if green_resolved > 0 else 0.0,
        "red_false_negative_rate": red_fn / red_resolved if red_resolved > 0 else 0.0,
        "average_calibrated_assertiveness": sum_calibrated_assertiveness / total_classifications if total_classifications > 0 else 0.0,
        "average_confidence": sum_confidence / total_classifications if total_classifications > 0 else 0.0,
        "by_label": by_label,
        "is_simulated": True,
        "paper_trading": True,
        "actionable": False,
        "not_operational_advice": True
    }
