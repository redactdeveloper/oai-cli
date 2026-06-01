from openai_py_cli.commands.compare import _run_model


class _Response:
    output_text = "hello"


class _Responses:
    def create(self, **kwargs: object) -> _Response:
        assert kwargs["model"] == "gpt-4.1-mini"
        return _Response()


class _Client:
    responses = _Responses()


def test_run_model_success_with_mock_client() -> None:
    result = _run_model(_Client(), {"model": "gpt-4.1-mini", "input": "say hello"})
    assert result.status == "success"
    assert result.output_text == "hello"
    assert result.total_tokens is not None


class _FailingResponses:
    def create(self, **kwargs: object) -> _Response:
        raise RuntimeError("boom")


class _FailingClient:
    responses = _FailingResponses()


def test_run_model_error_with_mock_client() -> None:
    result = _run_model(_FailingClient(), {"model": "unknown", "input": "say hello"})
    assert result.status == "error"
    assert result.error == "boom"
