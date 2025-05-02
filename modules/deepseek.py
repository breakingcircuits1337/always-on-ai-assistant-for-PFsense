from openai import OpenAI, AzureOpenAI
import os
import json
from dotenv import load_dotenv
from typing import List, Dict
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Initialize OpenAI client for Deepseek, or AzureOpenAI for Azure models
def get_openai_client():
    if os.getenv("DEEPSEEK_API_KEY"):
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com/beta"
        )
        return client
    elif os.getenv("AZURE_API_KEY") and os.getenv("AZURE_ENDPOINT"):
        client = AzureOpenAI(
                api_key = os.getenv("AZURE_API_KEY"),
                api_version = os.getenv("AZURE_API_VERSION"),
                azure_endpoint = os.getenv("AZURE_ENDPOINT"),
        )
        return client
    else:
        raise Exception("No Deepseek or Azure API key found")

client = get_openai_client()

# initialize google gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-pro')


# DEEPSEEK_V3_MODEL = "deepseek-chat"
DEFAULT_MODEL = "deepseek-chat"
DEEPSEEK_V3_MODEL = "deepseek-chat"


def get_deepseek_response(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Send a prompt to a Deepseek model and get detailed benchmarking response.
    """
    response = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def fill_in_the_middle_prompt(
    prompt: str, suffix: str, model: str = DEEPSEEK_V3_MODEL
) -> str:
    """
    Send a fill-in-the-middle prompt to DeepSeek and get response.

    The max tokens of FIM completion is 4K.

    example:
        prompt="def fib(a):",
        suffix="    return fib(a-1) + fib(a-2)",
    """
    response = client.completions.create(model=model, prompt=prompt, suffix=suffix)
    return prompt + response.choices[0].text + suffix


def json_prompt(prompt: str, model: str = DEEPSEEK_V3_MODEL) -> dict:
    """
    Send a prompt to DeepSeek and get JSON response.

    Args:
        prompt: The user prompt to send
        system_prompt: Optional system prompt to set context
        model: The model to use, defaults to deepseek-chat

    Returns:
        dict: The parsed JSON response
    """
    messages = [{"role": "user", "content": prompt}]

    response = client.chat.completions.create(
        model=model, messages=messages, response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)


def prefix_prompt(
    prompt: str, prefix: str, model: str = DEEPSEEK_V3_MODEL, no_prefix: bool = False
) -> str:
    """
    Send a prompt to DeepSeek with a prefix constraint and get 'prefix + response'

    Args:
        prompt: The user prompt to send
        prefix: The required prefix for the response
        model: The model to use, defaults to deepseek-chat
        no_prefix: If True, the prefix is not added to the response
    Returns:
        str: The model's response constrained by the prefix
    """
    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": prefix, "prefix": True},
    ]

    response = client.chat.completions.create(model=model, messages=messages)
    if no_prefix:
        return response.choices[0].message.content
    else:
        return prefix + response.choices[0].message.content


def prefix_then_stop_prompt(
    prompt: str, prefix: str, suffix: str, model: str = DEEPSEEK_V3_MODEL
) -> str:
    """
    Send a prompt to DeepSeek with a prefix and suffix constraint and get 'response' only that will have started with prefix and ended with suffix

    Args:
        prompt: The user prompt to send
        prefix: The required prefix for the response
        suffix: The required suffix for the response
        model: The model to use, defaults to deepseek-chat

    Returns:
        str: The model's response constrained by the prefix and suffix
    """
    messages = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": prefix, "prefix": True},
    ]
    response = client.chat.completions.create(
        model=model, messages=messages, stop=[suffix]
    )
    return prefix + response.choices[0].message.content
    # return prefix + response.choices[0].message.content


def conversational_prompt(
    messages: List[Dict[str, str]],
    system_prompt: str = "You are a helpful conversational assistant. Respond in a short, concise, friendly manner.",
    model: str = DEEPSEEK_V3_MODEL,
) -> str:
    """
    Send a conversational prompt to DeepSeek with message history.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: The model to use, defaults to deepseek-chat

    Returns:
        str: The model's response
    """
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]
        response = client.chat.completions.create(
            model=model, messages=messages, stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error in conversational prompt: {str(e)}")

def get_gemini_response(prompt: str) -> str:
    """
    Send a prompt to Google Gemini and get response.
    """
    try:
        response = gemini_model.generate_content(prompt)
        if response.candidates:
            return response.candidates[0].content.parts[0].text
        else:
            return ""

    except Exception as e:
        raise Exception(f"Error in Gemini prompt: {str(e)}")

def get_mistral_response(prompt: str, model: str = "mistral-tiny") -> str:
    """
    Send a prompt to Mistral and get detailed benchmarking response.
    """
    try:
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error in conversational prompt: {str(e)}")

def prompt(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    wrapper function to get the right response
    """
    return get_deepseek_response(prompt=prompt, model=model)
