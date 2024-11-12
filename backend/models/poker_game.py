from dataclasses import dataclass, field
import random
from typing import List

from .player import Player


@dataclass
class Move:
    """ 
    A class to represent a player's move in a poker game.
    The amount is only relevant for raise actions. 
    """

    action: str
    amount: float

    def __post_init__(self):
        if self.action not in ['call', 'raise', 'fold', 'check']:
            raise ValueError("Action must be 'call', 'raise', 'fold', or 'check'")

        if self.amount < 0:
            raise ValueError("Amount must be positive")


@dataclass
class GameStatistics:
    """ 
    A class to represent the statistics of a poker game. 
    """

    player_names: dict[int, str]
    num_rounds: int = 0
    winners: List[int] = field(default_factory=list)
    money_gained: dict[int, List[float]] = field(default_factory=dict)


class PokerGame:
    """
    A class to represent a poker game with multiple players and multiple rounds.
    """

    def __init__(self,
                players: List[Player],
                money: List[float] = [],
                small_blind: int = 10,
                big_blind: int = 20,
                raises_per_round: int = 3,
                tries_per_move: int = 3,
                num_rounds: int = 1,
                num_eliminations: int = 0
    ):
        """ 
        Initialize a poker game with a list of players and a list of starting money for each player.
        """

        # Initialize players
        self.players_dict = {i : player for i, player in enumerate(players)}
        self.player_names = {i : player.name for i, player in enumerate(players)}
        self.num_players = len(self.players_dict)
        assert self.num_players >= 2, "There must be at least 2 players to play poker"

        # Initialize money
        if money:
            assert len(money) == len(players), "Each player must have a starting amount of money"
        else:
            money= [100.0] * len(players)

        # Initialize blinds
        self.small_blind = small_blind
        self.small_blind_id = 0

        self.big_blind = big_blind
        self.big_blind_id = 1

        # Initialize game parameters
        self.raises_per_round = raises_per_round
        self.tries_per_move = tries_per_move
        self.num_rounds = num_rounds
        self.num_eliminations = num_eliminations

        # Initialize game state
        self.game_state = {}
        self.game_state_description = ""
        self.game_statistics = GameStatistics(player_names=self.player_names)

        self.deck = self.create_deck()
        random.shuffle(self.deck)

        # Initialize game parameters
        self.game_state = {
            'deck': self.deck,
            'pot': 0,
            'cards': [],
            'call_amount': self.big_blind
        }

        # Initialize player states
        self.player_states = {}
        for i in range(len(self.players_dict)):
            self.player_states[i] = {'hand': [], 'bet': 0.0, 'money': money[i], 'is_active': True, 'is_all_in': False}


    def reset_game(self):
        """ 
        Reset the game state and player states to be ready for a new round. 
        Returns the amount of eliminated players.
        """

        # Reset game state
        self.deck = self.create_deck()
        random.shuffle(self.deck)
        self.game_state = {'deck': self.deck, 'pot': 0, 'cards': [], 'call_amount': self.big_blind}

        # Reset player states
        eliminations = 0
        for i in range(len(self.players_dict)):
            self.player_states[i]['hand'] = []
            self.player_states[i]['bet'] = 0.0
            if self.player_states[i]['money'] > 0:
                self.player_states[i]['is_active'] = True
            else:
                self.player_states[i]['is_active'] = False
                eliminations += 1

            self.player_states[i]['is_all_in'] = False

        return eliminations


    def create_deck(self):
        """ 
        Create a full deck of cards. 
        """

        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'Jack', 'Queen', 'King', 'Ace']
        return [f"{rank} of {suit}" for suit in suits for rank in ranks]


    def deal_cards(self):
        """ 
        Deal 2 cards to each player. 
        """

        for i in range(self.num_players):
            self.player_states[i]['hand'] = [self.deck.pop(0), self.deck.pop(0)]


    def deal_community_cards(self, num_cards: int, river: bool = False):
        """ 
        Deal num_cards community cards. 
        """

        for _ in range(num_cards):
            self.game_state['cards'].append(self.deck.pop(0))

        if num_cards == 3:
            self.game_state_description += f"\nThe flop cards are {self.game_state['cards']}."
        elif num_cards == 1:
            self.game_state_description += f"\nThe {['turn', 'river'][river]} card is {self.game_state['cards'][-1]}."


    def get_active_players(self, starting_player_id: int = 0):
        """ 
        Get a list of all active players starting from a given player. 
        """

        return [(i % self.num_players) for i in range(starting_player_id, self.num_players + starting_player_id) if self.player_states[(i % self.num_players)]['is_active']]


    def betting_round(self, starting_player_id: int):
        """ 
        Handle a betting round by getting moves from each active player until a raise is made or the raise count is reached. 
        """

        # keep track of raise count
        raise_count = 0

        # queue of players to move before round is over
        players_to_move = self.get_active_players(starting_player_id)

        # while there are still players to move
        while len(players_to_move) > 0:

            # get current player
            player_id = players_to_move.pop(0)

            # skip if player is all in
            if self.player_states[player_id]['is_all_in']:
                continue
            
            for _ in range(self.tries_per_move):
                errors = ""
                #TODO write make move
                move = self.players_dict[player_id].make_move(self.game_state_description, errors)
                valid, error = self.handle_player_move(player_id, move, raise_allowed=raise_count < self.raises_per_round)
                errors += error

                if valid:
                    break
            
            if not valid:
                move = Move(action='fold', amount=0)
                self.handle_player_move(player_id, move)
            
            # if player raises, add all other players to the list of players to move
            if move.action == 'raise':
                raise_count += 1
                reactivated_players = self.get_active_players((player_id + 1) % self.num_players)
                for player_id in reactivated_players:
                    if player_id not in players_to_move:
                        players_to_move.append(player_id)


    def showdown(self):
        """ 
        Handle the showdown by determining the winner of the pot. 
        """

        players_to_show = self.get_active_players()
        best_hands = []

        for player_id in players_to_show:
            best_hands.append(self.get_best_hand(self.player_states[player_id]['hand'] + self.game_state['cards']))

        # Determine winner
        winner_id = self.get_winner(best_hands)

        # Update game state description
        self.game_state_description += f"\nPlayer {self.player_names[winner_id]} wins the pot of {self.game_state['pot']}!"

        # Winner gets the pot
        self.player_states[winner_id]['money'] += self.game_state['pot']  
        
        # Update game statistics
        self.game_statistics.winners.append(winner_id)
        self.game_statistics.money_gained[winner_id].append(self.game_state['pot'] - self.player_states[winner_id]['bet'])
        for player_id in range(self.num_players):
            if player_id != winner_id:
                self.game_statistics.money_gained[player_id].append(-self.player_states[player_id]['bet'])


    def get_best_hand(self, cards: List[str]):
        """ 
        Get the best hand from a list of 5 cards; the two cards in the player's hand and the three community cards. 
        """

        # Convert cards to (rank, suit) tuples for easier processing
        processed_cards = []
        for card in cards:
            rank, _, suit = card.partition(' of ')
            # Convert face cards to numbers
            if rank == 'Jack':
                rank = 11
            elif rank == 'Queen':
                rank = 12
            elif rank == 'King':
                rank = 13
            elif rank == 'Ace':
                rank = 14
            else:
                rank = int(rank)
            processed_cards.append((rank, suit))

        # Sort cards by rank, highest first
        processed_cards.sort(reverse=True, key=lambda x: x[0])

        # Check for straight flush
        for suit in ['Hearts', 'Diamonds', 'Clubs', 'Spades']:
            suited_cards = [card[0] for card in processed_cards if card[1] == suit]
            if len(suited_cards) >= 5:
                suited_cards.sort(reverse=True)
                for i in range(len(suited_cards) - 4):
                    if suited_cards[i] - suited_cards[i+4] == 4:
                        return ('straight_flush', suited_cards[i])

        # Check for four of a kind
        for rank in range(14, 1, -1):
            if sum(1 for card in processed_cards if card[0] == rank) == 4:
                return ('four_of_a_kind', rank)

        # Check for full house
        for three_rank in range(14, 1, -1):
            if sum(1 for card in processed_cards if card[0] == three_rank) == 3:
                for two_rank in range(14, 1, -1):
                    if two_rank != three_rank and sum(1 for card in processed_cards if card[0] == two_rank) >= 2:
                        return ('full_house', (three_rank, two_rank))

        # Check for flush
        for suit in ['Hearts', 'Diamonds', 'Clubs', 'Spades']:
            suited_cards = [card[0] for card in processed_cards if card[1] == suit]
            if len(suited_cards) >= 5:
                suited_cards.sort(reverse=True)
                return ('flush', suited_cards[:5])

        # Check for straight
        ranks = sorted(list(set(card[0] for card in processed_cards)), reverse=True)
        for i in range(len(ranks) - 4):
            if ranks[i] - ranks[i+4] == 4:
                return ('straight', ranks[i])

        # Check for three of a kind
        for rank in range(14, 1, -1):
            if sum(1 for card in processed_cards if card[0] == rank) == 3:
                return ('three_of_a_kind', rank)

        # Check for two pair
        pairs = []
        for rank in range(14, 1, -1):
            if sum(1 for card in processed_cards if card[0] == rank) == 2:
                pairs.append(rank)
            if len(pairs) == 2:
                return ('two_pair', tuple(pairs))

        # Check for one pair
        for rank in range(14, 1, -1):
            if sum(1 for card in processed_cards if card[0] == rank) == 2:
                return ('pair', rank)

        # High card
        return ('high_card', processed_cards[0][0])


    def get_winner(self, best_hands: List[tuple]):
        """ 
        Get the winner of the pot from a list of each player's best hand. 
        """

        # Define hand rankings
        hand_rankings = {
            'straight_flush': 8,
            'four_of_a_kind': 7,
            'full_house': 6,
            'flush': 5,
            'straight': 4,
            'three_of_a_kind': 3,
            'two_pair': 2,
            'pair': 1,
            'high_card': 0
        }
        
        # Find the highest hand type among all players
        max_hand_rank = max(hand_rankings[hand[0]] for hand in best_hands)
        
        # Filter to only hands of the highest type
        best_indices = [i for i, hand in enumerate(best_hands) 
                    if hand_rankings[hand[0]] == max_hand_rank]
        
        if len(best_indices) == 1:
            return best_indices[0]
        
        # If multiple players have the same hand type, compare their values
        hand_type = best_hands[best_indices[0]][0]
        values = [best_hands[i][1] for i in best_indices]
        
        if hand_type in ['straight_flush', 'four_of_a_kind', 'straight', 'three_of_a_kind', 'pair', 'high_card']:
            # Simple comparison of single values
            max_value = max(values)
            winners = [i for i, v in zip(best_indices, values) if v == max_value]
        
        elif hand_type == 'full_house' or hand_type == 'two_pair':
            # Compare tuples (primary rank, secondary rank)
            max_value = max(values)
            winners = [i for i, v in zip(best_indices, values) if v == max_value]
        
        elif hand_type == 'flush':
            # Compare lists of 5 cards
            max_value = max(values)
            winners = [i for i, v in zip(best_indices, values) if v == max_value]
        
        # If still tied, it's a split pot
        return winners[0] if len(winners) == 1 else winners


    def play_round(self):
        """ 
        Play a round of poker. 
        """

        eliminations = sum(1 for player in self.player_states.values() if not player['is_active'])

        # Update game state description
        self.game_state_description += f"\nA new round of poker is starting."
        self.game_state_description += f"\n{eliminations} players have been eliminated."
        self.game_state_description += f"\nThe small blind is {self.small_blind}."
        self.game_state_description += f"\nThe big blind is {self.big_blind}."
        
        for player_id in self.get_active_players():
            self.game_state_description += f"\nPlayer {self.player_names[player_id]} has {self.player_states[player_id]['money']} dollarsat the start of the round."

        # Small blind goes first
        self.handle_forced_bet(self.small_blind_id)

        # Big blind goes next
        self.handle_forced_bet(self.big_blind_id)

        # Forced bets are done, now cards are dealt
        self.deal_cards()

        # Pre-flop betting round
        self.betting_round((self.big_blind_id + 1) % self.num_players)

        # Deal flop
        self.deal_community_cards(3)

        # Flop betting round
        self.betting_round(self.small_blind_id)

        # Deal turn
        self.deal_community_cards(1)

        # Turn betting round
        self.betting_round(self.small_blind_id)

        # Deal river
        self.deal_community_cards(1)

        # River betting round
        self.betting_round(self.small_blind_id)

        # Showdown
        self.showdown()


    def handle_forced_bet(self, player_id: int):
        """ 
        Handle a forced bet by the small blind or big blind. 
        """

        # Check if forced bet is small blind or big blind
        if self.small_blind_id == player_id:
            required_bet = self.small_blind
            is_small_blind = True
        elif self.big_blind_id == player_id:
            required_bet = self.big_blind
            is_small_blind = False
        else:
            raise ValueError(f"Player {self.player_names[player_id]} is not the small blind or big blind and thus is not forced to bet")

        # Check if player is all in
        if self.player_states[player_id]['money'] <= required_bet:
            self.player_states[player_id]['is_all_in'] = True
            self.player_states[player_id]['bet'] = self.player_states[player_id]['money']
            self.player_states[player_id]['money'] = 0.0
            self.game_state['pot'] += self.player_states[player_id]['bet']

        else:
            self.player_states[player_id]['bet'] = required_bet
            self.player_states[player_id]['money'] -= required_bet
            self.game_state['pot'] += required_bet

        # Update game state description
        self.game_state_description += f"\nPlayer {self.player_names[player_id]} is forced to bet {required_bet} as {'small' if is_small_blind else 'big'} blind. "
        if self.player_states[player_id]['is_all_in']:
            self.game_state_description += f"Player {self.player_names[player_id]} is thus all in."


    def handle_player_move(self, player_id: int, move: Move, raise_allowed: bool = True):
        """ 
        Handle a player move by updating the game state and player states. 
        Return True if the move is valid, False and error message otherwise. 
        """

        call_amount = self.game_state['call_amount'] - self.player_states[player_id]['bet']

        if move.action == 'fold':
            self.player_states[player_id]['is_active'] = False
            return True, ""
        
        elif move.action == 'call':
            if self.player_states[player_id]['money'] > call_amount:
                self.player_states[player_id]['money'] -= call_amount
                self.player_states[player_id]['bet'] += call_amount
                self.game_state['pot'] += call_amount
                self.game_state_description += f"\nPlayer {self.player_names[player_id]} calls by betting {call_amount}."
            else:
                self.player_states[player_id]['is_all_in'] = True
                call_amount = self.player_states[player_id]['money']
                self.game_state['pot'] += call_amount
                self.player_states[player_id]['bet'] += call_amount
                self.player_states[player_id]['money'] = 0.0
                self.game_state_description += f"\nPlayer {self.player_names[player_id]} calls by betting {call_amount} and is thus all in."

            return True, ""

        elif move.action == 'raise':
            if not raise_allowed:
                return False, f"You tried raising but you are not allowed to raise this round as there have already been {self.raises_per_round} raises."

            if move.amount > call_amount:
                if self.player_states[player_id]['money'] < move.amount:
                    return False, f"You tried raising but your raise amount {move.amount} is greater than the amount of money you have {self.player_states[player_id]['money']}."
                else:
                    self.player_states[player_id]['money'] -= move.amount
                    self.player_states[player_id]['bet'] += move.amount
                    self.game_state['pot'] += move.amount
                    self.game_state['call_amount'] += move.amount - call_amount
                    self.game_state_description += f"\nPlayer {self.player_names[player_id]} raises by betting {move.amount}."
                    return True, ""
            else:
                return False, f"You tried raising but your raise amount {move.amount} is less than the current call amount {call_amount}."

        elif move.action == 'check':
            if self.player_states[player_id]['bet'] == self.game_state['call_amount']:
                self.game_state_description += f"\nPlayer {self.player_names[player_id]} checks."
                return True, ""
            else:
                return False, f"You tried checking but you have not bet the current call amount {call_amount}."

        else:
            return False, "Invalid move"

    def play_game(self):
        """ 
        Play a game of poker. 
        """
        eliminations = self.reset_game()

        while self.game_statistics.num_rounds < self.num_rounds and eliminations < self.num_eliminations:
            self.play_round()
            self.game_statistics.num_rounds += 1
            eliminations = self.reset_game()

        return self.game_statistics


    def get_game_statistics(self):
        return self.game_statistics

    
    def get_game_description(self):
        return self.game_state_description
