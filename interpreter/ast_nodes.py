class ASTNode:
    def __init__(self, token=None):
        self.token = token # Reference token for error reporting

    def __repr__(self):
        return f"{self.__class__.__name__}()"

class ProgramNode(ASTNode):
    def __init__(self, statements):
        super().__init__()
        self.statements = statements

class VarDeclNode(ASTNode):
    def __init__(self, token, name, expr):
        super().__init__(token)
        self.name = name
        self.expr = expr

class FuncDeclNode(ASTNode):
    def __init__(self, token, name, params, body):
        super().__init__(token)
        self.name = name
        self.params = params
        self.body = body

class AssignNode(ASTNode):
    def __init__(self, token, target, expr):
        super().__init__(token)
        self.target = target # IdentifierNode or IndexNode
        self.expr = expr

class IfNode(ASTNode):
    def __init__(self, token, condition, then_branch, else_branch=None):
        super().__init__(token)
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch

class WhileNode(ASTNode):
    def __init__(self, token, condition, body):
        super().__init__(token)
        self.condition = condition
        self.body = body

class ForNode(ASTNode):
    def __init__(self, token, item_name, list_expr, body):
        super().__init__(token)
        self.item_name = item_name
        self.list_expr = list_expr
        self.body = body

class ReturnNode(ASTNode):
    def __init__(self, token, expr=None):
        super().__init__(token)
        self.expr = expr

class BlockNode(ASTNode):
    def __init__(self, token, statements):
        super().__init__(token)
        self.statements = statements

class BinaryOpNode(ASTNode):
    def __init__(self, token, left, operator, right):
        super().__init__(token)
        self.left = left
        self.operator = operator
        self.right = right

class UnaryOpNode(ASTNode):
    def __init__(self, token, operator, expr):
        super().__init__(token)
        self.operator = operator
        self.expr = expr

class CallNode(ASTNode):
    def __init__(self, token, callee, args):
        super().__init__(token)
        self.callee = callee # IdentifierNode or other callable expr
        self.args = args

class LiteralNode(ASTNode):
    def __init__(self, token, value):
        super().__init__(token)
        self.value = value

class ListNode(ASTNode):
    def __init__(self, token, elements):
        super().__init__(token)
        self.elements = elements

class DictNode(ASTNode):
    def __init__(self, token, pairs):
        super().__init__(token)
        self.pairs = pairs # List of (key_expr, value_expr)

class IdentifierNode(ASTNode):
    def __init__(self, token, name):
        super().__init__(token)
        self.name = name

class IndexNode(ASTNode):
    def __init__(self, token, expr, index):
        super().__init__(token)
        self.expr = expr
        self.index = index

class ImportDefaultNode(ASTNode):
    def __init__(self, token, extension_name):
        super().__init__(token)
        self.extension_name = extension_name

class ImportFromNode(ASTNode):
    def __init__(self, token, db_path, extension_name):
        super().__init__(token)
        self.db_path = db_path
        self.extension_name = extension_name
