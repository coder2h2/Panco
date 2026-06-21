#!/usr/bin/env python3
import sys
import os

from interpreter import Lexer, Parser, Interpreter, PancoError

BANNER = ""

import re

def parse_directives(source_code):
    directives = {}
    lines = source_code.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        
        # Match directive [key}value]
        match = re.match(r'^\[([a-zA-Z_.]+)\}([^\]]*)\]$', line)
        if match:
            key, val = match.groups()
            if key == "allow":
                break
            directives[key] = val
            i += 1
        else:
            break
            
    # To keep error line numbers exact, replace directive lines with blank lines
    cleaned_source = "\n" * i + "\n".join(lines[i:])
    return directives, cleaned_source

def init_project():
    project_file = "Project.delta"
    if os.path.exists(project_file):
        print(f"Error: '{project_file}' already exists in this directory.", file=sys.stderr)
        sys.exit(1)
        
    template = r"""[db}~/.pco/database/panco.db]
[deltafolder}~/.pco/PROJECT/delta]
[.deltalog}~/.pco/delta/logs/.deltalog]

# ==========================================
#                  PANCO
# ==========================================
# File: Project.delta
# Created by 'delta init'

[allow}status\Successful]

makeword("Panco execution: " + status)
"""
    try:
        with open(project_file, "w", encoding="utf-8") as f:
            f.write(template)
            
        db_path = os.path.expanduser("~/.pco/database/panco.db")
        delta_dir = os.path.expanduser("~/.pco/PROJECT/delta")
        logs_dir = os.path.expanduser("~/.pco/delta/logs")

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(delta_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        
        # Seed math_ext and graphical extensions in default db
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extensions (
                name TEXT PRIMARY KEY,
                code TEXT
            )
        """)
        
        math_code = """
delta double_val(x) {
    return x * 2
}

delta triple_val(x) {
    return x * 3
}
"""
        graphical_code = """
delta create_window(title) {
    return gui_window(title)
}

delta add_label(win, text) {
    return gui_label(win, text)
}

delta add_button(win, text, callback) {
    return gui_button(win, text, callback)
}

delta add_input(win) {
    return gui_entry(win)
}

delta get_input_value(entry) {
    return gui_get_text(entry)
}

delta start_gui(win) {
    return gui_main_loop(win)
}
"""
        cursor.execute("INSERT OR REPLACE INTO extensions (name, code) VALUES (?, ?)", ("math_ext", math_code))
        cursor.execute("INSERT OR REPLACE INTO extensions (name, code) VALUES (?, ?)", ("graphical", graphical_code))
        conn.commit()
        conn.close()
        
        print("Panco project initialized successfully!")
        print("Created:")
        print("  - Project.delta")
        print("  - ~/.pco/database/ (containing extensions)")
        print("  - ~/.pco/PROJECT/delta/")
        print("  - ~/.pco/delta/logs/")
        print("\nTo run your project, type: delta start Project.delta")
    except Exception as e:
        print(f"Error: Failed to initialize project: {str(e)}", file=sys.stderr)
        sys.exit(1)

def run_file(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        source_code = f.read()

    directives, cleaned_source = parse_directives(source_code)
    interpreter = Interpreter(cleaned_source, filepath=filepath, directives=directives)
    
    # Log starting of execution
    interpreter.log_message("Execution started.")

    try:
        lexer = Lexer(cleaned_source, filepath=filepath)
        tokens = lexer.scan_tokens()

        parser = Parser(tokens, cleaned_source, filepath=filepath)
        program_ast = parser.parse()

        interpreter.interpret(program_ast)
    except PancoError as e:
        print(e, file=sys.stderr)
        interpreter.log_message(f"Execution failed: {str(e)}", level="ERROR")
        sys.exit(65 if "Syntax" in type(e).__name__ else 70)

def run_repl():
    if BANNER:
        print(BANNER)
    
    # We use a persistent interpreter and environment
    interpreter = Interpreter("", filepath="<repl>")
    
    # We want to support multiline inputs for block statements
    multiline = False
    buffer = []
    
    while True:
        try:
            prompt = "... " if multiline else "panco> "
            line = input(prompt)
            
            if not multiline and line.strip() == "exit()":
                break
                
            if multiline:
                buffer.append(line)
                # Count open and closed braces in the buffer
                full_code = "\n".join(buffer)
                open_braces = full_code.count("{")
                close_braces = full_code.count("}")
                if close_braces >= open_braces and line.strip() == "}":
                    multiline = False
                    code_to_eval = full_code
                    buffer = []
                else:
                    continue
            else:
                if line.strip().endswith("{"):
                    multiline = True
                    buffer.append(line)
                    continue
                code_to_eval = line

            if not code_to_eval.strip():
                continue

            # Update interpreter source reference for accurate errors
            interpreter.source = code_to_eval
            
            lexer = Lexer(code_to_eval, filepath="<repl>")
            tokens = lexer.scan_tokens()
            
            parser = Parser(tokens, code_to_eval, filepath="<repl>")
            program_ast = parser.parse()
            
            for stmt in program_ast.statements:
                val = interpreter.execute(stmt)
                
                # Check if it was an expression statement and print the evaluated value if not nil
                # We identify expressions by checking if the statement is an ASTNode representing a value/expression.
                from interpreter.ast_nodes import (
                    VarDeclNode, FuncDeclNode, IfNode, WhileNode, ForNode, ReturnNode, BlockNode
                )
                
                is_statement_node = isinstance(stmt, (VarDeclNode, FuncDeclNode, IfNode, WhileNode, ForNode, ReturnNode, BlockNode))
                if not is_statement_node and val is not None:
                    print(f"=> {interpreter.stringify_repr(val)}")
                    
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt (type exit() to quit)")
            multiline = False
            buffer = []
        except EOFError:
            print("\nGoodbye!")
            break
        except PancoError as e:
            print(e, file=sys.stderr)
            multiline = False
            buffer = []

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "init":
        init_project()
    elif len(sys.argv) == 2 and sys.argv[1] == "install":
        try:
            from install_gui import PancoX11Installer
            app = PancoX11Installer()
            app.run()
            sys.exit(0)
        except Exception as e:
            print(f"Error launching graphical installer: {str(e)}", file=sys.stderr)
            sys.exit(1)
    elif len(sys.argv) == 3 and sys.argv[1] == "start":
        run_file(sys.argv[2])
    elif len(sys.argv) == 2:
        if sys.argv[1] == "start":
            print("Error: Please specify a file to start (e.g., 'delta start Project.delta')", file=sys.stderr)
            sys.exit(64)
        run_file(sys.argv[1])
    elif len(sys.argv) == 1:
        run_repl()
    else:
        print("Usage: delta [start|init|install] [file.pco|file.delta]", file=sys.stderr)
        sys.exit(64) # EX_USAGE
