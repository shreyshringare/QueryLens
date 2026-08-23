from .models import DatabaseSchema

class SchemaValidator:
    
    def validate(
        self,schema: DatabaseSchema)->list[str]:
        
        errors = []
        
        table_names = set()
        
        for table in schema.tables:
            
            normalized_name = table.name.lower()
            
            if normalized_name in table_names:
                errors.append(
                    f"Duplicate table name found: '{table.name}'"
                )
                
            table_names.add(normalized_name)
            
            column_name = set()
            
            for column in table.columns:
                
                normalized_column_name = column.name.lower()
                
                if normalized_column_name in column_name:
                    errors.append(
                        f"Duplicate column name '{column.name}' found in table '{table.name}'"
                    )
                    
                column_name.add(normalized_column_name)
                
        return errors
    