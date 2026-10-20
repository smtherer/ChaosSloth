import pytest
from chaossloth.telemetry.collector import TelemetryCollector
from chaossloth.telemetry.schema import ExecutionRecord
from chaossloth.bayesian.oracle import BayesianSchedulingOracle
from chaossloth.interceptor.scheduler import DelaySchedule
from chaossloth.interceptor.vector_clock import VectorClockEngine
from chaossloth.interceptor.lock_graph import LockOrderGraph

def test_vector_clock_happens_before():
    vclock = VectorClockEngine()
    collision_1 = vclock.record_access("task_alpha", "shared_state", "WRITE")
    assert not collision_1
    collision_2 = vclock.record_access("task_beta", "shared_state", "WRITE")
    assert collision_2, "Vector Clock failed to detect concurrent unsynchronized write!"

def test_coffman_lock_graph_cycle_detection():
    graph = LockOrderGraph()
    graph.record_acquire_attempt("coro_1", "LOCK_A")
    graph.record_acquire_success("coro_1", "LOCK_A")
    graph.record_acquire_attempt("coro_1", "LOCK_B")
    graph.record_acquire_success("coro_1", "LOCK_B")

    graph.record_acquire_attempt("coro_2", "LOCK_B")
    graph.record_acquire_success("coro_2", "LOCK_B")
    cycle = graph.record_acquire_attempt("coro_2", "LOCK_A")
    assert cycle is not None, "Lock graph failed to detect circular wait deadlock condition!"

def test_bayesian_oracle_inversion():
    collector = TelemetryCollector()
    collector.record(ExecutionRecord(
        run_id=1, task_count=2, task_a_yield_us=1200.0, task_b_yield_us=80.0,
        queue_latency_us=150.0, context_switches=2, shared_mutations=1, is_race_condition=1
    ))
    collector.record(ExecutionRecord(
        run_id=2, task_count=2, task_a_yield_us=100.0, task_b_yield_us=200.0,
        queue_latency_us=120.0, context_switches=2, shared_mutations=2, is_race_condition=0
    ))

    oracle = BayesianSchedulingOracle()
    schedule, confidence = oracle.fit_and_invert_boundary(collector.to_dataframe())
    assert isinstance(schedule, DelaySchedule)
    assert schedule.task_a_delay_s > 0
