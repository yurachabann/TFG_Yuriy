from dataclasses import dataclass
from typing import Optional

from generic.game_state import GameState
from generic.game_action import GameAction
from generic.forward_model import ForwardModel

EMPTY = "."
WHITE = 1
BLACK = 2
PAWN = "P"
KNIGHT = "N"
BISHOP = "B"
ROOK = "R"
QUEEN = "Q"
KING = "K"

WHITE_PIECES = {
    PAWN: "♙",
    KNIGHT: "♘",
    BISHOP: "♗",
    ROOK: "♖",
    QUEEN: "♕",
    KING: "♔"
}

BLACK_PIECES = {
    PAWN: "♟",
    KNIGHT: "♞",
    BISHOP: "♝",
    ROOK: "♜",
    QUEEN: "♛",
    KING: "♚"
}


def other_player(player: int) -> int:
    return WHITE if player == BLACK else BLACK


def player_label(player: int) -> str:
    """
    Devuelve el nombre visible del jugador.

    En el modo Humano vs IA:
    - el jugador 1 controla las piezas blancas
    - el jugador 2 controla las piezas negras
    """
    if player == WHITE:
        return "Jugador 1 (Humano - Blancas)"

    return "Jugador 2 (IA - Negras)"


def make_piece(player: int, kind: str) -> str:
    return ("w" if player == WHITE else "b") + kind


def piece_player(piece: str) -> Optional[int]:
    if piece == EMPTY:
        return None

    return WHITE if piece[0] == "w" else BLACK


def piece_type(piece: str) -> Optional[str]:
    return None if piece == EMPTY else piece[1]


def piece_symbol(piece: str) -> str:
    if piece == EMPTY:
        return EMPTY

    symbols = (
        WHITE_PIECES
        if piece_player(piece) == WHITE
        else BLACK_PIECES
    )

    return symbols[piece_type(piece)]


@dataclass
class SimpleChessGameState(GameState):
    """Estado del ajedrez simplificado."""

    board: Optional[list[str]] = None
    current_player: int = WHITE
    is_terminal: bool = False
    winner: Optional[int] = None

    def __post_init__(self):
        if self.board is None:
            self.board = self.create_initial_board()

    def create_initial_board(self) -> list[str]:
        board = [EMPTY] * 64

        back_rank = [
            ROOK,
            KNIGHT,
            BISHOP,
            QUEEN,
            KING,
            BISHOP,
            KNIGHT,
            ROOK
        ]

        for x, kind in enumerate(back_rank):
            board[self.index(x, 0)] = make_piece(BLACK, kind)
            board[self.index(x, 7)] = make_piece(WHITE, kind)

        for x in range(8):
            board[self.index(x, 1)] = make_piece(BLACK, PAWN)
            board[self.index(x, 6)] = make_piece(WHITE, PAWN)

        return board

    def clone(self):
        return SimpleChessGameState(
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner
        )

    def index(self, x: int, y: int) -> int:
        return y * 8 + x

    def get(self, x: int, y: int) -> str:
        return self.board[self.index(x, y)]

    def set(self, x: int, y: int, value: str):
        self.board[self.index(x, y)] = value

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < 8 and 0 <= y < 8


@dataclass
class MovePieceAction(GameAction):
    from_x: int
    from_y: int
    to_x: int
    to_y: int
    player: int


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

    WIN_SCORE = 100000

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

        player = state.current_player
        pseudo_actions = self.compute_pseudo_legal_actions(
            state,
            player
        )

        legal_actions = []

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

    def find_king(
        self,
        state: SimpleChessGameState,
        player: int
    ) -> Optional[tuple[int, int]]:
        """
        Busca el rey de un jugador y devuelve sus coordenadas.
        """
        expected_king = make_piece(player, KING)

        for y in range(8):
            for x in range(8):
                if state.get(x, y) == expected_king:
                    return x, y

        return None

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

        legal_actions = self.compute_available_actions(state)

        if action not in legal_actions:
            raise ValueError(
                f"Movimiento no válido: {action}"
            )

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

        self.apply_action_without_validation(
            state,
            action,
            change_turn=True
        )

        # Se calculan las respuestas legales del siguiente jugador.
        next_actions = self.compute_available_actions(state)

        if next_actions:
            return

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


def print_board(state: SimpleChessGameState):
    print()
    print("=== AJEDREZ SIMPLIFICADO ===")
    print(
        "Jugador actual:",
        player_label(state.current_player)
    )
    print()
    print("Jugador 1 (Humano): Blancas ♙")
    print("Jugador 2 (IA): Negras ♟")

    # Se informa cuando el jugador actual debe responder a un jaque.
    model = SimpleChessForwardModel()

    if model.is_king_attacked(
        state,
        state.current_player
    ):
        print(
            "JAQUE:",
            player_label(state.current_player),
            "debe proteger su rey."
        )

    print()
    print("    a  b  c  d  e  f  g  h")

    for y in range(8):
        rank = 8 - y
        print(f"{rank} |", end=" ")

        for x in range(8):
            print(
                piece_symbol(state.get(x, y)),
                end="  "
            )

        print(f"| {rank}")

    print("    a  b  c  d  e  f  g  h")
    print()


def parse_square(square: str) -> tuple[int, int]:
    square = square.strip().lower()

    if (
        len(square) != 2
        or square[0] not in "abcdefgh"
        or square[1] not in "12345678"
    ):
        raise ValueError("Casilla inválida.")

    return (
        ord(square[0]) - ord("a"),
        8 - int(square[1])
    )


def square_name(x: int, y: int) -> str:
    return f"{chr(ord('a') + x)}{8 - y}"


def read_human_move(state: SimpleChessGameState):
    model = SimpleChessForwardModel()
    actions = model.compute_available_actions(state)

    while True:
        try:
            origin, destination = input(
                "Movimiento del Jugador 1 "
                "(Humano - Blancas), ejemplo e2 e4: "
            ).split()

            from_x, from_y = parse_square(origin)
            to_x, to_y = parse_square(destination)

        except ValueError:
            print(
                "Formato inválido. "
                "Ejemplo correcto: e2 e4"
            )
            continue

        action = MovePieceAction(
            from_x,
            from_y,
            to_x,
            to_y,
            state.current_player
        )

        if action not in actions:
            print("Movimiento no permitido.")
            continue

        return from_x, from_y, to_x, to_y