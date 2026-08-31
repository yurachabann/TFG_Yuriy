from __future__ import annotations

from abc import ABC, abstractmethod


class Game(ABC):
    """
    - Crear el estado inicial
    - Crear el modelo del juego (forward model)
    - Leer el movimiento del humano
    - Convertir un movimiento a una acción del dominio
    - Imprimir el tablero
    - Opcionalmente imprimir la acción elegida por una IA
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def create_state(self):
        pass

    @abstractmethod
    def create_model(self):
        pass

    @abstractmethod
    def read_human_move(self, state):
        pass

    @abstractmethod
    def create_action_from_move(self, move, player_id: int):
        pass

    @abstractmethod
    def print_board(self, state):
        pass

    def print_ai_action(self, action):
        pass