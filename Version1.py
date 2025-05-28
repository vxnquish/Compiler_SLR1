from typing import List, Tuple, Union, Dict, Set
from collections import namedtuple

class ParseTree:
    def __init__(self, symbol: str, children: List['ParseTree'] = None):
        self.symbol = symbol
        self.children = children or []
    def __repr__(self):
        if not self.children:
            return f"{self.symbol}"
        return f"({self.symbol} {' '.join(repr(c) for c in self.children)})"

class ErrorReport:
    def __init__(self, position: int, message: str):
        self.position = position
        self.message = message

# Grammar specification
GRAMMAR: Dict[str, List[List[str]]] = {
    "Program": [["DeclList"]],
    "DeclList": [["Decl", "DeclList"], []],
    "Decl": [["VarDecl"], ["FuncDecl"]],
    "VarDecl": [["type", "id", ";"], ["type", "id", "=", "Expr", ";"]],
    "FuncDecl": [["type", "id", "(", "ParamList", ")", "Block"]],
    "ParamList": [["Param", "ParamRest"], []],
    "ParamRest": [[",", "Param", "ParamRest"], []],
    "Param": [["type", "id"]],
    "Block": [["{", "StmtList", "}"]],
    "StmtList": [["Stmt", "StmtList"], []],
    "Stmt": [["MatchedStmt"], ["UnmatchedStmt"]],
    "MatchedStmt": [
        ["if", "(", "Expr", ")", "MatchedStmt", "else", "MatchedStmt"],
        ["while", "(", "Expr", ")", "MatchedStmt"],
        ["for", "(", "Expr", ";", "Expr", ";", "Expr", ")", "MatchedStmt"],
        ["return", "Expr", ";"],
        ["VarDecl"],
        ["ExprStmt"],
        ["Block"],
    ],
    "UnmatchedStmt": [
        ["if", "(", "Expr", ")", "Stmt"],
        ["if", "(", "Expr", ")", "MatchedStmt", "else", "UnmatchedStmt"],
        ["while", "(", "Expr", ")", "UnmatchedStmt"],
        ["for", "(", "Expr", ";", "Expr", ";", "Expr", ")", "UnmatchedStmt"],
    ],
    "ExprStmt": [["id", "=", "Expr", ";"]],
    "Expr": [["EqlExpr"]],
    "EqlExpr": [["EqlExpr", "==", "AddExpr"], ["AddExpr"]],
    "AddExpr": [["AddExpr", "+", "MulExpr"], ["MulExpr"]],
    "MulExpr": [["MulExpr", "*", "UnaryExpr"], ["UnaryExpr"]],
    "UnaryExpr": [["-", "UnaryExpr"], ["Primary"]],
    "Primary": [["id", "(", "ArgList", ")"], ["id"], ["num"], ["(", "Expr", ")"]],
    "ArgList": [["Expr", "ArgRest"], []],
    "ArgRest": [[",", "Expr", "ArgRest"], []],
}

# Augment grammar
GRAMMAR["Program'"] = [["Program"]]
NONTERMINALS: Set[str] = set(GRAMMAR.keys())
TERMINALS: Set[str] = set(
    sym for rhs_list in GRAMMAR.values() for rhs in rhs_list for sym in rhs
) - NONTERMINALS
TERMINALS.add("$")

# Compute FIRST sets

def compute_first() -> Dict[str, Set[str]]:
    FIRST: Dict[str, Set[str]] = {A: set() for A in NONTERMINALS}
    changed = True
    while changed:
        changed = False
        for A, productions in GRAMMAR.items():
            for rhs in productions:
                if not rhs:
                    if '' not in FIRST[A]:
                        FIRST[A].add('')
                        changed = True
                    continue
                for symbol in rhs:
                    if symbol in TERMINALS:
                        if symbol not in FIRST[A]:
                            FIRST[A].add(symbol)
                            changed = True
                        break
                    else:
                        before = len(FIRST[A])
                        FIRST[A] |= (FIRST[symbol] - {''})
                        if '' in FIRST[symbol]:
                            continue
                        break
                else:
                    if '' not in FIRST[A]:
                        FIRST[A].add('')
                        changed = True
    return FIRST

# Compute FOLLOW sets

def compute_follow(FIRST: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    FOLLOW: Dict[str, Set[str]] = {A: set() for A in NONTERMINALS}
    FOLLOW["Program"].add("$")
    changed = True
    while changed:
        changed = False
        for A, productions in GRAMMAR.items():
            for rhs in productions:
                trailer = FOLLOW[A].copy()
                for symbol in reversed(rhs):
                    if symbol in NONTERMINALS:
                        before = len(FOLLOW[symbol])
                        FOLLOW[symbol] |= trailer
                        if '' in FIRST[symbol]:
                            trailer |= (FIRST[symbol] - {''})
                        else:
                            trailer = FIRST[symbol]
                        if len(FOLLOW[symbol]) != before:
                            changed = True
                    else:
                        trailer = {symbol}
    return FOLLOW

# LR(0) item
Item = namedtuple("Item", ["lhs", "rhs", "dot"])

# Closure

def closure(items: Set[Item]) -> Set[Item]:
    closure_set = set(items)
    added = True
    while added:
        added = False
        for it in list(closure_set):
            if it.dot < len(it.rhs):
                B = it.rhs[it.dot]
                if B in NONTERMINALS:
                    for beta in GRAMMAR[B]:
                        new = Item(B, tuple(beta), 0)
                        if new not in closure_set:
                            closure_set.add(new)
                            added = True
    return closure_set

# GOTO

def goto(items: Set[Item], X: str) -> Set[Item]:
    return closure({Item(it.lhs, it.rhs, it.dot+1) for it in items if it.dot < len(it.rhs) and it.rhs[it.dot] == X})

# Build states

def build_states() -> List[Set[Item]]:
    C: List[Set[Item]] = []
    start = Item("Program'", tuple(GRAMMAR["Program'"][0]), 0)
    C.append(closure({start}))
    added = True
    while added:
        added = False
        for I in list(C):
            for X in NONTERMINALS | TERMINALS:
                J = goto(I, X)
                if J and J not in C:
                    C.append(J)
                    added = True
    return C

# Build parsing table

def build_parsing_table():
    FIRST = compute_first()
    FOLLOW = compute_follow(FIRST)
    C = build_states()
    action = [dict() for _ in C]
    goto_table = [dict() for _ in C]
    for i, I in enumerate(C):
        for it in I:
            if it.dot < len(it.rhs):
                a = it.rhs[it.dot]
                if a in TERMINALS:
                    j = C.index(goto(I, a))
                    action[i][a] = ("s", j)
            else:
                if it.lhs == "Program'":
                    action[i]["$"] = ("acc", 0)
                else:
                    for a in FOLLOW[it.lhs]:
                        action[i][a] = ("r", (it.lhs, list(it.rhs)))
        for A in NONTERMINALS:
            J = goto(I, A)
            if J in C:
                goto_table[i][A] = C.index(J)
    return action, goto_table

# Parser entry

def parser(tokens: List[str]) -> Tuple[bool, Union[ParseTree, ErrorReport]]:
    tokens = tokens + ["$"]
    action, goto_table = build_parsing_table()
    stack: List[int] = [0]
    node_stack: List[ParseTree] = []
    idx = 0
    while True:
        state = stack[-1]
        a = tokens[idx] if idx < len(tokens) else '$'
        if a not in action[state]:
            return False, ErrorReport(idx, f"Unexpected token '{a}'")
        act, val = action[state][a]
        if act == "s":
            stack.append(val)
            node_stack.append(ParseTree(a))
            idx += 1
        elif act == "r":
            lhs, rhs = val
            children = []
            for _ in rhs:
                stack.pop()
                children.insert(0, node_stack.pop())
            tree = ParseTree(lhs, children)
            state = stack[-1]
            stack.append(goto_table[state][lhs])
            node_stack.append(tree)
        else:  # accept
            return True, node_stack[0]
 # type: ignore