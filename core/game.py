from __future__ import annotations

from abc import ABC, abstractmethod


class Game(ABC):
    """
    Clase base abstracta para cualquier juego.

    Esta clase sustituye la idea anterior de usar un diccionario GAME.
    Ahora cada juego concreto (por ejemplo TicTacToeGame o Connect4Game)
    heredará de Game e implementará estos métodos.

    Responsabilidades de Game:
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
        """
        Debe crear y devolver el estado inicial del juego.
        """
        pass

    @abstractmethod
    def create_model(self):
        """
        Debe crear y devolver el forward model del juego.
        """
        pass

    @abstractmethod
    def read_human_move(self, state):
        """
        Debe leer un movimiento válido introducido por un humano.
        Ejemplo en 3 en raya: devuelve (x, y)
        """
        pass

    @abstractmethod
    def create_action_from_move(self, move, player_id: int):
        """
        Convierte el movimiento leído desde la interfaz humana
        en una acción del dominio del juego.
        """
        pass

    @abstractmethod
    def print_board(self, state):
        """
        Muestra el tablero por consola.
        """
        pass

    def print_ai_action(self, action):
        """
        Método opcional.
        Si un juego quiere mostrar cómo juega la IA, puede sobrescribirlo.
        """
        pass