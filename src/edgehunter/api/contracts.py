FORBIDDEN_FIELDS = {
    "stake", "kelly", "kelly_criterion", "bankroll", "bet_amount", "wager",
    "suggested_bet", "recommended_bet", "execute", "execution", "place_bet",
    "entrada"
}

def _check_forbidden_fields(data: dict):
    for key, value in data.items():
        k = str(key).lower()
        if k in FORBIDDEN_FIELDS:
            raise ValueError(f"Forbidden field found: {key}")
        if k == "actionable" and value is True:
            raise ValueError("actionable cannot be true")
        if k == "bet_placed" and value is True:
            raise ValueError("bet_placed cannot be true")
        if k == "alerted" and value is True:
            raise ValueError("alerted cannot be true")
        
        if isinstance(value, dict):
            _check_forbidden_fields(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _check_forbidden_fields(item)

def build_safe_api_response(payload: dict, *, message: str | None = None) -> dict:
    _check_forbidden_fields(payload)
    
    response = {
        "is_simulated": True,
        "paper_trading": True,
        "learning_mode": True,
        "actionable": False,
        "bet_placed": False,
        "alerted": False,
        "not_operational_advice": True,
        "disclaimer": "Data is simulated/paper trading only and is not betting advice.",
        "data": payload
    }
    if message is not None:
        response["message"] = message
    return response
