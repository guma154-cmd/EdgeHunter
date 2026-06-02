from typing import Union
from src.edgehunter.core.observed_result import ObservedResult

def _get_val(obj, key: str) -> str:
    if isinstance(obj, ObservedResult):
        val = getattr(obj, key, "")
    else:
        val = obj.get(key, "")
    return str(val).strip() if val else ""


def _check_operational_language_in_dict(obj: dict) -> None:
    forbidden = [
        "aposta", "apostar", "entrada", "sinal de aposta", "recomendado",
        "recomendação operacional", "recomendacao operacional", "lucro", "gain",
        "stake", "kelly", "bankroll", "bet_amount", "wager", "execute", "execution",
        "place_bet", "telegram", "scheduler", "autoevolution"
    ]
    for k, v in obj.items():
        if isinstance(v, str):
            lower_v = v.lower()
            for word in forbidden:
                if word in lower_v:
                    raise ValueError(f"Operational language blocked: {word}")


def match_observed_results_to_classifications(
    observed_results: list[Union[ObservedResult, dict]],
    classifications: list[dict],
) -> dict:
    matched = []
    unmatched_results = []
    unmatched_classifications = list(classifications)
    duplicates = []
    invalid = []

    # Fast lookups for classifications based on priority
    # priority: signal_id > classification_id > opportunity_id > match_id
    
    # We will just iterate over results and find the best match for each to maintain determinism.
    
    # Pre-check for operational language in dicts
    for cls in classifications:
        _check_operational_language_in_dict(cls)
        
    for res in observed_results:
        if isinstance(res, dict):
            _check_operational_language_in_dict(res)
            
    matched_classification_ids = set()
    matched_result_ids = set()

    # Pre-index classifications for fast lookup
    idx_signal = {}
    idx_class = {}
    idx_opp = {}
    idx_match = {}
    
    for cls in classifications:
        sid = str(cls.get("signal_id", "")).strip()
        cid = str(cls.get("classification_id", "")).strip()
        oid = str(cls.get("opportunity_id", "")).strip()
        mid = str(cls.get("match_id", "")).strip()
        
        if sid: idx_signal[sid] = cls
        if cid: idx_class[cid] = cls
        if oid: idx_opp[oid] = cls
        if mid: idx_match[mid] = cls

    for res in observed_results:
        try:
            res_id = _get_val(res, "result_id")
            if not res_id:
                invalid.append({"result": res, "error": "Missing result_id"})
                continue
                
            if res_id in matched_result_ids:
                duplicates.append({"result": res, "error": "Duplicate result_id processing"})
                continue
                
            # Attempt matching in priority order
            sid = _get_val(res, "signal_id")
            cid = _get_val(res, "classification_id")
            oid = _get_val(res, "opportunity_id")
            mid = _get_val(res, "match_id")
            
            best_match = None
            if sid and sid in idx_signal:
                best_match = idx_signal[sid]
            elif cid and cid in idx_class:
                best_match = idx_class[cid]
            elif oid and oid in idx_opp:
                best_match = idx_opp[oid]
            elif mid and mid in idx_match:
                best_match = idx_match[mid]
                
            if best_match:
                match_cid = str(best_match.get("classification_id", ""))
                if match_cid in matched_classification_ids:
                    # Classification already matched! Duplicate binding
                    duplicates.append({
                        "result": res, 
                        "classification": best_match, 
                        "error": "Classification already matched to another result"
                    })
                else:
                    matched_result_ids.add(res_id)
                    matched_classification_ids.add(match_cid)
                    matched.append({
                        "result": res,
                        "classification": best_match
                    })
            else:
                unmatched_results.append(res)
                
        except Exception as e:
            if isinstance(e, ValueError) and "Operational language blocked" in str(e):
                raise
            invalid.append({"result": res, "error": str(e)})

    # Compute unmatched classifications
    unmatched_classifications = [
        cls for cls in classifications 
        if str(cls.get("classification_id", "")) not in matched_classification_ids
    ]

    return {
        "matched": matched,
        "unmatched_results": unmatched_results,
        "unmatched_classifications": unmatched_classifications,
        "duplicates": duplicates,
        "invalid": invalid,
        "summary": {
            "matched_total": len(matched),
            "unmatched_results_total": len(unmatched_results),
            "unmatched_classifications_total": len(unmatched_classifications),
            "duplicates_total": len(duplicates),
            "invalid_total": len(invalid)
        },
        "is_simulated": True,
        "actionable": False
    }
