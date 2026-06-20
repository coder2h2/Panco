import enum
from interpreter.errors import PancoSyntaxError

class TokenType(enum.Enum):
    # Single-character tokens
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    COLON = ":"
    SEMICOLON = ";"
    
    # Operators (one or two characters)
    PLUS = "+"
    MINUS = "-"
    MUL = "*"
    DIV = "/"
    MOD = "%"
    ASSIGN = "="
    
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="
    
    PIPE = "->"
    
    # Literals
    IDENTIFIER = "IDENTIFIER"
    STRING = "STRING"
    NUMBER = "NUMBER"
    
    # Keywords
    ALLOW = "allow"
    DELTA = "delta"
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    FOR = "for"
    IN = "in"
    RETURN = "return"
    TRUE = "true"
    FALSE = "false"
    NIL = "nil"
    AND = "and"
    OR = "or"
    NOT = "not"
    
    DOT = "."
    IMPORT = "import"
    FROM = "from"
    IMPORT_DEFAULT = "import#"
    BACKSLASH = "\\"
    
    EOF = "EOF"

class Token:
    def __init__(self, token_type, value, line, column, length=1):
        self.type = token_type
        self.value = value
        self.line = line
        self.column = column
        self.length = length

    def __repr__(self):
        return f"Token({self.type.name}, {repr(self.value)}, L{self.line}:C{self.column})"

KEYWORDS = {
    "allow": TokenType.ALLOW,
    "let": TokenType.ALLOW,
    "delta": TokenType.DELTA,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "return": TokenType.RETURN,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "nil": TokenType.NIL,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
}

class Lexer:
    def __init__(self, source_code, filepath="<string>"):
        self.source = source_code
        self.filepath = filepath
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.token_start_column = 1

    def scan_tokens(self):
        while not self.is_at_end():
            self.start = self.current
            self.token_start_column = self.column
            self.scan_token()
            
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column, 1))
        return self.tokens

    def is_at_end(self):
        return self.current >= len(self.source)

    def advance(self):
        char = self.source[self.current]
        self.current += 1
        self.column += 1
        return char

    def peek(self):
        if self.is_at_end():
            return "\0"
        return self.source[self.current]

    def peek_next(self):
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def match(self, expected):
        if self.is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        self.current += 1
        self.column += 1
        return True

    def error(self, message, length=1):
        raise PancoSyntaxError(
            message,
            self.filepath,
            self.line,
            self.token_start_column,
            length,
            self.source
        )

    def scan_token(self):
        char = self.advance()
        
        # Single-character tokens
        if char == "(":
            self.add_token(TokenType.LPAREN)
        elif char == ")":
            self.add_token(TokenType.RPAREN)
        elif char == "{":
            self.add_token(TokenType.LBRACE)
        elif char == "}":
            self.add_token(TokenType.RBRACE)
        elif char == "[":
            self.add_token(TokenType.LBRACKET)
        elif char == "]":
            self.add_token(TokenType.RBRACKET)
        elif char == ",":
            self.add_token(TokenType.COMMA)
        elif char == ":":
            self.add_token(TokenType.COLON)
        elif char == ";":
            self.add_token(TokenType.SEMICOLON)
        elif char == ".":
            self.add_token(TokenType.DOT)
        elif char == "\\":
            self.add_token(TokenType.BACKSLASH)
        
        # Operators
        elif char == "+":
            self.add_token(TokenType.PLUS)
        elif char == "-":
            if self.match(">"):
                self.add_token(TokenType.PIPE)
            else:
                self.add_token(TokenType.MINUS)
        elif char == "*":
            self.add_token(TokenType.MUL)
        elif char == "%":
            self.add_token(TokenType.MOD)
        elif char == "/":
            if self.match("/"):
                # Line comment
                while self.peek() != "\n" and not self.is_at_end():
                    self.advance()
            else:
                self.add_token(TokenType.DIV)
        elif char == "#":
            # Python-style comment
            while self.peek() != "\n" and not self.is_at_end():
                self.advance()
        elif char == "=":
            if self.match("="):
                self.add_token(TokenType.EQ)
            else:
                self.add_token(TokenType.ASSIGN)
        elif char == "!":
            if self.match("="):
                self.add_token(TokenType.NE)
            else:
                # In Panco, 'not' is a keyword, but let's allow '!' too
                # Let's treat '!' as keyword not or just error out or define a NOT operator.
                # Let's map it to TokenType.NOT!
                self.add_token(TokenType.NOT)
        elif char == "<":
            if self.match("="):
                self.add_token(TokenType.LE)
            else:
                self.add_token(TokenType.LT)
        elif char == ">":
            if self.match("="):
                self.add_token(TokenType.GE)
            else:
                self.add_token(TokenType.GT)
        
        # Whitespace
        elif char in (" ", "\r", "\t"):
            pass
        elif char == "\n":
            self.line += 1
            self.column = 1
            
        # Literals
        elif char == '"':
            self.string()
        elif char.isdigit():
            self.number()
        elif char.isalpha() or char == "_":
            self.identifier()
        else:
            self.error(f"Unexpected character '{char}'")

    def add_token(self, token_type, value=None):
        text = self.source[self.start:self.current]
        length = self.current - self.start
        self.tokens.append(Token(token_type, value if value is not None else text, self.line, self.token_start_column, length))

    def string(self):
        value_chars = []
        while not self.is_at_end():
            char = self.peek()
            if char == '"':
                break
            elif char == "\n":
                self.line += 1
                self.column = 1
                value_chars.append(self.advance())
            elif char == "\\":
                self.advance() # consume '\\'
                if self.is_at_end():
                    self.error("Unterminated string escape sequence", self.current - self.start)
                esc = self.advance()
                if esc == "n":
                    value_chars.append("\n")
                elif esc == "t":
                    value_chars.append("\t")
                elif esc == "e":
                    value_chars.append("\x1b")
                elif esc == "x":
                    if self.current + 2 <= len(self.source):
                        hex_digits = self.source[self.current:self.current+2]
                        try:
                            val = int(hex_digits, 16)
                            value_chars.append(chr(val))
                            self.current += 2
                            self.column += 2
                        except ValueError:
                            value_chars.append("\\x")
                    else:
                        value_chars.append("\\x")
                elif esc == '"':
                    value_chars.append('"')
                elif esc == "\\":
                    value_chars.append("\\")
                else:
                    value_chars.append(f"\\{esc}")
            else:
                value_chars.append(self.advance())

        if self.is_at_end():
            self.error("Unterminated string literal", self.current - self.start)

        # Consume closing quote
        self.advance()
        
        # Store the actual string content as value
        self.add_token(TokenType.STRING, "".join(value_chars))

    def number(self):
        is_float = False
        while self.peek().isdigit():
            self.advance()

        # Look for a fractional part
        if self.peek() == "." and self.peek_next().isdigit():
            is_float = True
            # Consume the "."
            self.advance()
            while self.peek().isdigit():
                self.advance()

        text = self.source[self.start:self.current]
        val = float(text) if is_float else int(text)
        self.add_token(TokenType.NUMBER, val)

    def identifier(self):
        while self.peek().isalnum() or self.peek() == "_":
            self.advance()

        text = self.source[self.start:self.current]
        
        # Look ahead for '#' immediately following 'import'
        if text == "import" and self.peek() == "#":
            self.advance() # consume '#'
            self.add_token(TokenType.IMPORT_DEFAULT, "import#")
        else:
            token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
            self.add_token(token_type)
