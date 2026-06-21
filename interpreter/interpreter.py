import os
import sys
import math
import time
import sqlite3
from datetime import datetime
from interpreter.errors import PancoRuntimeError
from interpreter.environment import Environment
from interpreter.ast_nodes import (
    ProgramNode, VarDeclNode, FuncDeclNode, AssignNode, IfNode,
    WhileNode, ForNode, ReturnNode, BlockNode, BinaryOpNode,
    UnaryOpNode, CallNode, LiteralNode, ListNode, DictNode,
    IdentifierNode, IndexNode, ImportDefaultNode, ImportFromNode
)

class ReturnException(Exception):
    def __init__(self, value):
        super().__init__()
        self.value = value

class PancoCallable:
    def call(self, interpreter, arguments, token):
        raise NotImplementedError()

    def arity(self):
        return 0

class PancoFunction(PancoCallable):
    def __init__(self, declaration, closure):
        self.declaration = declaration
        self.closure = closure

    def arity(self):
        return len(self.declaration.params)

    def call(self, interpreter, arguments, token):
        env = Environment(self.closure)
        for i, param in enumerate(self.declaration.params):
            env.define(param, arguments[i])
            
        try:
            interpreter.execute_block(self.declaration.body, env)
        except ReturnException as r:
            return r.value
            
        return None

    def __repr__(self):
        return f"<delta {self.declaration.name}>"

class PancoBuiltin(PancoCallable):
    def __init__(self, name, arity_val, func):
        self.name = name
        self.arity_val = arity_val
        self.func = func

    def arity(self):
        return self.arity_val

    def call(self, interpreter, arguments, token):
        try:
            return self.func(interpreter, arguments, token)
        except PancoRuntimeError as e:
            raise e
        except Exception as e:
            raise PancoRuntimeError(
                f"Error in built-in '{self.name}': {str(e)}",
                interpreter.filepath,
                token.line,
                token.column,
                token.length,
                interpreter.source
            )

    def __repr__(self):
        return f"<builtin {self.name}>"

class Interpreter:
    def __init__(self, source_code, filepath="<string>", directives=None):
        self.source = source_code
        self.filepath = filepath
        self.directives = directives if directives is not None else {}
        self.globals = Environment()
        self.environment = self.globals
        
        # Determine the directory of the script file to resolve relative paths
        if self.filepath and self.filepath not in ("<string>", "<repl>"):
            self.script_dir = os.path.dirname(os.path.abspath(self.filepath))
        else:
            self.script_dir = os.getcwd()

        # Setup logging configurations
        log_path = self.directives.get(".deltalog")
        self.log_path = os.path.expanduser(log_path) if log_path else None
        self.fallback_logged_warning = False

        # Resolve paths for db and deltafolder
        db_directive = self.directives.get("db")
        self.db_path = self.resolve_path(db_directive)
        
        deltafolder_directive = self.directives.get("deltafolder")
        self.delta_folder = self.resolve_path(deltafolder_directive)

        # Define directive variables in environment (using resolved paths)
        self.globals.define("DB_PATH", self.db_path)
        self.globals.define("DELTA_FOLDER", self.delta_folder)
        
        # If deltafolder directive is present, make sure the directory is created
        if self.delta_folder:
            try:
                os.makedirs(self.delta_folder, exist_ok=True)
            except Exception:
                pass # Fail silently
                
        # If db directive is present, make sure its parent directory is created
        if self.db_path:
            try:
                parent = os.path.dirname(self.db_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
            except Exception:
                pass # Fail silently
                
        self._setup_builtins()

    def resolve_path(self, path):
        if not path:
            return path
        path = os.path.expanduser(path)
        if os.path.isabs(path):
            return path
        return os.path.abspath(os.path.join(self.script_dir, path))

    def _setup_builtins(self):
        # Helper to define built-in functions
        def define_builtin(name, arity_val, func):
            self.globals.define(name, PancoBuiltin(name, arity_val, func))

        # makeword(...)
        def bi_print(interpreter, args, token):
            print_strs = [interpreter.stringify(arg) for arg in args]
            msg = " ".join(print_strs)
            print(msg)
            interpreter.log_message(msg)
            return None
        # makeword is variadic, we handle arity check manually in call evaluation
        define_builtin("makeword", -1, bi_print)

        # len(obj)
        def bi_len(interpreter, args, token):
            obj = args[0]
            if isinstance(obj, (str, list, dict)):
                return len(obj)
            raise PancoRuntimeError(
                f"Object of type '{type(obj).__name__}' has no length.",
                interpreter.filepath,
                token.line,
                token.column,
                token.length,
                interpreter.source
            )
        define_builtin("len", 1, bi_len)

        # push(list, item)
        def bi_push(interpreter, args, token):
            lst, item = args[0], args[1]
            if not isinstance(lst, list):
                raise PancoRuntimeError("First argument to push must be a list.", interpreter.filepath, token.line, token.column, token.length, interpreter.source)
            lst.append(item)
            return lst
        define_builtin("push", 2, bi_push)

        # pop(list)
        def bi_pop(interpreter, args, token):
            lst = args[0]
            if not isinstance(lst, list):
                raise PancoRuntimeError("Argument to pop must be a list.", interpreter.filepath, token.line, token.column, token.length, interpreter.source)
            if not lst:
                raise PancoRuntimeError("Cannot pop from an empty list.", interpreter.filepath, token.line, token.column, token.length, interpreter.source)
            return lst.pop()
        define_builtin("pop", 1, bi_pop)

        # range(n)
        def bi_range(interpreter, args, token):
            n = args[0]
            if not isinstance(n, (int, float)):
                raise PancoRuntimeError("Range limit must be a number.", interpreter.filepath, token.line, token.column, token.length, interpreter.source)
            return list(range(int(n)))
        define_builtin("range", 1, bi_range)

        # type(val)
        def bi_type(interpreter, args, token):
            val = args[0]
            if val is None:
                return "nil"
            if isinstance(val, bool):
                return "boolean"
            if isinstance(val, (int, float)):
                return "number"
            if isinstance(val, str):
                return "string"
            if isinstance(val, list):
                return "list"
            if isinstance(val, dict):
                return "dictionary"
            if isinstance(val, PancoCallable):
                return "function"
            return "unknown"
        define_builtin("type", 1, bi_type)

        # input(prompt)
        def bi_input(interpreter, args, token):
            prompt = args[0] if args else ""
            try:
                return input(prompt)
            except KeyboardInterrupt:
                print()
                sys.exit(0)
        define_builtin("input", -1, bi_input)

        # sleep(seconds)
        def bi_sleep(interpreter, args, token):
            secs = args[0]
            if not isinstance(secs, (int, float)):
                raise PancoRuntimeError("Sleep duration must be a number.", interpreter.filepath, token.line, token.column, token.length, interpreter.source)
            time.sleep(secs)
            return None
        define_builtin("sleep", 1, bi_sleep)

        # math helpers
        define_builtin("abs", 1, lambda interp, args, tok: abs(args[0]) if isinstance(args[0], (int, float)) else exec("raise PancoRuntimeError('abs expects a number', interp.filepath, tok.line, tok.column, tok.length, interp.source)"))
        define_builtin("sqrt", 1, lambda interp, args, tok: math.sqrt(args[0]) if isinstance(args[0], (int, float)) else exec("raise PancoRuntimeError('sqrt expects a number', interp.filepath, tok.line, tok.column, tok.length, interp.source)"))
        define_builtin("sin", 1, lambda interp, args, tok: math.sin(args[0]) if isinstance(args[0], (int, float)) else exec("raise PancoRuntimeError('sin expects a number', interp.filepath, tok.line, tok.column, tok.length, interp.source)"))
        define_builtin("cos", 1, lambda interp, args, tok: math.cos(args[0]) if isinstance(args[0], (int, float)) else exec("raise PancoRuntimeError('cos expects a number', interp.filepath, tok.line, tok.column, tok.length, interp.source)"))

        # Graphical GUI Helpers (Custom Direct X11 integration)
        def bi_gui_window(interpreter, args, token):
            import ctypes
            try:
                x11 = ctypes.CDLL("libX11.so.6")
            except Exception:
                try:
                    x11 = ctypes.CDLL("libX11.so")
                except Exception:
                    raise PancoRuntimeError("Could not load libX11.so. Graphical extension requires X11 on Linux.", interpreter.filepath, token.line, token.column, token.length, interpreter.source)
                    
            x11.XOpenDisplay.restype = ctypes.c_void_p
            x11.XDefaultRootWindow.restype = ctypes.c_ulong
            x11.XCreateSimpleWindow.restype = ctypes.c_ulong
            
            display = x11.XOpenDisplay(None)
            if not display:
                raise PancoRuntimeError("Could not open X11 display. Ensure DISPLAY env variable is set.", interpreter.filepath, token.line, token.column, token.length, interpreter.source)
                
            root = x11.XDefaultRootWindow(display)
            # Create a simple window (400x300, white background 0xFFFFFF)
            window = x11.XCreateSimpleWindow(display, root, 100, 100, 400, 300, 1, 0, 0xFFFFFF)
            
            # Change window title
            x11.XStoreName(display, window, args[0].encode("utf-8"))
            
            # Select events: ExposureMask (1<<15), ButtonPressMask (1<<2), KeyPressMask (1<<0)
            x11.XSelectInput(display, window, (1<<15) | (1<<2) | (1<<0))
            x11.XMapWindow(display, window)
            
            gc = x11.XCreateGC(display, window, 0, None)
            
            return {
                "x11": x11,
                "display": display,
                "window": window,
                "gc": gc,
                "widgets": []
            }
        define_builtin("gui_window", 1, bi_gui_window)

        def bi_gui_label(interpreter, args, token):
            window = args[0]
            widget = {"type": "label", "text": args[1], "y": 50 + len(window["widgets"]) * 45}
            window["widgets"].append(widget)
            return widget
        define_builtin("gui_label", 2, bi_gui_label)

        def bi_gui_button(interpreter, args, token):
            window = args[0]
            y = 50 + len(window["widgets"]) * 45
            widget = {
                "type": "button",
                "text": args[1],
                "callback_name": args[2],
                "x": 80,
                "y": y,
                "w": 240,
                "h": 32
            }
            window["widgets"].append(widget)
            return widget
        define_builtin("gui_button", 3, bi_gui_button)

        def bi_gui_entry(interpreter, args, token):
            window = args[0]
            y = 50 + len(window["widgets"]) * 45
            widget = {
                "type": "entry",
                "text": "",
                "x": 80,
                "y": y,
                "w": 240,
                "h": 32
            }
            window["widgets"].append(widget)
            return widget
        define_builtin("gui_entry", 1, bi_gui_entry)

        def bi_gui_get_text(interpreter, args, token):
            widget = args[0]
            return widget.get("text", "")
        define_builtin("gui_get_text", 1, bi_gui_get_text)

        def bi_gui_main_loop(interpreter, args, token):
            import ctypes
            
            window = args[0]
            x11 = window["x11"]
            display = window["display"]
            win_id = window["window"]
            gc = window["gc"]
            widgets = window["widgets"]
            
            class XEvent(ctypes.Structure):
                _fields_ = [("type", ctypes.c_int), ("pad", ctypes.c_byte * 188)]
                
            class XButtonEvent(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.c_int),
                    ("serial", ctypes.c_ulong),
                    ("send_event", ctypes.c_int),
                    ("display", ctypes.c_void_p),
                    ("window", ctypes.c_ulong),
                    ("root", ctypes.c_ulong),
                    ("subwindow", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("x", ctypes.c_int),
                    ("y", ctypes.c_int),
                ]
                
            class XKeyEvent(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.c_int),
                    ("serial", ctypes.c_ulong),
                    ("send_event", ctypes.c_int),
                    ("display", ctypes.c_void_p),
                    ("window", ctypes.c_ulong),
                    ("root", ctypes.c_ulong),
                    ("subwindow", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("x", ctypes.c_int),
                    ("y", ctypes.c_int),
                    ("x_root", ctypes.c_int),
                    ("y_root", ctypes.c_int),
                    ("state", ctypes.c_uint),
                    ("keycode", ctypes.c_uint),
                ]

            event = XEvent()
            
            def draw_window():
                # Clear background (white rectangle)
                x11.XSetForeground(display, gc, 0xFFFFFF)
                x11.XFillRectangle(display, win_id, gc, 0, 0, 400, 300)
                
                # Set drawing color to black
                x11.XSetForeground(display, gc, 0x000000)
                
                for widget in widgets:
                    if widget["type"] == "label":
                        text_bytes = widget["text"].encode("utf-8")
                        x11.XDrawString(display, win_id, gc, 80, widget["y"] + 20, text_bytes, len(text_bytes))
                    elif widget["type"] == "button":
                        # Border
                        x11.XDrawRectangle(display, win_id, gc, widget["x"], widget["y"], widget["w"], widget["h"])
                        # Text
                        text_bytes = widget["text"].encode("utf-8")
                        x11.XDrawString(display, win_id, gc, widget["x"] + 20, widget["y"] + 20, text_bytes, len(text_bytes))
                    elif widget["type"] == "entry":
                        # Border
                        x11.XDrawRectangle(display, win_id, gc, widget["x"], widget["y"], widget["w"], widget["h"])
                        # Text
                        val = widget["text"] + ("_" if active_entry is widget else "")
                        text_bytes = val.encode("utf-8")
                        x11.XDrawString(display, win_id, gc, widget["x"] + 10, widget["y"] + 20, text_bytes, len(text_bytes))
                x11.XFlush(display)

            active_entry = None
            
            # Flush initial display mapping
            x11.XFlush(display)
            
            while True:
                x11.XNextEvent(display, ctypes.byref(event))
                
                if event.type == 12: # Expose
                    draw_window()
                elif event.type == 4: # ButtonPress
                    click = ctypes.cast(ctypes.byref(event), ctypes.POINTER(XButtonEvent)).contents
                    active_entry = None
                    for widget in widgets:
                        if widget["type"] == "button":
                            if widget["x"] <= click.x <= widget["x"] + widget["w"] and widget["y"] <= click.y <= widget["y"] + widget["h"]:
                                callback_name = widget["callback_name"]
                                try:
                                    val = interpreter.environment.get(callback_name, token, interpreter.filepath, interpreter.source)
                                    if isinstance(val, PancoCallable):
                                        val.call(interpreter, [], token)
                                    elif callable(val):
                                        val()
                                except Exception as e:
                                    print(f"Error in callback: {e}")
                                draw_window()
                        elif widget["type"] == "entry":
                            if widget["x"] <= click.x <= widget["x"] + widget["w"] and widget["y"] <= click.y <= widget["y"] + widget["h"]:
                                active_entry = widget
                                draw_window()
                elif event.type == 2: # KeyPress
                    key = ctypes.cast(ctypes.byref(event), ctypes.POINTER(XKeyEvent)).contents
                    buf = (ctypes.c_char * 8)()
                    keysym = ctypes.c_ulong()
                    res = x11.XLookupString(ctypes.byref(key), buf, 8, ctypes.byref(keysym), None)
                    if res > 0:
                        char = buf.value.decode("utf-8", errors="ignore")
                        if active_entry:
                            if ord(char) in (8, 127): # Backspace
                                active_entry["text"] = active_entry["text"][:-1]
                            elif char in ("\r", "\n"): # Enter
                                active_entry = None
                            else:
                                active_entry["text"] += char
                            draw_window()
            return None
        define_builtin("gui_main_loop", 1, bi_gui_main_loop)

    def interpret(self, program_node):
        try:
            for stmt in program_node.statements:
                self.execute(stmt)
            self.log_message("Execution completed successfully.")
        except PancoRuntimeError as e:
            self.log_message(f"Execution failed: {str(e)}", level="ERROR")
            raise e

    def execute(self, stmt):
        method_name = f"visit_{type(stmt).__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(stmt)

    def evaluate(self, expr):
        return self.execute(expr)

    def generic_visit(self, node):
        raise Exception(f"No visit_{type(node).__name__} method defined.")

    def stringify(self, value):
        if value is None:
            return "nil"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, list):
            return "[" + ", ".join(self.stringify_repr(item) for item in value) + "]"
        if isinstance(value, dict):
            parts = []
            for k, v in value.items():
                parts.append(f"{self.stringify_repr(k)}: {self.stringify_repr(v)}")
            return "{" + ", ".join(parts) + "}"
        return str(value)

    def stringify_repr(self, value):
        if isinstance(value, str):
            # Show quotes inside list/dict outputs
            return f'"{value}"'
        return self.stringify(value)

    # --- Statement Visitors ---

    def visit_VarDeclNode(self, node):
        value = self.evaluate(node.expr)
        self.environment.define(node.name, value)
        return None

    def visit_FuncDeclNode(self, node):
        func = PancoFunction(node, self.environment)
        self.environment.define(node.name, func)
        return None

    def visit_IfNode(self, node):
        cond = self.evaluate(node.condition)
        if self.is_truthy(cond):
            self.execute(node.then_branch)
        elif node.else_branch:
            self.execute(node.else_branch)
        return None

    def visit_WhileNode(self, node):
        while self.is_truthy(self.evaluate(node.condition)):
            self.execute(node.body)
        return None

    def visit_ForNode(self, node):
        lst = self.evaluate(node.list_expr)
        if not isinstance(lst, list):
            raise PancoRuntimeError(
                "Can only loop over lists.",
                self.filepath,
                node.token.line,
                node.token.column,
                node.token.length,
                self.source
            )
            
        previous_env = self.environment
        for item in lst:
            # Each iteration has its own scope
            self.environment = Environment(previous_env)
            self.environment.define(node.item_name, item)
            try:
                self.execute(node.body)
            finally:
                self.environment = previous_env
        return None

    def visit_ReturnNode(self, node):
        value = None
        if node.expr:
            value = self.evaluate(node.expr)
        raise ReturnException(value)

    def visit_BlockNode(self, node):
        self.execute_block(node, Environment(self.environment))
        return None

    def execute_block(self, block_node, env):
        previous_env = self.environment
        try:
            self.environment = env
            for stmt in block_node.statements:
                self.execute(stmt)
        finally:
            self.environment = previous_env

    # --- Expression Visitors ---

    def visit_AssignNode(self, node):
        value = self.evaluate(node.expr)
        
        if isinstance(node.target, IdentifierNode):
            self.environment.assign(node.target.name, value, node.token, self.filepath, self.source)
        elif isinstance(node.target, IndexNode):
            base = self.evaluate(node.target.expr)
            index = self.evaluate(node.target.index)
            
            if isinstance(base, list):
                if not isinstance(index, int):
                    raise PancoRuntimeError("List index must be an integer.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
                try:
                    base[index] = value
                except IndexError:
                    raise PancoRuntimeError("List assignment index out of range.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
            elif isinstance(base, dict):
                # Ensure key is hashable
                if isinstance(index, (list, dict)):
                    raise PancoRuntimeError("Dictionary keys must be hashable types (strings, numbers, booleans, nil).", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
                base[index] = value
            else:
                raise PancoRuntimeError("Can only assign to indices of lists or dictionaries.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
        
        return value

    def visit_BinaryOpNode(self, node):
        left = self.evaluate(node.left)
        
        # Handle short-circuit logical operators
        if node.operator == "or":
            if self.is_truthy(left):
                return left
            return self.evaluate(node.right)
        if node.operator == "and":
            if not self.is_truthy(left):
                return left
            return self.evaluate(node.right)
            
        right = self.evaluate(node.right)
        op = node.operator

        # Arithmetic
        if op == "+":
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            if isinstance(left, list) and isinstance(right, list):
                return left + right
            # If string is involved, do string concatenation
            if isinstance(left, str) or isinstance(right, str):
                return self.stringify(left) + self.stringify(right)
                
            raise PancoRuntimeError(
                f"Unsupported operand types for +: '{type(left).__name__}' and '{type(right).__name__}'.",
                self.filepath,
                node.token.line,
                node.token.column,
                node.token.length,
                self.source
            )
            
        if op == "-":
            self.check_number_operands(node.token, left, right)
            return left - right
        if op == "*":
            self.check_number_operands(node.token, left, right)
            return left * right
        if op == "/":
            self.check_number_operands(node.token, left, right)
            if right == 0:
                raise PancoRuntimeError("Division by zero.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
            return left / right
        if op == "%":
            self.check_number_operands(node.token, left, right)
            if right == 0:
                raise PancoRuntimeError("Modulo by zero.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
            return left % right

        # Comparison
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
            
        if op in ("<", "<=", ">", ">="):
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                pass
            elif isinstance(left, str) and isinstance(right, str):
                pass
            else:
                raise PancoRuntimeError(
                    f"Comparison '{op}' requires operands of the same type (both numbers or both strings).",
                    self.filepath,
                    node.token.line,
                    node.token.column,
                    node.token.length,
                    self.source
                )
            
            if op == "<": return left < right
            if op == "<=": return left <= right
            if op == ">": return left > right
            if op == ">=": return left >= right

        raise PancoRuntimeError(f"Unknown operator '{op}'.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)

    def visit_UnaryOpNode(self, node):
        right = self.evaluate(node.expr)
        if node.operator == "-":
            self.check_number_operand(node.token, right)
            return -right
        if node.operator in ("not", "!"):
            return not self.is_truthy(right)
            
        raise PancoRuntimeError(f"Unknown unary operator '{node.operator}'.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)

    def visit_CallNode(self, node):
        callee = self.evaluate(node.callee)
        
        arguments = []
        for arg in node.args:
            arguments.append(self.evaluate(arg))
            
        if not isinstance(callee, PancoCallable):
            raise PancoRuntimeError(
                "Can only call functions.",
                self.filepath,
                node.token.line,
                node.token.column,
                node.token.length,
                self.source
            )
            
        # Arity check. A built-in function arity of -1 means variadic arguments
        expected_arity = callee.arity()
        if expected_arity != -1 and len(arguments) != expected_arity:
            raise PancoRuntimeError(
                f"Expected {expected_arity} arguments but got {len(arguments)}.",
                self.filepath,
                node.token.line,
                node.token.column,
                node.token.length,
                self.source
            )
            
        return callee.call(self, arguments, node.token)

    def visit_LiteralNode(self, node):
        if isinstance(node.value, str):
            return self.evaluate_string_interpolation(node.value, node.token)
        return node.value

    def visit_ListNode(self, node):
        return [self.evaluate(element) for element in node.elements]

    def visit_DictNode(self, node):
        pairs = {}
        for key_expr, val_expr in node.pairs:
            k = self.evaluate(key_expr)
            if isinstance(k, (list, dict)):
                raise PancoRuntimeError(
                    "Dictionary keys must be hashable (strings, numbers, booleans, nil).",
                    self.filepath,
                    key_expr.token.line,
                    key_expr.token.column,
                    key_expr.token.length,
                    self.source
                )
            v = self.evaluate(val_expr)
            pairs[k] = v
        return pairs

    def visit_IdentifierNode(self, node):
        return self.environment.get(node.name, node.token, self.filepath, self.source)

    def visit_IndexNode(self, node):
        base = self.evaluate(node.expr)
        index = self.evaluate(node.index)
        
        if isinstance(base, list):
            if not isinstance(index, int):
                raise PancoRuntimeError("List index must be an integer.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
            try:
                return base[index]
            except IndexError:
                raise PancoRuntimeError("List index out of range.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
        elif isinstance(base, str):
            if not isinstance(index, int):
                raise PancoRuntimeError("String index must be an integer.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
            try:
                return base[index]
            except IndexError:
                raise PancoRuntimeError("String index out of range.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
        elif isinstance(base, dict):
            if isinstance(index, (list, dict)):
                raise PancoRuntimeError("Dictionary key must be hashable.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)
            # Return nil if not found, Javascript style
            return base.get(index, None)
        else:
            raise PancoRuntimeError("Can only index lists, strings, or dictionaries.", self.filepath, node.token.line, node.token.column, node.token.length, self.source)

    # --- Helpers for Execution ---

    def is_truthy(self, value):
        if value is None: return False
        if isinstance(value, bool): return value
        return True

    def check_number_operand(self, token, operand):
        if isinstance(operand, (int, float)): return
        raise PancoRuntimeError("Operand must be a number.", self.filepath, token.line, token.column, token.length, self.source)

    def check_number_operands(self, token, left, right):
        if isinstance(left, (int, float)) and isinstance(right, (int, float)): return
        raise PancoRuntimeError("Operands must be numbers.", self.filepath, token.line, token.column, token.length, self.source)

    def evaluate_string_interpolation(self, value, token):
        result = []
        i = 0
        while i < len(value):
            if value[i] == '{' and (i == 0 or value[i-1] != '\\'):
                start = i + 1
                brace_count = 1
                j = start
                while j < len(value):
                    if value[j] == '{' and value[j-1] != '\\':
                        brace_count += 1
                    elif value[j] == '}' and value[j-1] != '\\':
                        brace_count -= 1
                        if brace_count == 0:
                            break
                    j += 1
                if j >= len(value):
                    raise PancoRuntimeError(
                        "Unterminated string interpolation '{' in string literal.",
                        self.filepath,
                        token.line,
                        token.column,
                        token.length,
                        self.source
                    )
                expr_str = value[start:j]
                
                # Import lexer/parser here to avoid circular imports
                from interpreter.lexer import Lexer
                from interpreter.parser import Parser
                
                # Lex and parse the inner expression
                expr_lexer = Lexer(expr_str, filepath=self.filepath)
                # Adjust the relative position for inner tokens to map to original source file
                expr_tokens = expr_lexer.scan_tokens()
                
                # Setup parser and parse
                expr_parser = Parser(expr_tokens, self.source, filepath=self.filepath)
                expr_ast = expr_parser.expression()
                
                # Evaluate and append
                val = self.evaluate(expr_ast)
                result.append(self.stringify(val))
                i = j + 1
            elif value[i] == '}' and (i == 0 or value[i-1] != '\\'):
                raise PancoRuntimeError(
                    "Unmatched closing brace '}' in string literal. Escape with '\\}' for a literal brace.",
                    self.filepath,
                    token.line,
                    token.column,
                    token.length,
                    self.source
                )
            else:
                # Handle escaped braces
                if value[i] == '\\' and i + 1 < len(value) and value[i+1] in ('{', '}'):
                    result.append(value[i+1])
                    i += 2
                else:
                    result.append(value[i])
                    i += 1
        return "".join(result)

    def log_message(self, message, level="INFO"):
        if not self.log_path:
            return
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{now}] [{level}] {message}\n"
        
        paths_to_try = [
            self.log_path,
            # Fallback path relative to script directory (stripping leading slash)
            os.path.join(self.script_dir, self.log_path.lstrip("/"))
        ]
        
        success = False
        last_error = None
        
        for path in paths_to_try:
            try:
                # Ensure directory exists
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(formatted)
                success = True
                break
            except Exception as e:
                last_error = e
                
        if not success and not self.fallback_logged_warning:
            self.fallback_logged_warning = True
            print(
                f"\033[93m[Warning] Unable to write logs to any of {paths_to_try}. Error: {str(last_error)}\033[0m",
                file=sys.stderr
            )

    def visit_ImportDefaultNode(self, node):
        # Resolve panco.db relative to script directory if self.db_path is empty
        db_path = self.db_path if self.db_path else self.resolve_path("panco.db")
        self._import_extension(db_path, node.extension_name, node.token)
        return None

    def visit_ImportFromNode(self, node):
        # Resolve target database path relative to script directory
        resolved_db_path = self.resolve_path(node.db_path)
        self._import_extension(resolved_db_path, node.extension_name, node.token)
        return None

    def _import_extension(self, db_path, extension_name, token):
        try:
            parent = os.path.dirname(db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extensions (
                    name TEXT PRIMARY KEY,
                    code TEXT
                )
            """)
            conn.commit()
            
            cursor.execute("SELECT code FROM extensions WHERE name = ?", (extension_name,))
            row = cursor.fetchone()
            conn.close()
        except Exception as e:
            raise PancoRuntimeError(
                f"Failed to query database '{db_path}': {str(e)}",
                self.filepath,
                token.line,
                token.column,
                token.length,
                self.source
            )
            
        if not row:
            raise PancoRuntimeError(
                f"Extension '{extension_name}' not found in database '{db_path}'.",
                self.filepath,
                token.line,
                token.column,
                token.length,
                self.source
            )
            
        code = row[0]
        
        # Parse the loaded code
        from interpreter.lexer import Lexer
        from interpreter.parser import Parser
        
        virtual_path = f"<ext:{extension_name}>"
        
        try:
            lexer = Lexer(code, filepath=virtual_path)
            tokens = lexer.scan_tokens()
            
            parser = Parser(tokens, code, filepath=virtual_path)
            ast = parser.parse()
            
            # Execute loaded code statements in current environment scope
            for stmt in ast.statements:
                self.execute(stmt)
        except PancoRuntimeError as e:
            raise e
        except Exception as e:
            raise PancoRuntimeError(
                f"Failed to execute extension '{extension_name}': {str(e)}",
                self.filepath,
                token.line,
                token.column,
                token.length,
                self.source
            )
