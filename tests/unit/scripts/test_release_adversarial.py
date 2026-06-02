import os
import pytest

def test_docs_contain_no_forbidden_words():
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    forbidden_words = [
        "aposta", "apostar", "entrada", "sinal de aposta", "recomendação operacional",
        "lucro", "gain", "stake", "Kelly", "bankroll", "bet_amount", "wager",
        "place_bet", "AutoEvolution"
    ]
    
    docs_to_check = [
        "docs/OPERATIONS_MANUAL.md",
        "docs/LOCAL_DEPLOYMENT.md",
        "docs/BACKUP_RESTORE.md",
        "docs/RELEASE_CHECKLIST.md"
    ]
    
    for doc in docs_to_check:
        full_path = os.path.join(base_path, doc)
        if not os.path.exists(full_path):
            continue
            
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for word in forbidden_words:
                assert word.lower() not in content, f"Forbidden word '{word}' found in {doc}"

def test_scripts_contain_no_forbidden_words():
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    forbidden_words = [
        "aposta", "apostar", "entrada", "sinal de aposta", "recomendação operacional",
        "lucro", "gain", "stake", "Kelly", "bankroll", "bet_amount", "wager",
        "place_bet", "AutoEvolution"
    ]
    
    scripts_to_check = [
        "scripts/run_local_api.py",
        "scripts/smoke_test_local.py",
        "scripts/release_check.py"
    ]
    
    for script in scripts_to_check:
        full_path = os.path.join(base_path, script)
        if not os.path.exists(full_path):
            continue
            
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            for word in forbidden_words:
                assert word.lower() not in content, f"Forbidden word '{word}' found in {script}"
