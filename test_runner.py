#!/usr/bin/env python3
import unittest
import io
import sys
from interpreter import Lexer, Parser, Interpreter, PancoSyntaxError, PancoRuntimeError

class TestPancoLexer(unittest.TestCase):
    def test_basic_tokens(self):
        source = "[allow}x\\10] + 20 -> double"
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        token_types = [t.type.value for t in tokens]
        expected = ["[", "allow", "}", "IDENTIFIER", "\\", "NUMBER", "]", "+", "NUMBER", "->", "IDENTIFIER", "EOF"]
        self.assertEqual(token_types, expected)

    def test_string_escapes(self):
        source = '"hello \\n \\t \\e \\x41"'
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        self.assertEqual(tokens[0].value, "hello \n \t \x1b A")

class TestPancoParser(unittest.TestCase):
    def test_precedence_parsing(self):
        source = "[allow}res\\2 + 3 * 4]"
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        parser = Parser(tokens, source)
        ast = parser.parse()
        self.assertEqual(len(ast.statements), 1)
        # Verify structure
        stmt = ast.statements[0]
        self.assertEqual(stmt.name, "res")
        self.assertEqual(stmt.expr.operator, "+")
        self.assertEqual(stmt.expr.right.operator, "*")

    def test_pipe_parsing(self):
        source = "5 -> double -> add(3)"
        lexer = Lexer(source)
        tokens = lexer.scan_tokens()
        parser = Parser(tokens, source)
        ast = parser.parse()
        # Verify right-most operation is CallNode for 'add' with prepended pipe results
        call = ast.statements[0]
        self.assertEqual(call.callee.name, "add")
        self.assertEqual(len(call.args), 2)
        self.assertEqual(call.args[1].value, 3)

class TestPancoInterpreter(unittest.TestCase):
    def run_code(self, source):
        # Captures print output
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            lexer = Lexer(source)
            tokens = lexer.scan_tokens()
            parser = Parser(tokens, source)
            ast = parser.parse()
            interpreter = Interpreter(source)
            interpreter.interpret(ast)
            return sys.stdout.getvalue(), interpreter
        finally:
            sys.stdout = old_stdout

    def test_variables(self):
        code = """
        [allow}x\\10]
        [allow}y\\x + 5]
        makeword(y)
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip(), "15")

    def test_delta_functions(self):
        code = """
        delta add(a, b) {
            return a + b
        }
        makeword(add(2, 3))
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip(), "5")

    def test_closures(self):
        code = """
        delta make_counter() {
            [allow}count\\0]
            delta counter() {
                count = count + 1
                return count
            }
            return counter
        }
        [allow}c\\make_counter()]
        makeword(c())
        makeword(c())
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip().split(), ["1", "2"])

    def test_pipe_execution(self):
        code = """
        delta sq(x) { return x * x }
        delta add_one(x) { return x + 1 }
        makeword(5 -> sq -> add_one)
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip(), "26")

    def test_list_and_dict(self):
        code = """
        [allow}lst\\[1, 2, 3]]
        lst[1] = 5
        [allow}user\\{"name": "alice"}]
        makeword(lst[1], user["name"])
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip(), "5 alice")

    def test_for_loop(self):
        code = """
        [allow}total\\0]
        for x in [1, 2, 3, 4] {
            total = total + x
        }
        makeword(total)
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip(), "10")

    def test_string_interpolation(self):
        code = """
        [allow}name\\World]
        [allow}msg\\"Hello, {name}! 2 + 2 = {2 + 2}"]
        makeword(msg)
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip(), "Hello, World! 2 + 2 = 4")

    def test_runtime_error(self):
        code = "10 / 0"
        with self.assertRaises(PancoRuntimeError):
            self.run_code(code)

    def test_syntax_error(self):
        code = "[allow}x"
        with self.assertRaises(PancoSyntaxError):
            self.run_code(code)

    def test_database_imports(self):
        import sqlite3
        import os
        db_path = "temp_test.db"
        # Setup temp sqlite db with an extension
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS extensions (name TEXT PRIMARY KEY, code TEXT)")
        cursor.execute("INSERT OR REPLACE INTO extensions VALUES (?, ?)", ("test_ext", "delta multiply(a, b) { return a * b }"))
        conn.commit()
        conn.close()
        
        try:
            code = """
            from temp_test.db import test_ext
            makeword(multiply(3, 4))
            """
            output, _ = self.run_code(code)
            self.assertEqual(output.strip(), "12")
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_allow_declarations_disabled(self):
        code = "allow name = \"Bob\""
        with self.assertRaises(PancoSyntaxError):
            self.run_code(code)

    def test_brackets_declarations(self):
        code = """
        [allow}name\\Alice]
        [allow}age\\25]
        makeword(name, age)
        """
        output, _ = self.run_code(code)
        self.assertEqual(output.strip(), "Alice 25")

if __name__ == "__main__":
    unittest.main()
