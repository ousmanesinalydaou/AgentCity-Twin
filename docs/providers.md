# Providers

Admins can configure providers in **Settings → Model providers** and test a saved connection. The schema supports a credential, organization, deployment, API version, context window, timeout, priority, and temperature. Set a server-side Fernet key before saving an API credential through the UI. Environment-configured providers are visible as read-only entries.

| Provider | Runtime contract |
|---|---|
| OpenAI, vLLM, llama.cpp, Ollama, compatible gateways | OpenAI-format `POST /chat/completions` relative to the configured API root |
| LM Studio | OpenAI-format `POST /chat/completions` with a JSON schema for advisories |
| Azure OpenAI | Deployment chat endpoint with `api-key` and configured API version |
| Azure AI Foundry / hosted inference | OpenAI-compatible API root and bearer authorization |
| Gemini | Google OpenAI-compatible API root |
| Anthropic | Anthropic `POST /messages` API with a configured or default API version |
| Custom REST | POST to the exact URL with `model`, `system`, `prompt`, `max_tokens`, and `temperature`, returning `{"text":"..." }` |

Docker defaults to the `prism-ml/bonsai-27b` model in LM Studio. Configure the model ID with `LM_STUDIO_MODEL` and the API root with `LM_STUDIO_BASE_URL`. Use `http://host.docker.internal:1234/v1` from Docker Desktop, or `http://127.0.0.1:1234/v1` for a native backend. Include the corresponding origin without the API path in `MODEL_LOCAL_ORIGINS`. The gateway requests concise, schema-constrained Bonsai advisories. If LM Studio requires authentication, set `LM_STUDIO_API_KEY` on the backend. [LM Studio structured output](https://lmstudio.ai/docs/developer/openai-compat/structured-output)

An independently hosted Ollama server remains an optional gateway provider. Configure its model tag and approved endpoint with `OLLAMA_MODEL` and `OLLAMA_BASE_URL`.

For Model Lab operations, custom REST providers receive an `operation` field and the corresponding chat or embedding body. Return `text` for vision, `embedding` for vectors, a chat `message` containing OpenAI-format `tool_calls` for a tool request, or SSE events with a `text` delta and a terminal `done` event for streaming. Enable only the capabilities implemented by the provider.

