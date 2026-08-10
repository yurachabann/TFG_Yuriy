from typing import Optional
from .game_state import BattleshipGameState
from .actions import ShootAction


def print_board(state: BattleshipGameState, debug_mode: bool = True):
    """Muestra el tablero con la cabecera ajustada al ancho real de los emojis en terminal."""
    print("\n=================== ESTADO DEL TABLERO ===================")

    if getattr(state, "last_action_summary", None):
        print(f"📢 ÚLTIMA JUGADA: {state.last_action_summary}")
        print("----------------------------------------------------------")

    print(f"🎯 Turno actual: Jugador {state.current_player}")
    print("----------------------------------------------------------")

    p = 1
    enemy = 2

    # Alineación exacta de la cabecera
    cols_header = "   " + "  ".join(str(c) for c in range(state.grid_size))

    print(f"  [TU TABLERO / RECIBIDOS]             [ENEMIGO / TUS DISPAROS]")
    print(f"{cols_header}     | {cols_header}")

    for r in range(state.grid_size):
        # Lado Izquierdo (Mi Tablero)
        row_left = []
        for c in range(state.grid_size):
            cell = (r, c)
            is_ship = any(cell in s for s in state.ships[p])
            was_shot = cell in state.shots[enemy]

            if is_ship and was_shot:
                row_left.append("🔥")
            elif was_shot:
                row_left.append("⚪") 
            elif is_ship:
                row_left.append("🚢")
            else:
                row_left.append("🌊")

        # Lado Derecho (Tablero Enemigo)
        row_right = []
        for c in range(state.grid_size):
            cell = (r, c)
            is_enemy_ship = any(cell in s for s in state.ships[enemy])
            was_shot = cell in state.shots[p]

            if was_shot:
                row_right.append("💥" if is_enemy_ship else "⚪")  # Representación de agua disparada
            else:
                if debug_mode and is_enemy_ship:
                    row_right.append("🚢")
                else:
                    row_right.append("❓")

        print(f"{r}  {' '.join(row_left)}    | {r}  {' '.join(row_right)}")

    print("==========================================================\n")


def print_action_summary(action: ShootAction, state_before: BattleshipGameState):
    """Muestra la intención del disparo en formato (X, Y)."""
    p = action.player
    print(f"\n🎬 >>> JUGADA REAL: El Jugador {p} dispara a la casilla ({action.col}, {action.row}) <<<")


def print_action_result(state_before: BattleshipGameState, action: ShootAction, state_after: BattleshipGameState):
    """Muestra la consecuencia del disparo usando el resumen guardado en el estado."""
    summary = getattr(state_after, "last_action_summary", None)
    if summary:
        print(f"  └─ 📢 {summary}")
    print("----------------------------------------------------------\n")


def print_ai_action(action: ShootAction):
    """
    Muestra la acción elegida por la IA en formato (X, Y).
    Compatible con Match.py.
    """
    print(f"🤖 IA (Jugador {action.player}) dispara a la casilla: ({action.col}, {action.row})")


def read_human_move(state: BattleshipGameState) -> tuple[int, int]:
    """
    Gestión interactiva de la entrada del jugador humano.
    Entrada esperada: X Y o X,Y (donde X=columna, Y=fila).
    Devuelve (row, col) internamente para la matriz.
    """
    player = state.current_player
    print(f"\n👉 TU TURNO (Jugador {player})")

    while True:
        try:
            inp = input(f"Introduce coordenadas X Y (0-{state.grid_size-1}), ej. '3 1' o '3,1': ").strip()
            
            # Reemplaza comas por espacios y separa los números
            coords = inp.replace(",", " ").split()
            if len(coords) != 2:
                print("⚠️ Debe introducir exactamente dos números (Columna X y Fila Y).")
                continue

            x, y = int(coords[0]), int(coords[1])

            if 0 <= x < state.grid_size and 0 <= y < state.grid_size:
                row, col = y, x  # Internamente row = Y, col = X
                
                if (row, col) not in state.shots[player]:
                    return row, col
                print(f"⚠️ Ya has disparado previamente en la casilla ({x}, {y}). Elige otra.")
            else:
                print(f"⚠️ Las coordenadas deben estar entre 0 y {state.grid_size - 1}.")
        except ValueError:
            print("⚠️ Formato no válido. Ejemplo de uso: '3 1' o '3,1'")