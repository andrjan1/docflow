from docflow.core.workflow import toposort_actions, execute_workflow
from docflow.core.context import ExecutionContext


def test_toposort_and_cycle():
    actions = [
        {"id": "a", "deps": []},
        {"id": "b", "deps": ["a"]},
        {"id": "c", "deps": ["b"]},
    ]
    order = toposort_actions(actions)
    assert [x["id"] for x in order] == ["a", "b", "c"]

    # cycle
    actions2 = [{"id": "x", "deps": ["y"]}, {"id": "y", "deps": ["x"]}]
    import pytest

    with pytest.raises(ValueError):
        toposort_actions(actions2)


def test_execute_and_chaining_and_exports():
    ctx = ExecutionContext()
    actions = [
        {"id": "gen1", "type": "generative", "cfg": {}, "deps": [], "exports": []},
        {
            "id": "code1",
            "type": "code",
            "code": "def run(vars):\n    return {'vars': {'from_code': 'ok'}, 'result_text': 'code result'}",
            "deps": ["gen1"],
            "exports": [{"name": "greeting_export", "source": "result_text", "jinja": "{{text}} - done"}],
        },
    ]
    mapping = execute_workflow(actions, ctx)
    assert "gen1" in mapping and "code1" in mapping
    assert ctx.global_vars.get("from_code") == "ok"
    assert ctx.global_vars.get("greeting_export") == "code result - done"
