class AliasResolver:

    def __init__(self):
        self.aliases: dict[str, str] = {}

    def add(self, alias: str, table: str):
        self.aliases[alias.lower()] = table

    def resolve(self, name: str) -> str:
        return self.aliases.get(name.lower(), name)
