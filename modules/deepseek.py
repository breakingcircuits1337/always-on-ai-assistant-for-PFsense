from openai import OpenAI, AzureOpenAI
import os
import json
from dotenv import load_dotenv
from typing import List, Dict
import google.generativeai as genai
# You might need to import a specific client for Mistral if not using the OpenAI compatible API
# from mistralai.client import MistralClient

# Load environment variables
load_dotenv()

# This function will get the appropriate client based on the model name
def get_llm_client(model_name: str):
    if "deepseek" in model_name:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise Exception("DEEPSEEK_API_KEY not found in environment variables")
        return OpenAI(
            api_key=api_key, base_url="https://api.deepseek.com/beta"
        )
    elif "azure" in model_name:
        api_key = os.getenv("AZURE_API_KEY")
        azure_endpoint = os.getenv("AZURE_ENDPOINT")
        if not api_key or not azure_endpoint:
             raise Exception("AZURE_API_KEY or AZURE_ENDPOINT not found in environment variables")
        return AzureOpenAI(
                api_key = api_key,
                api_version = os.getenv("AZURE_API_VERSION"), # Ensure AZURE_API_VERSION is also in .env
                azure_endpoint = azure_endpoint,
        )
    elif "gemini" in model_name:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise Exception("GEMINI_API_KEY not found in environment variables")
        # Configure genai globally if not already, though ideally this would be part of client getting if possible
        genai.configure(api_key=api_key)
        return genai
    elif "mistral" in model_name:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise Exception("MISTRAL_API_KEY not found in environment variables")
        # Assuming Mistral might use an OpenAI compatible API for chat completions
        # If not, you'll need to use the specific Mistral client library
        return OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1") # Example base_url for Mistral
    # Add other models here as needed
    else:
        raise Exception(f"Unsupported model specified: {model_name}")

# Remove global client initialization
# client = get_openai_client()

# Remove global gemini initialization
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# gemini_model = genai.GenerativeModel('gemini-pro')


DEFAULT_MODEL = "deepseek-chat" # Consider making this configurable


def get_deepseek_response(prompt: str, model: str = "deepseek-chat") -> str:
    """
    Send a prompt to a Deepseek model and get response.
    """
    try:
        client = get_llm_client(model)
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error in Deepseek prompt: {str(e)}")

# Note: Other deepseek specific functions (fill_in_the_middle_prompt, json_prompt, prefix_prompt, prefix_then_stop_prompt, conversational_prompt)
# will need to be reviewed and potentially refactored if they are intended to work with other models, as their API calls are specific to OpenAI/Deepseek.
# For now, I will leave them as they are, assuming they are only used with Deepseek models.

def get_gemini_response(prompt: str, model: str = "gemini-pro") -> str:
    """
    Send a prompt to Google Gemini and get response.
    """
    try:
        # For Gemini, we get the genai module and then the model
        genai_module = get_llm_client(model)
        gemini_model_instance = genai_module.GenerativeModel(model)
        response = gemini_model_instance.generate_content(prompt)
        if response.candidates:
            return response.candidates[0].content.parts[0].text
        else:
            return ""
    except Exception as e:
        raise Exception(f"Error in Gemini prompt: {str(e)}")

def get_mistral_response(prompt: str, model: str = "mistral-tiny") -> str:
    """
    Send a prompt to Mistral and get response.
    """
    try:
        client = get_llm_client(model)
        # Assuming Mistral uses a similar chat completions API to OpenAI
        # If not, replace with the correct Mistral API call
        response = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error in Mistral prompt: {str(e)}")

def prompt(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Wrapper function to get the right response based on the model.
    """
    if "deepseek" in model:
        return get_deepseek_response(prompt=prompt, model=model)
    elif "gemini" in model:
        return get_gemini_response(prompt=prompt, model=model)
    elif "mistral" in model:
        return get_mistral_response(prompt=prompt, model=model)
    # Add other models here
    else:
        raise Exception(f"Unsupported model in prompt function: {model}")
