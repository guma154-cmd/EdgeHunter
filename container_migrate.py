
import sqlite3
import os

# Caminho DENTRO do container
db_path = '/app/database/edgehunter.db'

if os.path.exists(db_path):
    print(f"Conectando ao banco dentro do container: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        columns = [
            ("bookmaker_X", "VARCHAR(50)"),
            ("outcome_X", "VARCHAR(20)"),
            ("odds_X", "FLOAT"),
            ("stake_X", "FLOAT")
        ]
        
        for col_name, col_type in columns:
            try:
                cursor.execute(f"ALTER TABLE surebets ADD COLUMN {col_name} {col_type}")
                print(f"Coluna {col_name} adicionada.")
            except sqlite3.OperationalError as e:
                print(f"Coluna {col_name} falhou: {e}")
                
        conn.commit()
        print("Migração concluída.")
    except Exception as e:
        print(f"Erro fatal na migração: {e}")
    finally:
        conn.close()
else:
    print(f"ERRO: Banco não encontrado em {db_path}")
