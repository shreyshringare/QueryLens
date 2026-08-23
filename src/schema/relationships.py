from dataclasses import dataclass

@dataclass 
class Relationship:
    source_table: str
    source_column: str
    target_table: str
    target_column: str