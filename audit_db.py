import sqlite3
import os

db_path = '/home/telematica/EdgeHunter/data/edgehunter.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- Auditoria de Banco de Dados ---")
try:
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    print(f"Tabelas encontradas: {tables}")

    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"Tabela {table}: {count} registros")

    if 'matches' in tables:
        c.execute("SELECT MAX(updated_at) FROM matches")
        last_update = c.fetchone()[0]
        print(f"Última atualização em 'matches': {last_update}")

except Exception as e:
    print(f"Erro na auditoria: {e}")

conn.close()
