from interpreter.lexer import TokenType
from interpreter.ast_nodes import (
    ProgramNode, VarDeclNode, FuncDeclNode, AssignNode, IfNode,
    WhileNode, ForNode, ReturnNode, BlockNode, BinaryOpNode,
    UnaryOpNode, CallNode, LiteralNode, ListNode, DictNode,
    IdentifierNode, IndexNode, ImportDefaultNode, ImportFromNode
)
from interpreter.errors import PancoSyntaxError

class Parser:
    def __init__(self, tokens, source_code, filepath="<string>"):
        self.tokens = tokens
        self.source = source_code
        self.filepath = filepath
        self.current = 0

    def parse(self):
        statements = []
        try:
            while not self.is_at_end():
                stmt = self.statement()
                if stmt:
                    statements.append(stmt)
            return ProgramNode(statements)
        except PancoSyntaxError as e:
            # Let it propagate to the caller (cli) for beautiful rendering
            raise e

    # --- Parser Helper Methods ---
    
    def peek(self):
        return self.tokens[self.current]

    def previous(self):
        return self.tokens[self.current - 1]

    def is_at_end(self):
        return self.peek().type == TokenType.EOF

    def advance(self):
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def check(self, token_type):
        if self.is_at_end():
            return False
        return self.peek().type == token_type

    def check_lookahead(self, distance, token_type):
        if self.current + distance >= len(self.tokens):
            return False
        return self.tokens[self.current + distance].type == token_type

    def match(self, *types):
        for t in types:
            if self.check(t):
                self.advance()
                return True
        return False

    def error(self, token, message):
        raise PancoSyntaxError(
            message,
            self.filepath,
            token.line,
            token.column,
            token.length,
            self.source
        )

    def consume(self, token_type, message):
        if self.check(token_type):
            return self.advance()
        raise self.error(self.peek(), message)

    # --- Grammar Rules ---

    def statement(self):
        if self.check(TokenType.LBRACKET) and self.check_lookahead(1, TokenType.ALLOW) and self.check_lookahead(2, TokenType.RBRACE):
            return self.brackets_var_declaration()
        if self.match(TokenType.IMPORT_DEFAULT):
            return self.import_default_statement()
        if self.match(TokenType.FROM):
            return self.import_from_statement()
        if self.match(TokenType.DELTA):
            return self.func_declaration()
        if self.match(TokenType.IF):
            return self.if_statement()
        if self.match(TokenType.WHILE):
            return self.while_statement()
        if self.match(TokenType.FOR):
            return self.for_statement()
        if self.match(TokenType.RETURN):
            return self.return_statement()
        if self.check(TokenType.LBRACE):
            return self.block_statement()
            
        return self.expression_statement()

    def var_declaration(self):
        let_token = self.previous()
        name_token = self.consume(TokenType.IDENTIFIER, "Expect variable name after 'allow' or 'let'.")
        
        self.consume(TokenType.ASSIGN, f"Expect '=' after variable name '{name_token.value}'.")
        expr = self.expression()
        
        # Semicolons are optional, consume if present
        self.match(TokenType.SEMICOLON)
        
        return VarDeclNode(let_token, name_token.value, expr)

    def brackets_var_declaration(self):
        bracket_token = self.consume(TokenType.LBRACKET, "Expect '['.")
        self.consume(TokenType.ALLOW, "Expect 'allow'.")
        self.consume(TokenType.RBRACE, "Expect '}'.")
        
        name_token = self.consume(TokenType.IDENTIFIER, "Expect variable name.")
        self.consume(TokenType.BACKSLASH, "Expect '\\'.")
        
        # If the value is a plain identifier, parse it as a string literal (e.g. Alice)
        if self.check(TokenType.IDENTIFIER) and self.check_lookahead(1, TokenType.RBRACKET):
            val_token = self.advance()
            value_expr = LiteralNode(val_token, val_token.value)
        else:
            value_expr = self.expression()
            
        self.consume(TokenType.RBRACKET, "Expect ']'.")
        self.match(TokenType.SEMICOLON)
        
        return VarDeclNode(bracket_token, name_token.value, value_expr)

    def func_declaration(self):
        delta_token = self.previous()
        name_token = self.consume(TokenType.IDENTIFIER, "Expect function name after 'delta'.")
        
        self.consume(TokenType.LPAREN, "Expect '(' after function name.")
        params = []
        if not self.check(TokenType.RPAREN):
            while True:
                param_token = self.consume(TokenType.IDENTIFIER, "Expect parameter name.")
                params.append(param_token.value)
                if not self.match(TokenType.COMMA):
                    break
        self.consume(TokenType.RPAREN, "Expect ')' after function parameters.")
        
        # Enforce function body block to start with LBRACE
        self.consume(TokenType.LBRACE, "Expect '{' before function body block.")
        body = self.block_statement()
        
        return FuncDeclNode(delta_token, name_token.value, params, body)

    def if_statement(self):
        if_token = self.previous()
        
        # Condition can optionally be in parentheses
        cond_in_parens = self.match(TokenType.LPAREN)
        condition = self.expression()
        if cond_in_parens:
            self.consume(TokenType.RPAREN, "Expect ')' after if condition.")
            
        # Require { } for block
        self.consume(TokenType.LBRACE, "Expect '{' after if condition.")
        then_branch = self.block_statement()
        
        else_branch = None
        if self.match(TokenType.ELSE):
            if self.match(TokenType.IF):
                else_branch = self.if_statement()
            else:
                self.consume(TokenType.LBRACE, "Expect '{' after 'else'.")
                else_branch = self.block_statement()
                
        return IfNode(if_token, condition, then_branch, else_branch)

    def while_statement(self):
        while_token = self.previous()
        
        cond_in_parens = self.match(TokenType.LPAREN)
        condition = self.expression()
        if cond_in_parens:
            self.consume(TokenType.RPAREN, "Expect ')' after while condition.")
            
        self.consume(TokenType.LBRACE, "Expect '{' after while condition.")
        body = self.block_statement()
        
        return WhileNode(while_token, condition, body)

    def for_statement(self):
        for_token = self.previous()
        
        cond_in_parens = self.match(TokenType.LPAREN)
        item_token = self.consume(TokenType.IDENTIFIER, "Expect loop variable name.")
        self.consume(TokenType.IN, "Expect 'in' after loop variable.")
        list_expr = self.expression()
        if cond_in_parens:
            self.consume(TokenType.RPAREN, "Expect ')' after loop header.")
            
        self.consume(TokenType.LBRACE, "Expect '{' after loop header.")
        body = self.block_statement()
        
        return ForNode(for_token, item_token.value, list_expr, body)

    def return_statement(self):
        ret_token = self.previous()
        expr = None
        
        # Check if return has expression (if not followed by semicolon or end of statement block)
        if not self.check(TokenType.SEMICOLON) and not self.check(TokenType.RBRACE):
            expr = self.expression()
            
        self.match(TokenType.SEMICOLON)
        return ReturnNode(ret_token, expr)

    def block_statement(self):
        # We assume the leading LBRACE was already consumed
        brace_token = self.previous()
        statements = []
        
        while not self.check(TokenType.RBRACE) and not self.is_at_end():
            stmt = self.statement()
            if stmt:
                statements.append(stmt)
                
        self.consume(TokenType.RBRACE, "Expect '}' at end of block.")
        return BlockNode(brace_token, statements)

    def expression_statement(self):
        expr = self.expression()
        self.match(TokenType.SEMICOLON)
        return expr

    def import_default_statement(self):
        import_token = self.previous()
        name_token = self.consume(TokenType.IDENTIFIER, "Expect extension name to import.")
        self.match(TokenType.SEMICOLON)
        return ImportDefaultNode(import_token, name_token.value)

    def import_from_statement(self):
        from_token = self.previous()
        path_parts = []
        while not self.check(TokenType.IMPORT) and not self.is_at_end():
            token = self.advance()
            path_parts.append(token.value)
        if not path_parts:
            raise self.error(self.peek(), "Expect database path after 'from'.")
        db_path = "".join(path_parts)
        
        self.consume(TokenType.IMPORT, "Expect 'import' after database path.")
        ext_token = self.consume(TokenType.IDENTIFIER, "Expect extension name to import.")
        self.match(TokenType.SEMICOLON)
        return ImportFromNode(from_token, db_path, ext_token.value)

    # --- Expression Grammar ---

    def expression(self):
        return self.assignment()

    def assignment(self):
        expr = self.pipe()
        
        if self.match(TokenType.ASSIGN):
            assign_token = self.previous()
            value = self.assignment() # recursive for chaining, e.g., a = b = 5
            
            # Check if left-hand side is an assignable target:
            # - IdentifierNode
            # - IndexNode
            if isinstance(expr, (IdentifierNode, IndexNode)):
                return AssignNode(assign_token, expr, value)
                
            raise self.error(assign_token, "Invalid assignment target.")
            
        return expr

    def pipe(self):
        expr = self.logical_or()
        
        while self.match(TokenType.PIPE):
            pipe_token = self.previous()
            right = self.logical_or() # Precedence rules mean pipeline is high priority but lower than functions
            
            # Check if right is a function call or identifier
            if isinstance(right, CallNode):
                # Prepend the left expr to arguments
                right.args.insert(0, expr)
                expr = right
            elif isinstance(right, IdentifierNode):
                # Convert identifier to a CallNode with left as the single arg
                expr = CallNode(pipe_token, right, [expr])
            else:
                raise self.error(pipe_token, "Right side of a pipe operator '->' must be an identifier or a function call.")
                
        return expr

    def logical_or(self):
        expr = self.logical_and()
        
        while self.match(TokenType.OR):
            op_token = self.previous()
            right = self.logical_and()
            expr = BinaryOpNode(op_token, expr, "or", right)
            
        return expr

    def logical_and(self):
        expr = self.comparison()
        
        while self.match(TokenType.AND):
            op_token = self.previous()
            right = self.comparison()
            expr = BinaryOpNode(op_token, expr, "and", right)
            
        return expr

    def comparison(self):
        expr = self.term()
        
        while self.match(TokenType.EQ, TokenType.NE, TokenType.LT, TokenType.LE, TokenType.GT, TokenType.GE):
            op_token = self.previous()
            right = self.term()
            expr = BinaryOpNode(op_token, expr, op_token.value, right)
            
        return expr

    def term(self):
        expr = self.factor()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op_token = self.previous()
            right = self.factor()
            expr = BinaryOpNode(op_token, expr, op_token.value, right)
            
        return expr

    def factor(self):
        expr = self.unary()
        
        while self.match(TokenType.MUL, TokenType.DIV, TokenType.MOD):
            op_token = self.previous()
            right = self.unary()
            expr = BinaryOpNode(op_token, expr, op_token.value, right)
            
        return expr

    def unary(self):
        if self.match(TokenType.NOT, TokenType.MINUS):
            op_token = self.previous()
            right = self.unary()
            return UnaryOpNode(op_token, op_token.value, right)
            
        return self.call_or_index()

    def call_or_index(self):
        expr = self.primary()
        
        while True:
            if self.match(TokenType.LPAREN):
                # Call expression
                paren_token = self.previous()
                args = []
                if not self.check(TokenType.RPAREN):
                    while True:
                        args.append(self.expression())
                        if not self.match(TokenType.COMMA):
                            break
                self.consume(TokenType.RPAREN, "Expect ')' after call arguments.")
                expr = CallNode(paren_token, expr, args)
            elif self.check(TokenType.LBRACKET) and not (self.check_lookahead(1, TokenType.ALLOW) and self.check_lookahead(2, TokenType.RBRACE)):
                self.advance()
                # Index expression
                bracket_token = self.previous()
                index = self.expression()
                self.consume(TokenType.RBRACKET, "Expect ']' after index.")
                expr = IndexNode(bracket_token, expr, index)
            else:
                break
                
        return expr

    def primary(self):
        if self.match(TokenType.TRUE):
            return LiteralNode(self.previous(), True)
        if self.match(TokenType.FALSE):
            return LiteralNode(self.previous(), False)
        if self.match(TokenType.NIL):
            return LiteralNode(self.previous(), None)
            
        if self.match(TokenType.NUMBER, TokenType.STRING):
            return LiteralNode(self.previous(), self.previous().value)
            
        if self.match(TokenType.IDENTIFIER):
            return IdentifierNode(self.previous(), self.previous().value)
            
        if self.match(TokenType.LPAREN):
            paren_token = self.previous()
            expr = self.expression()
            self.consume(TokenType.RPAREN, "Expect ')' after expression.")
            return expr
            
        # List literal
        if self.match(TokenType.LBRACKET):
            bracket_token = self.previous()
            elements = []
            if not self.check(TokenType.RBRACKET):
                while True:
                    elements.append(self.expression())
                    if not self.match(TokenType.COMMA):
                        break
            self.consume(TokenType.RBRACKET, "Expect ']' at end of list literal.")
            return ListNode(bracket_token, elements)
            
        # Dict literal
        if self.match(TokenType.LBRACE):
            brace_token = self.previous()
            pairs = []
            if not self.check(TokenType.RBRACE):
                while True:
                    # Key can be an expression, e.g. a string or a variable
                    key = self.expression()
                    self.consume(TokenType.COLON, "Expect ':' after dictionary key.")
                    value = self.expression()
                    pairs.append((key, value))
                    if not self.match(TokenType.COMMA):
                        break
            self.consume(TokenType.RBRACE, "Expect '}' at end of dictionary literal.")
            return DictNode(brace_token, pairs)
            
        raise self.error(self.peek(), "Expect expression.")
