from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from generic.game_state import GameState
from generic.game_action import GameAction
from generic.forward_model import ForwardModel


# ============================================================
# CONSTANTES DEL JUEGO
# ============================================================
#
# Guardamos el tablero como una lista de enteros.
# Cada número representa una casilla:
#
# 0 = casilla vacía
# 1 = peón del jugador 1
# 2 = peón del jugador 2
# 3 = dama del jugador 1
# 4 = dama del jugador 2
#
# Visualmente:
# jugador 1 -> x
# jugador 2 -> o
# dama jugador 1 -> X
# dama jugador 2 -> O
# ============================================================

EMPTY = 0

P1_MAN = 1
P2_MAN = 2
P1_KING = 3
P2_KING = 4


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def owner_of(piece: int) -> Optional[int]:
    """
    Devuelve a qué jugador pertenece una pieza.

    Ejemplos:
    - P1_MAN o P1_KING pertenecen al jugador 1.
    - P2_MAN o P2_KING pertenecen al jugador 2.
    - EMPTY no pertenece a nadie, por eso devuelve None.
    """
    if piece in (P1_MAN, P1_KING):
        return 1

    if piece in (P2_MAN, P2_KING):
        return 2

    return None


def is_king(piece: int) -> bool:
    """
    Devuelve True si la pieza es una dama coronada.

    En este juego:
    - P1_KING representa una dama del jugador 1.
    - P2_KING representa una dama del jugador 2.
    """
    return piece in (P1_KING, P2_KING)


def belongs_to_player(piece: int, player: int) -> bool:
    """
    Comprueba si una pieza pertenece a un jugador concreto.
    """
    return owner_of(piece) == player


def belongs_to_opponent(piece: int, player: int) -> bool:
    """
    Comprueba si una pieza pertenece al rival del jugador dado.

    Si la casilla está vacía, owner_of(piece) devuelve None,
    así que no cuenta como rival.
    """
    piece_owner = owner_of(piece)
    return piece_owner is not None and piece_owner != player


def other_player(player: int) -> int:
    """
    Devuelve el jugador contrario.

    Si player es 1, devuelve 2.
    Si player es 2, devuelve 1.
    """
    return 1 if player == 2 else 2


# ============================================================
# GAME STATE
# ============================================================

@dataclass
class CheckersGameState(GameState):
    """
    Estado del juego de damas.

    Sigue la misma idea que tu TicTacToeGameState:
    - guarda el tablero
    - guarda el jugador actual
    - indica si la partida ha terminado
    - guarda el ganador si existe

    Coordenadas:
    - x representa la columna, de 0 a 7.
    - y representa la fila, de 0 a 7.

    Importante:
    - y = 0 es la fila de arriba.
    - y = 7 es la fila de abajo.

    En esta versión:
    - jugador 1 = x empieza abajo.
    - jugador 2 = o empieza arriba.
    - jugador 1 avanza hacia arriba, es decir, y - 1.
    - jugador 2 avanza hacia abajo, es decir, y + 1.

    Así, si tú eres jugador 1, verás tus piezas x abajo.
    """
    size: int = 8
    board: Optional[list[int]] = None
    current_player: int = 1
    is_terminal: bool = False
    winner: Optional[int] = None

    def __post_init__(self):
        """
        Este método se ejecuta automáticamente después de crear el dataclass.

        Si no se ha pasado un tablero concreto, se crea un tablero vacío
        y se colocan las piezas iniciales.
        """
        if self.board is None:
            self.board = [EMPTY] * (self.size * self.size)
            self.setup_initial_board()

    def setup_initial_board(self) -> None:
        """
        Coloca las piezas iniciales.

        Queremos que jugador 1, que es x, aparezca abajo.

        Por tanto:
        - jugador 2 empieza arriba: filas 0, 1, 2.
        - jugador 1 empieza abajo: filas 5, 6, 7.

        Solo se colocan piezas en casillas oscuras.
        En este tablero consideramos casilla oscura si:
            (x + y) % 2 == 1
        """
        # Jugador 2 arriba.
        for y in range(3):
            for x in range(self.size):
                if self.is_dark_square(x, y):
                    self.set(x, y, P2_MAN)

        # Jugador 1 abajo.
        for y in range(5, 8):
            for x in range(self.size):
                if self.is_dark_square(x, y):
                    self.set(x, y, P1_MAN)

    def clone(self) -> "CheckersGameState":
        """
        Devuelve una copia independiente del estado.

        Esto es imprescindible para algoritmos como:
        - Minimax
        - Alpha-Beta
        - MCTS

        Porque esos algoritmos simulan jugadas sin modificar el estado real.
        """
        return CheckersGameState(
            size=self.size,
            board=self.board.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner
        )

    def index(self, x: int, y: int) -> int:
        """
        Convierte coordenadas 2D en índice de lista.

        Ejemplo:
        - tablero 8x8
        - posición (3, 2)
        - índice = 2 * 8 + 3 = 19
        """
        return y * self.size + x

    def inside(self, x: int, y: int) -> bool:
        """
        Comprueba si una coordenada está dentro del tablero.
        """
        return 0 <= x < self.size and 0 <= y < self.size

    def is_dark_square(self, x: int, y: int) -> bool:
        """
        En damas solo se juega en las casillas oscuras.

        Con esta fórmula alternamos las casillas.
        """
        return (x + y) % 2 == 1

    def get(self, x: int, y: int) -> int:
        """
        Devuelve la pieza que hay en una casilla.
        """
        return self.board[self.index(x, y)]

    def set(self, x: int, y: int, value: int) -> None:
        """
        Escribe una pieza en una casilla.
        """
        self.board[self.index(x, y)] = value


# ============================================================
# GAME ACTION
# ============================================================

@dataclass
class MovePieceAction(GameAction):
    """
    Acción del juego de damas.

    En 3 en raya tu acción era:
        SetCellAction(x, y, player)

    En damas necesitamos un camino completo, porque puede haber
    capturas múltiples.

    Ejemplo de movimiento normal:
        path = [(2, 5), (3, 4)]

    Ejemplo de captura simple:
        path = [(2, 5), (4, 3)]

    Ejemplo de captura múltiple:
        path = [(2, 5), (4, 3), (6, 1)]

    player indica quién realiza la acción.
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


# ============================================================
# FORWARD MODEL
# ============================================================

class CheckersForwardModel(ForwardModel[CheckersGameState, MovePieceAction]):
    """
    Motor de reglas del juego de damas.

    Sigue el mismo papel que TicTacToeForwardModel.

    Responsabilidades:
    - generar acciones legales
    - aplicar una acción al estado
    - comprobar fin de partida
    - evaluar terminales para minimax
    - ofrecer heurística para algoritmos con profundidad limitada

    Reglas implementadas:
    - tablero 8x8
    - jugador 1 = x empieza abajo
    - jugador 2 = o empieza arriba
    - peones se mueven una casilla diagonal hacia delante
    - damas se mueven una casilla diagonal en cualquier dirección
    - captura obligatoria
    - captura múltiple
    - coronación al llegar al extremo rival
    - gana quien deja al rival sin piezas o sin movimientos
    """

    def compute_available_actions(self, state: CheckersGameState) -> list[MovePieceAction]:
        """
        Devuelve todas las acciones legales desde el estado actual.

        Regla importante de damas:
        si existe al menos una captura, solo se pueden devolver capturas.

        Por eso primero buscamos capturas.
        Si hay capturas, las devolvemos.
        Si no hay capturas, devolvemos movimientos normales.
        """
        if state.is_terminal:
            return []

        captures: list[MovePieceAction] = []
        normal_moves: list[MovePieceAction] = []

        for y in range(state.size):
            for x in range(state.size):
                piece = state.get(x, y)

                # Solo miramos las piezas del jugador al que le toca.
                if not belongs_to_player(piece, state.current_player):
                    continue

                # Primero buscamos capturas para esta pieza.
                piece_captures = self.compute_captures_for_piece(
                    state=state,
                    x=x,
                    y=y,
                    piece=piece,
                    player=state.current_player
                )

                captures.extend(piece_captures)

                # Solo calculamos movimientos normales si esta pieza no captura.
                # Da igual si otra pieza captura, porque al final si captures no está vacío,
                # se ignorarán todos los movimientos normales.
                if not piece_captures:
                    piece_moves = self.compute_normal_moves_for_piece(
                        state=state,
                        x=x,
                        y=y,
                        piece=piece,
                        player=state.current_player
                    )
                    normal_moves.extend(piece_moves)

        if captures:
            return captures

        return normal_moves

    def advance(self, state: CheckersGameState, action: MovePieceAction) -> None:
        """
        Aplica una acción legal al estado.

        Flujo:
        1. Comprueba que la partida no haya terminado.
        2. Comprueba que mueve el jugador correcto.
        3. Comprueba que la acción está dentro de las acciones legales.
        4. Aplica la acción.
        5. Comprueba si la partida terminó.
        6. Si no terminó, cambia el turno.
        7. Comprueba si el nuevo jugador se quedó sin movimientos.
        """
        if state.is_terminal:
            return

        if action.player != state.current_player:
            raise ValueError(
                f"Turno inválido: action.player={action.player}, "
                f"pero current_player={state.current_player}."
            )

        legal_actions = self.compute_available_actions(state)

        if action not in legal_actions:
            raise ValueError(f"Movimiento ilegal: {action}")

        self.apply_action_without_validation(state, action)
        self.update_terminal_status(state)

        if not state.is_terminal:
            state.current_player = other_player(state.current_player)
            self.update_terminal_status(state)

    def evaluate_terminal(self, state: CheckersGameState, ai_player: int, depth: int) -> int:
        """
        Evaluación de estados terminales para minimax / alpha-beta.

        Convención:
        - victoria IA: valor positivo grande
        - derrota IA: valor negativo grande
        - empate: 0

        Usamos depth para preferir:
        - ganar antes
        - perder más tarde
        """
        if state.winner is None:
            return 0

        if state.winner == ai_player:
            return 100000 - depth

        return -100000 + depth

    def evaluate_heuristic(self, state: CheckersGameState, ai_player: int) -> int:
        """
        Heurística para estados no terminales.

        Sirve para:
        - minimax con profundidad máxima
        - alpha-beta con profundidad máxima
        - MCTS con max_rollout_depth si se corta el rollout

        La heurística valora:
        - cantidad de piezas
        - damas valen más que peones
        - avance de peones hacia la coronación

        Como jugador 1 empieza abajo y avanza hacia arriba:
        - P1_MAN está más avanzado cuanto menor es y.
        - P2_MAN está más avanzado cuanto mayor es y.
        """
        opponent = other_player(ai_player)
        score = 0

        for y in range(state.size):
            for x in range(state.size):
                piece = state.get(x, y)

                if piece == EMPTY:
                    continue

                piece_owner = owner_of(piece)

                # Valor base de la pieza.
                if piece in (P1_MAN, P2_MAN):
                    value = 100
                else:
                    value = 175

                # Bonus por estar más cerca de coronar.
                if piece == P1_MAN:
                    # Jugador 1 corona en y = 0.
                    value += (state.size - 1 - y) * 5
                elif piece == P2_MAN:
                    # Jugador 2 corona en y = 7.
                    value += y * 5

                if piece_owner == ai_player:
                    score += value
                elif piece_owner == opponent:
                    score -= value

        return score

    # ========================================================
    # GENERACIÓN DE MOVIMIENTOS
    # ========================================================

    def movement_directions(self, piece: int, player: int) -> list[tuple[int, int]]:
        """
        Devuelve las direcciones en las que una pieza puede moverse
        de forma normal.

        Cada dirección es un par:
            (dx, dy)

        Como jugador 1 está abajo:
        - jugador 1 avanza hacia arriba: dy = -1
        - jugador 2 avanza hacia abajo: dy = +1

        Las damas pueden moverse en las cuatro diagonales.
        """
        if is_king(piece):
            return [
                (-1, -1),
                (1, -1),
                (-1, 1),
                (1, 1),
            ]

        if player == 1:
            return [
                (-1, -1),
                (1, -1),
            ]

        return [
            (-1, 1),
            (1, 1),
        ]

    def capture_directions(self, piece: int, player: int) -> list[tuple[int, int]]:
        """
        Devuelve las direcciones en las que una pieza puede capturar.

        En esta versión:
        - los peones capturan solo hacia delante.
        - las damas capturan en cualquier diagonal.

        Si quisieras una variante donde los peones también capturan hacia atrás,
        habría que cambiar solo esta función.
        """
        return self.movement_directions(piece, player)

    def compute_normal_moves_for_piece(
        self,
        state: CheckersGameState,
        x: int,
        y: int,
        piece: int,
        player: int
    ) -> list[MovePieceAction]:
        """
        Calcula movimientos normales de una pieza.

        Movimiento normal:
        - una casilla en diagonal
        - la casilla destino debe estar vacía
        - no hay captura
        """
        moves: list[MovePieceAction] = []

        for dx, dy in self.movement_directions(piece, player):
            nx = x + dx
            ny = y + dy

            if not state.inside(nx, ny):
                continue

            if state.get(nx, ny) != EMPTY:
                continue

            moves.append(
                MovePieceAction(
                    path=[(x, y), (nx, ny)],
                    player=player
                )
            )

        return moves

    def compute_captures_for_piece(
        self,
        state: CheckersGameState,
        x: int,
        y: int,
        piece: int,
        player: int
    ) -> list[MovePieceAction]:
        """
        Calcula todas las capturas posibles de una pieza.

        Puede devolver capturas simples o múltiples.
        """
        captures: list[MovePieceAction] = []

        self.search_capture_paths(
            state=state,
            x=x,
            y=y,
            piece=piece,
            player=player,
            path=[(x, y)],
            captures=captures
        )

        return captures

    def search_capture_paths(
        self,
        state: CheckersGameState,
        x: int,
        y: int,
        piece: int,
        player: int,
        path: list[tuple[int, int]],
        captures: list[MovePieceAction]
    ) -> None:
        """
        Busca capturas múltiples de forma recursiva.

        Idea:
        - Desde la posición actual miramos todos los saltos posibles.
        - Si encontramos un salto, clonamos el estado.
        - Quitamos la pieza capturada.
        - Movemos la pieza.
        - Seguimos buscando más capturas desde la nueva posición.
        - Si ya no hay más capturas, guardamos el camino completo.
        """
        found_capture = False

        for dx, dy in self.capture_directions(piece, player):
            middle_x = x + dx
            middle_y = y + dy
            landing_x = x + 2 * dx
            landing_y = y + 2 * dy

            if not state.inside(middle_x, middle_y):
                continue

            if not state.inside(landing_x, landing_y):
                continue

            middle_piece = state.get(middle_x, middle_y)
            landing_piece = state.get(landing_x, landing_y)

            # Para capturar, en medio tiene que haber una pieza rival.
            if not belongs_to_opponent(middle_piece, player):
                continue

            # Y la casilla de aterrizaje debe estar vacía.
            if landing_piece != EMPTY:
                continue

            found_capture = True

            next_state = state.clone()

            # Aplicamos solo esta captura parcial.
            next_state.set(x, y, EMPTY)
            next_state.set(middle_x, middle_y, EMPTY)
            next_state.set(landing_x, landing_y, piece)

            self.search_capture_paths(
                state=next_state,
                x=landing_x,
                y=landing_y,
                piece=piece,
                player=player,
                path=path + [(landing_x, landing_y)],
                captures=captures
            )

        # Si no hemos encontrado más capturas y el path tiene más de una posición,
        # significa que tenemos una captura completa.
        if not found_capture and len(path) > 1:
            captures.append(
                MovePieceAction(
                    path=path,
                    player=player
                )
            )

    # ========================================================
    # APLICACIÓN DE ACCIONES
    # ========================================================

    def apply_action_without_validation(
        self,
        state: CheckersGameState,
        action: MovePieceAction
    ) -> None:
        """
        Aplica una acción que ya sabemos que es legal.

        No valida nada aquí porque advance() ya validó antes.
        """
        path = action.path

        start_x, start_y = path[0]
        end_x, end_y = path[-1]

        piece = state.get(start_x, start_y)

        # Quitamos la pieza de la casilla inicial.
        state.set(start_x, start_y, EMPTY)

        # Si hay saltos de captura, eliminamos las piezas capturadas.
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]

            if abs(x2 - x1) == 2 and abs(y2 - y1) == 2:
                captured_x = (x1 + x2) // 2
                captured_y = (y1 + y2) // 2
                state.set(captured_x, captured_y, EMPTY)

        # Coronación.
        #
        # Jugador 1 empieza abajo y avanza hacia arriba.
        # Por tanto corona al llegar a y = 0.
        #
        # Jugador 2 empieza arriba y avanza hacia abajo.
        # Por tanto corona al llegar a y = 7.
        if piece == P1_MAN and end_y == 0:
            piece = P1_KING
        elif piece == P2_MAN and end_y == state.size - 1:
            piece = P2_KING

        # Colocamos la pieza en su destino final.
        state.set(end_x, end_y, piece)

    # ========================================================
    # COMPROBACIÓN DE FINAL DE PARTIDA
    # ========================================================

    def update_terminal_status(self, state: CheckersGameState) -> None:
        """
        Comprueba si la partida terminó.

        Casos:
        - jugador 1 no tiene piezas -> gana jugador 2
        - jugador 2 no tiene piezas -> gana jugador 1
        - el jugador actual no tiene movimientos -> gana el rival
        """
        p1_pieces = 0
        p2_pieces = 0

        for piece in state.board:
            if belongs_to_player(piece, 1):
                p1_pieces += 1
            elif belongs_to_player(piece, 2):
                p2_pieces += 1

        if p1_pieces == 0:
            state.is_terminal = True
            state.winner = 2
            return

        if p2_pieces == 0:
            state.is_terminal = True
            state.winner = 1
            return

        actions = self.compute_available_actions(state)

        if not actions:
            state.is_terminal = True
            state.winner = other_player(state.current_player)
            return


# ============================================================
# FUNCIONES DE CONSOLA
# ============================================================

def print_board(state: CheckersGameState) -> None:
    """
    Imprime el tablero por consola.

    Como jugador 1 = x empieza abajo, imprimimos y de 0 a 7,
    que es la forma normal de representar una matriz:
    - fila 0 arriba
    - fila 7 abajo

    Así se ve:
    - o arriba
    - x abajo
    """
    symbols = {
        EMPTY: ".",
        P1_MAN: "x",
        P2_MAN: "o",
        P1_KING: "X",
        P2_KING: "O",
    }

    print()
    print("    ", end="")
    for x in range(state.size):
        print(f"{x} ", end="")
    print()

    for y in range(state.size):
        print(f"{y} | ", end="")

        for x in range(state.size):
            print(symbols[state.get(x, y)], end=" ")

        print()

    print()
    print("x = jugador 1, o = jugador 2, X/O = dama")
    print(f"Turno actual: jugador {state.current_player}")
    print()


def read_human_move(state: CheckersGameState) -> list[tuple[int, int]]:
    """
    Lee una jugada humana por consola.

    Formato:
        x1 y1 x2 y2

    Ejemplo movimiento normal:
        2 5 1 4

    Ejemplo captura:
        2 5 4 3

    Ejemplo captura múltiple:
        2 5 4 3 6 1

    Además de comprobar formato y rango, también comprobamos si el
    movimiento está dentro de las acciones legales.

    Esto evita que el programa se caiga con un traceback cuando el humano
    introduce una jugada ilegal.
    """
    model = CheckersForwardModel()

    while True:
        legal_actions = model.compute_available_actions(state)

        print("Introduce movimiento como: x1 y1 x2 y2")
        print("Para captura múltiple: x1 y1 x2 y2 x3 y3 ...")

        if state.current_player == 1:
            print("Te toca mover: x / X")
        else:
            print("Te toca mover: o / O")

        try:
            values = list(map(int, input("Movimiento: ").split()))
        except ValueError:
            print("Formato inválido. Usa solo números.")
            continue

        if len(values) < 4 or len(values) % 2 != 0:
            print("Debes introducir pares de coordenadas.")
            continue

        path: list[tuple[int, int]] = []
        valid_coordinates = True

        for i in range(0, len(values), 2):
            x = values[i]
            y = values[i + 1]

            if not state.inside(x, y):
                print("Coordenada fuera de rango.")
                valid_coordinates = False
                break

            path.append((x, y))

        if not valid_coordinates:
            continue

        action = MovePieceAction(
            path=path,
            player=state.current_player
        )

        if action in legal_actions:
            return path

        print("Movimiento ilegal.")
        print("Movimientos legales disponibles:")

        for legal_action in legal_actions:
            print(" -", legal_action.path)

        print()