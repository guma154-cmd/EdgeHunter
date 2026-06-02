with open(".env", "r") as f:
    lines = f.readlines()
with open(".env", "w") as f:
    f.writelines([l for l in lines if "GEMINI" not in l and "TELEGRAM" not in l])
