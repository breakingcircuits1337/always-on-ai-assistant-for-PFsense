from typing import List
import os
import logging
from datetime import datetime
from modules.assistant_config import get_config
from modules.utils import (
    build_file_name_session,
    create_session_logger_id,
    setup_logging,
)
from modules.deepseek import get_deepseek_response, get_gemini_response, get_mistral_response
from modules.execute_python import execute_uv_python, execute
from elevenlabs import play
from elevenlabs.client import ElevenLabs
import time


class TyperAgent:
    def __init__(self, logger: logging.Logger, session_id: str):
        self.logger = logger
        self.session_id = session_id
        self.log_file = build_file_name_session("session.log", session_id)
        self.elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVEN_API_KEY"))
        self.previous_successful_requests = []
        self.previous_responses = []

    def _validate_markdown(self, file_path: str) -> bool:
        """Validate that file is markdown and has expected structure"""
        if not file_path.endswith((".md", ".markdown")):
            self.logger.error(f"📄 Scratchpad file {file_path} must be a markdown file")
            return False

        try:
            with open(file_path, "r") as f:
                content = f.read()
                # Basic validation - could be expanded based on needs
                if not content.strip():
                    self.logger.warning("📄 Markdown file is empty")
                return True
        except Exception as e:
            self.logger.error(f"📄 Error reading markdown file: {str(e)}")
            return False

    @classmethod
    def build_agent(cls, typer_file: str, scratchpad: List[str]):
        """Create and configure a new TyperAssistant instance"""
        session_id = create_session_logger_id()
        logger = setup_logging(session_id)
        logger.info(f"🚀 Starting STT session {session_id}")

        if not os.path.exists(typer_file):
            logger.error(f"📂 Typer file {typer_file} does not exist")
            raise FileNotFoundError(f"Typer file {typer_file} does not exist")

        # Validate markdown scratchpad
        agent = cls(logger, session_id)
        if scratchpad and not agent._validate_markdown(scratchpad[0]):
            raise ValueError(f"Invalid markdown scratchpad file: {scratchpad[0]}")

        return agent, typer_file, scratchpad[0]

    def build_prompt(
        self,
        typer_file: str,
        scratchpad: str,
        context_files: List[str],
        prompt_text: str,
    ) -> str:
        """Build and format the prompt template with current state"""
        try:
            # Load typer file
            self.logger.info("📂 Loading typer file...")
            with open(typer_file, "r") as f:
                typer_content = f.read()

            # Load scratchpad file
            self.logger.info("📝 Loading scratchpad file...")
            if not os.path.exists(scratchpad):
                self.logger.error(f"📄 Scratchpad file {scratchpad} does not exist")
                raise FileNotFoundError(f"Scratchpad file {scratchpad} does not exist")

            with open(scratchpad, "r") as f:
                scratchpad_content = f.read()

            # Load context files
            context_content = ""
            for file_path in context_files:
                if not os.path.exists(file_path):
                    self.logger.error(f"📄 Context file {file_path} does not exist")
                    raise FileNotFoundError(f"Context file {file_path} does not exist")

                with open(file_path, "r") as f:
                    file_content = f.read()
                    file_name = os.path.basename(file_path)
                    context_content += f'''	<context name="{file_name}">
{file_content}
</context>

''' # Corrected multiline f-string

            # Load and format prompt template
            self.logger.info("📝 Loading prompt template...")
            with open("prompts/typer-commands.xml", "r") as f:
                prompt_template = f.read()

            # Replace template placeholders
            formatted_prompt = (
                prompt_template.replace("{{typer-commands}}", typer_content)
                .replace("{{scratch_pad}}", scratchpad_content)
                .replace("{{context_files}}", context_content)
                .replace("{{natural_language_request}}", prompt_text)
            )

            # Log the filled prompt template to file only (not stdout)
            with open(self.log_file, "a") as log:
                log.write("
📝 Filled prompt template:
")
                log.write(formatted_prompt)
                log.write("

")

            return formatted_prompt

        except Exception as e:
            self.logger.error(f"❌ Error building prompt: {str(e)}")
            raise

    def get_response_for_typer_prompt(
        self,
        prompt: str,
        typer_file: str,
        model_name:str
    ) -> str:
        """Get the deepseek response, and handle errors.
        Args:
            prompt (str): The prompt to send to deepseek
            typer_file (str): the name of the typer_file
        Returns:
            str: The deepseek response
        Raises:
            Exception: If deepseek is not available
        """
        self.logger.info(f"🤖 Processing text with {model_name}...")

        prefix = f"uv run python {typer_file}"

        if model_name == "deepseek":
            # Note: Passing prefix here might be a remnant of old deepseek function.
            # Consider if the prefix needs to be part of the prompt itself.
            command = get_deepseek_response(prompt, prefix)
        elif model_name == "gemini":
            # Gemini get_gemini_response expects a list of messages or a string prompt
            # If prefix is needed, it should be part of the prompt structure.
            command = get_gemini_response(prompt)
        elif model_name == "mistral":
             # Mistral get_mistral_response expects a list of messages or a string prompt
            # If prefix is needed, it should be part of the prompt structure.
            command = get_mistral_response(prompt)
        else:
            raise Exception(f"Model {model_name} is not supported")

        if command == prefix.strip():
            self.logger.info(f"🤖 Command not found for '{prompt}'")
            return "Command not found"
        return command


    def process_text(
        self,
        text: str,
        typer_file: str,
        scratchpad: str,
        context_files: List[str],
        mode: str,
    ) -> str:
        """Process text input and handle based on execution mode"""
        try:
            # Build fresh prompt with current state
            formatted_prompt = self.build_prompt(
                typer_file, scratchpad, context_files, text
            )

            # Generate command using DeepSeek
            # Get model from xml file
            with open("prompts/typer-commands.xml", "r") as f:
                typer_prompt_file = f.read()
            model_name = (
                typer_prompt_file.split("<model-name>")[1].split("</model-name>")[0]
            )
            self.logger.info(f"Using model {model_name}")

            command = self.get_response_for_typer_prompt(formatted_prompt, typer_file, model_name)

            if command == "Command not found":
                return "Command not found"

            # Handle different modes with markdown formatting
            assistant_name = get_config("typer_assistant.assistant_name")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # command_with_prefix = f"uv run python {typer_file} {command}"
            command_with_prefix = command

            if mode == "default":
                result = (
                    f"
## {assistant_name} Generated Command ({timestamp})

"
                    f"> Request: {text}

"
                    f"```bash
{command_with_prefix}
```"
                )
                with open(scratchpad, "a") as f:
                    f.write(result)
                self.think_speak(f"Command generated")
                return result

            elif mode == "execute":
                self.logger.info(f"⚡ Executing command: `{command_with_prefix}`")
                output = execute(command)

                result = (
                    f"

## {assistant_name} Executed Command ({timestamp})

"
                    f"> Request: {text}

"
                    f"**{assistant_name}'s Command:** 
```bash
{command_with_prefix}
```

"
                    f"**Output:** 
```
{output}```"
                )
                with open(scratchpad, "a") as f:
                    f.write(result)
                self.think_speak(f"Command generated and executed")
                return output

            elif mode == "execute-no-scratch":
                self.logger.info(f"⚡ Executing command: `{command_with_prefix}`")
                output = execute(command)
                self.think_speak(f"Command generated and executed")
                return output

            else:
                self.think_speak(f"I had trouble running that command")
                raise ValueError(f"Invalid mode: {mode}")

        except Exception as e:
            self.logger.error(f"❌ Error occurred: {str(e)}")
            raise

    def think_speak(self, text: str):
        response_prompt_base = ""
        with open("prompts/concise-assistant-response.xml", "r") as f:
            response_prompt_base = f.read()

        assistant_name = get_config("typer_assistant.assistant_name")
        human_companion_name = get_config("typer_assistant.human_companion_name")

        response_prompt = response_prompt_base.replace("{{latest_action}}", text)
        response_prompt = response_prompt.replace(
            "{{human_companion_name}}", human_companion_name
        )
        response_prompt = response_prompt.replace(
            "{{personal_ai_assistant_name}}", assistant_name
        )
        
        # Replaced prefix_prompt with get_gemini_response
        # The prompt formatting for different models should be handled within the respective get_*_response functions
        response = get_gemini_response(prompt=response_prompt)

        self.logger.info(f"🤖 Response: '{response}'")
        self.speak(response)

    def speak(self, text: str):

        start_time = time.time()
        model = "eleven_flash_v2_5"
        # model="eleven_flash_v2"
        # model = "eleven_turbo_v2"
        # model = "eleven_turbo_v2_5"
        # model="eleven_multilingual_v2"
        voice = get_config("typer_assistant.elevenlabs_voice")

        audio_generator = self.elevenlabs_client.generate(
            text=text,
            voice=voice,
            model=model,
            stream=False,
        )
        audio_bytes = b"".join(list(audio_generator))
        duration = time.time() - start_time
        self.logger.info(f"Model {model} completed tts in {duration:.2f} seconds")
        play(audio_bytes)
