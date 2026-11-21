# Model gateway

All model inference flows through the provider gateway. The simulation requests structured advisories with evidence and confidence. The gateway validates the output, records the model, execution locality, and latency, and tries bounded fallbacks when a provider fails.

**Research → Model lab** exposes image analysis, text streaming, embeddings, and a read-only city data tool. The workspace chooses providers by capability and privacy policy. Model outputs never change scores calculated by the simulator. The deterministic demo can exercise each workflow without a model server, and the output identifies its execution mode.

Docker uses Bonsai 27B for supported chat operations and the local Nomic model for embeddings. Capability-specific cloud adapters are usable when the administrator configures privacy consent and credentials. [LM Studio OpenAI-compatible endpoints](https://lmstudio.ai/docs/developer/openai-compat)

