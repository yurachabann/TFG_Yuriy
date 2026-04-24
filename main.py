from core.match_runner import MatchRunner
from core.players import HumanPlayer, AIPlayer

from juegos.tictactoe.game import TicTacToeGame
from juegos.four_in_line.game import Connect4Game

from algoritmos.minmax import choose_ai_move
from algoritmos.minmax_ab import choose_ai_move_alpha_beta
from algoritmos.minmax_ab_depth_limit import choose_ai_move_alpha_beta_depth_limit
from algoritmos.mcts import choose_ai_move_mcts


# =========================
# REGISTRO DE JUEGOS
# =========================

GAMES = {
    "1": TicTacToeGame,
    "2": Connect4Game,
}


# =========================
# TODOS LOS ALGORITMOS
# =========================
# Se muestran siempre todos, sin distinguir por juego.
ALL_ALGORITHMS = {
    "1": {
        "name": "Minimax",
        "fn": choose_ai_move,
        "params": {}
    },
    "2": {
        "name": "Alpha-Beta",
        "fn": choose_ai_move_alpha_beta,
        "params": {}
    },
    "3": {
        "name": "Alpha-Beta Depth Limit 5",
        "fn": choose_ai_move_alpha_beta_depth_limit,
        "params": {"max_depth": 5}
    },
    "4": {
        "name": "Alpha-Beta Depth Limit 7",
        "fn": choose_ai_move_alpha_beta_depth_limit,
        "params": {"max_depth": 7}
    },
    "5": {
        "name": "MCTS (1000 iter)",
        "fn": choose_ai_move_mcts,
        "params": {"iterations": 1000}
    }
}


# =========================
# MENÚS
# =========================

def choose_game():
    """
    Pregunta al usuario qué juego quiere y devuelve
    una instancia del juego seleccionado.
    """
    while True:
        print("\n=== Selecciona juego ===")
        print("1. 3 en raya")
        print("2. 4 en raya")

        option = input("Opción: ").strip()

        if option in GAMES:
            return GAMES[option]()

        print("Opción no válida")


def choose_mode():
    """
    Pregunta si quiere humano vs IA o IA vs IA.
    """
    while True:
        print("\n=== Selecciona modo ===")
        print("1. Humano vs IA")
        print("2. IA vs IA")

        option = input("Opción: ").strip()

        if option in ("1", "2"):
            return option

        print("Opción no válida")


def choose_algorithm(prompt="Selecciona algoritmo"):
    """
    Muestra todos los algoritmos disponibles y devuelve
    la configuración del algoritmo elegido.
    """
    while True:
        print(f"\n=== {prompt} ===")

        for key, config in ALL_ALGORITHMS.items():
            print(f"{key}. {config['name']}")

        option = input("Opción: ").strip()

        if option in ALL_ALGORITHMS:
            return ALL_ALGORITHMS[option]

        print("Opción no válida")


def ask_yes_no(text, default=True):
    """
    Pregunta sí/no con valor por defecto.
    """
    raw = input(f"{text} [{'S/n' if default else 's/N'}]: ").strip().lower()

    if raw == "":
        return default

    return raw in ("s", "si", "sí", "y", "yes")


def ask_stats_file():
    """
    Pregunta si se quieren guardar estadísticas en un JSON.
    Si sí, devuelve la ruta del fichero.
    Si no, devuelve None.
    """
    save_stats = ask_yes_no("¿Guardar estadísticas en un JSON?", default=False)

    if not save_stats:
        return None

    path = input("Ruta del fichero JSON [stats/results.json]: ").strip()

    if path == "":
        path = "stats/results.json"

    return path


# =========================
# CREACIÓN DE JUGADORES
# =========================

def build_human_vs_ai_players():
    """
    Crea los jugadores para el modo Humano vs IA.
    """
    ai_config = choose_algorithm("Selecciona IA")

    human = HumanPlayer(name="Humano", player_id=1)
    ai = AIPlayer(
        name=ai_config["name"],
        player_id=2,
        algorithm_fn=ai_config["fn"],
        algorithm_params=ai_config["params"]
    )

    return [human, ai]


def build_ai_vs_ai_players():
    """
    Crea los jugadores para el modo IA vs IA.
    """
    ai1_config = choose_algorithm("Selecciona algoritmo jugador 1")
    ai2_config = choose_algorithm("Selecciona algoritmo jugador 2")

    ai1 = AIPlayer(
        name=ai1_config["name"],
        player_id=1,
        algorithm_fn=ai1_config["fn"],
        algorithm_params=ai1_config["params"]
    )

    ai2 = AIPlayer(
        name=ai2_config["name"],
        player_id=2,
        algorithm_fn=ai2_config["fn"],
        algorithm_params=ai2_config["params"]
    )

    return [ai1, ai2]


# =========================
# MAIN LOOP
# =========================

def main():
    while True:
        game = choose_game()
        mode = choose_mode()

        # ---------------------------------
        # HUMANO VS IA
        # ---------------------------------
        if mode == "1":
            players = build_human_vs_ai_players()
            games_count = 1
            show_board = True
            stats_file = ask_stats_file()

        # ---------------------------------
        # IA VS IA
        # ---------------------------------
        else:
            players = build_ai_vs_ai_players()

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

            stats_file = ask_stats_file()

        runner = MatchRunner(
            game=game,
            players=players,
            games_count=games_count,
            show_board=show_board,
            stats_file=stats_file
        )

        runner.run()

        # ---------------------------------
        # REPEAT
        # ---------------------------------
        if not ask_yes_no("¿Quieres volver al menú?", default=True):
            print("Saliendo...")
            break


if __name__ == "__main__":
    main()