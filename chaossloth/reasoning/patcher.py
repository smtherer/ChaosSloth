import ast
import difflib
import inspect
import asyncio
import random
from typing import Tuple, Type, Any

class AmdahlOptimalLockTransformer(ast.NodeTransformer):
    """
    Theoretical Ceiling AST Transformer:
    1. Injects `self._lock = asyncio.Lock()` inside `__init__`.
    2. Leaves asynchronous delays and non-shared operations OUTSIDE the lock.
    3. Atomically encapsulates the entire Read-Modify-Write cycle on `self.sessions`
       inside `async with self._lock:`, preventing stale reads.
    """
    def __init__(self, target_method: str):
        self.target_method = target_method

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == "__init__":
            lock_assign = ast.Assign(
                targets=[ast.Attribute(
                    value=ast.Name(id='self', ctx=ast.Load()),
                    attr='_lock',
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
        if node.name == self.target_method:
            pre_lock_stmts = []
            critical_stmts = []

            for stmt in node.body:
                # Delays and external yields stay outside the lock
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Await):
                    pre_lock_stmts.append(stmt)
                elif isinstance(stmt, ast.If):
                    # Branches containing yields stay outside
                    pre_lock_stmts.append(stmt)
                else:
                    # All state reads, mutations, and assignments belong in the critical section
                    critical_stmts.append(stmt)

            with_block = ast.AsyncWith(
                items=[ast.withitem(
                    context_expr=ast.Attribute(
                        value=ast.Name(id='self', ctx=ast.Load()),
                        attr='_lock',
                        ctx=ast.Load()
                    ),
                    optional_vars=None
                )],
                body=critical_stmts
            )

            node.body = pre_lock_stmts + [with_block]
            ast.fix_missing_locations(node)
        return node

class ASTConcurrencyPatcher:
    @staticmethod
    def patch_and_compile(target_cls: Type, method_name: str) -> Tuple[Type, str]:
        source = inspect.getsource(target_cls)
        tree = ast.parse(source)

        transformer = AmdahlOptimalLockTransformer(method_name)
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
        exec_globals.update({"asyncio": asyncio, "random": random, "Any": Any})

        compiled_code = compile(modified_tree, filename="<chaossloth_optimal>", mode="exec")
        namespace = {}
        exec(compiled_code, exec_globals, namespace)

        return namespace[target_cls.__name__], diff_text
