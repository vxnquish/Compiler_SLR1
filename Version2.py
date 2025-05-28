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
        
        # Add epsilon to FIRST sets for nullable nonterminals
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar.rules:
                if not rhs:  # epsilon production
                    if '' not in self.first_sets[lhs]:
                        self.first_sets[lhs].add('')
                        changed = True
                else:
                    # Add FIRST(rhs[0]) to FIRST(lhs)
                    old_size = len(self.first_sets[lhs])
                    if rhs[0] in self.grammar.terminals:
                        self.first_sets[lhs].add(rhs[0])
                    else:
                        self.first_sets[lhs].update(self.first_sets[rhs[0]] - {''})
                        
                        # If rhs[0] can derive epsilon, check rhs[1], etc.
                        i = 0
                        while i < len(rhs) and '' in self.first_sets.get(rhs[i], set()):
                            if i + 1 < len(rhs):
                                if rhs[i + 1] in self.grammar.terminals:
                                    self.first_sets[lhs].add(rhs[i + 1])
                                else:
                                    self.first_sets[lhs].update(self.first_sets[rhs[i + 1]] - {''})
                            i += 1
                        
                        # If all symbols can derive epsilon
                        if i == len(rhs) and all('' in self.first_sets.get(sym, set()) for sym in rhs):
                            self.first_sets[lhs].add('')
                    
                    if len(self.first_sets[lhs]) > old_size:
                        changed = True
    
    def build_follow_sets(self):
        # Initialize FOLLOW sets
        for symbol in self.grammar.nonterminals:
            self.follow_sets[symbol] = set()
        self.follow_sets["Program"] = {"$"}
        
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar.rules:
                for i, symbol in enumerate(rhs):
                    if symbol in self.grammar.nonterminals:
                        old_size = len(self.follow_sets[symbol])
                        
                        # Add FIRST(beta) - {epsilon} to FOLLOW(symbol)
                        beta = rhs[i + 1:]
                        if beta:
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
    
    def get_first_of_sequence(self, sequence):
        result = set()
        for symbol in sequence:
            if symbol in self.grammar.terminals:
                result.add(symbol)
                break
            else:
                result.update(self.first_sets[symbol] - {''})
                if '' not in self.first_sets[symbol]:
                    break
        else:
            # All symbols can derive epsilon
            result.add('')
        return result
    
    def build_lr0_items(self):
        # Build LR(0) items and states
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
            return closure(new_items)
        
        # Start with initial item
        initial_item = (0, 0)  # Program' -> .Program
        initial_state = closure({initial_item})
        
        states = [initial_state]
        state_map = {initial_state: 0}
        transitions = {}
        
        queue = [initial_state]
        while queue:
            state = queue.pop(0)
            state_idx = state_map[state]
            
            # Get all symbols after dot
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
        states, transitions = self.build_lr0_items()
        
        # Build ACTION and GOTO tables
        for i, state in enumerate(states):
            for item in state:
                rule_idx, dot_pos = item
                lhs, rhs = self.grammar.rules[rule_idx]
                
                if dot_pos < len(rhs):
                    # Shift actions
                    symbol = rhs[dot_pos]
                    if symbol in self.grammar.terminals and (i, symbol) in transitions:
                        self.parsing_table[(i, symbol)] = ('shift', transitions[(i, symbol)])
                else:
                    # Reduce actions
                    if lhs == "Program'" and rhs == ["Program"]:
                        # Accept state
                        self.parsing_table[(i, "$")] = ('accept',)
                    else:
                        # Add reduce actions for all terminals in FOLLOW(lhs)
                        for terminal in self.follow_sets[lhs]:
                            if (i, terminal) not in self.parsing_table:
                                self.parsing_table[(i, terminal)] = ('reduce', rule_idx)
        
        # Add GOTO entries
        for (state, symbol), next_state in transitions.items():
            if symbol in self.grammar.nonterminals:
                self.parsing_table[(state, symbol)] = ('goto', next_state)
    
    def parse(self, tokens):
        # Add end marker
        tokens = tokens + ["$"]
        
        stack = [0]  # Stack of states
        symbol_stack = []  # Stack of symbols for parse tree construction
        index = 0
        
        while True:
            state = stack[-1]
            token = tokens[index]
            
            # Handle special tokens
            if token not in self.grammar.terminals:
                if token.startswith("id:") or token == "id":
                    lookahead = "id"
                elif token.startswith("num:") or token == "num":
                    lookahead = "num"
                elif token == "int" or token == "float" or token == "bool":
                    lookahead = "type"
                else:
                    lookahead = token
            else:
                lookahead = token
            
            if (state, lookahead) not in self.parsing_table:
                # Error: no action defined
                expected = []
                for (s, t) in self.parsing_table:
                    if s == state:
                        expected.append(t)
                return False, ErrorReport(index, f"unexpected token '{token}', expected one of: {', '.join(expected)}")
            
            action = self.parsing_table[(state, lookahead)]
            
            if action[0] == 'shift':
                stack.append(action[1])
                symbol_stack.append(ParseTree(token))
                index += 1
            
            elif action[0] == 'reduce':
                rule_idx = action[1]
                lhs, rhs = self.grammar.rules[rule_idx]
                
                # Pop |rhs| states and symbols
                children = []
                for _ in range(len(rhs)):
                    stack.pop()
                    if symbol_stack:
                        children.insert(0, symbol_stack.pop())
                
                # Create new parse tree node
                node = ParseTree(lhs, children)
                symbol_stack.append(node)
                
                # Push GOTO state
                state = stack[-1]
                if (state, lhs) in self.parsing_table:
                    goto_action = self.parsing_table[(state, lhs)]
                    stack.append(goto_action[1])
                else:
                    return False, ErrorReport(index, f"no GOTO entry for state {state} and symbol {lhs}")
            
            elif action[0] == 'accept':
                # Success!
                return True, symbol_stack[0].children[0]  # Return Program node (not Program')
            
            else:
                return False, ErrorReport(index, f"unknown action: {action}")

def parser(tokens: List[str]) -> Tuple[bool, Union[ParseTree, ErrorReport]]:
    """
    Returns (True, parse_tree) on success or (False, ErrorReport) on failure.
    """
    slr_parser = SLRParser()
    return slr_parser.parse(tokens) # type: ignore