"""Thin Azure OpenAI client wrapper shared by the router and message generator."""

from functools import lru_cache

from openai import AzureOpenAI

from app.config import get_settings


@lru_cache
def get_azure_client() -> AzureOpenAI:
    settings = get_settings()
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )


def chat_completion(messages: list[dict], temperature: float = 0.3, response_format: dict | None = None) -> str:
    settings = get_settings()
    client = get_azure_client()
    kwargs = {}
    if response_format:
        kwargs["response_format"] = response_format
    completion = client.chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=messages,
        temperature=temperature,
        **kwargs,
    )
    return completion.choices[0].message.content or ""
