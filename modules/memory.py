class Memory:
    def __init__(self):
        self.conversation_history = []
        self.user_preferences = {}

    def add_interaction(self, user_input: str, assistant_response: str):
        self.conversation_history.append({"user": user_input, "assistant": assistant_response})

    def get_conversation_history(self):
        return self.conversation_history

    def set_user_preference(self, key: str, value: str):
        self.user_preferences[key] = value

    def get_user_preference(self, key: str):
        return self.user_preferences.get(key)