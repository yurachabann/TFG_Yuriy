from core.match_runner import MatchRunner
from core.players import HumanPlayer, AIPlayer

from generic.tournament_runner import TournamentRunner

from juegos.tictactoe.game import TicTacToeGame
from juegos.four_in_line.game import Connect4Game
from juegos.checkers.game import CheckersGame
from juegos.love_letter.game import LoveLetterGame
from juegos.simple_chess.game import SimpleChessGame
from juegos.love_letter.game import LoveLetterGame
from juegos.battleship.game import BattleshipGame

from algoritmos.minmax import choose_ai_move
from algoritmos.minmax_ab import choose_ai_move_alpha_beta
from algoritmos.minmax_ab_depth_limit import choose_ai_move_alpha_beta_depth_limit
from algoritmos.mcts import choose_ai_move_mcts
from algoritmos.mcts_max_depth import choose_ai_move_mcts_max_depth
from algoritmos.ismcts import choose_ai_move_ismcts
from algoritmos.mccfr import choose_ai_move_mccfr_dynamic

from heuristics.checkers.combined_heuristic import CheckersCombinedHeuristic
from heuristics.four_in_line.connect_four_heuristic import ConnectFourHeuristic
from heuristics.simple_chess.simple_chess_heuristic import SimpleChessHeuristic


# =========================
# REGISTRO DE JUEGOS
# =========================

GAMES = {
    "1": TicTacToeGame,
    "2": Connect4Game,
    "3": CheckersGame,
    "4": LoveLetterGame,
    "5": SimpleChessGame,
    "6": LoveLetterGame,
    "7": BattleshipGame
}


# =========================
# HEURÍSTICAS POR JUEGO
# =========================

HEURISTICS_BY_GAME = {
    "1": {
        # 3 en raya: no tiene una heurística separada
    },
    "2": {
        "1": {
            "name": "Heurística de 4 en raya",
            "instance": ConnectFourHeuristic(),
        }
    },
    "3": {
        "1": {
            "name": "Heurística de damas",
            "instance": CheckersCombinedHeuristic(),
        }
    },
    "4": {
        "1": {
            "name": "Heurística del ajedrez simplificado",
            "instance": SimpleChessHeuristic(),
        }
    },
}


ALGORITHMS_REQUIRING_HEURISTIC = (
    choose_ai_move_alpha_beta_depth_limit,
    choose_ai_move_mcts_max_depth,
)


# =========================
# TODOS LOS ALGORITMOS
# =========================

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
    },
    "6": {
        "name": "MCTS con max depth (1000 iter)",
        "fn": choose_ai_move_mcts_max_depth,
        "params": {
            "iterations": 1000,
            "max_rollout_depth": 20
        }
    },
    "7": {
        "name": "ISMCTS (1000 iter)",
        "fn": choose_ai_move_ismcts,
        "params": {
            "iterations": 1000,
            "exploration_weight": 1.414  # O math.sqrt(2)
        }
    },
    "8": {
        "name": "MCCFR (5000 iter)",
        "fn": choose_ai_move_mccfr_dynamic,
        "params": {
            "iterations": 5000,
            "deterministic": False
        }
    },
}


# =========================
# MENÚS
# =========================

def choose_main_option():
    while True:
        print("\n=== MENÚ PRINCIPAL ===")
        print("1. Ejecutar partida normal")
        print("2. Ejecutar todas las IAs contra todas y guardar los resultados en results.json")
        print("0. Salir")

        option = input("Opción: ").strip()

        if option in ("0", "1", "2"):
            return option

        print("Opción no válida")


def choose_game():
    """
    Pregunta al usuario qué juego quiere y devuelve
    la clave y una instancia del juego seleccionado.
    """
    while True:
        print("\n=== Selecciona juego ===")
        print("1. 3 en raya")
        print("2. 4 en raya")
        print("3. Las damas")
        print("4. Love Letter")
        print("5. Ajedrez simplificado")
        print("6. LoveLetter")
        print("7. Hundir la flota")

        option = input("Opción: ").strip()

        if option in GAMES:
            return option, GAMES[option]()

        print("Opción no válida")


def choose_mode():
    """
    Pregunta si se quiere jugar humano contra IA o IA contra IA.
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


def choose_heuristic(game_key: str):
    """
    Muestra las heurísticas disponibles para el juego seleccionado.

    Devuelve:
    - la instancia de la heurística elegida;
    - None si el juego no dispone de heurísticas.
    """
    available_heuristics = HEURISTICS_BY_GAME.get(game_key, {})

    if not available_heuristics:
        return None

    while True:
        print("\n=== Selecciona heurística ===")

        for key, config in available_heuristics.items():
            print(f"{key}. {config['name']}")

        option = input("Opción: ").strip()

        if option in available_heuristics:
            return available_heuristics[option]["instance"]

        print("Opción no válida")


def build_algorithm_params(ai_config: dict, game_key: str) -> dict:
    """
    Crea los parámetros del algoritmo.

    Solo pregunta por una heurística cuando el algoritmo elegido
    realmente la necesita.
    """
    params = ai_config["params"].copy()

    if ai_config["fn"] not in ALGORITHMS_REQUIRING_HEURISTIC:
        return params

    heuristic = choose_heuristic(game_key)

    if heuristic is None:
        raise ValueError(
            f"El algoritmo '{ai_config['name']}' necesita una heurística, "
            "pero el juego seleccionado no dispone de ninguna."
        )

    params["heuristic"] = heuristic
    return params


def choose_algorithm_and_params(game_key: str, prompt: str):
    """
    Permite elegir un algoritmo y prepara sus parámetros.

    Si el algoritmo necesita una heurística que no existe para el juego,
    vuelve a pedir otro algoritmo.
    """
    while True:
        ai_config = choose_algorithm(prompt)

        try:
            algorithm_params = build_algorithm_params(
                ai_config=ai_config,
                game_key=game_key
            )
            return ai_config, algorithm_params
        except ValueError as error:
            print(error)
            print("Selecciona otro algoritmo.")


def ask_yes_no(text, default=True):
    """
    Pregunta sí/no con valor por defecto.
    """
    raw = input(
        f"{text} [{'S/n' if default else 's/N'}]: "
    ).strip().lower()

    if raw == "":
        return default

    return raw in ("s", "si", "sí", "y", "yes")


def ask_stats_file():
    """
    Pregunta si se quieren guardar estadísticas en un JSON.

    Devuelve:
    - la ruta del fichero si se quieren guardar;
    - None en caso contrario.
    """
    save_stats = ask_yes_no(
        "¿Guardar estadísticas en un JSON?",
        default=False
    )

    if not save_stats:
        return None

    path = input(
        "Ruta del fichero JSON [stats/results.json]: "
    ).strip()

    if path == "":
        path = "stats/results.json"

    return path


def ask_float(text, default):
    raw = input(f"{text} [{default}]: ").strip()

    if raw == "":
        return default

    try:
        value = float(raw)

        if value <= 0:
            return default

        return value
    except ValueError:
        return default


def ask_tournament_file():
    path = input(
        "Ruta del JSON final [stats/results.json]: "
    ).strip()

    if path == "":
        path = "stats/results.json"

    return path


# =========================
# CREACIÓN DE JUGADORES
# =========================

def build_human_vs_ai_players(game_key: str):
    ai_config, algorithm_params = choose_algorithm_and_params(
        game_key=game_key,
        prompt="Selecciona IA"
    )

    human = HumanPlayer(
        name="Humano",
        player_id=1
    )

    ai = AIPlayer(
        name=ai_config["name"],
        player_id=2,
        algorithm_fn=ai_config["fn"],
        algorithm_params=algorithm_params
    )

    return [human, ai]


def build_ai_vs_ai_players(game_key: str):
    ai1_config, ai1_params = choose_algorithm_and_params(
        game_key=game_key,
        prompt="Selecciona algoritmo jugador 1"
    )

    ai2_config, ai2_params = choose_algorithm_and_params(
        game_key=game_key,
        prompt="Selecciona algoritmo jugador 2"
    )

    ai1 = AIPlayer(
        name=ai1_config["name"],
        player_id=1,
        algorithm_fn=ai1_config["fn"],
        algorithm_params=ai1_params
    )

    ai2 = AIPlayer(
        name=ai2_config["name"],
        player_id=2,
        algorithm_fn=ai2_config["fn"],
        algorithm_params=ai2_params
    )

    return [ai1, ai2]


# =========================
# TORNEO AUTOMÁTICO
# =========================

def run_full_ai_tournament():
    """
    Ejecuta todos los juegos y todas las combinaciones posibles de IAs.
    Cada IA juega contra todas las demás.

    También se ejecutan ambos órdenes:
    - IA A como jugador 1 contra IA B como jugador 2
    - IA B como jugador 1 contra IA A como jugador 2
    """
    results_file = ask_tournament_file()

    move_timeout_seconds = ask_float(
        "Tiempo máximo por movimiento en segundos",
        default=5.0
    )

    match_timeout_seconds = ask_float(
        "Tiempo máximo por partida en segundos",
        default=120.0
    )

    runner = TournamentRunner(
        game_registry=GAMES,
        algorithm_registry=ALL_ALGORITHMS,
        heuristics_by_game=HEURISTICS_BY_GAME,
        algorithms_requiring_heuristic=ALGORITHMS_REQUIRING_HEURISTIC,
        results_file=results_file,
        move_timeout_seconds=move_timeout_seconds,
        match_timeout_seconds=match_timeout_seconds,
        play_both_orders=True
    )

    runner.run_all()


# =========================
# MAIN LOOP
# =========================

def main():
    while True:
        main_option = choose_main_option()

        if main_option == "0":
            print("Saliendo...")
            break

        # ---------------------------------
        # TORNEO AUTOMÁTICO IA VS IA
        # ---------------------------------
        if main_option == "2":
            run_full_ai_tournament()

            if not ask_yes_no(
                "¿Quieres volver al menú?",
                default=True
            ):
                print("Saliendo...")
                break

            continue

        # ---------------------------------
        # PARTIDA NORMAL
        # ---------------------------------
        game_key, game = choose_game()
        mode = choose_mode()

        # ---------------------------------
        # HUMANO VS IA
        # ---------------------------------
        if mode == "1":
            players = build_human_vs_ai_players(game_key)
            games_count = 1
            show_board = True
            stats_file = ask_stats_file()

        # ---------------------------------
        # IA VS IA
        # ---------------------------------
        else:
            players = build_ai_vs_ai_players(game_key)

            try:
                games_count = int(
                    input(
                        "¿Cuántas partidas quieres ejecutar?: "
                    ).strip()
                )

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
        # REPETIR
        # ---------------------------------
        if not ask_yes_no(
            "¿Quieres volver al menú?",
            default=True
        ):
            print("Saliendo...")
            break


if __name__ == "__main__":
    main()