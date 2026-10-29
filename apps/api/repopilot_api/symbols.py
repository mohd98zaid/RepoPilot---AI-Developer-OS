from __future__ import annotations

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language, Parser


def parse(text, language, path=""):
    factories = {
        "python": tree_sitter_python.language,
        "javascript": tree_sitter_javascript.language,
        "typescript": tree_sitter_typescript.language_tsx
        if path.endswith(".tsx")
        else tree_sitter_typescript.language_typescript,
    }
    factory = factories.get(language)
    return Parser(Language(factory())).parse(text.encode("utf-8")) if factory else None


def extract_symbols(text: str, language: str, path="") -> list[dict]:
    tree = parse(text, language, path)
    if tree is None:
        return []
    kinds = {
        "class_definition": "class",
        "class_declaration": "class",
        "function_definition": "function",
        "function_declaration": "function",
        "method_definition": "method",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "variable_declarator": "variable",
    }
    raw, lines, symbols = text.encode("utf-8"), text.splitlines(), []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        kind = kinds.get(node.type)
        name = node.child_by_field_name("name")
        if kind and name:
            symbols.append(
                {
                    "name": raw[name.start_byte : name.end_byte].decode(),
                    "kind": kind,
                    "start_line": node.start_point.row + 1,
                    "end_line": node.end_point.row + 1,
                    "signature": lines[node.start_point.row].strip()[:500],
                }
            )
        stack.extend(reversed(node.named_children))
    return symbols


def extract_relationships(text, language, path=""):
    tree = parse(text, language, path)
    if tree is None:
        return []
    raw, results = text.encode(), []
    stack = [(tree.root_node, "<module>")]
    while stack:
        node, caller = stack.pop()
        if node.type in {"function_definition", "function_declaration", "method_definition"}:
            name = node.child_by_field_name("name")
            if name:
                caller = raw[name.start_byte : name.end_byte].decode()
        kind = None
        target = node
        if node.type in {"import_statement", "import_from_statement"}:
            kind = "import"
        elif node.type in {"call", "call_expression"}:
            kind = "call_candidate"
            target = node.child_by_field_name("function") or node
        if kind:
            results.append(
                {
                    "kind": kind,
                    "source": caller,
                    "target": raw[target.start_byte : target.end_byte].decode()[:500],
                    "line": node.start_point.row + 1,
                }
            )
        stack.extend((child, caller) for child in reversed(node.named_children))
    return results
