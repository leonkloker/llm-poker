class Player:
    def __init__(self, name, model):
        self.name = name
        self.model = model
        self.history = []
        self.context = ""
        self.base_prompt = """You are a poker player playing texas holdem poker against other players.
        You're goal is to win the game consisting of multiple rounds by any strategy you can devise.
        """


    def make_move(self, game_state: str, additional_context: str = ""):

        # Fetch current game state and update history
        self.update_context(game_state, additional_context)

        # Get move from LLM
        move = self.model.get_move(self.history, raise_allowed)
        # Record move in history
        self.history.append(move)
        return move

    def update_context(self, game_state: str, additional_context: str = ""):
        # Add '(you)' after player's name
        self.context = game_state.replace(self.name, f"{self.name} (you)")

        # Add any additional context
        if additional_context:
            self.context += additional_context

    def to_dict(self):
        return {
            'name': self.name,
            'model': self.model.name,
            'history': self.history
        }