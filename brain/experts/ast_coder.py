import ast

def extract_ast_snippet(text: str, query_tokens: set[str], symbols: list[str]) -> str | None:
    """
    Parses Python code and extracts the entire function or class block that matches
    the queried symbols or tokens. It gives a full structured answer to 'code like an AI'.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
        
    # We want to find a matching ClassDef or FunctionDef
    matching_nodes = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            node_name_lower = node.name.lower()
            # Direct symbol match check
            if any(sym in node.name for sym in symbols):
                matching_nodes.append(node)
                continue
                
            # Token match check
            if any(tok in node_name_lower for tok in query_tokens):
                matching_nodes.append(node)
                continue
                
            # Docstring match check
            docstring = ast.get_docstring(node)
            if docstring:
                doc_lower = docstring.lower()
                if any(tok in doc_lower for tok in query_tokens):
                    matching_nodes.append(node)
                    continue

    if not matching_nodes:
        return None
        
    # Take the most relevant node (the one that matched)
    best_node = matching_nodes[0]
    
    # Extract the source code lines for this node
    lines = text.splitlines()
    start_line = best_node.lineno - 1
    end_line = best_node.end_lineno if getattr(best_node, "end_lineno", None) else min(start_line + 15, len(lines))
    
    block = "\n".join(lines[start_line:end_line])
    
    # Add a contextual AI-like explanation algorithmically
    node_type = "Class" if isinstance(best_node, ast.ClassDef) else "Function"
    
    explanation = (
        f"I have parsed the AST and located the exact {node_type} `{best_node.name}`. "
        f"Here is the complete implementation block:\n"
        f"```python\n{block}\n```"
    )
    return explanation
