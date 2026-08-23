from dataclasses import asdict

from .models import DatabaseSchema

def schema_to_dict(schema: DatabaseSchema) -> dict:
    return asdict(schema)

def schema_to_json(schema: DatabaseSchema) -> str:
    import json
    return json.dumps(schema_to_dict(schema), indent=2)