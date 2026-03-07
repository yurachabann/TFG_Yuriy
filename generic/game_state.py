from abc import ABC, abstractmethod
from typing import Optional

class GameState(ABC):

    def __init__(self):
        self.current_player: int = 1
        self.is_terminal: bool = False
        self.winner: Optional[int] = None

    @abstractmethod
    def clone(self):
        pass