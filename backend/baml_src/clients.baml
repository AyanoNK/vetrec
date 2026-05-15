client<llm> GLM51 {
  provider openai-generic
  options {
    base_url env.LLM_BASE_URL
    api_key env.FIREWORKS_API_KEY
    model env.LLM_MODEL
    temperature 0.0
  }
}

retry_policy ProviderRetry {
  max_retries 2
  strategy {
    type exponential_backoff
    delay_ms 500
    multiplier 2
  }
}
