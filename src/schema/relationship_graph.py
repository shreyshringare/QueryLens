from .models import DatabaseSchema
from .relationships import Relationship

def extract_relationships(
    schema: DatabaseSchema
) -> list[Relationship]:
    
    relationships = []
    
    for table in schema.tables:
        for foreign_key in table.foreign_keys:
            
            relationships.append(
                Relationship(
                    source_table=table.name,
                    source_column=foreign_key.column,
                    target_table=foreign_key.referenced_table,
                    target_column=foreign_key.referenced_column
                )
            )
            
    return relationships