from __future__ import annotations

from typing import Optional

from .constants import (
    EMPTY,
    P1_MAN,
    P2_MAN,
    P1_KING,
    P2_KING,
)


def owner_of(piece: int) -> Optional[int]:
    """
    Devuelve a qué jugador pertenece una pieza.

    Ejemplos:
    - P1_MAN o P1_KING pertenecen al jugador 1.
    - P2_MAN o P2_KING pertenecen al jugador 2.
    - EMPTY no pertenece a nadie, por eso devuelve None.
    """
    if piece in (P1_MAN, P1_KING):
        return 1

    if piece in (P2_MAN, P2_KING):
        return 2

    return None


def is_king(piece: int) -> bool:
    """
    Devuelve True si la pieza es una dama coronada.

    - P1_KING representa una dama del jugador 1.
    - P2_KING representa una dama del jugador 2.
    """
    return piece in (P1_KING, P2_KING)


def belongs_to_player(piece: int, player: int) -> bool:
    """
    Comprueba si una pieza pertenece a un jugador concreto.
    """
    return owner_of(piece) == player


def belongs_to_opponent(piece: int, player: int) -> bool:
    """
    Comprueba si una pieza pertenece al rival del jugador dado.

    Si la casilla está vacía, owner_of(piece) devuelve None,
    así que no cuenta como rival.
    """
    piece_owner = owner_of(piece)
    return piece_owner is not None and piece_owner != player


def other_player(player: int) -> int:
    """
    Devuelve el jugador contrario.

    Si player es 1, devuelve 2.
    Si player es 2, devuelve 1.
    """
    return 1 if player == 2 else 2