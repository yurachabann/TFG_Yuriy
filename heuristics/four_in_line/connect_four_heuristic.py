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

        # ============================================================
        # CONTROL DEL CENTRO
        # ============================================================
        # En 4 en raya las columnas centrales son más importantes
        # porque una ficha situada cerca del centro puede formar
        # combinaciones horizontales y diagonales en más direcciones.
        center_col = state.width // 2

        for x in range(state.width):
            distance = abs(center_col - x)
            column_value = max(0, 4 - distance)

            for y in range(state.height):
                value = state.get(x, y)

                if value == ai_player:
                    score += column_value * 2
                elif value == opponent:
                    score -= column_value * 2

        # ============================================================
        # VENTANAS HORIZONTALES
        # ============================================================
        for y in range(state.height):
            for x in range(state.width - 3):
                positions = [
                    (x + i, y)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    state,
                    positions,
                    ai_player,
                    opponent
                )

        # ============================================================
        # VENTANAS VERTICALES
        # ============================================================
        for x in range(state.width):
            for y in range(state.height - 3):
                positions = [
                    (x, y + i)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    state,
                    positions,
                    ai_player,
                    opponent
                )

        # ============================================================
        # DIAGONALES HACIA ABAJO
        # ============================================================
        for x in range(state.width - 3):
            for y in range(state.height - 3):
                positions = [
                    (x + i, y + i)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    state,
                    positions,
                    ai_player,
                    opponent
                )

        # ============================================================
        # DIAGONALES HACIA ARRIBA
        # ============================================================
        for x in range(state.width - 3):
            for y in range(3, state.height):
                positions = [
                    (x + i, y - i)
                    for i in range(4)
                ]

                score += self.evaluate_window(
                    state,
                    positions,
                    ai_player,
                    opponent
                )

        # ============================================================
        # AMENAZAS INMEDIATAS
        # ============================================================
        # Se cuentan los movimientos que permitirían ganar
        # inmediatamente a cada jugador.
        ai_winning_moves = self.count_winning_moves(
            state,
            ai_player
        )

        opponent_winning_moves = self.count_winning_moves(
            state,
            opponent
        )

        # Una victoria disponible en el siguiente movimiento
        # debe tener muchísimo peso.
        score += ai_winning_moves * 1500
        score -= opponent_winning_moves * 1800

        # Una doble amenaza es especialmente importante:
        # si existen dos movimientos ganadores diferentes,
        # el rival normalmente no puede bloquear ambos.
        if ai_winning_moves >= 2:
            score += 6000

        if opponent_winning_moves >= 2:
            score -= 7000

        return score

    def evaluate_window(
        self,
        state: ConnectFourGameState,
        positions: list[tuple[int, int]],
        ai_player: int,
        opponent: int
    ) -> float:
        score = 0

        window = [
            state.get(x, y)
            for x, y in positions
        ]

        ai_count = window.count(ai_player)
        opponent_count = window.count(opponent)
        empty_count = window.count(0)

        # Una ventana que contiene fichas de ambos jugadores
        # no puede convertirse directamente en una línea de cuatro.
        if ai_count > 0 and opponent_count > 0:
            return 0

        playable_empty_count = 0

        for x, y in positions:
            if state.get(x, y) == 0 and self.is_playable_cell(
                state,
                x,
                y
            ):
                playable_empty_count += 1

        # ============================================================
        # PATRONES DEL JUGADOR IA
        # ============================================================
        if ai_count == 4:
            score += 10000

        elif ai_count == 3 and empty_count == 1:
            # Si el hueco se puede jugar ahora mismo,
            # estamos ante una amenaza inmediata real.
            if playable_empty_count == 1:
                score += 500
            else:
                score += 80

        elif ai_count == 2 and empty_count == 2:
            if playable_empty_count >= 1:
                score += 25
            else:
                score += 8

        elif ai_count == 1 and empty_count == 3:
            score += 2

        # ============================================================
        # PATRONES DEL RIVAL
        # ============================================================
        if opponent_count == 4:
            score -= 10000

        elif opponent_count == 3 and empty_count == 1:
            # Se penalizan ligeramente más las amenazas inmediatas
            # del rival para favorecer el bloqueo.
            if playable_empty_count == 1:
                score -= 600
            else:
                score -= 90

        elif opponent_count == 2 and empty_count == 2:
            if playable_empty_count >= 1:
                score -= 30
            else:
                score -= 10

        elif opponent_count == 1 and empty_count == 3:
            score -= 2

        return score

    def is_playable_cell(
        self,
        state: ConnectFourGameState,
        x: int,
        y: int
    ) -> bool:
        # La casilla debe estar vacía.
        if state.get(x, y) != 0:
            return False

        # Una casilla de la fila inferior siempre es jugable.
        if y == state.height - 1:
            return True

        # Para cualquier otra fila debe existir una ficha
        # inmediatamente debajo debido a la gravedad.
        return state.get(x, y + 1) != 0

    def count_winning_moves(
        self,
        state: ConnectFourGameState,
        player: int
    ) -> int:
        winning_moves = 0

        for x in range(state.width):
            y = self.get_drop_row(state, x)

            if y is None:
                continue

            test_state = state.clone()
            test_state.set(x, y, player)

            if self.has_four_from_cell(
                test_state,
                player,
                x,
                y
            ):
                winning_moves += 1

        return winning_moves

    def get_drop_row(
        self,
        state: ConnectFourGameState,
        x: int
    ):
        for y in range(state.height - 1, -1, -1):
            if state.get(x, y) == 0:
                return y

        return None

    def has_four_from_cell(
        self,
        state: ConnectFourGameState,
        player: int,
        x: int,
        y: int
    ) -> bool:
        directions = [
            (1, 0),
            (0, 1),
            (1, 1),
            (1, -1)
        ]

        for dx, dy in directions:
            count = 1

            nx = x + dx
            ny = y + dy

            while (
                0 <= nx < state.width
                and 0 <= ny < state.height
                and state.get(nx, ny) == player
            ):
                count += 1
                nx += dx
                ny += dy

            nx = x - dx
            ny = y - dy

            while (
                0 <= nx < state.width
                and 0 <= ny < state.height
                and state.get(nx, ny) == player
            ):
                count += 1
                nx -= dx
                ny -= dy

            if count >= 4:
                return True

        return False