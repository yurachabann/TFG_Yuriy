from core.match_runner import run_human_vs_ai, run_ai_vs_ai, print_aggregated_stats

from juegos.tictactoe.adapter import GAME as TICTACTOE_GAME
from juegos.four_in_line.adapter import GAME as CONNECT4_GAME

from algoritmos.minmax import choose_ai_move
from algoritmos.minmax_ab import choose_ai_move_alpha_beta
from algoritmos.minmax_ab_depth_limit import choose_ai_move_alpha_beta_depth_limit


# =========================
# WRAPPERS DEPTH LIMIT
# =========================

def depth_limit_5(state, model, ai_player):
    return choose_ai_move_alpha_beta_depth_limit(state, model, ai_player, max_depth=5)


def depth_limit_7(state, model, ai_player):
    return choose_ai_move_alpha_beta_depth_limit(state, model, ai_player, max_depth=7)


# =========================
# REGISTRO DE JUEGOS
# =========================

GAMES = {
    "1": TICTACTOE_GAME,
    "2": CONNECT4_GAME,
}


# =========================
# ALGORITMOS POR JUEGO
# =========================

TICTACTOE_ALGORITHMS = {
    "1": ("Minimax", choose_ai_move),
    "2": ("Alpha-Beta", choose_ai_move_alpha_beta),
}

CONNECT4_ALGORITHMS = {
    "1": ("Alpha-Beta Depth Limit 5", depth_limit_5),
    "2": ("Alpha-Beta Depth Limit 7", depth_limit_7),
}


def get_algorithms_for_game(game):
    if game["name"] == "3 en raya":
        return TICTACTOE_ALGORITHMS
    return CONNECT4_ALGORITHMS


# =========================
# MENÚS
# =========================

def choose_game():
    while True:
        print("\n=== Selecciona juego ===")
        print("1. 3 en raya")
        print("2. 4 en raya")

        option = input("Opción: ").strip()

        if option in GAMES:
            return GAMES[option]

        print("Opción no válida")


def choose_mode():
    while True:
        print("\n=== Selecciona modo ===")
        print("1. Humano vs IA")
        print("2. IA vs IA")

        option = input("Opción: ").strip()

        if option in ("1", "2"):
            return option

        print("Opción no válida")


def choose_algorithm(algorithms, prompt="Selecciona algoritmo"):
    while True:
        print(f"\n=== {prompt} ===")

        for key, (name, _) in algorithms.items():
            print(f"{key}. {name}")

        option = input("Opción: ").strip()

        if option in algorithms:
            return algorithms[option]

        print("Opción no válida")


def ask_yes_no(text, default=True):
    raw = input(f"{text} [{'S/n' if default else 's/N'}]: ").strip().lower()

    if raw == "":
        return default

    return raw in ("s", "si", "sí", "y", "yes")


# =========================
# MAIN LOOP
# =========================

def main():
    while True:
        game = choose_game()
        algorithms = get_algorithms_for_game(game)
        mode = choose_mode()

        # ---------------------------------
        # HUMANO VS IA
        # ---------------------------------
        if mode == "1":
            ai_name, ai_fn = choose_algorithm(algorithms, "Selecciona IA")

            stats = run_human_vs_ai(
                game=game,
                ai_fn=ai_fn,
                ai_name=ai_name,
                human_player=1,
                show_board=True
            )

            print_aggregated_stats(stats, "Humano", ai_name)

        # ---------------------------------
        # IA VS IA
        # ---------------------------------
        else:
            ai1_name, ai1_fn = choose_algorithm(algorithms, "Selecciona algoritmo jugador 1")
            ai2_name, ai2_fn = choose_algorithm(algorithms, "Selecciona algoritmo jugador 2")

            try:
                games_count = int(input("¿Cuántas partidas quieres ejecutar?: ").strip())
                if games_count <= 0:
                    games_count = 1
            except ValueError:
                games_count = 1

            show_board = ask_yes_no(
                "¿Mostrar tablero durante las partidas?",
                default=(games_count == 1)
            )

            stats = run_ai_vs_ai(
                game=game,
                ai1_fn=ai1_fn,
                ai1_name=ai1_name,
                ai2_fn=ai2_fn,
                ai2_name=ai2_name,
                games_count=games_count,
                show_board=show_board
            )

            print_aggregated_stats(stats, ai1_name, ai2_name)

        # ---------------------------------
        # REPEAT
        # ---------------------------------
        if not ask_yes_no("¿Quieres volver al menú?", default=True):
            print("Saliendo...")
            break


if __name__ == "__main__":
    main()