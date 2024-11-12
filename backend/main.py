from fastapi import FastAPI
from models.poker_game import PokerGame
from models.model_handler import ModelHandler

app = FastAPI()
model_handler = ModelHandler()

@app.get("/standings")
def get_standings():
    standings = model_handler.get_standings()
    return standings

@app.get("/random_game")
def get_random_game():
    game = PokerGame()
    game.initialize_game()
    game.play_game()
    game_state = game.get_game_state()
    return game_state