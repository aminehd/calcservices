import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(service):
    path = ROOT / service / "main.py"
    spec = importlib.util.spec_from_file_location(f"{service}_main", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_adder_computes():
    adder = load("adder")
    assert adder.NAME == "adder"
    assert adder.compute(6, 7) == 13
    assert adder.compute(-1, 1) == 0


def test_multiplier_computes():
    multiplier = load("multiplier")
    assert multiplier.NAME == "multiplier"
    assert multiplier.compute(6, 7) == 42
    assert multiplier.compute(5, 0) == 0


def test_coordinator_tally_counts_per_op():
    coordinator = load("coordinator")
    coordinator.tally("add")
    coordinator.tally("add")
    coordinator.tally("mul")
    assert coordinator.state == {"done": 3, "per_op": {"add": 2, "mul": 1}}


def test_coordinator_sends_one_path_and_lets_the_mesh_route(monkeypatch):
    coordinator = load("coordinator")
    seen = {}

    def fake_post(path, body):
        seen["path"] = path
        seen["body"] = body
        return {"service": "adder", "result": 13}

    monkeypatch.setattr(coordinator, "post", fake_post)
    reply = coordinator.calculate({"op": "add", "a": 6, "b": 7})
    assert seen["path"] == "/calc"
    assert seen["body"]["op"] == "add"
    assert reply["result"] == 13
