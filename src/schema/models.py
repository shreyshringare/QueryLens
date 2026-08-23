from dataclasses import dataclass,field

from typing import List

@dataclass
class Column:
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    
@dataclass 
class ForeignKey:
    column: str
    referenced_table: str
    referenced_column: str
    
@dataclass 
class Table:
    name: str
    columns: List[Column] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)
    
    def get_column(self,name:str) -> Column:
        for column in self.columns:
            if column.name == name:
                return column
            
        raise ValueError(f"Column '{name}' not found in table '{self.name}'")

@dataclass
class DatabaseSchema:
    database_id: str
    tables: List[Table] = field(default_factory=list)
    
    def get_table(self,name:str) -> Table | None:
        for table in self.tables:
            if table.name.lower() == name.lower():
                return table
            
        return None
    
    def has_table(self,table_name:str) ->bool:
        return self.get_table(table_name) is not None
    
    def has_column(self,table_name:str,column_name:str)->bool:
        table = self.get_table(table_name)
        if table is None:
            return False
        return table.get_column(column_name) is not None