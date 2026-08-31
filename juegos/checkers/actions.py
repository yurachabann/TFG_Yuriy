from __future__ import annotations

from dataclasses import dataclass

from generic.game_action import GameAction

@dataclass
class MovePieceAction(GameAction):
    """
    Ejemplo de movimiento normal:
        path = [(2, 5), (3, 4)]

    Ejemplo de captura simple:
        path = [(2, 5), (4, 3)]

    Ejemplo de captura múltiple:
        path = [(2, 5), (4, 3), (6, 1)]

    """
    path: list[tuple[int, int]]
    player: int

    def is_capture(self) -> bool:
        """
        Devuelve True si la acción contiene al menos un salto de captura.

        En esta versión una captura se detecta porque la pieza se mueve
        dos casillas en diagonal:
            abs(dx) == 2 and abs(dy) == 2
        """
        if len(self.path) < 2:
            return False

        for i in range(len(self.path) - 1):
            x1, y1 = self.path[i]
            x2, y2 = self.path[i + 1]

            if abs(x2 - x1) == 2 and abs(y2 - y1) == 2:
                return True

        return False