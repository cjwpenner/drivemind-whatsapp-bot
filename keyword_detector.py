"""
Keyword detection for automatic model selection
Ported from DriveMind Android app's KeywordDetector.kt
"""

class ProcessedMessage:
    def __init__(self, model, cleaned_message, was_modified, triggered_sonnet):
        self.model = model
        self.cleaned_message = cleaned_message
        self.was_modified = was_modified
        self.triggered_sonnet = triggered_sonnet


class KeywordDetector:
    """Utility for detecting keywords in user messages"""

    # Keywords that trigger Sonnet (thoughtful) model
    SONNET_TRIGGERS = [
        "think hard",
        "think carefully",
        "think deep",
        "think deeply",
        "deep dive",
        "analyze",
        "analyze carefully",
        "be thorough",
        "explain in detail",
        "detailed explanation",
        "comprehensive",
        "in depth"
    ]

    # Keywords that indicate end of question (like "over" in CB radio)
    END_OF_QUESTION_KEYWORDS = [
        "over",
        "done",
        "send",
        "that's it",
        "end"
    ]

    @staticmethod
    def detect_model_preference(message):
        """
        Detect if message should use Sonnet model instead of default Haiku
        Returns: Tuple[model, cleaned_message]
        """
        lower_message = message.lower()

        # Check for Sonnet triggers
        uses_sonnet = any(trigger in lower_message for trigger in KeywordDetector.SONNET_TRIGGERS)

        if uses_sonnet:
            return ("sonnet", message)
        else:
            return ("haiku", message)

    @staticmethod
    def remove_end_keywords(message):
        """
        Remove end-of-question keywords from message
        Returns: Cleaned message without trailing keywords
        """
        cleaned = message.strip()
        lower_cleaned = cleaned.lower()

        # Check each end keyword
        for keyword in KeywordDetector.END_OF_QUESTION_KEYWORDS:
            # Possible patterns
            patterns = [
                f" {keyword}",
                f" {keyword}.",
                f" {keyword}!",
                f",{keyword}",
                f" {keyword}?",
                f".{keyword}",
                f"!{keyword}",
                f"?{keyword}"
            ]

            for pattern in patterns:
                if lower_cleaned.endswith(pattern.lower()):
                    # Remove the keyword and any trailing punctuation
                    start_index = len(cleaned) - len(pattern)
                    cleaned = cleaned[:start_index].strip()
                    # Remove any trailing punctuation left behind
                    cleaned = cleaned.rstrip('.,!?')
                    break

        return cleaned

    @staticmethod
    def process_message(message, current_model="haiku"):
        """
        Process user message: detect model and clean keywords
        Returns: ProcessedMessage
        """
        # First, remove end keywords
        without_end = KeywordDetector.remove_end_keywords(message)

        # Then detect model preference
        detected_model, final_message = KeywordDetector.detect_model_preference(without_end)

        # Only override current model if Sonnet was explicitly requested
        if detected_model == "sonnet":
            selected_model = "sonnet"
        else:
            selected_model = current_model  # Keep user's current selection

        was_modified = without_end != message or detected_model == "sonnet"

        return ProcessedMessage(
            model=selected_model,
            cleaned_message=final_message,
            was_modified=was_modified,
            triggered_sonnet=(detected_model == "sonnet")
        )
