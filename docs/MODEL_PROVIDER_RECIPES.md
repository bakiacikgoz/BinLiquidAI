# Model Provider Recipes

## DeepSeek OpenAI-Compatible

Use the OpenAI-compatible adapter shape with the DeepSeek public endpoint disabled by default.

```toml
[providers.deepseek-public]
kind = "deepseek"
enabled = false
base_url = "https://api.deepseek.com/v1"
api_key_env = "DEEPSEEK_API_KEY"
auth_mode = "bearer_env"
default_model = "deepseek-v4-flash"
models = ["deepseek-v4-flash", "deepseek-v4-pro"]
```

Recommended model names:

- `deepseek-v4-flash`
- `deepseek-v4-pro`

Older DeepSeek model names are compatibility aliases only and should be treated as deprecated in new examples.

## Gemini OpenAI-Compatible Preview

Gemini OpenAI-compatible config is included only as a disabled fixture for conformance and operator trust display. Native Gemini adapter work is out of scope for V1.1.

```toml
[providers.gemini-openai-compatible]
kind = "openai_compatible"
enabled = false
base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
api_key_env = "GEMINI_API_KEY"
auth_mode = "bearer_env"
default_model = "gemini-2.5-flash"
models = ["gemini-2.5-flash"]
```
