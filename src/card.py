import pygame
from enum import Enum
from .constants import *

class Suit(Enum):
    SPADES = '♠'
    HEARTS = '♥'
    CLUBS = '♣'
    DIAMONDS = '♦'
    
    def __str__(self):
        return self.value
    
    def color(self):
        return RED if self in [Suit.HEARTS, Suit.DIAMONDS] else BLACK

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
    
    def __str__(self):
        if self.value == 1:
            return 'A'
        elif self.value == 11:
            return 'J'
        elif self.value == 12:
            return 'Q'
        elif self.value == 13:
            return 'K'
        return str(self.value)

class Card:
    def __init__(self, suit: Suit, rank: Rank):
        self.suit = suit
        self.rank = rank
        self.face_up = True
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)
        self.selected = False
        
    def __str__(self):
        return f"{self.rank}{self.suit}"
    
    def __repr__(self):
        return self.__str__()
    
    def can_place_on(self, other: 'Card') -> bool:
        if other is None:
            return True
        return (self.suit.color() != other.suit.color() and 
                self.rank.value == other.rank.value - 1)
    
    def can_place_on_foundation(self, foundation_cards: list) -> bool:
        if not foundation_cards:
            return self.rank == Rank.ACE
        top_card = foundation_cards[-1]
        return (self.suit == top_card.suit and 
                self.rank.value == top_card.rank.value + 1)
    
    def draw(self, screen, x, y, font):
        self.rect.x = x
        self.rect.y = y
        
        pygame.draw.rect(screen, WHITE, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)
        
        if self.selected:
            pygame.draw.rect(screen, YELLOW, self.rect, 3)
        
        color = self.suit.color()
        text = font.render(str(self.rank), True, color)
        screen.blit(text, (x + 5, y + 5))
        
        suit_text = font.render(str(self.suit), True, color)
        screen.blit(suit_text, (x + 40, y + 5))

def create_deck():
    deck = []
    for suit in Suit:
        for rank in Rank:
            deck.append(Card(suit, rank))
    return deck

def microsoft_deal(seed: int):
    import random
    deck = create_deck()
    random.seed(seed)
    random.shuffle(deck)
    return deck