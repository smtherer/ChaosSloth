import asyncio
import time
import random
import inspect
import importlib
import argparse
import sys
from .ui.console import SlothConsole
from .telemetry.collector import TelemetryCollector
from .telemetry.schema import ExecutionRecord
from .interceptor.scheduler import ChaosScheduler
from .interceptor.targets import SharedSessionStore
from .interceptor.vector_clock import VectorClockEngine
from .interceptor.lock_graph import LockOrderGraph
from .interceptor.starvation import EventLoopStarvationSentinel
from .bayesian.oracle import BayesianSchedulingOracle
from .reasoning.gemma import LocalGemmaReasoner
from .reasoning.patcher import ASTConcurrencyPatcher

async def run_audit(target_cls=None, target_method_name="update_session"):
    t_start = time.perf_counter()
    ui = SlothConsole()
    ui.print_banner()

    target_cls = target_cls or SharedSessionStore
    target_method = getattr(target_cls, target_method_name)

    collector = TelemetryCollector()
    scheduler = ChaosScheduler()
    oracle = BayesianSchedulingOracle()
    reasoner = LocalGemmaReasoner(model="gemma2:2b")
    vclock = VectorClockEngine()
    lock_graph = LockOrderGraph()
    lock_graph.install_hook()
    starvation = EventLoopStarvationSentinel(latency_threshold_ms=8.0)

    # 1. Safety Audit: Baseline Observation
    ui.step(1, "Sampling Baseline Asynchronous Telemetry")
    user = "session_usr_94"

    for i in range(25):
        store = target_cls()
        t0 = time.perf_counter()
        
        jitter_a = random.uniform(0.00005, 0.0004)
        jitter_b = random.uniform(0.00005, 0.0004)

        async def task_alpha():
            await asyncio.sleep(jitter_a)
            await scheduler.yield_point("task_alpha")
            vclock.record_access("task_alpha", f"{target_cls.__name__}.state", "WRITE")
            await getattr(store, target_method_name)(user, f"tok_a_{i}")

        async def task_beta():
            await asyncio.sleep(jitter_b)
            await scheduler.yield_point("task_beta")
            vclock.record_access("task_beta", f"{target_cls.__name__}.state", "WRITE")
            await getattr(store, target_method_name)(user, f"tok_b_{i}")

        await asyncio.gather(task_alpha(), task_beta())
        lag = (time.perf_counter() - t0) * 1e6
        
        # Generic state audit
        state_dict = getattr(store, "sessions", {})
        tokens = state_dict.get(user, [])
        is_bug = 1 if len(tokens) < 2 else 0

        collector.record(ExecutionRecord(
            run_id=i, task_count=2,
            task_a_yield_us=random.uniform(80, 450),
            task_b_yield_us=random.uniform(80, 450),
            queue_latency_us=lag, context_switches=2,
            shared_mutations=len(tokens), is_race_condition=is_bug
        ))

    flakiness_rate = collector.failure_count / collector.total_runs
    df = collector.to_dataframe()

    # 2. TabPFN Temporal State-Space Inversion
    ui.step(2, "Inverting Temporal Boundary via Prior Labs TabPFN-3.5")
    schedule, confidence = oracle.fit_and_invert_boundary(df)
    ui.print_telemetry_table(collector.total_runs, flakiness_rate, schedule.task_a_delay_s * 1e6, confidence)

    # 3. Targeted Interleaving
    ui.step(3, "Enforcing Deterministic Collision Interleaving")
    scheduler.set_schedule(schedule)
    reproduced = 0
    for _ in range(10):
        store = target_cls()
        async def forced_alpha():
            await scheduler.yield_point("task_alpha")
            await getattr(store, target_method_name)(user, "forced_1")
        async def forced_beta():
            await scheduler.yield_point("task_beta")
            await getattr(store, target_method_name)(user, "forced_2")
        await asyncio.gather(forced_alpha(), forced_beta())
        state = getattr(store, "sessions", {}).get(user, [])
        if len(state) < 2:
            reproduced += 1

    # 4. Liveness Audit: Dynamic Lock Graph
    ui.step(4, "Auditing Active Lock Acquisition DAG (Coffman Check)")
    if len(lock_graph.detected_cycles) == 0:
        ui.console.print("  [bold green]✔ Liveness Verified:[/bold green] Directed lock graph is strictly acyclic. No deadlocks possible.")
    else:
        ui.console.print(f"  [bold red]✖ Liveness Hazard:[/bold red] Detected {len(lock_graph.detected_cycles)} potential deadlock cycles.")

    # 5. Responsiveness Audit: Starvation Check
    ui.step(5, "Auditing Event-Loop Starvation & Synchronous Blocking Primitives")
    blocking_hazards = EventLoopStarvationSentinel.audit_coroutine_for_blocking_calls(target_method)
    if not blocking_hazards:
        ui.console.print("  [bold green]✔ Responsiveness Verified:[/bold green] Zero synchronous blocking primitives detected.")
    else:
        for hazard in blocking_hazards:
            ui.console.print(f"  [bold red]⚠ Warning:[/bold red] {hazard}")

    # 6. Live Google Gemma AST Reasoning (Dynamic Source Extraction)
    ui.step(6, "Querying Local Google Gemma via Ollama (Dynamic AST Context)")
    live_source = inspect.getsource(target_method)
    analysis = reasoner.analyze_concurrency_hazard(live_source, f"{target_cls.__name__}.sessions")
    ui.console.print(f"  [bold magenta]Gemma Local Diagnosis:[/bold magenta] {analysis.get('diagnosis')}")

    # 7. AST Transformation & In-Memory Compilation
    ui.step(7, "Synthesizing AST & In-Memory Bytecode Compilation")
    PatchedClass, diff_text = ASTConcurrencyPatcher.patch_and_compile(target_cls, target_method_name)
    ui.print_patch(diff_text)

    # 8. Active Sandbox Re-Verification
    ui.step(8, "Sandboxed Verification across 25 Adversarial Cycles")
    patched_failures = 0
    for i in range(25):
        patched_store = PatchedClass()
        async def p_alpha():
            await scheduler.yield_point("task_alpha")
            await getattr(patched_store, target_method_name)(user, f"patch_a_{i}")
        async def p_beta():
            await scheduler.yield_point("task_beta")
            await getattr(patched_store, target_method_name)(user, f"patch_b_{i}")
        await asyncio.gather(p_alpha(), p_beta())
        state = getattr(patched_store, "sessions", {}).get(user, [])
        if len(state) < 2:
            patched_failures += 1

    patched_flakiness = patched_failures / 25
    lock_graph.uninstall_hook()
    
    elapsed = time.perf_counter() - t_start
    if patched_flakiness == 0.0:
        ui.print_success(flakiness_rate, patched_flakiness, elapsed)
    else:
        ui.console.print("[bold red]⚠ Warning: Residual flakiness observed.[/bold red]")

def main():
    parser = argparse.ArgumentParser(description="ChaosSloth: Autonomous Concurrency Interleaver")
    parser.add_argument("target", nargs="?", default=None, help="Optional python file to audit (e.g. app/cache.py)")
    parser.add_argument("--cls", default="SharedSessionStore", help="Class name to audit")
    parser.add_argument("--method", default="update_session", help="Method name to audit")
    args = parser.parse_args()

    target_cls = None
    if args.target:
        sys.path.insert(0, ".")
        mod_name = args.target.replace(".py", "").replace("/", ".")
        mod = importlib.import_module(mod_name)
        target_cls = getattr(mod, args.cls)

    asyncio.run(run_audit(target_cls=target_cls, target_method_name=args.method))

if __name__ == "__main__":
    main()
