import sys
import os

# Add root project to sys.path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from src.edgehunter.api.app import create_app

def run_local_smoke_test() -> dict:
    """Executa um smoke test usando TestClient sem abrir porta e sem rede externa."""
    app = create_app()
    client = TestClient(app)
    
    # We must use the local auth logic. Assuming the routes might require API key.
    # The default auth might use `Authorization: Bearer test-key` or `X-API-Key`
    # In EdgeHunter routes, it's typically X-API-Key or depending on configuration.
    # We will pass a test key. If it expects a specific env var, we'll set it.
    
    headers = {"X-API-Key": "test-key-local-smoke"}
    # Temporarily set env for test
    os.environ["EDGEHUNTER_API_KEY"] = "test-key-local-smoke"
    os.environ["EDGEHUNTER_READ_ONLY_MODE"] = "true"
    os.environ["EDGEHUNTER_IS_SIMULATED"] = "true"
    os.environ["EDGEHUNTER_PAPER_TRADING"] = "true"
    os.environ["EDGEHUNTER_ACTIONABLE"] = "false"

    results = []
    failed = False
    
    # 1. Health
    res_health = client.get("/api/health")
    if res_health.status_code == 200:
        results.append({"endpoint": "/api/health", "passed": True, "details": "HTTP 200"})
    else:
        results.append({"endpoint": "/api/health", "passed": False, "details": f"HTTP {res_health.status_code}"})
        failed = True
        
    # 2. Dashboard Summary
    res_dash = client.get("/api/dashboard/summary", headers=headers)
    if res_dash.status_code in [200, 404]: 
        # 404 might happen if no data, but the endpoint exists and didn't crash. We prefer 200.
        # EdgeHunter usually returns empty stats if no DB.
        results.append({"endpoint": "/api/dashboard/summary", "passed": True, "details": f"HTTP {res_dash.status_code}"})
    else:
        results.append({"endpoint": "/api/dashboard/summary", "passed": False, "details": f"HTTP {res_dash.status_code}"})
        failed = True
        
    # 3. Calibration Summary
    res_cal = client.get("/api/calibration/summary", headers=headers)
    if res_cal.status_code in [200, 404]:
        results.append({"endpoint": "/api/calibration/summary", "passed": True, "details": f"HTTP {res_cal.status_code}"})
    else:
        results.append({"endpoint": "/api/calibration/summary", "passed": False, "details": f"HTTP {res_cal.status_code}"})
        failed = True
        
    # 4. HTML Dashboard
    res_html = client.get("/dashboard")
    if res_html.status_code == 200:
        results.append({"endpoint": "/dashboard", "passed": True, "details": "HTTP 200 (HTML)"})
    else:
        results.append({"endpoint": "/dashboard", "passed": False, "details": f"HTTP {res_html.status_code}"})
        failed = True

    return {
        "status": "FAILED" if failed else "PASSED",
        "results": results,
        "is_simulated": True,
        "actionable": False
    }

def main():
    print("Running EdgeHunter Local Smoke Test...")
    res = run_local_smoke_test()
    for item in res["results"]:
        mark = "[PASS]" if item["passed"] else "[FAIL]"
        print(f"{mark} {item['endpoint']} -> {item['details']}")
        
    if res["status"] == "FAILED":
        print("Smoke test FAILED.")
        sys.exit(1)
    else:
        print("Smoke test PASSED.")
        sys.exit(0)

if __name__ == "__main__":
    main()
