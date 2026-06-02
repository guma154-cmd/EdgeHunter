# Backup e Restore do SQLite

## 1. Como Criar Backup
Para gerar uma cópia segura (com path traversal validation) sem envolver processos externos e shells não autorizados:

```python
from src.edgehunter.ops.backup_restore import create_local_backup

result = create_local_backup(
    db_path="data/edgehunter.db",
    backup_dir="backups/"
)
print(result)
```

## 2. Como Validar Backup
Antes de aplicar um restore, sempre efetue a validação de integridade. A camada verificará o `.bak` sem abrir o banco em modo write.

```python
from src.edgehunter.ops.backup_restore import validate_backup_file

validation = validate_backup_file("backups/edgehunter.db.20260101_100000.bak")
if validation["status"] == "VALID":
    print("O backup está íntegro e legível.")
```

## 3. Como Restaurar em Dry-Run
O default de `restore_local_backup` é o modo de simulação, validando se todos os arquivos estão íntegros e os paths são seguros antes de qualquer IO.

```python
from src.edgehunter.ops.backup_restore import restore_local_backup

restore_local_backup(
    backup_path="backups/edgehunter.db.20260101_100000.bak",
    target_db_path="data/edgehunter.db",
    dry_run=True
)
```

## 4. Como Restaurar de Verdade
Uma vez validado o dry-run e aprovada a consistência de banco, aplique:

```python
from src.edgehunter.ops.backup_restore import restore_local_backup

restore_local_backup(
    backup_path="backups/edgehunter.db.20260101_100000.bak",
    target_db_path="data/edgehunter.db",
    dry_run=False
)
```

## 5. Riscos e Cuidados
- **Isolamento de Diretório**: Nunca armazene seus backups em caminhos expostos por qualquer servidor web.
- **Corrupção de Concorrência**: O SQLite realiza lock próprio no backup. Recomendamos interromper a aplicação/API local (Uvicorn) caso queira realizar um _restore_ de verdade, evitando travas no arquivo durante o overwrite.
- **Não há Deleção**: O sistema não exclui backups antigos. A rotatividade de dados (housekeeping) deve ser realizada manualmente no diretório de backups.
