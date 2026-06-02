from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

class MigrationOperation(Enum):
    CREATE_TABLE = "CREATE_TABLE"
    ADD_COLUMN = "ADD_COLUMN"
    CREATE_INDEX = "CREATE_INDEX"
    VALIDATE_SCHEMA = "VALIDATE_SCHEMA"
    NO_OP = "NO_OP"

class MigrationSafetyLevel(Enum):
    SAFE = "SAFE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"

class MigrationExecutionMode(Enum):
    DRY_RUN = "DRY_RUN"
    APPLY = "APPLY"

class MigrationResultStatus(Enum):
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    VALIDATED = "VALIDATED"
    PENDING = "PENDING"

@dataclass(frozen=True)
class MigrationDefinition:
    migration_id: str
    version: int
    name: str
    operation: MigrationOperation
    safety_level: MigrationSafetyLevel
    checksum: str
    is_simulated: bool = True
    actionable: bool = False
    not_operational_advice: bool = True

    def __post_init__(self):
        if not self.migration_id or not self.name or not self.checksum:
            raise ValueError("migration_id, name, and checksum cannot be empty")
        
        if self.safety_level not in MigrationSafetyLevel:
            raise ValueError("Invalid safety level")
            
        if self.operation not in MigrationOperation:
            raise ValueError("Invalid operation")
            
        # Security constraints
        if not self.is_simulated or self.actionable or not self.not_operational_advice:
            raise ValueError("Migration definitions must be strictly simulated and not actionable")
            
        # Hard block on dangerous operational language (as a safeguard)
        forbidden = ["stake", "kelly", "bankroll", "execute", "bet", "financial"]
        for field in [self.migration_id, self.name]:
            for f in forbidden:
                if f in field.lower():
                    raise ValueError(f"Forbidden operational language in migration definition: {f}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "version": self.version,
            "name": self.name,
            "operation": self.operation.value,
            "safety_level": self.safety_level.value,
            "checksum": self.checksum,
            "is_simulated": self.is_simulated,
            "actionable": self.actionable,
            "not_operational_advice": self.not_operational_advice
        }

@dataclass(frozen=True)
class MigrationPlanItem:
    definition: MigrationDefinition
    status: MigrationResultStatus

    def to_dict(self) -> Dict[str, Any]:
        return {
            "definition": self.definition.to_dict(),
            "status": self.status.value
        }

@dataclass(frozen=True)
class MigrationPlan:
    execution_mode: MigrationExecutionMode
    items: List[MigrationPlanItem]
    is_simulated: bool = True
    actionable: bool = False
    not_operational_advice: bool = True

    def __post_init__(self):
        if self.execution_mode not in MigrationExecutionMode:
            raise ValueError("Invalid execution mode")
            
        if not self.is_simulated or self.actionable or not self.not_operational_advice:
            raise ValueError("Migration plan must be strictly simulated and not actionable")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_mode": self.execution_mode.value,
            "items": [item.to_dict() for item in self.items],
            "is_simulated": self.is_simulated,
            "actionable": self.actionable,
            "not_operational_advice": self.not_operational_advice
        }

@dataclass(frozen=True)
class MigrationResult:
    migration_id: str
    status: MigrationResultStatus
    details: Dict[str, Any]
    is_simulated: bool = True
    actionable: bool = False
    not_operational_advice: bool = True

    def __post_init__(self):
        if not self.migration_id:
            raise ValueError("migration_id cannot be empty")
            
        if self.status not in MigrationResultStatus:
            raise ValueError("Invalid status")
            
        if not self.is_simulated or self.actionable or not self.not_operational_advice:
            raise ValueError("Migration result must be strictly simulated and not actionable")
            
        if "sql" in self.details:
            forbidden = ["drop table", "drop column", "delete from"]
            sql = str(self.details["sql"]).lower()
            if any(f in sql for f in forbidden):
                raise ValueError("Destructive operations are forbidden in this context")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "status": self.status.value,
            "details": self.details,
            "is_simulated": self.is_simulated,
            "actionable": self.actionable,
            "not_operational_advice": self.not_operational_advice
        }
