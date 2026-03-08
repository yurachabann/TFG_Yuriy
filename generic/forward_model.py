from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List

from .game_state import GameState #dentro d misma carpeta
from .game_action import GameAction

S = TypeVar("S", bound=GameState) #S solo puede ser GameState o una clase que herede de GameState.
A = TypeVar("A", bound=GameAction) #typevar = tipo generico

class ForwardModel(ABC, Generic[S, A]):
    @abstractmethod
    def compute_available_actions(self, state: S) -> list[A]:
        pass

    @abstractmethod
    def advance(self, state: S, action: A) -> None:
        pass

    @abstractmethod
    def evaluate_terminal(self, state: S, ai_player: int, depth: int) -> int:
        pass