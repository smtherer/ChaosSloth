import ast
import difflib
import inspect
import asyncio
import random
from typing import Tuple, Type, Any, Optional, Dict, List, Set

class MultiAttributeHazardScanner(ast.NodeVisitor):
    """
    Mazurkiewicz Dataflow Scanner:
    Scans method AST statements to detect all independent attributes on `self`
    that exhibit a Read-Modify-Write cycle spanning at least one `await` yield point.
    """
    def __init__(self):
        self.statement_profiles: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Scan inner functions separately
        pass

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        for stmt in node.body:
            reads: Set[str] = set()
            writes: Set[str] = set()
            awaits: List[ast.Await] = []

            for sub in ast.walk(stmt):
                # Detect reads on self.<attr>
                if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                    if isinstance(sub.ctx, ast.Load):
                        reads.add(sub.attr)
                    elif isinstance(sub.ctx, (ast.Store, ast.Del)):
                        writes.add(sub.attr)

                # Detect container mutations: self.<attr>[key] = val
                elif isinstance(sub, ast.Subscript) and isinstance(sub.ctx, (ast.Store, ast.Del)):
                    val = sub.value
                    if isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name) and val.value.id == "self":
                        writes.add(val.attr)

                # Detect in-place mutating method calls: self.<attr>.append(), .pop(), .update()
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    val = sub.func.value
                    if isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name) and val.value.id == "self":
                        if sub.func.attr in ("append", "extend", "update", "pop", "clear", "add", "insert", "remove"):
                            writes.add(val.attr)

                elif isinstance(sub, ast.Await):
                    awaits.append(sub)

            self.statement_profiles.append({
                "stmt": stmt,
                "reads": reads,
                "writes": writes,
                "has_await": len(awaits) > 0
            })

class DijkstraOrderedDisjointTransformer(ast.NodeTransformer):
    """
    Dijkstra-Ordered Disjoint Lock Synthesizer:
    1. Identifies all attributes with valid [read ... await ... write] hazard intervals.
    2. Sorts locks in strict lexicographical order to prevent Coffman deadlocks by construction.
    3. Wraps the minimal convex dataflow hull without hoisting or altering statement order.
    """
    def __init__(self, target_method: str, explicit_attr: Optional[str] = None):
        self.target_method = target_method
        self.explicit_attr = explicit_attr
        self.active_locks: List[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == "__init__":
            # Ensure initialization of all active locks
            for lock_attr in self.active_locks:
                has_init = any(
                    isinstance(stmt, ast.Assign) and
                    any(isinstance(t, ast.Attribute) and t.attr == lock_attr for t in stmt.targets)
                    for stmt in node.body
                )
                if not has_init:
                    lock_assign = ast.Assign(
                        targets=[ast.Attribute(
                            value=ast.Name(id='self', ctx=ast.Load()),
                            attr=lock_attr,
                            ctx=ast.Store()
                        )],
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='asyncio', ctx=ast.Load()),
                                attr='Lock',
                                ctx=ast.Load()
                            ),
                            args=[],
                            keywords=[]
                        )
                    )
                    node.body.append(lock_assign)
            ast.fix_missing_locations(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if node.name != self.target_method:
            return node

        # Step 1: Scan all statements for hazard intervals
        scanner = MultiAttributeHazardScanner()
        scanner.visit_AsyncFunctionDef(node)
        profiles = scanner.statement_profiles

        # Find all candidate attributes
        all_attrs = set()
        for p in profiles:
            all_attrs.update(p["reads"])
            all_attrs.update(p["writes"])

        if self.explicit_attr:
            all_attrs = {self.explicit_attr}

        # Step 2: Determine valid hazard intervals [first_read, last_write] across await
        hazards: Dict[str, Tuple[int, int]] = {}
        for attr in sorted(all_attrs):  # Enforce Dijkstra lexicographical total order
            first_r = None
            last_w = None
            for idx, p in enumerate(profiles):
                if attr in p["reads"] and first_r is None:
                    first_r = idx
                if attr in p["writes"]:
                    last_w = idx

            if first_r is not None and last_w is not None and first_r <= last_w:
                has_yield = any(profiles[i]["has_await"] for i in range(first_r, last_w + 1))
                if has_yield:
                    hazards[attr] = (first_r, last_w)

        if not hazards:
            return node

        # Step 3: Compute convex hull across all conflicting attributes
        global_start = min(h[0] for h in hazards.values())
        global_end = max(h[1] for h in hazards.values())

        # Register active locks (ordered alphabetically for deadlock prevention)
        self.active_locks = [f"_lock_{attr}" for attr in sorted(hazards.keys())]

        pre_stmts = [p["stmt"] for p in profiles[:global_start]]
        critical_stmts = [p["stmt"] for p in profiles[global_start:global_end + 1]]
        post_stmts = [p["stmt"] for p in profiles[global_end + 1:]]

        # Build nested or multi-item AsyncWith block adhering to Dijkstra rank
        with_items = [
            ast.withitem(
                context_expr=ast.Attribute(
                    value=ast.Name(id='self', ctx=ast.Load()),
                    attr=lock_name,
                    ctx=ast.Load()
                ),
                optional_vars=None
            )
            for lock_name in self.active_locks
        ]

        # Self-healing runtime lock initialization guards
        guards = []
        for lock_name in self.active_locks:
            guard = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.Call(
                        func=ast.Name(id='hasattr', ctx=ast.Load()),
                        args=[
                            ast.Name(id='self', ctx=ast.Load()),
                            ast.Constant(value=lock_name)
                        ],
                        keywords=[]
                    )
                ),
                body=[
                    ast.Assign(
                        targets=[ast.Attribute(
                            value=ast.Name(id='self', ctx=ast.Load()),
                            attr=lock_name,
                            ctx=ast.Store()
                        )],
                        value=ast.Call(
                            func=ast.Attribute(
                                value=ast.Name(id='asyncio', ctx=ast.Load()),
                                attr='Lock',
                                ctx=ast.Load()
                            ),
                            args=[],
                            keywords=[]
                        )
                    )
                ],
                orelse=[]
            )
            guards.append(guard)

        with_block = ast.AsyncWith(items=with_items, body=critical_stmts)
        node.body = pre_stmts + guards + [with_block] + post_stmts
        ast.fix_missing_locations(node)
        return node

class ASTConcurrencyPatcher:
    @staticmethod
    def patch_and_compile(target_cls: Type, method_name: str, target_attr: Optional[str] = None) -> Tuple[Type, str]:
        source = inspect.getsource(target_cls)
        tree = ast.parse(source)

        transformer = DijkstraOrderedDisjointTransformer(method_name, target_attr)
        modified_tree = transformer.visit(tree)
        ast.fix_missing_locations(modified_tree)

        patched_source = ast.unparse(modified_tree)

        diff_lines = list(difflib.unified_diff(
            source.splitlines(keepends=True),
            patched_source.splitlines(keepends=True),
            fromfile=f"a/{target_cls.__name__}.py",
            tofile=f"b/{target_cls.__name__}.py"
        ))
        diff_text = "".join(diff_lines)

        target_mod = inspect.getmodule(target_cls)
        exec_globals = target_mod.__dict__.copy() if target_mod else {}
        exec_globals.update({"asyncio": asyncio, "random": random, "Any": Any, "hasattr": hasattr})

        compiled_code = compile(modified_tree, filename=f"<{target_cls.__name__}_dijkstra_verified>", mode="exec")
        namespace = {}
        exec(compiled_code, exec_globals, namespace)

        return namespace[target_cls.__name__], diff_text
