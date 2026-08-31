from __future__ import annotations

import concurrent.futures
import contextlib
import io
import itertools
import json
import multiprocessing
import queue
import time
import traceback
from pathlib import Path
from typing import Any

from core.match import Match
from core.stats_manager import StatsManager
from core.players import AIPlayer


# ============================================================
# EXCEPCIONES PERSONALIZADAS
# ============================================================

class AlgorithmTimeout(Exception):
    """
    Excepción propia para indicar que un algoritmo ha tardado demasiado
    en devolver una acción.

    Se usa para marcar una partida como inválida cuando una IA no responde
    dentro del tiempo máximo permitido.
    """

    def __init__(self, algorithm_name: str, player_id: int, seconds: float):
        # Nombre del algoritmo que ha superado el tiempo máximo.
        self.algorithm_name = algorithm_name

        # Jugador que estaba usando ese algoritmo.
        self.player_id = player_id

        # Tiempo máximo permitido.
        self.seconds = seconds

        # Mensaje descriptivo de la excepción.
        super().__init__(
            f"El algoritmo '{algorithm_name}' del jugador {player_id} "
            f"ha superado el límite de {seconds} segundos."
        )


class AlgorithmExecutionError(Exception):
    """
    Excepción propia para indicar que un algoritmo ha fallado durante su ejecución.

    No representa un timeout, sino un error interno del algoritmo:
    excepción de Python, acción inválida, error de heurística, etc.
    """

    def __init__(self, algorithm_name: str, player_id: int, original_error: Exception):
        # Nombre del algoritmo que ha producido el error.
        self.algorithm_name = algorithm_name

        # Jugador que estaba usando ese algoritmo.
        self.player_id = player_id

        # Error original producido por Python.
        self.original_error = original_error

        # Mensaje descriptivo de la excepción.
        super().__init__(
            f"El algoritmo '{algorithm_name}' del jugador {player_id} "
            f"ha producido un error: {original_error}"
        )


# ============================================================
# IA CON TIMEOUT POR MOVIMIENTO
# ============================================================

class TimedAIPlayer(AIPlayer):
    """
    Variante de AIPlayer que añade un límite de tiempo por movimiento.

    La clase AIPlayer original llama al algoritmo y espera hasta que termine.
    Esta clase hace lo mismo, pero ejecutando el algoritmo en un hilo separado
    para poder controlar cuánto tarda en devolver una acción.

    Se usa únicamente dentro del TournamentRunner.
    """

    def __init__(
        self,
        name: str,
        player_id: int,
        algorithm_fn,
        algorithm_params: dict | None = None,
        timeout_seconds: float = 5.0
    ):
        # Inicializamos la parte común de AIPlayer:
        # nombre, id del jugador, función del algoritmo y parámetros.
        super().__init__(
            name=name,
            player_id=player_id,
            algorithm_fn=algorithm_fn,
            algorithm_params=algorithm_params
        )

        # Tiempo máximo que este jugador IA puede tardar en elegir una acción.
        self.timeout_seconds = timeout_seconds

    def choose_action(self, state, game):
        """
        Devuelve la acción elegida por la IA y sus estadísticas.

        La diferencia respecto a AIPlayer es que aquí el algoritmo se ejecuta
        con un límite de tiempo.
        """

        # Creamos el modelo del juego.
        model = game.create_model()

        # En los juegos de información perfecta el algoritmo trabaja directamente
        # con el estado completo de la partida.
        algorithm_state = state

        # En los juegos de información imperfecta el algoritmo no debe recibir
        # el estado real completo, ya que contiene información oculta del rival.
        # Si el modelo permite crear un InformationState, generamos la vista
        # correspondiente al jugador que está tomando la decisión.
        if hasattr(model, "create_information_state"):
            algorithm_state = model.create_information_state(
                state,
                self.player_id
            )

        # Creamos un executor con un único hilo.
        # Ese hilo será el encargado de ejecutar el algoritmo.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        # Lanzamos la función del algoritmo en el hilo.
        # La convención de tus algoritmos es:
        # algorithm_fn(state, model, ai_player, **params) -> (action, stats)
        #
        # Para juegos de información perfecta, algorithm_state es el GameState.
        # Para juegos de información imperfecta, algorithm_state es el InformationState
        # observable por este jugador.
        future = executor.submit(
            self.algorithm_fn,
            algorithm_state,
            model,
            self.player_id,
            **self.algorithm_params
        )

        try:
            # Esperamos el resultado solo durante timeout_seconds.
            # Si el algoritmo termina a tiempo, result será (action, stats).
            result = future.result(timeout=self.timeout_seconds)

            # Cerramos correctamente el executor.
            executor.shutdown(wait=True, cancel_futures=True)

            return result

        except concurrent.futures.TimeoutError:
            # Si el algoritmo tarda demasiado, no esperamos más.
            executor.shutdown(wait=False, cancel_futures=True)

            # Lanzamos una excepción propia para que el torneo pueda marcar
            # esta partida como inválida.
            raise AlgorithmTimeout(
                algorithm_name=self.name,
                player_id=self.player_id,
                seconds=self.timeout_seconds
            )

        except Exception as exc:
            # Si el algoritmo falla por cualquier otro motivo,
            # lo envolvemos en una excepción más clara.
            executor.shutdown(wait=False, cancel_futures=True)

            raise AlgorithmExecutionError(
                algorithm_name=self.name,
                player_id=self.player_id,
                original_error=exc
            )


# ============================================================
# FUNCIONES AUXILIARES PARA GUARDAR DATOS EN JSON
# ============================================================

def _safe_params(params: dict | None) -> dict:
    """
    Devuelve una copia de los parámetros del algoritmo que pueda guardarse en JSON.

    Algunos valores de Python no se pueden guardar directamente en JSON.
    Por eso, si un parámetro no es serializable, se convierte a texto.
    """

    if params is None:
        return {}

    result = {}

    for key, value in params.items():
        try:
            # Comprobamos si el valor se puede convertir a JSON.
            json.dumps(value)

            # Si se puede, lo guardamos tal cual.
            result[key] = value

        except TypeError:
            # Si no se puede, lo convertimos a string.
            result[key] = str(value)

    return result


def _public_algorithm_config(key: str, config: dict) -> dict:
    """
    Devuelve la información pública y serializable de un algoritmo.

    En ALL_ALGORITHMS cada entrada contiene:
    - name
    - fn
    - params

    Pero fn es una función de Python, y no se puede guardar en JSON.
    Por eso aquí solo guardamos la clave, el nombre y los parámetros.
    """

    return {
        "key": key,
        "name": config["name"],
        "params": _safe_params(config.get("params", {}))
    }


# ============================================================
# WORKER DE UNA PARTIDA
# ============================================================

def _run_single_match_worker(
    game_key: str,
    game_cls,
    alg1_key: str,
    alg1_config: dict,
    alg2_key: str,
    alg2_config: dict,
    move_timeout_seconds: float,
    save_decisions: bool,
    output_queue,
    shared_stats,
    training_finished_event
):
    """
    Ejecuta una única partida dentro de un proceso separado.

    Esta función no se llama directamente desde main.
    La usa TournamentRunner al crear un multiprocessing.Process.

    La razón de ejecutarla en otro proceso es que, si la partida se queda bloqueada,
    el proceso completo se puede terminar desde fuera.
    """

    stats_manager = None
    started_at = None
    training_started_at = None
    training_elapsed_time = 0.0

    try:
        # Creamos una instancia del juego actual.
        game = game_cls()

        # Creamos el jugador 1 con timeout por movimiento.
        player1 = TimedAIPlayer(
            name=alg1_config["name"],
            player_id=1,
            algorithm_fn=alg1_config["fn"],
            algorithm_params=alg1_config.get("params", {}),
            timeout_seconds=move_timeout_seconds
        )

        # Creamos el jugador 2 con timeout por movimiento.
        player2 = TimedAIPlayer(
            name=alg2_config["name"],
            player_id=2,
            algorithm_fn=alg2_config["fn"],
            algorithm_params=alg2_config.get("params", {}),
            timeout_seconds=move_timeout_seconds
        )

        players = [player1, player2]

        # Creamos un StatsManager para esta partida.
        # No se va a llamar a save(), porque el torneo guarda todo al final.
        stats_manager = StatsManager(
            file_path="__not_saved_here__.json",
            game_name=game.name,
            players=players,
            save_decisions=save_decisions,
            on_stats_update=lambda data: shared_stats.__setitem__("data", data)
        )
        shared_stats["data"] = stats_manager.data

        # Redirigimos la salida estándar para ocultar los prints de Match.
        # Así el torneo no imprime todos los tableros ni todos los resultados.
        with contextlib.redirect_stdout(io.StringIO()):
            match = Match(
                game=game,
                players=players,
                show_board=False,
                stats_manager=stats_manager
            )

            # El pre-entrenamiento MCCFR se ejecuta antes de iniciar el timeout
            # total de la partida. Tampoco pasa por TimedAIPlayer, por lo que no
            # consume el timeout por movimiento.
            training_started_at = time.perf_counter()
            match.warmup_mccfr()
            training_elapsed_time = time.perf_counter() - training_started_at
            shared_stats["training_elapsed_time"] = training_elapsed_time

            # Guardamos el instante inicial para medir cuánto tarda la partida.
            started_at = time.perf_counter()

            # Avisamos al proceso principal de que el entrenamiento ya ha terminado
            # y de que a partir de este punto puede empezar a contar match_timeout_seconds.
            training_finished_event.set()

            # Ejecutamos la partida.
            final_state = match.run(match_number=1)

            if game.name == "Leduc Poker":
                model = game.create_model()
                utilities = {
                    1: model.evaluate_terminal(final_state, 1, 0),
                    2: model.evaluate_terminal(final_state, 2, 0)
                }
                max_contribution = model.MAX_PLAYER_CONTRIBUTION
                chips = {
                    player_id: utility * max_contribution
                    for player_id, utility in utilities.items()
                }
                stats_manager.record_poker_utility(
                    match_number=1,
                    utilities=utilities,
                    chips=chips
                )

        # Calculamos el tiempo total de esta partida.
        elapsed_time = time.perf_counter() - started_at

        # Si todo ha ido bien, enviamos el resultado al proceso principal.
        output_queue.put({
            "status": "valid",
            "valid": True,
            "game": {
                "key": game_key,
                "name": game.name
            },
            "player1": _public_algorithm_config(alg1_key, alg1_config),
            "player2": _public_algorithm_config(alg2_key, alg2_config),
            "winner": final_state.winner,
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time,
            "stats": stats_manager.data
        })

    except AlgorithmTimeout as exc:
        # Si una IA ha superado el tiempo máximo por movimiento,
        # la partida se marca como inválida.
        if started_at is not None:
            elapsed_time = time.perf_counter() - started_at
        else:
            elapsed_time = 0.0

        if training_started_at is not None and not training_finished_event.is_set():
            training_elapsed_time = time.perf_counter() - training_started_at

        training_finished_event.set()

        output_queue.put({
            "status": "invalid_algorithm_for_game",
            "valid": False,
            "game": {
                "key": game_key,
                "name": getattr(game_cls(), "name", game_cls.__name__)
            },
            "player1": _public_algorithm_config(alg1_key, alg1_config),
            "player2": _public_algorithm_config(alg2_key, alg2_config),
            "invalid_algorithm": exc.algorithm_name,
            "invalid_player_id": exc.player_id,
            "reason": str(exc),
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time,
            "stats": stats_manager.data if stats_manager is not None else shared_stats.get("data")
        })

    except AlgorithmExecutionError as exc:
        # Si una IA ha producido un error interno,
        # también se marca como inválida para esa partida.
        if started_at is not None:
            elapsed_time = time.perf_counter() - started_at
        else:
            elapsed_time = 0.0

        if training_started_at is not None and not training_finished_event.is_set():
            training_elapsed_time = time.perf_counter() - training_started_at

        training_finished_event.set()

        output_queue.put({
            "status": "invalid_algorithm_for_game",
            "valid": False,
            "game": {
                "key": game_key,
                "name": getattr(game_cls(), "name", game_cls.__name__)
            },
            "player1": _public_algorithm_config(alg1_key, alg1_config),
            "player2": _public_algorithm_config(alg2_key, alg2_config),
            "invalid_algorithm": exc.algorithm_name,
            "invalid_player_id": exc.player_id,
            "reason": str(exc),
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time,
            "stats": stats_manager.data if stats_manager is not None else shared_stats.get("data")
        })

    except Exception as exc:
        # Cualquier otro error no esperado se guarda como error general.
        if started_at is not None:
            elapsed_time = time.perf_counter() - started_at
        else:
            elapsed_time = 0.0

        if training_started_at is not None and not training_finished_event.is_set():
            training_elapsed_time = time.perf_counter() - training_started_at

        training_finished_event.set()

        output_queue.put({
            "status": "error",
            "valid": False,
            "game": {
                "key": game_key,
                "name": getattr(game_cls(), "name", game_cls.__name__)
            },
            "player1": _public_algorithm_config(alg1_key, alg1_config),
            "player2": _public_algorithm_config(alg2_key, alg2_config),
            "reason": str(exc),
            "traceback": traceback.format_exc(),
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time,
            "stats": stats_manager.data if stats_manager is not None else shared_stats.get("data")
        })


def _run_match_worker_loop(
    task_queue,
    output_queue,
    shared_stats,
    training_finished_event
):
    """
    Mantiene vivo un único proceso para ejecutar varias partidas del torneo.

    Al reutilizar el mismo proceso, las cachés globales de los algoritmos permanecen
    en RAM entre partidas. En particular, MCCFR no necesita volver a deserializar
    su caché persistente para cada enfrentamiento mientras el worker siga vivo.

    Si un movimiento supera su timeout, el proceso principal terminará este worker
    completo y creará otro para la siguiente partida, porque el hilo que excedió
    el límite puede seguir ejecutándose.
    """

    while True:
        task = task_queue.get()

        # None se utiliza como señal de cierre limpio del worker.
        if task is None:
            return

        # Reiniciamos los datos compartidos y el evento para la nueva partida.
        shared_stats.clear()
        training_finished_event.clear()

        _run_single_match_worker(
            game_key=task["game_key"],
            game_cls=task["game_cls"],
            alg1_key=task["alg1_key"],
            alg1_config=task["alg1_config"],
            alg2_key=task["alg2_key"],
            alg2_config=task["alg2_config"],
            move_timeout_seconds=task["move_timeout_seconds"],
            save_decisions=task["save_decisions"],
            output_queue=output_queue,
            shared_stats=shared_stats,
            training_finished_event=training_finished_event
        )


# ============================================================
# TOURNAMENT RUNNER
# ============================================================

class TournamentRunner:
    """
    Ejecuta automáticamente todas las combinaciones posibles de IAs
    para todos los juegos registrados.

    Diferencia con MatchRunner:
    - MatchRunner ejecuta una configuración concreta.
    - TournamentRunner ejecuta todas las combinaciones automáticamente.

    Además, TournamentRunner no guarda el JSON partida por partida.
    Acumula todo en memoria y guarda un único fichero al final.
    """

    def __init__(
        self,
        game_registry: dict[str, Any],
        algorithm_registry: dict[str, dict],
        algorithms_by_game: dict[str, tuple[str, ...]],
        heuristics_by_game: dict[str, dict],
        algorithms_requiring_heuristic: tuple,
        results_file: str = "stats/results.json",
        move_timeout_seconds: float = 5.0,
        match_timeout_seconds: float = 120.0,
        play_both_orders: bool = True,
        save_decisions: bool = False
    ):
        # Diccionario de juegos disponibles.
        # Ejemplo: {"1": TicTacToeGame, "2": Connect4Game, ...}
        self.game_registry = game_registry

        # Diccionario de algoritmos disponibles.
        # Ejemplo: {"1": {"name": "Minimax", "fn": ..., "params": {...}}, ...}
        self.algorithm_registry = algorithm_registry


        self.algorithms_by_game = algorithms_by_game


        # Diccionario de heurísticas disponibles para cada juego.
        # Ejemplo: {"2": {"1": {"name": "...", "instance": ...}}, ...}
        self.heuristics_by_game = heuristics_by_game

        # Funciones de los algoritmos que necesitan recibir una heurística.
        self.algorithms_requiring_heuristic = algorithms_requiring_heuristic

        # Fichero final donde se guardarán todos los resultados.
        self.results_file = results_file

        # Tiempo máximo que una IA puede tardar en elegir una acción.
        self.move_timeout_seconds = move_timeout_seconds

        # Tiempo máximo permitido para una partida completa.
        self.match_timeout_seconds = match_timeout_seconds

        # Si es True, se ejecutan ambos órdenes:
        # A como jugador 1 contra B como jugador 2,
        # y B como jugador 1 contra A como jugador 2.
        self.play_both_orders = play_both_orders

        # Si es True, se guardan en el JSON las decisiones tomadas en cada turno.
        self.save_decisions = save_decisions

        # Estructura principal que se guardará al final en JSON.
        self.results = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results_file": self.results_file,
            "move_timeout_seconds": self.move_timeout_seconds,
            "match_timeout_seconds": self.match_timeout_seconds,
            "play_both_orders": self.play_both_orders,
            "save_decisions": self.save_decisions,
            "games": [],
            "algorithms": [],
            "summary": {
                "total_matches": 0,
                "valid_matches": 0,
                "invalid_matches": 0,
                "errors": 0
            },
            "matches": [],
            "invalid_algorithms_by_game": {}
        }

        # Recursos del proceso persistente del torneo.
        # Se reutilizan entre partidas para conservar en RAM las cachés de los algoritmos.
        self._worker_process = None
        self._worker_task_queue = None
        self._worker_output_queue = None
        self._worker_manager = None
        self._worker_shared_stats = None
        self._worker_training_finished_event = None


    def _build_algorithm_config_for_game(
        self,
        game_key: str,
        algorithm_config: dict
    ) -> dict:
        """
        Crea una copia de la configuración de un algoritmo para un juego concreto.

        Si el algoritmo necesita una heurística:
        - busca las heurísticas registradas para ese juego
        - toma la primera heurística disponible
        - la añade a los parámetros del algoritmo

        La configuración original de self.algorithm_registry no se modifica.
        """

        # Creamos una copia independiente de la configuración.
        config = {
            "name": algorithm_config["name"],
            "fn": algorithm_config["fn"],
            "params": algorithm_config.get("params", {}).copy()
        }

        # Los algoritmos sin límite de profundidad no necesitan heurística.
        if config["fn"] not in self.algorithms_requiring_heuristic:
            return config

        # Obtenemos las heurísticas registradas para el juego actual.
        game_heuristics = self.heuristics_by_game.get(game_key, {})

        # Si el algoritmo necesita heurística y el juego no tiene ninguna,
        # esta combinación no se puede ejecutar.
        if not game_heuristics:
            raise ValueError(
                f"El juego '{game_key}' no tiene una heurística configurada "
                f"para el algoritmo '{config['name']}'."
            )

        # Actualmente cada juego tiene una única heurística registrada.
        # Si en el futuro hay varias, aquí se podrá decidir cuál utilizar.
        heuristic_config = next(iter(game_heuristics.values()))

        # Añadimos la instancia de la heurística a los parámetros del algoritmo.
        config["params"]["heuristic"] = heuristic_config["instance"]

        return config


    def run_all(self) -> dict:
        """
        Ejecuta el torneo completo.

        Recorre:
        - todos los juegos
        - todas las parejas de algoritmos compatibles con cada juego
        - todas las partidas necesarias

        Al final guarda todos los resultados en un único JSON.
        """

        # Guardamos en self.results la lista de juegos y algoritmos usados.
        self._initialize_metadata()

        # Convertimos los juegos a una lista para poder recorrerlos cómodamente.
        game_items = list(self.game_registry.items())

        # Preparamos los algoritmos compatibles con cada juego.
        algorithm_items_by_game = {}
        total = 0

        for game_key, _ in game_items:
            allowed_algorithm_keys = self.algorithms_by_game.get(game_key, ())

            game_algorithm_items = [
                (key, self.algorithm_registry[key])
                for key in allowed_algorithm_keys
                if key in self.algorithm_registry
            ]

            algorithm_items_by_game[game_key] = game_algorithm_items

            if self.play_both_orders:
                total += len(list(itertools.permutations(game_algorithm_items, 2)))
            else:
                total += len(list(itertools.combinations(game_algorithm_items, 2)))

        # Contador de progreso.
        current = 0

        print("\n=== TORNEO AUTOMÁTICO IA VS IA ===")
        print(f"Juegos: {len(game_items)}")
        print(f"Algoritmos: {len(self.algorithm_registry)}")
        print(f"Partidas a ejecutar: {total}")
        print(f"Timeout por movimiento: {self.move_timeout_seconds} segundos")
        print(f"Timeout por partida: {self.match_timeout_seconds} segundos")
        print(f"Fichero de salida: {self.results_file}")

        # Recorremos todos los juegos.
        for game_key, game_cls in game_items:
            game_name = game_cls().name
            print(f"\n=== Juego: {game_name} ===")

            algorithm_items = algorithm_items_by_game[game_key]

            # Generamos las parejas de algoritmos compatibles con este juego.
            if self.play_both_orders:
                # Permutaciones: A vs B y B vs A son partidas distintas.
                pairs = list(itertools.permutations(algorithm_items, 2))
            else:
                # Combinaciones: A vs B solo se juega una vez.
                pairs = list(itertools.combinations(algorithm_items, 2))

            # Cerramos el worker del juego anterior y creamos uno nuevo para este juego.
            # Dentro de este proceso todas las partidas del juego comparten la misma RAM.
            self._stop_process_worker()
            self._start_process_worker()

            # Para cada juego, recorremos todas las parejas de algoritmos.
            for (alg1_key, alg1_config), (alg2_key, alg2_config) in pairs:
                # Seguridad extra: evitamos algoritmo contra sí mismo.
                if alg1_key == alg2_key:
                    continue

                current += 1

                print(
                    f"[{current}/{total}] "
                    f"{game_name}: {alg1_config['name']} vs {alg2_config['name']}"
                )

                # Preparamos las configuraciones para el juego actual.
                # Si un algoritmo necesita heurística, se añade aquí.
                try:
                    game_alg1_config = self._build_algorithm_config_for_game(
                        game_key=game_key,
                        algorithm_config=alg1_config
                    )

                    game_alg2_config = self._build_algorithm_config_for_game(
                        game_key=game_key,
                        algorithm_config=alg2_config
                    )

                except ValueError as error:
                    # Si falta una heurística necesaria, la partida se marca
                    # como inválida sin llegar a crear el proceso.
                    match_result = {
                        "status": "invalid_algorithm_for_game",
                        "valid": False,
                        "game": {
                            "key": game_key,
                            "name": game_name
                        },
                        "player1": _public_algorithm_config(alg1_key, alg1_config),
                        "player2": _public_algorithm_config(alg2_key, alg2_config),
                        "invalid_algorithm": "heuristic_missing",
                        "invalid_player_id": None,
                        "reason": str(error),
                        "elapsed_time": 0.0
                    }

                    # Guardamos el resultado inválido y continuamos con la siguiente pareja.
                    self._record_match_result(match_result)
                    self._save_results()
                    continue

                # Ejecutamos la partida con timeout de proceso.
                match_result = self._run_match_with_process_timeout(
                    game_key=game_key,
                    game_cls=game_cls,
                    alg1_key=alg1_key,
                    alg1_config=game_alg1_config,
                    alg2_key=alg2_key,
                    alg2_config=game_alg2_config
                )

                # Guardamos el resultado en la estructura general.
                self._record_match_result(match_result)

                if game_name == "Leduc Poker" and match_result.get("valid"):
                    poker_utility = match_result.get("stats", {}).get("poker_utility", {})
                    p1_utility = poker_utility.get("1", {})
                    p2_utility = poker_utility.get("2", {})

                    print("--- Utilidad Leduc Poker ---")
                    print(
                        f"{alg1_config['name']}: "
                        f"utilidad={round(p1_utility.get('total_utility', 0.0), 4)} | "
                        f"fichas netas={round(p1_utility.get('net_chips', 0.0), 4)}"
                    )
                    print(
                        f"{alg2_config['name']}: "
                        f"utilidad={round(p2_utility.get('total_utility', 0.0), 4)} | "
                        f"fichas netas={round(p2_utility.get('net_chips', 0.0), 4)}"
                    )

                self._save_results()

        # Cerramos el último worker persistente cuando ya no quedan partidas.
        self._stop_process_worker()

        # Cuando todas las partidas han terminado, guardamos el JSON final.
        self._save_results()

        print("\n=== TORNEO FINALIZADO ===")
        print("Partidas totales:", self.results["summary"]["total_matches"])
        print("Partidas válidas:", self.results["summary"]["valid_matches"])
        print("Partidas inválidas:", self.results["summary"]["invalid_matches"])
        print("Errores:", self.results["summary"]["errors"])
        print("Resultados guardados en:", self.results_file)

        return self.results

    def _initialize_metadata(self) -> None:
        """
        Guarda en self.results la información general de los juegos
        y algoritmos que se van a usar en el torneo.

        Esto no ejecuta partidas. Solo prepara metadatos para que el JSON final
        indique qué juegos y qué algoritmos participaron.
        """

        # Guardamos la lista de juegos registrados.
        self.results["games"] = [
            {
                "key": key,
                "name": game_cls().name
            }
            for key, game_cls in self.game_registry.items()
        ]

        # Guardamos la lista de algoritmos registrados.
        # No se guarda la función Python, solo nombre, clave y parámetros.
        self.results["algorithms"] = [
            _public_algorithm_config(key, config)
            for key, config in self.algorithm_registry.items()
        ]

    def _start_process_worker(self):
        """
        Crea el proceso persistente usado por el torneo.

        Si ya existe un worker vivo, se reutiliza para que las cachés globales de
        los algoritmos sigan disponibles en RAM.
        """
        if (
            self._worker_process is not None
            and self._worker_process.is_alive()
        ):
            return

        # Si quedaron recursos de un worker anterior terminado, los limpiamos.
        self._stop_process_worker(force=True)

        self._worker_task_queue = multiprocessing.Queue()
        self._worker_output_queue = multiprocessing.Queue()
        self._worker_manager = multiprocessing.Manager()
        self._worker_shared_stats = self._worker_manager.dict()
        self._worker_training_finished_event = multiprocessing.Event()

        self._worker_process = multiprocessing.Process(
            target=_run_match_worker_loop,
            args=(
                self._worker_task_queue,
                self._worker_output_queue,
                self._worker_shared_stats,
                self._worker_training_finished_event
            )
        )

        self._worker_process.start()

    def _stop_process_worker(self, force: bool = False):
        """
        Cierra el proceso persistente del torneo.

        Con force=True se mata inmediatamente el proceso completo. Esto se usa
        después de un timeout por movimiento o por partida para asegurarnos de
        que ningún hilo del algoritmo quede ejecutándose en segundo plano.
        """
        process = self._worker_process

        if process is not None and process.is_alive():
            if force:
                process.terminate()
            else:
                try:
                    self._worker_task_queue.put(None)
                except Exception:
                    pass

                process.join(timeout=1.0)

                if process.is_alive():
                    process.terminate()

            process.join()

        for process_queue in (
            self._worker_task_queue,
            self._worker_output_queue
        ):
            if process_queue is not None:
                try:
                    process_queue.close()
                except Exception:
                    pass

        if self._worker_manager is not None:
            try:
                self._worker_manager.shutdown()
            except Exception:
                pass

        self._worker_process = None
        self._worker_task_queue = None
        self._worker_output_queue = None
        self._worker_manager = None
        self._worker_shared_stats = None
        self._worker_training_finished_event = None

    def _run_match_with_process_timeout(
        self,
        game_key: str,
        game_cls,
        alg1_key: str,
        alg1_config: dict,
        alg2_key: str,
        alg2_config: dict
    ) -> dict:
        """
        Ejecuta una partida en un proceso separado y controla el timeout total
        de la partida.

        Si la partida termina bien, recoge el resultado desde output_queue.
        Si la partida se queda bloqueada, mata el proceso y devuelve un resultado
        marcado como inválido.
        """

        # Cola usada para recibir el resultado desde el proceso hijo.
        # En la versión persistente la cola se crea una vez y se reutiliza.
        self._start_process_worker()
        output_queue = self._worker_output_queue

        # Memoria compartida para conservar las últimas estadísticas incluso
        # si el proceso hijo tiene que ser terminado por timeout.
        shared_stats = self._worker_shared_stats
        shared_stats.clear()

        # Evento usado para saber cuándo ha terminado el pre-entrenamiento MCCFR.
        # El tiempo de entrenamiento queda fuera del timeout total de la partida.
        training_finished_event = self._worker_training_finished_event
        training_finished_event.clear()

        # Creamos un proceso separado para ejecutar una única partida.
        # Ahora el proceso se mantiene vivo y recibe cada partida mediante task_queue.
        process = self._worker_process

        # Arrancamos el proceso hijo.
        # _start_process_worker() ya lo ha arrancado si no existía.
        self._worker_task_queue.put({
            "game_key": game_key,
            "game_cls": game_cls,
            "alg1_key": alg1_key,
            "alg1_config": alg1_config,
            "alg2_key": alg2_key,
            "alg2_config": alg2_config,
            "move_timeout_seconds": self.move_timeout_seconds,
            "save_decisions": self.save_decisions
        })

        # Esperamos a que termine el pre-entrenamiento MCCFR.
        # Este tiempo no consume match_timeout_seconds.
        while process.is_alive() and not training_finished_event.wait(timeout=0.1):
            pass

        # Medimos cuánto tarda esta partida.
        started_at = time.perf_counter()

        result = None
        match_timed_out = False
        deadline = started_at + self.match_timeout_seconds

        # Esperamos como máximo match_timeout_seconds.
        # No hacemos un join ciego: leemos la cola mientras esperamos para poder
        # reaccionar inmediatamente a un AlgorithmTimeout de movimiento.
        while result is None:
            remaining = deadline - time.perf_counter()

            if remaining <= 0:
                match_timed_out = True
                break

            try:
                result = output_queue.get(timeout=min(0.1, remaining))
            except queue.Empty:
                if process is None or not process.is_alive():
                    break

        # Si después del timeout el proceso sigue vivo, significa que la partida
        # se ha quedado bloqueada o tarda demasiado.
        if result is None and match_timed_out:
            # Matamos el proceso completo.
            elapsed_time = time.perf_counter() - started_at
            latest_stats = shared_stats.get("data")
            training_elapsed_time = shared_stats.get("training_elapsed_time", 0.0)

            self._stop_process_worker(force=True)

            result = {
                "status": "match_timeout",
                "valid": False,
                "game": {
                    "key": game_key,
                    "name": game_cls().name
                },
                "player1": _public_algorithm_config(alg1_key, alg1_config),
                "player2": _public_algorithm_config(alg2_key, alg2_config),
                "invalid_algorithm": "unknown",
                "invalid_player_id": None,
                "reason": (
                    "La partida completa ha superado el límite de tiempo. "
                    "No se puede determinar con seguridad qué algoritmo se quedó bloqueado."
                ),
                "elapsed_time": elapsed_time,
                "training_elapsed_time": training_elapsed_time
            }

            if latest_stats is not None:
                result["stats"] = latest_stats

            return result

        # Si el proceso terminó, intentamos leer el resultado que dejó en la cola.
        # En el worker persistente el proceso normalmente sigue vivo después de una
        # partida válida; el resultado ya se ha obtenido arriba desde output_queue.
        if result is not None:
            if result.get("status") == "invalid_algorithm_for_game":
                # El hijo ya ha identificado qué algoritmo superó el timeout.
                # Matamos inmediatamente el proceso para detener también su hilo.
                self._stop_process_worker(force=True)

            return result

        # Si el proceso terminó pero no dejó resultado, lo marcamos como error.
        elapsed_time = time.perf_counter() - started_at
        latest_stats = shared_stats.get("data")
        training_elapsed_time = shared_stats.get("training_elapsed_time", 0.0)

        self._stop_process_worker(force=True)

        result = {
            "status": "error",
            "valid": False,
            "game": {
                "key": game_key,
                "name": game_cls().name
            },
            "player1": _public_algorithm_config(alg1_key, alg1_config),
            "player2": _public_algorithm_config(alg2_key, alg2_config),
            "reason": "El proceso terminó sin devolver resultado.",
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time
        }

        if latest_stats is not None:
            result["stats"] = latest_stats

        return result

    def _record_match_result(self, match_result: dict) -> None:
        """
        Añade el resultado de una partida a la estructura general del torneo.

        También actualiza el resumen:
        - total de partidas
        - partidas válidas
        - partidas inválidas
        - errores
        """

        # Aumentamos el total de partidas ejecutadas.
        self.results["summary"]["total_matches"] += 1

        # Guardamos el resultado completo de la partida.
        self.results["matches"].append(match_result)

        status = match_result.get("status")

        # Si la partida fue válida, aumentamos valid_matches.
        if match_result.get("valid"):
            self.results["summary"]["valid_matches"] += 1
            return

        # Si no fue válida, distinguimos entre error general e inválida por timeout/fallo.
        if status == "error":
            self.results["summary"]["errors"] += 1
        else:
            self.results["summary"]["invalid_matches"] += 1

        # Si sabemos qué algoritmo falló, lo guardamos agrupado por juego.
        game_name = match_result.get("game", {}).get("name", "unknown")
        invalid_algorithm = match_result.get("invalid_algorithm")

        if invalid_algorithm:
            if game_name not in self.results["invalid_algorithms_by_game"]:
                self.results["invalid_algorithms_by_game"][game_name] = []

            entry = {
                "algorithm": invalid_algorithm,
                "reason": match_result.get("reason", "")
            }

            # Evitamos duplicados exactos.
            if entry not in self.results["invalid_algorithms_by_game"][game_name]:
                self.results["invalid_algorithms_by_game"][game_name].append(entry)

    def _save_results(self) -> None:
        """
        Guarda todos los resultados acumulados en un único fichero JSON.

        A diferencia de StatsManager.save(), esto se hace una sola vez,
        al final del torneo completo.
        """

        path = Path(self.results_file)

        # Creamos la carpeta si no existe.
        path.parent.mkdir(parents=True, exist_ok=True)

        # Guardamos todo el torneo en JSON.
        with path.open("w", encoding="utf-8") as file:
            json.dump(self.results, file, indent=4, ensure_ascii=False)