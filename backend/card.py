from enum import Enum
from typing import List, Optional
import random

class Suit(Enum):
    SPADES = 0
    HEARTS = 1
    CLUBS = 2
    DIAMONDS = 3

class Rank(Enum):
    ACE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13

class Card:
    __slots__ = ('suit', 'rank', 'id') 
    
    _next_id = 0
    _id_map = {}
    
    def __init__(self, suit: Suit, rank: Rank):
        self.suit = suit
        self.rank = rank
        
        key = (suit.value, rank.value)
        if key not in Card._id_map:
            Card._id_map[key] = Card._next_id
            Card._next_id += 1
        self.id = Card._id_map[key]
    
    def __repr__(self):
        rank_str = {
            Rank.ACE: 'A', Rank.TWO: '2', Rank.THREE: '3', Rank.FOUR: '4',
            Rank.FIVE: '5', Rank.SIX: '6', Rank.SEVEN: '7', Rank.EIGHT: '8',
            Rank.NINE: '9', Rank.TEN: '10', Rank.JACK: 'J', Rank.QUEEN: 'Q',
            Rank.KING: 'K'
        }[self.rank]
        suit_str = {
            Suit.SPADES: '♠', Suit.HEARTS: '♥', Suit.CLUBS: '♣', Suit.DIAMONDS: '♦'
        }[self.suit]
        return f"{rank_str}{suit_str}"
    
    def __str__(self):
        return self.__repr__()
    
    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.rank == other.rank
    
    def __hash__(self):
        return self.id
    def is_red(self):
        return self.suit in {Suit.HEARTS, Suit.DIAMONDS}

    def is_black(self):
        return self.suit in {Suit.SPADES, Suit.CLUBS}
    def can_place_on(self, other: 'Card') -> bool:
        if other is None:
            return False

        if self.is_red() == other.is_red():
            return False

        return self.rank.value == other.rank.value - 1
    
    def can_place_on_foundation(self, foundation: List['Card']) -> bool:
        if not foundation:
            return self.rank == Rank.ACE
        top_card = foundation[-1]
        return self.suit == top_card.suit and self.rank.value == top_card.rank.value + 1

def create_deck() -> list:
    deck = []
    for suit in Suit:
        for rank in Rank:
            deck.append(Card(suit, rank))
    return deck

def microsoft_deal(seed: int) -> list:
    # Bản đồ quy đổi index sang Suit và Rank chuẩn của MS FreeCell
    suit_map = {0: Suit.CLUBS, 1: Suit.DIAMONDS, 2: Suit.HEARTS, 3: Suit.SPADES}
    rank_map = {i: Rank(i + 1) for i in range(13)}

    deck_indices = list(range(52))
    state = seed
    
    # MS FreeCell random generator (LCG)
    for i in range(51, 0, -1):
        state = (state * 214013 + 2531011) & 0x7FFFFFFF
        swap = (state >> 16) % (i + 1)
        deck_indices[i], deck_indices[swap] = deck_indices[swap], deck_indices[i]
        
    # MS FreeCell deals from the back of the deck
    deck_indices.reverse()
    
    deck = []
    for idx in deck_indices:
        deck.append(Card(suit_map[idx % 4], rank_map[idx // 4]))
        
    return deck