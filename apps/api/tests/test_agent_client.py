from unittest.mock import MagicMock, Mock

import sentry_sdk
from agent.client import OllamaClient


def test_client_accepts_render_private_hostport():
    ollama = OllamaClient(host="reposeance-ollama:11434")

    assert ollama.host == "http://reposeance-ollama:11434"


def _context_manager(value):
    manager = MagicMock()
    manager.__enter__.return_value = value
    return manager


def test_generate_records_model_latency_and_ollama_token_counts(monkeypatch):
    ollama = OllamaClient(model="gemma2:2b")
    span = Mock()
    monkeypatch.setattr(
        sentry_sdk,
        "start_span",
        Mock(return_value=_context_manager(span)),
    )
    monkeypatch.setattr(
        ollama,
        "_post",
        Mock(
            return_value={
                "response": "grounded answer",
                "prompt_eval_count": 24,
                "eval_count": 8,
                "total_duration": 1_500_000_000,
            }
        ),
    )

    assert ollama.generate("private prompt") == "grounded answer"
    span.set_data.assert_any_call("model", "gemma2:2b")
    span.set_data.assert_any_call("prompt_tokens", 24)
    span.set_data.assert_any_call("completion_tokens", 8)
    span.set_data.assert_any_call("ollama_total_duration_ms", 1500.0)
    assert any(call.args[:1] == ("latency_ms",) for call in span.set_data.call_args_list)
    span.set_data.assert_any_call("success", True)


def test_generate_captures_sanitized_failure_context(monkeypatch):
    ollama = OllamaClient(model="gemma2:2b")
    span = Mock()
    scope = Mock()
    capture_exception = Mock()
    monkeypatch.setattr(
        sentry_sdk,
        "start_span",
        Mock(return_value=_context_manager(span)),
    )
    monkeypatch.setattr(
        sentry_sdk,
        "push_scope",
        Mock(return_value=_context_manager(scope)),
    )
    monkeypatch.setattr(sentry_sdk, "capture_exception", capture_exception)
    monkeypatch.setattr(
        ollama,
        "_post",
        Mock(return_value={"_error": "private transport detail", "_error_type": "URLError"}),
    )

    result = ollama.generate("private prompt must not be captured")

    assert result.startswith("[error]")
    captured = capture_exception.call_args.args[0]
    assert str(captured) == "Ollama generate request failed (URLError)"
    assert "private prompt" not in str(captured)
    scope.set_tag.assert_any_call("ai.model", "gemma2:2b")
    scope.set_tag.assert_any_call("ai.failure_type", "URLError")
    scope.set_context.assert_called_once()
    span.set_data.assert_any_call("success", False)
