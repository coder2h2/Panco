from interpreter.errors import PancoRuntimeError

class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent

    def define(self, name, value):
        self.values[name] = value

    def get(self, name, token, filepath, source_code):
        if name in self.values:
            return self.values[name]
            
        if self.parent:
            return self.parent.get(name, token, filepath, source_code)
            
        raise PancoRuntimeError(
            f"Undefined variable '{name}'.",
            filepath,
            token.line,
            token.column,
            token.length,
            source_code
        )

    def assign(self, name, value, token, filepath, source_code):
        if name in self.values:
            self.values[name] = value
            return
            
        if self.parent:
            self.parent.assign(name, value, token, filepath, source_code)
            return
            
        raise PancoRuntimeError(
            f"Undefined variable '{name}' for assignment.",
            filepath,
            token.line,
            token.column,
            token.length,
            source_code
        )
