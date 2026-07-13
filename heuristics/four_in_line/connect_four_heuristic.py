# heuristics/four_in_line/combined_heuristic.py

from generic.heuristic import Heuristic
from juegos.four_in_line.four_in_line import ConnectFourGameState


class ConnectFourHeuristic(
    Heuristic[ConnectFourGameState]
):

    def evaluate(
        self,
        state: ConnectFourGameState,
        ai_player: int
    ) -> float:
        opponent = 1 if ai_player == 2 else 2
        score = 0

        # Control del centro
        center_col = state.width // 2
        center_values = [
            state.get(center_col, y)
            for y in range(state.height)
        ]

        score += center_values.count(ai_player) * 6
        score -= center_values.count(opponent) * 6

        # Horizontales
        for y in range(state.height):
            for x in range(state.width - 3):
                window = [
                    state.get(x + i, y)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    window,
                    ai_player,
                    opponent
                )

        # Verticales
        for x in range(state.width):
            for y in range(state.height - 3):
                window = [
                    state.get(x, y + i)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    window,
                    ai_player,
                    opponent
                )

        # Diagonales hacia abajo
        for x in range(state.width - 3):
            for y in range(state.height - 3):
                window = [
                    state.get(x + i, y + i)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    window,
                    ai_player,
                    opponent
                )

        # Diagonales hacia arriba
        for x in range(state.width - 3):
            for y in range(3, state.height):
                window = [
                    state.get(x + i, y - i)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    window,
                    ai_player,
                    opponent
                )

        return score

    def evaluate_window(
        self,
        window: list[int],
        ai_player: int,
        opponent: int
    ) -> float:
        score = 0

        ai_count = window.count(ai_player)
        opponent_count = window.count(opponent)
        empty_count = window.count(0)

        if ai_count == 4:
            score += 10000
        elif ai_count == 3 and empty_count == 1:
            score += 100
        elif ai_count == 2 and empty_count == 2:
            score += 10

        if opponent_count == 4:
            score -= 10000
        elif opponent_count == 3 and empty_count == 1:
            score -= 120
        elif opponent_count == 2 and empty_count == 2:
            score -= 12

        return score