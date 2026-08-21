from dataclasses import dataclass,field
from typing import Any

@dataclass
class NormalizedQuery:
    id:str
    source:str
    domain:str
    dialect:str
    database_id:str
    nl_question:str
    ground_truth_sql:str
    ddl:str
    metadata: dict[str,Any]=field(default_factory=dict)
    