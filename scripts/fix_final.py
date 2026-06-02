import re

with open(".env", "r") as f:
    c = f.read()

c = re.sub(r"^TELEGRAM_ENABLED=.*$", "TELEGRAM_ENABLED=false", c, flags=re.MULTILINE)
c = re.sub(r"^SCRAPER_ENABLED=.*$", "SCRAPER_ENABLED=true", c, flags=re.MULTILINE)

with open(".env", "w") as f:
    f.write(c)
