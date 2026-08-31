from __future__ import annotations

from abc import ABC, abstractmethod


class Player(ABC):
    """
    Clase base abstracta para cualquier tipo de jugador.

    Atributos:
    - name: nombre visible del jugador
    - player_id: identificador del jugador (normalmente 1 o 2)
    """

    def __init__(self, name: str, player_id: int):
        self.name = name
        self.player_id = player_id

    @abstractmethod
    def choose_action(self, state, game):
        """
        Debe devolver una tupla:
            (action, stats)

        - HumanPlayer devolverá (action, None)
        - AIPlayer devolverá (action, stats)
        """
        pass

    def is_human(self) -> bool:
        return False

    def is_ai(self) -> bool:
        return False