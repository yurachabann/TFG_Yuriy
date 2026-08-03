from dataclasses import dataclass
from typing import Optional

from generic.game_state import GameState


@dataclass
class ConnectFourGameState(GameState):
    width: int = 7
    height: int = 6
    board: Optional[list[int]] = None
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None

    def __post_init__(self):
        if self.board is None:
            self.board = [0] * (self.width * self.height)

    def clone(self):
        return ConnectFourGameState(
            width=self.width,
            height=self.height,
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner
        )

    def get(self, x: int, y: int) -> int:
        return self.board[y * self.width + x]

    def set(self, x: int, y: int, value: int) -> None:
        self.board[y * self.width + x] = value