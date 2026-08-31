from generic.heuristic import Heuristic
from juegos.battleship.game_state import BattleshipGameState, SHIP_SIZES


class BattleshipHeuristic(
    Heuristic[BattleshipGameState]
):

    def __init__(
        self,
        hit_weight: float = 0.65,
        sunk_ship_weight: float = 0.25,
        near_sunk_weight: float = 0.10
    ):
        # Peso principal: diferencia entre partes de barcos acertadas por ambos jugadores.
        self.hit_weight = hit_weight

        # Peso adicional por barcos completamente hundidos.
        self.sunk_ship_weight = sunk_ship_weight

        # Peso adicional por barcos enemigos que están a un único impacto de hundirse.
        self.near_sunk_weight = near_sunk_weight

    def evaluate(
        self,
        state: BattleshipGameState,
        ai_player: int
    ) -> float:
        """
        Evalúa un estado no terminal de Battleship desde la perspectiva
        de ai_player.

        La puntuación final se mantiene en el rango [-0.99, 0.99] para
        reservar +1.0 y -1.0 a las victorias y derrotas terminales reales.
        """
        opponent = 1 if ai_player == 2 else 2

        # Seguridad adicional por si la heurística recibe accidentalmente
        # un estado terminal. El ISMCTS normalmente usa terminal_reward()
        # antes de llegar aquí.
        if state.is_terminal:
            if state.winner is None:
                return 0.0
            return 0.99 if state.winner == ai_player else -0.99

        my_ship_positions = (
            set().union(*state.ships[ai_player])
            if state.ships[ai_player]
            else set()
        )

        enemy_ship_positions = (
            set().union(*state.ships[opponent])
            if state.ships[opponent]
            else set()
        )

        # ============================================================
        # 1. DAÑO REALIZADO Y RECIBIDO
        # ============================================================
        my_hits = state.shots[ai_player].intersection(
            enemy_ship_positions
        )

        opponent_hits = state.shots[opponent].intersection(
            my_ship_positions
        )

        total_ship_cells = sum(SHIP_SIZES)

        hit_balance = (
            (len(my_hits) / total_ship_cells)
            - (len(opponent_hits) / total_ship_cells)
        )

        # ============================================================
        # 2. BARCOS HUNDIDOS
        # ============================================================
        enemy_sunk_ships = sum(
            1
            for ship in state.ships[opponent]
            if ship.issubset(state.shots[ai_player])
        )

        my_sunk_ships = sum(
            1
            for ship in state.ships[ai_player]
            if ship.issubset(state.shots[opponent])
        )

        total_ships = len(SHIP_SIZES)

        sunk_ship_balance = (
            (enemy_sunk_ships / total_ships)
            - (my_sunk_ships / total_ships)
        )

        # ============================================================
        # 3. BARCOS A UN IMPACTO DE SER HUNDIDOS
        # ============================================================
        enemy_near_sunk = self.count_near_sunk_ships(
            state.ships[opponent],
            state.shots[ai_player]
        )

        my_near_sunk = self.count_near_sunk_ships(
            state.ships[ai_player],
            state.shots[opponent]
        )

        near_sunk_balance = (
            (enemy_near_sunk / total_ships)
            - (my_near_sunk / total_ships)
        )

        # ============================================================
        # 4. PUNTUACIÓN FINAL
        # ============================================================
        score = (
            hit_balance * self.hit_weight
            + sunk_ship_balance * self.sunk_ship_weight
            + near_sunk_balance * self.near_sunk_weight
        )

        # La recompensa terminal del ISMCTS utiliza +1 / -1.
        # Por eso la heurística nunca debe alcanzar esos valores.
        return max(-0.99, min(0.99, score))

    def count_near_sunk_ships(
        self,
        ships,
        shots
    ) -> int:
        near_sunk = 0

        for ship in ships:
            hits_on_ship = len(ship.intersection(shots))

            # Solo cuenta barcos todavía vivos a los que les falta
            # exactamente un impacto para hundirse.
            if hits_on_ship == len(ship) - 1:
                near_sunk += 1

        return near_sunk
