from typing import List, Dict, Optional
import logging
from playwright.sync_api import sync_playwright
import json
from modules.api_interaction import call_api
from modules.memory import Memory
import os
from modules.deepseek import get_deepseek_response, get_gemini_response, get_mistral_response
from modules.ollama import conversational_prompt as ollama_conversational_prompt
from modules.utils import build_file_name_session
from RealtimeTTS import TextToAudioStream, SystemEngine
from elevenlabs import play
from elevenlabs.client import ElevenLabs
import pyttsx3
from modules.prompts import get_api_json_prompt, get_queue_task_prompt
import time
from modules.execute_python import run_terminal_command
from modules.assistant_config import get_config
from modules.data_types import Task

def browse_web(
    url: str,
    query: Optional[str] = None,
    fill_form: Optional[Dict[str, str]] = None,
    click_element: Optional[str] = None,
    extract_data: Optional[str] = None,
) -> str:

    """
    Launches a browser, navigates to a given URL, searches for a given query, and returns the search results.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            # Assuming there is an input field with a specific name or id
            if query:
                page.fill("input[name='q']", query)
                page.press("input[name='q']", "Enter")

            if fill_form:
                for field, value in fill_form.items():
                    page.fill(f"input[name='{field}']", value)

            if click_element:
                page.click(click_element)

            if extract_data:
                extracted_elements = page.query_selector_all(extract_data)
                data_string = " ".join([element.inner_text() for element in extracted_elements])
                return data_string

            # Wait for search results to load
            page.wait_for_selector("div")  # You might need to adjust this selector


            search_results = page.inner_text("body")  # Grab all text from the results page
            browser.close()
            return search_results

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"An error occurred while browsing: {e}"


class PlainAssistant:
    def __init__(self, logger: logging.Logger, session_id: str):
        self.logger = logger
        self.session_id = session_id
        self.conversation_history = []

        self.memory = Memory()
        self.tasks: List[Task] = []
        # Get voice configuration
        self.voice_type = get_config("base_assistant.voice")
        self.elevenlabs_voice = get_config("base_assistant.elevenlabs_voice")
        self.brain = get_config("base_assistant.brain")

        # Initialize appropriate TTS engine
        if self.voice_type == "local":
            self.logger.info("🔊 Initializing local TTS engine")
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 150)  # Speed of speech
            self.engine.setProperty("volume", 1.0)  # Volume level
        elif self.voice_type == "realtime-tts":
            self.logger.info("🔊 Initializing RealtimeTTS engine")
            self.engine = SystemEngine()
            self.stream = TextToAudioStream(
                self.engine, frames_per_buffer=256, playout_chunk_size=1024
            )
        elif self.voice_type == "elevenlabs":
            self.logger.info("🔊 Initializing ElevenLabs TTS engine")
            self.elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
        else:
            raise ValueError(f"Unsupported voice type: {self.voice_type}")

    def process_text(self, text: str) -> str:
        """Process text input and generate response"""
        if text.lower().startswith("queue task"):
            command = text.split(" ", 1)[1]
            result = run_terminal_command(f"python commands/template_empty.py queue-task {command}")
            self.logger.info(f"🤖 {result}")
            return result
        if text.lower().startswith("remove task"):
            command = text.split(" ", 1)[1]
            result = run_terminal_command(f"python commands/template_empty.py remove-task {command}")
            self.logger.info(f"🤖 {result}")
            return result
        try:
            if text.lower().startswith("call api"):
                prompt = get_api_json_prompt()
                response = get_gemini_response([{"role":"user","content":prompt},{"role":"user","content":text}])
                try:
                    api_data = json.loads(response)
                    if not all(key in api_data for key in ['endpoint', 'method', 'headers', 'data']):
                        result = "Invalid json format, missing field: endpoint, method, headers or data"
                        self.logger.info(f"🤖 {result}")
                        return result
                    api_response = call_api(api_data['endpoint'],api_data['method'],api_data['headers'],api_data['data'])
                    result = f"Api response: {api_response}"
                    self.logger.info(f"🤖 {result}")
                    return result
                except json.JSONDecodeError:
                    result = f"Invalid json format: {response}"
                    self.logger.info(f"🤖 {result}")
                    return result
            # Check if text matches our last response
            if (
                self.conversation_history
                and text.strip().lower()
                in self.conversation_history[-1]["content"].lower()
            ):
                self.logger.info("🤖 Ignoring own speech input")
                return ""

            # Add user message to conversation history
            self.conversation_history.append({"role": "user", "content": text})

            # Generate response using configured brain
            self.logger.info(f"🤖 Processing text with {self.brain}...")
            if self.brain.startswith("ollama:"):
                model_no_prefix = ":".join(self.brain.split(":")[1:])
                response = ollama_conversational_prompt(
                    self.conversation_history, model=model_no_prefix
                )
            elif self.brain == "deepseek":
                 response = get_deepseek_response(self.conversation_history)
            elif self.brain == "gemini":
                response = get_gemini_response(self.conversation_history)
            elif self.brain == "mistral":
                response = get_mistral_response(self.conversation_history)
            else:
               raise ValueError(f"Unsupported brain: {self.brain}")

            # Add assistant response to history
            if response is None:
                self.logger.error("❌ Got empty or None response from the model")
                response = "Sorry, I don't know how to respond to that."

            self.conversation_history.append({"role": "assistant", "content": response})

            # Add interaction to memory
            self.add_to_memory(text, response)

            # Speak the response
            self.speak(response)

            return response

        except Exception as e:
            self.logger.error(f"❌ Error occurred: {str(e)}")
            raise

    def speak(self, text: str):
        """Convert text to speech using configured engine"""
        try:
            self.logger.info(f"🔊 Speaking: {text}")

            if self.voice_type == "local":
                self.engine.say(text)
                self.engine.runAndWait()

            elif self.voice_type == "realtime-tts":
                self.stream.feed(text)
                self.stream.play()

            elif self.voice_type == "elevenlabs":
                audio = self.elevenlabs_client.generate(
                    text=text,
                    voice=self.elevenlabs_voice,
                    model="eleven_turbo_v2",
                    stream=False,
                )
                play(audio)

            self.logger.info(f"🔊 Spoken: {text}")

        except Exception as e:
            self.logger.error(f"❌ Error in speech synthesis: {str(e)}")
            raise

    def add_to_memory(self, user_input: str, assistant_response: str):
        """Adds an interaction to the memory."""
        self.memory.add_interaction(user_input, assistant_response)

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Returns the conversation history."""
        return self.memory.get_conversation_history()

    def set_user_preference(self, key: str, value: str):
        """Sets a user preference."""
        self.memory.set_user_preference(key, value)

    def get_user_preference(self, key: str) -> Optional[str]:
        """Returns a user preference."""
        return self.memory.get_user_preference(key)
