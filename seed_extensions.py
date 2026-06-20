#!/usr/bin/env python3
import sqlite3
import os

def seed_db(db_path, extension_name, code):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extensions (
            name TEXT PRIMARY KEY,
            code TEXT
        )
    """)
    cursor.execute("INSERT OR REPLACE INTO extensions (name, code) VALUES (?, ?)", (extension_name, code))
    conn.commit()
    conn.close()
    print(f"Successfully seeded extension '{extension_name}' inside '{db_path}'.")

if __name__ == "__main__":
    # Seed default db (which is database/panco.db in our workspace)
    default_db_path = "database/panco.db"
    math_code = """
delta double_val(x) {
    return x * 2
}

delta triple_val(x) {
    return x * 3
}
"""
    seed_db(default_db_path, "math_ext", math_code)

    # Seed a custom db in the workspace
    custom_db_path = "custom.db"
    utils_code = """
delta greet(name) {
    return "Greetings, " + name + " from custom.db!"
}
"""
    seed_db(custom_db_path, "utils_ext", utils_code)
