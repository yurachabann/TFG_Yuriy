from abc import ABC, abstractmethod
from typing import Generic

from generic.game_state import GameState
from generic.forward_model import S


class Heuristic(ABC, Generic[S]):

    @abstractmethod
    def evaluate(self, state: S, ai_player: int) -> float:
        pass