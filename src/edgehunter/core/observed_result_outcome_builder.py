import uuid
from src.edgehunter.core.observed_result import ObservedResultStatus
from src.edgehunter.core.simulated_signal_outcome import SimulatedSignalOutcome, OutcomeStatus


def _map_status(status: ObservedResultStatus) -> OutcomeStatus:
    return OutcomeStatus(status.value)


def build_simulated_outcomes_from_matches(matches: list[dict]) -> list[SimulatedSignalOutcome]:
    outcomes = []
    
    for match in matches:
        result = match["result"]
        classification = match["classification"]
        
        # Result can be a dict (from parser) or ObservedResult object
        def _get(obj, key):
            if hasattr(obj, key):
                return getattr(obj, key)
            return obj.get(key)
            
        result_status = _get(result, "result_status")
        if isinstance(result_status, str):
            result_status = ObservedResultStatus(result_status)
            
        outcome_status = _map_status(result_status)
        
        # We create a new UUID for the simulated outcome or use result_id?
        # Usually it's better to generate a new uuid to isolate models, but let's use a deterministic one if we can or just uuid4.
        # Actually, using result_id might be okay. Let's just generate uuid4 for outcome_id.
        
        outcome_id = str(uuid.uuid4())
        
        # We need signal_id, classification_id, opportunity_id from classification, and observed_at from result
        signal_id = str(classification.get("signal_id", ""))
        classification_id = str(classification.get("classification_id", ""))
        opportunity_id = str(classification.get("opportunity_id", ""))
        
        observed_at = _get(result, "observed_at")
        if not isinstance(observed_at, str):
            # If datetime object, convert to isoformat
            observed_at = observed_at.isoformat()
            
        # source usually comes from result source_ref or source
        source_val = _get(result, "source")
        if hasattr(source_val, "value"):
            source_val = source_val.value
            
        source_ref = _get(result, "source_ref") or ""
        source = f"{source_val}:{source_ref}" if source_ref else source_val
        
        notes = _get(result, "notes") or ""
        
        outcome = SimulatedSignalOutcome.from_dict({
            "outcome_id": outcome_id,
            "signal_id": signal_id,
            "classification_id": classification_id,
            "opportunity_id": opportunity_id,
            "outcome_status": outcome_status.value,
            "observed_at": observed_at,
            "source": source,
            "notes": notes,
            "is_simulated": True,
            "paper_trading": True,
            "learning_mode": True,
            "actionable": False,
            "bet_placed": False,
            "alerted": False,
            "not_operational_advice": True,
        })
        outcomes.append(outcome)
        
    return outcomes
