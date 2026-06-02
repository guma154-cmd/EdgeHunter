from src.edgehunter.core.simulated_signal_classifier_persistence import list_simulated_signal_classifications
from src.edgehunter.core.simulated_signal_outcome_persistence import list_simulated_signal_outcomes


def generate_reconciliation_report(db_path: str) -> dict:
    """
    Generates a read-only reconciliation report between classifications and outcomes.
    """
    # Fetch all (up to a large limit or we could use custom queries, but using existing lists for simplicity)
    classifications = list_simulated_signal_classifications(db_path, limit=1000)["data"]
    outcomes = list_simulated_signal_outcomes(db_path, limit=1000)["data"]

    matched_count = 0
    pending_classifications = []
    
    # Map outcomes by classification_id
    outcome_by_cid = {o["classification_id"]: o for o in outcomes}
    
    for cls in classifications:
        cid = cls["classification_id"]
        if cid in outcome_by_cid:
            matched_count += 1
        else:
            pending_classifications.append(cls)
            
    unmatched_outcomes = [o for o in outcomes if o["classification_id"] not in {c["classification_id"] for c in classifications}]

    return {
        "summary": {
            "total_classifications": len(classifications),
            "total_outcomes": len(outcomes),
            "matched_outcomes": matched_count,
            "pending_classifications": len(pending_classifications),
            "unmatched_outcomes": len(unmatched_outcomes)
        },
        "pending_classifications_sample": pending_classifications[:10],
        "is_simulated": True,
        "actionable": False,
        "not_operational_advice": True
    }
