# Self-hosted Panco Interpreter in Panco

[allow}env\{}]

delta interpret_panco(code) {
    [allow}i\0]
    [allow}code_len\len(code)]
    
    while (i < code_len) {
        [allow}char\code[i]]
        
        # Skip whitespaces and newlines
        if (char == " " or char == "\n" or char == "\r" or char == "\t") {
            i = i + 1
        }
        # Skip comments
        else if (char == "#") {
            while (i < code_len and code[i] != "\n") {
                i = i + 1
            }
        }
        # Variable Declaration: [allow}name\value]
        else if (char == "[") {
            # Skip '[allow}'
            i = i + 7
            
            # Parse variable name
            [allow}name\""]
            while (i < code_len and code[i] != "\\") {
                name = name + code[i]
                i = i + 1
            }
            i = i + 1 # skip '\'
            
            # Parse value up to ']'
            [allow}val_str\""]
            while (i < code_len and code[i] != "]") {
                val_str = val_str + code[i]
                i = i + 1
            }
            i = i + 1 # skip ']'
            
            [allow}evaluated\eval_expr(val_str)]
            env[name] = evaluated
        }
        # Statement: makeword(...)
        else if (char == "m" and i + 8 <= code_len and code[i + 1] == "a" and code[i + 2] == "k" and code[i + 3] == "e" and code[i + 4] == "w" and code[i + 5] == "o" and code[i + 6] == "r" and code[i + 7] == "d") {
            i = i + 8 # skip 'makeword'
            
            while (i < code_len and code[i] != "(") {
                i = i + 1
            }
            i = i + 1 # skip '('
            
            # Parse argument up to ')'
            [allow}arg_str\""]
            while (i < code_len and code[i] != ")") {
                arg_str = arg_str + code[i]
                i = i + 1
            }
            i = i + 1 # skip ')'
            
            [allow}res\eval_expr(arg_str)]
            makeword(res)
        }
        else {
            i = i + 1
        }
    }
}

# Helper to evaluate expression (handles numbers, strings, variables, and + operator)
delta eval_expr(expr_str) {
    [allow}expr_str\trim(expr_str)]
    
    # Check for addition expression: left + right
    [allow}plus_idx\find_char(expr_str, "+")]
    if (plus_idx != -1) {
        [allow}left_part\slice(expr_str, 0, plus_idx)]
        [allow}right_part\slice(expr_str, plus_idx + 1, len(expr_str))]
        return eval_expr(left_part) + eval_expr(right_part)
    }
    
    # Check for string literal: "..."
    if (len(expr_str) >= 2 and expr_str[0] == "\"" and expr_str[len(expr_str) - 1] == "\"") {
        return slice(expr_str, 1, len(expr_str) - 1)
    }
    
    # Check if number
    [allow}num_val\to_number(expr_str)]
    if (num_val != nil) {
        return num_val
    }
    
    # Otherwise lookup in env
    [allow}lookup_val\env[expr_str]]
    if (lookup_val != nil) {
        return lookup_val
    }
    
    return expr_str
}

# Helper to trim whitespaces
delta trim(s) {
    [allow}start\0]
    [allow}end_idx\len(s)]
    while (start < end_idx and (s[start] == " " or s[start] == "\t" or s[start] == "\n" or s[start] == "\r")) {
        start = start + 1
    }
    while (end_idx > start and (s[end_idx - 1] == " " or s[end_idx - 1] == "\t" or s[end_idx - 1] == "\n" or s[end_idx - 1] == "\r")) {
        end_idx = end_idx - 1
    }
    return slice(s, start, end_idx)
}

# Helper to slice string
delta slice(s, start, end_idx) {
    [allow}res\""]
    [allow}curr\(start)]
    while (curr < end_idx) {
        res = res + s[curr]
        curr = curr + 1
    }
    return res
}

# Helper to find character index
delta find_char(s, c) {
    [allow}idx\0]
    [allow}s_len\len(s)]
    while (idx < s_len) {
        if (s[idx] == c) {
            return idx
        }
        idx = idx + 1
    }
    return -1
}

# Helper to convert string to number
delta to_number(s) {
    # Check if the string consists of only digits
    [allow}idx\0]
    [allow}s_len\len(s)]
    if (s_len == 0) {
        return nil
    }
    while (idx < s_len) {
        [allow}ch\s[idx]]
        if (ch != "0" and ch != "1" and ch != "2" and ch != "3" and ch != "4" and ch != "5" and ch != "6" and ch != "7" and ch != "8" and ch != "9") {
            return nil
        }
        idx = idx + 1
    }
    
    # Calculate number
    [allow}res\0]
    idx = 0
    while (idx < s_len) {
        [allow}digit\0]
        [allow}ch\s[idx]]
        if (ch == "1") { digit = 1 }
        else if (ch == "2") { digit = 2 }
        else if (ch == "3") { digit = 3 }
        else if (ch == "4") { digit = 4 }
        else if (ch == "5") { digit = 5 }
        else if (ch == "6") { digit = 6 }
        else if (ch == "7") { digit = 7 }
        else if (ch == "8") { digit = 8 }
        else if (ch == "9") { digit = 9 }
        res = res * 10 + digit
        idx = idx + 1
    }
    return res
}

# --- Demo Run ---
[allow}panco_code\"
[allow\\}x\\15]
[allow\\}y\\25]
[allow\\}msg\\\"The sum is: \"]
makeword(msg + x + y)
"
]

makeword("Running self-hosted Panco interpreter on:")
makeword(panco_code)
makeword("------------------------------")
interpret_panco(panco_code)
makeword("------------------------------")
