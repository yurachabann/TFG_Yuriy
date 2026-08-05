from enum import IntEnum

class Card(IntEnum):
    GUARD = 1       # 5 copias
    PRIEST = 2      # 2 copias
    BARON = 3       # 2 copias
    HANDMAID = 4    # 2 copias
    PRINCE = 5      # 2 copias
    KING = 6        # 1 copia
    COUNTESS = 7    # 1 copia
    PRINCESS = 8    # 1 copia

DECK_COMPOSITION = [
    Card.GUARD, Card.GUARD, Card.GUARD, Card.GUARD, Card.GUARD,
    Card.PRIEST, Card.PRIEST,
    Card.BARON, Card.BARON,
    Card.HANDMAID, Card.HANDMAID,
    Card.PRINCE, Card.PRINCE,
    Card.KING,
    Card.COUNTESS,
    Card.PRINCESS
]