import sys

class PancoError(Exception):
    def __init__(self, message, filepath, line, column, length=1, source_code=None):
        super().__init__(message)
        self.message = message
        self.filepath = filepath
        self.line = line
        self.column = column
        self.length = length
        self.source_code = source_code

    def __str__(self):
        return self.format_error()

    def format_error(self):
        # ANSI Escape Codes for formatting
        RED = "\033[91;1m"
        BLUE = "\033[94;1m"
        BOLD = "\033[1m"
        RESET = "\033[0m"

        error_type = self.__class__.__name__.replace("Panco", "")
        # Add spacing/labels to match the Rust/Elm styling
        result = f"{RED}Error [{error_type}]:{RESET} {BOLD}{self.message}{RESET}\n"
        result += f"  {BLUE}-->{RESET} {self.filepath}:{self.line}:{self.column}\n"

        if self.source_code and self.line > 0:
            lines = self.source_code.splitlines()
            if 0 <= self.line - 1 < len(lines):
                error_line = lines[self.line - 1]
                
                # Format the line number
                line_str = str(self.line)
                padding = len(line_str)
                
                result += f"{' ' * padding} {BLUE}|{RESET}\n"
                result += f"{line_str} {BLUE}|{RESET} {error_line}\n"
                
                # Highlight the exact column location
                marker_padding = self.column - 1
                markers = "^" * max(1, self.length)
                result += f"{' ' * padding} {BLUE}|{RESET} {' ' * marker_padding}{RED}{markers}{RESET}\n"
        return result

class PancoSyntaxError(PancoError):
    pass

class PancoRuntimeError(PancoError):
    pass
