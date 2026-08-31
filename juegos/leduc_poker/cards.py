from enum import IntEnum


class Card(IntEnum):
    JACK = 1
    QUEEN = 2
    KING = 3


DECK_COMPOSITION = [
    Card.JACK, Card.JACK,
    Card.QUEEN, Card.QUEEN,
    Card.KING, Card.KING
]


CARD_NAMES = {
    Card.JACK: "JACK (J)",
    Card.QUEEN: "QUEEN (Q)",
    Card.KING: "KING (K)"
}
