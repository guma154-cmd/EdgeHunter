import os

files_flask = [
    'backend/test_apifootball.py',
    'backend/test_oddsio.py',
    'backend/test_oddsportal.py',
    'backend/test_rapidapi.py'
]
for f in files_flask:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if 'pytest.importorskip' not in content:
        with open(f, 'w', encoding='utf-8') as file:
            file.write('import pytest\npytest.importorskip("flask")\n' + content)

file_playwright = 'backend/test_h2h_link.py'
with open(file_playwright, 'r', encoding='utf-8') as file:
    content = file.read()
if 'pytest.importorskip' not in content:
    with open(file_playwright, 'w', encoding='utf-8') as file:
        file.write('import pytest\npytest.importorskip("playwright")\n' + content)

file_remote = 'remote_test.py'
with open(file_remote, 'r', encoding='utf-8') as file:
    content = file.read()
content = content.replace("sys.path.insert(0, '/app')", "current_dir = os.path.dirname(os.path.abspath(__file__))\nsys.path.insert(0, current_dir)")
content = content.replace("os.chdir('/app')", "os.chdir(current_dir)")
with open(file_remote, 'w', encoding='utf-8') as file:
    file.write(content)
