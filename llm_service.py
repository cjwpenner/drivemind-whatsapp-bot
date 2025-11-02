"""
LLM Service for Claude and OpenAI API integration
Ported from DriveMind Android app's ClaudeService and OpenAIService
"""
import anthropic
import openai
from models import ClaudeModel, OpenAIModel, Message
from typing import List, Dict, Tuple
import os


class LLMService:
    """Service for interacting with Claude and OpenAI APIs"""

    # System prompt optimized for voice/TTS output
    # Same as DriveMind Android app
    VOICE_FRIENDLY_SYSTEM_PROMPT = """
You are a helpful voice assistant designed for hands-free use while driving. Your responses will be read aloud via text-to-speech.

Guidelines for responses:
- Use natural, conversational language as if speaking to someone
- Avoid markdown formatting (no asterisks, hashes, pipes, arrows, code blocks)
- Instead of bullet points with dashes or asterisks, use phrases like "First," "Second," "Another point is," or "Also,"
- Spell out symbols and abbreviations (use "dollars" not "$", "percent" not "%")
- Use words instead of numbers when it sounds more natural (e.g., "twenty dollars" rather than "20 dollars" for speech)
- Keep responses concise but informative - imagine you're explaining to someone who can't see a screen
- For lists, use natural transitions like "The first item is... The second item is... And finally..."
- Avoid emoji, special characters, or visual-only elements
- When giving directions or steps, speak them clearly: "Step one: do this. Step two: do that."

Be helpful, accurate, and concise. Remember: your audience is listening, not reading.
"""

    def __init__(self, claude_api_key: str = None, openai_api_key: str = None, provider: str = "claude"):
        """
        Initialize LLM service
        provider: "claude" or "openai"
        """
        self.provider = provider

        if provider == "claude":
            self.claude_client = anthropic.Anthropic(
                api_key=claude_api_key or os.getenv('CLAUDE_API_KEY'),
                timeout=180.0  # 3 minutes for Sonnet deep dives
            )
        else:
            openai.api_key = openai_api_key or os.getenv('OPENAI_API_KEY')

    def send_message(self, messages: List[Message], model: str = "haiku") -> Tuple[str, int, int]:
        """
        Send message to LLM and get response
        Returns: (response_text, input_tokens, output_tokens)
        """
        if self.provider == "claude":
            return self._send_claude_message(messages, model)
        else:
            return self._send_openai_message(messages, model)

    def _send_claude_message(self, messages: List[Message], model: str) -> Tuple[str, int, int]:
        """Send message to Claude API"""
        try:
            # Convert messages to Claude format
            claude_messages = []
            for msg in messages:
                claude_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            # Select model
            if model == "sonnet":
                model_id = ClaudeModel.SONNET["id"]
                max_tokens = ClaudeModel.SONNET["maxOutput"]
            else:
                model_id = ClaudeModel.HAIKU["id"]
                max_tokens = ClaudeModel.HAIKU["maxOutput"]

            print(f"[LLM] Calling Claude API with model: {model_id}")
            print(f"[LLM] Message count: {len(claude_messages)}")

            # Call Claude API
            response = self.claude_client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                system=self.VOICE_FRIENDLY_SYSTEM_PROMPT,
                messages=claude_messages
            )

            # Extract response
            response_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            print(f"[LLM] Response received - Input tokens: {input_tokens}, Output tokens: {output_tokens}")

            return (response_text, input_tokens, output_tokens)

        except Exception as e:
            print(f"[LLM] Error calling Claude API: {e}")
            raise Exception(f"Claude API error: {str(e)}")

    def _send_openai_message(self, messages: List[Message], model: str) -> Tuple[str, int, int]:
        """Send message to OpenAI API"""
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": "system", "content": self.VOICE_FRIENDLY_SYSTEM_PROMPT}
            ]

            for msg in messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            # Select model
            if model == "gpt4o":
                model_id = OpenAIModel.GPT4O["id"]
            else:
                model_id = OpenAIModel.GPT4O_MINI["id"]

            print(f"[LLM] Calling OpenAI API with model: {model_id}")
            print(f"[LLM] Message count: {len(openai_messages)}")

            # Call OpenAI API
            response = openai.chat.completions.create(
                model=model_id,
                messages=openai_messages,
                max_tokens=4096
            )

            # Extract response
            response_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

            print(f"[LLM] Response received - Input tokens: {input_tokens}, Output tokens: {output_tokens}")

            return (response_text, input_tokens, output_tokens)

        except Exception as e:
            print(f"[LLM] Error calling OpenAI API: {e}")
            raise Exception(f"OpenAI API error: {str(e)}")

    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            test_message = Message(
                content="Hello",
                role="user",
                timestamp=None
            )
            response, _, _ = self.send_message([test_message], "haiku")
            return len(response) > 0
        except Exception as e:
            print(f"[LLM] Connection test failed: {e}")
            return False
