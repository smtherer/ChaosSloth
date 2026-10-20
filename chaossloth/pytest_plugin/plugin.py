import pytest

def pytest_addoption(parser):
    group = parser.getgroup("chaossloth", "ChaosSloth Concurrency Auditor")
    group.addoption(
        "--chaossloth",
        action="store_true",
        default=False,
        help="Enable ChaosSloth Bayesian concurrency interleaving auditor."
    )

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "sloth: mark test for ChaosSloth Bayesian concurrency interleaving audit."
    )
