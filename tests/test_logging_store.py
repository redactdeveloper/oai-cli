from pathlib import Path

from openai_py_cli.logging_store import LoggingStore


def test_log_insert_list_show_delete(tmp_path: Path) -> None:
    store = LoggingStore(tmp_path / "logs.sqlite")
    row = store.insert(
        command="ask",
        model="gpt-4.1-mini",
        input_text="hello",
        output_text="world",
        status="success",
    )
    assert store.list()[0].id == row.id
    assert store.show(row.id) is not None
    assert store.delete(row.id)
    assert store.show(row.id) is None
