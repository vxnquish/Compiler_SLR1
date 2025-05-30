from typing import List, Tuple, Union, Dict, Set

class ParseTree:
    def __init__(self, symbol: str, children: List['ParseTree'] = None):
        self.symbol = symbol
        self.children = children or []
    
    def __str__(self):
        return self._str_helper(0)
    
    def _str_helper(self, depth):
        indent = "  " * depth
        result = f"{indent}{self.symbol}"
        if self.children:
            for child in self.children:
                result += "\n" + child._str_helper(depth + 1)
        return result

class ErrorReport:
    def __init__(self, position: int, message: str):
        self.position = position
        self.message = message

class Grammar:
    def __init__(self):
        # Define the grammar rules
        self.rules = [
            ("Program'", ["Program"]),  # Augmented start
            ("Program", ["DeclList"]),
            ("DeclList", ["Decl", "DeclList"]),
            ("DeclList", []),  # epsilon
            ("Decl", ["VarDecl"]),
            ("Decl", ["FuncDecl"]),
            ("VarDecl", ["type", "id", ";"]),
            ("VarDecl", ["type", "id", "=", "Expr", ";"]),
            ("FuncDecl", ["type", "id", "(", "ParamList", ")", "Block"]),
            ("ParamList", ["Param", "ParamRest"]),
            ("ParamList", []),  # epsilon
            ("ParamRest", [",", "Param", "ParamRest"]),
            ("ParamRest", []),  # epsilon
            ("Param", ["type", "id"]),
            ("Block", ["{", "StmtList", "}"]),
            ("StmtList", ["Stmt", "StmtList"]),
            ("StmtList", []),  # epsilon
            ("Stmt", ["MatchedStmt"]),
            ("Stmt", ["UnmatchedStmt"]),
            ("MatchedStmt", ["if", "(", "Expr", ")", "MatchedStmt", "else", "MatchedStmt"]),
            ("MatchedStmt", ["while", "(", "Expr", ")", "MatchedStmt"]),
            ("MatchedStmt", ["for", "(", "Expr", ";", "Expr", ";", "Expr", ")", "MatchedStmt"]),
            ("MatchedStmt", ["return", "Expr", ";"]),
            ("MatchedStmt", ["VarDecl"]),
            ("MatchedStmt", ["ExprStmt"]),
            ("MatchedStmt", ["Block"]),
            ("UnmatchedStmt", ["if", "(", "Expr", ")", "Stmt"]),
            ("UnmatchedStmt", ["if", "(", "Expr", ")", "MatchedStmt", "else", "UnmatchedStmt"]),
            ("UnmatchedStmt", ["while", "(", "Expr", ")", "UnmatchedStmt"]),
            ("UnmatchedStmt", ["for", "(", "Expr", ";", "Expr", ";", "Expr", ")", "UnmatchedStmt"]),
            ("ExprStmt", ["id", "=", "Expr", ";"]),
            ("Expr", ["EqlExpr"]),
            ("EqlExpr", ["EqlExpr", "==", "AddExpr"]),
            ("EqlExpr", ["AddExpr"]),
            ("AddExpr", ["AddExpr", "+", "MulExpr"]),
            ("AddExpr", ["MulExpr"]),
            ("MulExpr", ["MulExpr", "*", "UnaryExpr"]),
            ("MulExpr", ["UnaryExpr"]),
            ("UnaryExpr", ["-", "UnaryExpr"]),
            ("UnaryExpr", ["Primary"]),
            ("Primary", ["id", "(", "ArgList", ")"]),
            ("Primary", ["id"]),
            ("Primary", ["num"]),
            ("Primary", ["(", "Expr", ")"]),
            ("ArgList", ["Expr", "ArgRest"]),
            ("ArgList", []),  # epsilon
            ("ArgRest", [",", "Expr", "ArgRest"]),
            ("ArgRest", []),  # epsilon
        ]
        
        self.start_symbol = "Program'"
        self.terminals = {"type", "id", ";", "=", "(", ")", ",", "{", "}", "if", "else", 
                         "while", "for", "return", "==", "+", "*", "-", "num", "$"}
        self.nonterminals = {rule[0] for rule in self.rules}
        
    def get_rule(self, index):
        return self.rules[index]

class SLRParser:
    def __init__(self):
        self.grammar = Grammar()
        self.first_sets = {}
        self.follow_sets = {}
        self.parsing_table = {}
        self.build_first_sets()
        self.build_follow_sets()
        self.build_parsing_table()
    
    def build_first_sets(self):
        # Initialize FIRST sets
        for symbol in self.grammar.terminals:
            self.first_sets[symbol] = {symbol}
        for symbol in self.grammar.nonterminals:
            self.first_sets[symbol] = set()
        
        # Add epsilon to empty string symbol
        self.first_sets[''] = {''}
        
        # Iteratively compute FIRST sets
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar.rules:
                old_size = len(self.first_sets[lhs])
                
                if not rhs:  # epsilon production
                    self.first_sets[lhs].add('')
                else:
                    # Compute FIRST of the entire RHS sequence
                    first_rhs = self.get_first_of_sequence(rhs)
                    self.first_sets[lhs].update(first_rhs)
                
                if len(self.first_sets[lhs]) > old_size:
                    changed = True
    
    def get_first_of_sequence(self, sequence):
        """Compute FIRST set for a sequence of symbols"""
        if not sequence:
            return {''}
        
        result = set()
        all_have_epsilon = True
        
        for symbol in sequence:
            if symbol in self.grammar.terminals:
                result.add(symbol)
                all_have_epsilon = False
                break
            elif symbol in self.first_sets:
                # Add FIRST(symbol) - {epsilon}
                result.update(self.first_sets[symbol] - {''})
                # If symbol doesn't have epsilon, stop
                if '' not in self.first_sets[symbol]:
                    all_have_epsilon = False
                    break
            else:
                # Symbol not yet computed, assume no epsilon for now
                all_have_epsilon = False
                break
        
        # If all symbols can derive epsilon, add epsilon to result
        if all_have_epsilon:
            result.add('')
        
        return result
    
    def build_follow_sets(self):
        # Initialize FOLLOW sets
        for symbol in self.grammar.nonterminals:
            self.follow_sets[symbol] = set()
        
        # Start symbol gets $ in its FOLLOW set
        self.follow_sets["Program'"] = {"$"}
        
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar.rules:
                for i, symbol in enumerate(rhs):
                    if symbol in self.grammar.nonterminals:
                        old_size = len(self.follow_sets[symbol])
                        
                        # Get the sequence after this symbol (beta)
                        beta = rhs[i + 1:]
                        if beta:
                            # Add FIRST(beta) - {epsilon} to FOLLOW(symbol)
                            first_beta = self.get_first_of_sequence(beta)
                            self.follow_sets[symbol].update(first_beta - {''})
                            
                            # If beta can derive epsilon, add FOLLOW(lhs)
                            if '' in first_beta:
                                self.follow_sets[symbol].update(self.follow_sets[lhs])
                        else:
                            # symbol is at the end, add FOLLOW(lhs)
                            self.follow_sets[symbol].update(self.follow_sets[lhs])
                        
                        if len(self.follow_sets[symbol]) > old_size:
                            changed = True
    
    def build_lr0_items(self):
        """Build LR(0) items and states"""
        def closure(items):
            result = set(items)
            changed = True
            while changed:
                changed = False
                for item in list(result):
                    rule_idx, dot_pos = item
                    lhs, rhs = self.grammar.rules[rule_idx]
                    if dot_pos < len(rhs) and rhs[dot_pos] in self.grammar.nonterminals:
                        # Add all productions for this nonterminal
                        for i, (prod_lhs, prod_rhs) in enumerate(self.grammar.rules):
                            if prod_lhs == rhs[dot_pos]:
                                new_item = (i, 0)
                                if new_item not in result:
                                    result.add(new_item)
                                    changed = True
            return frozenset(result)
        
        def goto(items, symbol):
            new_items = set()
            for rule_idx, dot_pos in items:
                lhs, rhs = self.grammar.rules[rule_idx]
                if dot_pos < len(rhs) and rhs[dot_pos] == symbol:
                    new_items.add((rule_idx, dot_pos + 1))
            return closure(new_items) if new_items else frozenset()
        
        # Start with initial item: Program' -> .Program
        initial_item = (0, 0)
        initial_state = closure({initial_item})
        
        states = [initial_state]
        state_map = {initial_state: 0}
        transitions = {}
        
        queue = [initial_state]
        while queue:
            state = queue.pop(0)
            state_idx = state_map[state]
            
            # Get all symbols that can appear after the dot
            symbols = set()
            for rule_idx, dot_pos in state:
                lhs, rhs = self.grammar.rules[rule_idx]
                if dot_pos < len(rhs):
                    symbols.add(rhs[dot_pos])
            
            # Compute GOTO for each symbol
            for symbol in symbols:
                new_state = goto(state, symbol)
                if new_state:
                    if new_state not in state_map:
                        state_map[new_state] = len(states)
                        states.append(new_state)
                        queue.append(new_state)
                    transitions[(state_idx, symbol)] = state_map[new_state]
        
        return states, transitions
    
    def build_parsing_table(self):
        """Build the SLR parsing table"""
        states, transitions = self.build_lr0_items()
        
        # Initialize parsing table
        self.parsing_table = {}
        
        # Build ACTION and GOTO tables
        for i, state in enumerate(states):
            for item in state:
                rule_idx, dot_pos = item
                lhs, rhs = self.grammar.rules[rule_idx]
                
                if dot_pos < len(rhs):
                    # Shift actions for terminals
                    symbol = rhs[dot_pos]
                    if symbol in self.grammar.terminals and (i, symbol) in transitions:
                        next_state = transitions[(i, symbol)]
                        if (i, symbol) in self.parsing_table:
                            # Conflict detection
                            existing = self.parsing_table[(i, symbol)]
                            if existing != ('shift', next_state):
                                print(f"Shift/Reduce conflict at state {i}, symbol {symbol}")
                        self.parsing_table[(i, symbol)] = ('shift', next_state)
                else:
                    # Reduce actions
                    if rule_idx == 0:  # Program' -> Program
                        # Accept state
                        self.parsing_table[(i, "$")] = ('accept',)
                    else:
                        # Add reduce actions for all terminals in FOLLOW(lhs)
                        for terminal in self.follow_sets[lhs]:
                            if (i, terminal) in self.parsing_table:
                                # Conflict detection
                                existing = self.parsing_table[(i, terminal)]
                                if existing != ('reduce', rule_idx):
                                    print(f"Reduce/Reduce conflict at state {i}, symbol {terminal}")
                            else:
                                self.parsing_table[(i, terminal)] = ('reduce', rule_idx)
        
        # Add GOTO entries for nonterminals
        for (state, symbol), next_state in transitions.items():
            if symbol in self.grammar.nonterminals:
                self.parsing_table[(state, symbol)] = ('goto', next_state)
    
    def normalize_token(self, token):
        """Normalize tokens to match grammar terminals"""
        if token == "$":
            return "$"
        elif token in ["int", "float", "bool", "void"]:
            return "type"
        elif token.startswith("id") or token == "identifier":
            return "id"
        elif token.startswith("num") or token.isdigit() or token == "number":
            return "num"
        elif token in self.grammar.terminals:
            return token
        else:
            # Try to extract the actual token value
            if ":" in token:
                return token.split(":")[0]
            return token
    
    def parse(self, tokens):
        """Parse a list of tokens using SLR parsing"""
        # Normalize tokens and add end marker
        normalized_tokens = [self.normalize_token(token) for token in tokens]
        normalized_tokens.append("$")
        
        stack = [0]  # Stack of states
        symbol_stack = []  # Stack of symbols for parse tree construction
        index = 0
        
        while index < len(normalized_tokens):
            state = stack[-1]
            lookahead = normalized_tokens[index]
            
            if (state, lookahead) not in self.parsing_table:
                # Error: no action defined
                expected = []
                for (s, t) in self.parsing_table:
                    if s == state and t in self.grammar.terminals:
                        expected.append(t)
                expected = list(set(expected))  # Remove duplicates
                return False, ErrorReport(index, 
                    f"Unexpected token '{tokens[index] if index < len(tokens) else '$'}' at position {index}. Expected one of: {', '.join(expected)}")
            
            action = self.parsing_table[(state, lookahead)]
            
            if action[0] == 'shift':
                next_state = action[1]
                stack.append(next_state)
                # Use original token for parse tree
                original_token = tokens[index] if index < len(tokens) else "$"
                symbol_stack.append(ParseTree(original_token))
                index += 1
            
            elif action[0] == 'reduce':
                rule_idx = action[1]
                lhs, rhs = self.grammar.rules[rule_idx]
                
                # Pop |rhs| states and symbols
                children = []
                for _ in range(len(rhs)):
                    if stack:
                        stack.pop()
                    if symbol_stack:
                        children.insert(0, symbol_stack.pop())
                
                # Create new parse tree node
                node = ParseTree(lhs, children)
                symbol_stack.append(node)
                
                # Push GOTO state
                current_state = stack[-1] if stack else 0
                if (current_state, lhs) in self.parsing_table:
                    goto_action = self.parsing_table[(current_state, lhs)]
                    if goto_action[0] == 'goto':
                        stack.append(goto_action[1])
                    else:
                        return False, ErrorReport(index, f"Expected GOTO action for state {current_state} and symbol {lhs}")
                else:
                    return False, ErrorReport(index, f"No GOTO entry for state {current_state} and symbol {lhs}")
            
            elif action[0] == 'accept':
                # Success! Return the Program node (child of Program')
                if symbol_stack and symbol_stack[0].children:
                    return True, symbol_stack[0].children[0]
                else:
                    return True, symbol_stack[0] if symbol_stack else ParseTree("Program")
            
            else:
                return False, ErrorReport(index, f"Unknown action: {action}")
        
        return False, ErrorReport(index, "Unexpected end of input")

def parser(tokens: List[str]) -> Tuple[bool, Union[ParseTree, ErrorReport]]:
    """
    Parse a list of tokens and return either a parse tree or an error report.
    
    Args:
        tokens: List of tokens to parse
        
    Returns:
        Tuple of (success, result) where:
        - success is True if parsing succeeded, False otherwise
        - result is ParseTree if success=True, ErrorReport if success=False
    """
    slr_parser = SLRParser()
    return slr_parser.parse(tokens)

# Example usage and testing
if __name__ == "__main__":
    # Test with a simple program
    test_tokens = [
        "int", "id:main", "(", ")", "{", 
        "int", "id:x", ";",
        "return", "num:0", ";",
        "}"
    ]
    
    success, result = parser(test_tokens)
    if success:
        print("Parsing successful!")
        print("Parse tree:")
        print(result)
    else:
        print("Parsing failed:")
        print(f"Error at position {result.position}: {result.message}") # type: ignore