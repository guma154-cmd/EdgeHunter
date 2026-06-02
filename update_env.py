import os
env_path = '/home/telematica/EdgeHunter/.env'
example_path = '/home/telematica/EdgeHunter/.env.example'

existing = {}
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                existing[k] = v

import secrets
api_key = existing.get('EDGEHUNTER_API_KEY', secrets.token_urlsafe(32))

new_config = {
    'EDGEHUNTER_API_KEY': api_key,
    'EDGEHUNTER_DB_PATH': './data/edgehunter.db',
    'EDGEHUNTER_HOST': '127.0.0.1',
    'EDGEHUNTER_PORT': '8000',
    'EDGEHUNTER_READ_ONLY_MODE': 'true',
    'EDGEHUNTER_RUNTIME_ENABLED': 'true',
    'EDGEHUNTER_RUNTIME_DRY_RUN': 'false',
    'EDGEHUNTER_RUNTIME_INTERVAL_SECONDS': '300',
    'EDGEHUNTER_RUNTIME_MAX_CYCLES': '1',
    'TELEGRAM_ENABLED': 'false',
    'SCRAPER_ENABLED': 'false',
    'GEMINI_ENABLED': 'false',
    'TELEGRAM_BOT_TOKEN': existing.get('TELEGRAM_BOT_TOKEN', ''),
    'TELEGRAM_CHAT_ID': existing.get('TELEGRAM_CHAT_ID', ''),
}

with open(example_path, 'r') as ex:
    lines = ex.readlines()

with open(env_path, 'w') as f:
    for line in lines:
        if '=' in line and not line.startswith('#'):
            k = line.split('=')[0]
            if k in new_config:
                f.write(f'{k}={new_config[k]}\n')
            elif k in existing:
                f.write(f'{k}={existing[k]}\n')
            else:
                f.write(line)
        else:
            f.write(line)

print('Done')
