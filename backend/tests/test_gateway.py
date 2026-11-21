import json

import httpx
import pytest
from app.ai.gateway import ProviderError, advise, generate, persist_provider, public_provider, route
from app.domain import ProviderInput
from app.workspace import providers_for
from cryptography.fernet import Fernet


def test_lm_studio_bonsai_is_available_to_demo(monkeypatch):
    monkeypatch.setenv("LM_STUDIO_MODEL", "prism-ml/bonsai-27b")
    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setenv("MODEL_LOCAL_ORIGINS", "http://127.0.0.1:1234")
    monkeypatch.setenv("OPENAI_MODEL", "test-cloud")
    monkeypatch.setenv("DEMO_LOCAL_PROVIDER", "openai")
    assert providers_for(None, "test", demo=True) == []

    monkeypatch.setenv("DEMO_LOCAL_PROVIDER", "lm-studio")
    (provider,) = providers_for(None, "test", demo=True)

    def respond(request):
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "prism-ml/bonsai-27b"
        assert body["reasoning_effort"] == "none"
        spec = body["response_format"]
        assert spec["type"] == "json_schema"
        assert spec["json_schema"]["schema"]["properties"]["preference"]["enum"] == ["", "reroute"]
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary":"Use diversion","evidence":"Score 82",'
                            '"confidence":0.8,"preference":"reroute"}',
                            "reasoning_content": "Ignored",
                        }
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 20},
            },
        )

    monkeypatch.setattr(
        "app.ai.gateway.generate",
        lambda *args, **kwargs: generate(*args, **kwargs, transport=httpx.MockTransport(respond)),
    )
    advisory, metadata = advise(
        [provider],
        {"instruction": "Test"},
        "Test",
        False,
        None,
        lambda *args, **kwargs: None,
        allowed_preferences={"reroute"},
    )
    assert advisory["preference"] == "reroute"
    assert metadata["usage"] == {"prompt_tokens": 12, "completion_tokens": 20}


def local_config(monkeypatch):
    monkeypatch.setenv("MODEL_LOCAL_ORIGINS", "http://127.0.0.1:11434")
    monkeypatch.setenv("PROVIDER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    return persist_provider(
        ProviderInput(id="local", name="Local model", kind="ollama", model="test", secret="test-key", local=True)
    )


def test_provider_adapters_and_credential_redaction(monkeypatch):
    config = local_config(monkeypatch)
    assert config["credential"] != "test-key"
    assert "credential" not in public_provider(config)

    def respond(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert json.loads(request.content)["model"] == "test"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "OK"}}], "usage": {"total_tokens": 13}}
        )

    reply = generate(config, "Test", "Hello", transport=httpx.MockTransport(respond))
    assert reply.text == "OK" and reply.metadata["usage"] == {"total_tokens": 13}
    assert reply.metadata["execution"] == "Local"


def test_custom_transport_and_ssrf_policy(monkeypatch):
    config = local_config(monkeypatch)
    custom = {**config, "kind": "custom", "url": "http://127.0.0.1:11434/custom"}
    reply = generate(
        custom,
        "Use JSON",
        "Check",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"text": "ok"})),
    )
    assert reply.text == "ok"
    with pytest.raises(ProviderError):
        persist_provider(
            ProviderInput(
                id="unsafe",
                name="Test",
                kind="custom",
                model="test",
                local=True,
                url="http://169.254.169.254/latest",
            )
        )


def test_model_fallback_and_privacy(monkeypatch):
    config = local_config(monkeypatch)
    cloud = {**config, "id": "cloud", "local": False, "default": True}
    backup = {**config, "id": "backup"}
    assert [p["id"] for p in route([cloud, backup, config], {"preferred": "local"}, False)] == ["local", "backup"]
    attempts = []

    def fake(provider, *_args):
        from app.ai.gateway import ModelReply

        if provider["id"] == "local":
            raise ProviderError("Unavailable")
        return ModelReply(
            '{"summary":"Verified","evidence":"Scores","preference":"baseline","confidence":0.7}',
            {"provider": provider["id"]},
        )

    monkeypatch.setattr("app.ai.gateway.generate", fake)
    result, meta = advise(
        [cloud, backup, config],
        {"preferred": "local", "instruction": "Test"},
        "{}",
        False,
        None,
        lambda stage, *_args, **kw: attempts.append((stage, kw["provider"])),
    )
    assert result["confidence"] == 0.7 and meta["provider"] == "backup"
    assert attempts == [("provider", "local"), ("fallback", "local"), ("provider", "backup")]


def test_routing_enforces_cost_and_language_and_matches_reasoning(monkeypatch):
    config = local_config(monkeypatch)
    standard = {**config, "languages": ["en", "fr"], "reasoning_tier": "standard", "default": True}
    advanced = {
        **config,
        "id": "advanced",
        "languages": ["fr"],
        "reasoning_tier": "advanced",
        "cost_per_million": 2,
    }
    costly = {**advanced, "id": "costly", "cost_per_million": 10}
    other = {**advanced, "id": "other", "languages": ["en"]}
    cloud = {**advanced, "id": "cloud", "local": False, "cost_per_million": 1}
    options = [standard, advanced, costly, other, cloud]
    rules = {"max_cost_per_million": 3, "require_language_match": True, "prefer_low_cost": True}
    assert [
        item["id"]
        for item in route(
            options,
            {},
            False,
            preferred="costly",
            routing=rules,
            language="fr",
            complexity="advanced",
        )
    ] == ["advanced", "local"]
    assert route(options, {}, True, routing=rules, language="fr", complexity="advanced")[0]["id"] == "cloud"
    assert route(options, {}, False, routing=rules, language="fr")[0]["id"] == "local"
    assert route(options, {}, True, routing=rules, language="bm") == []


@pytest.mark.parametrize(
    ("kind", "path", "host", "payload"),
    [
        (
            "azure",
            "/openai/deployments/test/chat/completions",
            "demo.openai.azure.com",
            {"choices": [{"message": {"content": "azure response"}}]},
        ),
        (
            "anthropic",
            "/v1/messages",
            "api.anthropic.com",
            {"content": [{"type": "text", "text": "anthropic response"}]},
        ),
        (
            "gemini",
            "/v1beta/openai/chat/completions",
            "generativelanguage.googleapis.com",
            {"choices": [{"message": {"content": "gemini response"}}]},
        ),
    ],
)
def test_cloud_provider_contracts(monkeypatch, kind, path, host, payload):
    import socket

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    monkeypatch.setenv("PROVIDER_ENCRYPTION_KEY", Fernet.generate_key().decode())
    config = persist_provider(
        ProviderInput(
            id=kind,
            kind=kind,
            name=kind,
            model="test",
            secret="test-key",
            url="https://demo.openai.azure.com" if kind == "azure" else "",
        )
    )

    def respond(request):
        assert request.url.host == host
        assert request.url.path == path
        if kind == "azure":
            assert request.headers["api-key"] == "test-key"
            assert request.url.params["api-version"] == "2024-10-21"
        if kind == "anthropic":
            assert request.headers["x-api-key"] == "test-key"
            assert json.loads(request.content)["system"] == "System test"
        return httpx.Response(200, json=payload)

    assert (
        generate(config, "System test", "Hello", transport=httpx.MockTransport(respond)).text == kind + " response"
    )
