import os

from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lmstudio").lower()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234")
LLM_NUM_CTX = int(os.getenv("LLM_NUM_CTX", "8192"))

REASONING_MODEL = os.getenv("REASONING_MODEL", "qwen3:latest")
REASONING_TEMPERATURE = float(os.getenv("REASONING_TEMPERATURE", "0.7"))

CODE_MODEL = os.getenv("CODE_MODEL", "qwen3:latest")
CODE_TEMPERATURE = float(os.getenv("CODE_TEMPERATURE", "0.3"))


def create_reasoning_client():
    """Client for PM, Architect, QA agents."""
    if LLM_PROVIDER == "ollama":
        from agent_framework.ollama import OllamaChatClient

        return OllamaChatClient(model=REASONING_MODEL, host=LLM_BASE_URL)
    else:
        from agent_framework.openai import OpenAIChatClient

        return OpenAIChatClient(
            model=REASONING_MODEL,
            base_url=f"{LLM_BASE_URL}/v1/",
            api_key="lm-studio",
        )


def create_code_client():
    """Client for Developer, Reviewer, Code Generator agents."""
    if LLM_PROVIDER == "ollama":
        from agent_framework.ollama import OllamaChatClient

        return OllamaChatClient(model=CODE_MODEL, host=LLM_BASE_URL)
    else:
        from agent_framework.openai import OpenAIChatClient

        return OpenAIChatClient(
            model=CODE_MODEL,
            base_url=f"{LLM_BASE_URL}/v1/",
            api_key="lm-studio",
        )


def get_reasoning_options():
    """Default options for reasoning model agents."""
    if LLM_PROVIDER == "ollama":
        return {"temperature": REASONING_TEMPERATURE, "num_ctx": LLM_NUM_CTX}
    return {"temperature": REASONING_TEMPERATURE}


def get_code_options():
    """Default options for code model agents."""
    if LLM_PROVIDER == "ollama":
        return {"temperature": CODE_TEMPERATURE, "num_ctx": LLM_NUM_CTX}
    return {"temperature": CODE_TEMPERATURE}
