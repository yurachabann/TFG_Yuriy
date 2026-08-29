from .game_state import SimpleChessGameState
from .actions import MovePieceAction

from generic.forward_model import ForwardModel
from .helpers import piece_player, make_piece, piece_type, other_player
from .constants import KING, QUEEN, PAWN, BISHOP, KNIGHT, WHITE, BLACK, EMPTY, ROOK
from typing import Optional


class SimpleChessForwardModel(
    ForwardModel[SimpleChessGameState, MovePieceAction]
):
    """
    Ajedrez simplificado:
    - incluye detección básica de jaque
    - no permite movimientos que dejan al propio rey atacado
    - incluye jaque mate y ahogado básicos
    - sin enroque
    - sin captura al paso
    - promoción automática a dama
    """

    # Valor terminal suficientemente alto para dominar la heurística.
    WIN_SCORE = 100000
    MAX_MOVES_WITHOUT_PROGRESS = 20


    # Genera únicamente los movimientos verdaderamente legales.
    def compute_available_actions(
        self,
        state: SimpleChessGameState
    ) -> list[MovePieceAction]:
        """
        Devuelve únicamente movimientos legales.

        Primero genera movimientos pseudolegales según la forma de mover
        de cada pieza. Después simula cada acción y elimina las que dejan
        al rey del jugador actual bajo ataque.
        """
        if state.is_terminal:
            return []

        # El jugador activo es el único para quien se generan acciones.
        player = state.current_player

        # Primero se obtienen todos los movimientos permitidos por la pieza.
        pseudo_actions = self.compute_pseudo_legal_actions(
            state,
            player
        )

        # Aquí se guardarán solamente los movimientos que no dejan
        # al propio rey en jaque.
        legal_actions = []

        # Cada movimiento se prueba sobre una copia del estado.
        for action in pseudo_actions:
            next_state = state.clone()

            # Se aplica la acción sin volver a validar, porque estamos
            # comprobando precisamente si la acción debe ser legal.
            self.apply_action_without_validation(
                next_state,
                action,
                change_turn=False
            )

            # Una acción es legal si después de realizarla
            # el propio rey continúa existiendo y no está atacado.
            if (
                self.find_king(next_state, player) is not None
                and not self.is_king_attacked(next_state, player)
            ):
                legal_actions.append(action)

        return legal_actions


    # Genera movimientos válidos por geometría de pieza, pero todavía
    # no comprueba si el propio rey queda expuesto.
    def compute_pseudo_legal_actions(
        self,
        state: SimpleChessGameState,
        player: int
    ) -> list[MovePieceAction]:
        """
        Genera movimientos según las reglas de movimiento de las piezas,
        pero todavía no comprueba si el propio rey queda en jaque.
        """
        actions = []

        # Las funciones existentes utilizan state.current_player.
        # Se conserva su valor para no modificar permanentemente el estado.
        original_player = state.current_player
        state.current_player = player

        try:
            for y in range(8):
                for x in range(8):
                    piece = state.get(x, y)

                    if piece_player(piece) == player:
                        actions.extend(
                            self.get_piece_actions(
                                state,
                                x,
                                y,
                                piece
                            )
                        )
        finally:
            state.current_player = original_player

        return actions


    # Localiza el rey de un jugador dentro del tablero.
    def find_king(
        self,
        state: SimpleChessGameState,
        player: int
    ) -> Optional[tuple[int, int]]:
        """
        Busca el rey de un jugador y devuelve sus coordenadas.
        """
        # Construye exactamente el código interno del rey buscado.
        expected_king = make_piece(player, KING)

        for y in range(8):
            for x in range(8):
                if state.get(x, y) == expected_king:
                    return x, y

        return None


    # Comprueba si una casilla está atacada por alguna pieza rival.
    def is_square_attacked(
        self,
        state: SimpleChessGameState,
        target_x: int,
        target_y: int,
        attacker: int
    ) -> bool:
        """
        Comprueba si una casilla está atacada por un jugador.

        Se comprueban directamente los patrones de ataque para evitar
        llamar a compute_available_actions y producir recursión infinita.
        """
        # Ataques de peón.
        pawn_direction = -1 if attacker == WHITE else 1
        pawn_source_y = target_y - pawn_direction

        for pawn_source_x in (target_x - 1, target_x + 1):
            if (
                state.inside(pawn_source_x, pawn_source_y)
                and state.get(pawn_source_x, pawn_source_y)
                == make_piece(attacker, PAWN)
            ):
                return True

        # Ataques de caballo.
        knight_offsets = [
            (-2, -1),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 1)
        ]

        for dx, dy in knight_offsets:
            source_x = target_x - dx
            source_y = target_y - dy

            if (
                state.inside(source_x, source_y)
                and state.get(source_x, source_y)
                == make_piece(attacker, KNIGHT)
            ):
                return True

        # Ataques del rey rival a una casilla contigua.
        king_offsets = [
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1)
        ]

        for dx, dy in king_offsets:
            source_x = target_x - dx
            source_y = target_y - dy

            if (
                state.inside(source_x, source_y)
                and state.get(source_x, source_y)
                == make_piece(attacker, KING)
            ):
                return True

        # Ataques diagonales de alfil y dama.
        diagonal_directions = [
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1)
        ]

        for dx, dy in diagonal_directions:
            x = target_x + dx
            y = target_y + dy

            while state.inside(x, y):
                piece = state.get(x, y)

                if piece != EMPTY:
                    if (
                        piece_player(piece) == attacker
                        and piece_type(piece) in (BISHOP, QUEEN)
                    ):
                        return True

                    break

                x += dx
                y += dy

        # Ataques rectos de torre y dama.
        straight_directions = [
            (0, -1),
            (0, 1),
            (-1, 0),
            (1, 0)
        ]

        for dx, dy in straight_directions:
            x = target_x + dx
            y = target_y + dy

            while state.inside(x, y):
                piece = state.get(x, y)

                if piece != EMPTY:
                    if (
                        piece_player(piece) == attacker
                        and piece_type(piece) in (ROOK, QUEEN)
                    ):
                        return True

                    break

                x += dx
                y += dy

        return False


    # Comprueba si el rey del jugador indicado está actualmente en jaque.
    def is_king_attacked(
        self,
        state: SimpleChessGameState,
        player: int
    ) -> bool:
        """
        Indica si el rey de un jugador está actualmente en jaque.
        """
        king_position = self.find_king(state, player)

        if king_position is None:
            return True

        king_x, king_y = king_position

        return self.is_square_attacked(
            state,
            king_x,
            king_y,
            other_player(player)
        )


    # Delega la generación de movimientos según el tipo de pieza.
    def get_piece_actions(self, state, x, y, piece):
        kind = piece_type(piece)

        if kind == PAWN:
            return self.get_pawn_actions(state, x, y)

        if kind == KNIGHT:
            return self.get_step_actions(
                state,
                x,
                y,
                [
                    (-2, -1),
                    (-2, 1),
                    (-1, -2),
                    (-1, 2),
                    (1, -2),
                    (1, 2),
                    (2, -1),
                    (2, 1)
                ]
            )

        if kind == KING:
            return self.get_step_actions(
                state,
                x,
                y,
                [
                    (-1, -1),
                    (0, -1),
                    (1, -1),
                    (-1, 0),
                    (1, 0),
                    (-1, 1),
                    (0, 1),
                    (1, 1)
                ]
            )

        if kind == BISHOP:
            return self.get_sliding_actions(
                state,
                x,
                y,
                [
                    (-1, -1),
                    (1, -1),
                    (-1, 1),
                    (1, 1)
                ]
            )

        if kind == ROOK:
            return self.get_sliding_actions(
                state,
                x,
                y,
                [
                    (0, -1),
                    (0, 1),
                    (-1, 0),
                    (1, 0)
                ]
            )

        if kind == QUEEN:
            return self.get_sliding_actions(
                state,
                x,
                y,
                [
                    (-1, -1),
                    (1, -1),
                    (-1, 1),
                    (1, 1),
                    (0, -1),
                    (0, 1),
                    (-1, 0),
                    (1, 0)
                ]
            )

        return []


    # Genera avance simple, avance doble inicial y capturas diagonales.
    def get_pawn_actions(self, state, x, y):
        player = state.current_player
        direction = -1 if player == WHITE else 1
        start_row = 6 if player == WHITE else 1
        actions = []

        one_y = y + direction

        if (
            state.inside(x, one_y)
            and state.get(x, one_y) == EMPTY
        ):
            actions.append(
                MovePieceAction(
                    x,
                    y,
                    x,
                    one_y,
                    player
                )
            )

            two_y = y + 2 * direction

            if (
                y == start_row
                and state.get(x, two_y) == EMPTY
            ):
                actions.append(
                    MovePieceAction(
                        x,
                        y,
                        x,
                        two_y,
                        player
                    )
                )

        for dx in (-1, 1):
            tx = x + dx
            ty = y + direction

            if not state.inside(tx, ty):
                continue

            target = state.get(tx, ty)

            if (
                target != EMPTY
                and piece_player(target) == other_player(player)
            ):
                actions.append(
                    MovePieceAction(
                        x,
                        y,
                        tx,
                        ty,
                        player
                    )
                )

        return actions


    # Genera movimientos de salto o de una casilla usando desplazamientos.
    # Se usa para caballo y rey.
    def get_step_actions(self, state, x, y, offsets):
        player = state.current_player
        actions = []

        for dx, dy in offsets:
            tx = x + dx
            ty = y + dy

            if not state.inside(tx, ty):
                continue

            if piece_player(state.get(tx, ty)) != player:
                actions.append(
                    MovePieceAction(
                        x,
                        y,
                        tx,
                        ty,
                        player
                    )
                )

        return actions


    # Genera movimientos deslizantes para alfil, torre y dama.
    # La pieza avanza en una dirección hasta encontrar un obstáculo.
    def get_sliding_actions(
        self,
        state,
        x,
        y,
        directions
    ):
        player = state.current_player
        actions = []

        for dx, dy in directions:
            tx = x + dx
            ty = y + dy

            while state.inside(tx, ty):
                target = state.get(tx, ty)

                if target == EMPTY:
                    actions.append(
                        MovePieceAction(
                            x,
                            y,
                            tx,
                            ty,
                            player
                        )
                    )

                elif piece_player(target) == other_player(player):
                    actions.append(
                        MovePieceAction(
                            x,
                            y,
                            tx,
                            ty,
                            player
                        )
                    )
                    break

                else:
                    break

                tx += dx
                ty += dy

        return actions


    # Aplica una jugada de forma interna sin recalcular su legalidad.
    # Es necesaria para simular posibles movimientos durante el jaque.
    def apply_action_without_validation(
        self,
        state: SimpleChessGameState,
        action: MovePieceAction,
        change_turn: bool = True
    ) -> None:
        """
        Aplica físicamente una acción sin comprobar si es legal.

        Este método se utiliza internamente para simular movimientos
        al comprobar si el rey queda en jaque.
        """
        # Se recupera la pieza antes de vaciar su casilla de origen.
        moving_piece = state.get(
            action.from_x,
            action.from_y
        )

        state.set(
            action.from_x,
            action.from_y,
            EMPTY
        )

        state.set(
            action.to_x,
            action.to_y,
            moving_piece
        )

        # Promoción automática a dama.
        if piece_type(moving_piece) == PAWN:
            if (
                action.player == WHITE
                and action.to_y == 0
            ):
                state.set(
                    action.to_x,
                    action.to_y,
                    make_piece(WHITE, QUEEN)
                )

            elif (
                action.player == BLACK
                and action.to_y == 7
            ):
                state.set(
                    action.to_x,
                    action.to_y,
                    make_piece(BLACK, QUEEN)
                )

        if change_turn:
            state.current_player = other_player(
                state.current_player
            )


    # Aplica una acción legal al estado real y comprueba el final.
    def advance(
        self,
        state: SimpleChessGameState,
        action: MovePieceAction
    ) -> None:
        """
        Aplica un movimiento legal y actualiza jaque mate o ahogado.
        """
        if state.is_terminal:
            return

        if action.player != state.current_player:
            raise ValueError("Turno inválido.")

        # El rey no se captura directamente.
        # La partida termina cuando está en jaque y no tiene defensa legal.
        target_piece = state.get(
            action.to_x,
            action.to_y
        )

        if piece_type(target_piece) == KING:
            raise ValueError(
                "El rey no se captura directamente. "
                "La partida termina por jaque mate."
            )

        moving_piece = state.get(
            action.from_x,
            action.from_y
        )

        # Una vez validada, la acción puede aplicarse al estado real.
        self.apply_action_without_validation(
            state,
            action,
            change_turn=True
        )

        if target_piece != EMPTY or piece_type(moving_piece) == PAWN:
            state.moves_without_progress = 0
        else:
            state.moves_without_progress += 1

        # Se calculan las respuestas legales del siguiente jugador.
        next_actions = self.compute_available_actions(state)

        if not next_actions:
            # Sin movimientos legales:
            # - si el rey está atacado, es jaque mate;
            # - si no está atacado, es ahogado.
            if self.is_king_attacked(
                state,
                state.current_player
            ):
                state.is_terminal = True
                state.winner = other_player(
                    state.current_player
                )
            else:
                state.is_terminal = True
                state.winner = None

            return

        if state.moves_without_progress >= self.MAX_MOVES_WITHOUT_PROGRESS:
            state.is_terminal = True
            state.winner = None


    # Convierte victoria, derrota o empate en una puntuación numérica.
    def evaluate_terminal(
        self,
        state: SimpleChessGameState,
        ai_player: int,
        depth: int
    ) -> int:
        if state.winner is None:
            return 0

        if state.winner == ai_player:
            return self.WIN_SCORE - depth

        return -self.WIN_SCORE + depth