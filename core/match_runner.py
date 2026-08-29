from __future__ import annotations

import multiprocessing
import queue
import time
import traceback

from core.match import Match
from core.stats_manager import StatsManager
from generic.tournament_runner import (
    AlgorithmExecutionError,
    AlgorithmTimeout,
    TimedAIPlayer
)


def _run_timed_match_worker(
    game_cls,
    player_configs: list,
    match_number: int,
    show_board: bool,
    move_timeout_seconds: float,
    output_queue,
    shared_stats,
    training_finished_event
):
    """
    Ejecuta una partida IA vs IA dentro de un proceso separado.

    De esta forma se puede aplicar un timeout total de partida y recuperar,
    mediante memoria compartida, las estadísticas y movimientos completados
    antes de que el proceso tenga que ser terminado.
    """
    started_at = None
    training_started_at = None
    training_elapsed_time = 0.0
    stats_manager = None

    try:
        game = game_cls()

        players = [
            TimedAIPlayer(
                name=config["name"],
                player_id=config["player_id"],
                algorithm_fn=config["algorithm_fn"],
                algorithm_params=config["algorithm_params"],
                timeout_seconds=move_timeout_seconds
            )
            for config in player_configs
        ]

        stats_manager = StatsManager(
            file_path="__not_saved_here__.json",
            game_name=game.name,
            players=players,
            save_decisions=True,
            on_stats_update=lambda data: shared_stats.__setitem__("data", data)
        )
        shared_stats["data"] = stats_manager.data

        match = Match(
            game=game,
            players=players,
            show_board=show_board,
            stats_manager=stats_manager
        )

        # El pre-entrenamiento/carga de MCCFR se ejecuta antes de iniciar el
        # timeout total de la partida. Tampoco pasa por TimedAIPlayer, por lo
        # que no consume el timeout por movimiento.
        training_started_at = time.perf_counter()
        match.warmup_mccfr()
        training_elapsed_time = time.perf_counter() - training_started_at
        shared_stats["training_elapsed_time"] = training_elapsed_time

        # El tiempo de partida empieza únicamente cuando MCCFR ya está preparado.
        started_at = time.perf_counter()

        # Avisamos al proceso principal de que ya puede empezar a contar
        # match_timeout_seconds.
        training_finished_event.set()

        final_state = match.run(
            match_number=match_number,
            show_match_header=True
        )

        output_queue.put({
            "status": "valid",
            "valid": True,
            "winner": final_state.winner,
            "elapsed_time": time.perf_counter() - started_at,
            "training_elapsed_time": training_elapsed_time,
            "stats": stats_manager.data
        })

    except AlgorithmTimeout as exc:
        if started_at is not None:
            elapsed_time = time.perf_counter() - started_at
        else:
            elapsed_time = 0.0

        if training_started_at is not None and not training_finished_event.is_set():
            training_elapsed_time = time.perf_counter() - training_started_at

        training_finished_event.set()

        output_queue.put({
            "status": "move_timeout",
            "valid": False,
            "invalid_algorithm": exc.algorithm_name,
            "invalid_player_id": exc.player_id,
            "reason": str(exc),
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time,
            "stats": (
                stats_manager.data
                if stats_manager is not None
                else shared_stats.get("data")
            )
        })

    except AlgorithmExecutionError as exc:
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
            "invalid_algorithm": exc.algorithm_name,
            "invalid_player_id": exc.player_id,
            "reason": str(exc),
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time,
            "stats": (
                stats_manager.data
                if stats_manager is not None
                else shared_stats.get("data")
            )
        })

    except Exception as exc:
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
            "reason": str(exc),
            "traceback": traceback.format_exc(),
            "elapsed_time": elapsed_time,
            "training_elapsed_time": training_elapsed_time,
            "stats": (
                stats_manager.data
                if stats_manager is not None
                else shared_stats.get("data")
            )
        })


def _run_timed_match_worker_loop(
    game_cls,
    show_board: bool,
    move_timeout_seconds: float,
    task_queue,
    output_queue,
    shared_stats,
    training_finished_event
):
    """
    Mantiene vivo un único proceso para ejecutar varias partidas IA vs IA.

    Cada partida sigue usando TimedAIPlayer para detectar el timeout por movimiento,
    pero el proceso no se destruye después de una partida válida. De esta forma,
    las cachés globales de los algoritmos, como _MCCFR_CACHE, permanecen en RAM
    entre partidas.

    Si una partida sufre un timeout por movimiento, el proceso principal terminará
    este worker completo, porque el hilo del algoritmo que excedió el timeout puede
    seguir ejecutándose aunque ThreadPoolExecutor deje de esperarlo.
    """

    while True:
        task = task_queue.get()

        # None se utiliza como señal de cierre limpio del worker.
        if task is None:
            return

        # Eliminamos las estadísticas de la partida anterior para que, si esta
        # partida tiene que ser terminada, shared_stats solo contenga datos actuales.
        shared_stats.clear()
        training_finished_event.clear()

        _run_timed_match_worker(
            game_cls=game_cls,
            player_configs=task["player_configs"],
            match_number=task["match_number"],
            show_board=show_board,
            move_timeout_seconds=move_timeout_seconds,
            output_queue=output_queue,
            shared_stats=shared_stats,
            training_finished_event=training_finished_event
        )


class MatchRunner:
    """
    Orquestador de una o varias partidas.

    Responsabilidades:
    - Recibir el juego y los jugadores
    - Ejecutar una o varias partidas
    - Crear el StatsManager si se ha indicado un archivo
    - Guardar el JSON al final si corresponde
    - Mostrar resultados agregados

    Idea:
    - MatchRunner coordina varias partidas
    - Match representa una partida concreta
    """

    def __init__(
        self,
        game,
        players: list,
        games_count: int = 1,
        show_board: bool = True,
        stats_file: str | None = None,
        move_timeout_seconds: float | None = None,
        match_timeout_seconds: float | None = None
    ):
        self.game = game
        self.players = players
        self.games_count = games_count
        self.show_board = show_board
        self.stats_file = stats_file
        self.move_timeout_seconds = move_timeout_seconds
        self.match_timeout_seconds = match_timeout_seconds

        self.stats_manager = None
        if self.stats_file:
            self.stats_manager = StatsManager(
                file_path=self.stats_file,
                game_name=self.game.name,
                players=self.players
            )

        # Recursos del proceso persistente usado en IA vs IA con timeouts.
        # Se crean una sola vez para todas las partidas y se destruyen al terminar.
        self._timed_worker_process = None
        self._timed_task_queue = None
        self._timed_output_queue = None
        self._timed_manager = None
        self._timed_shared_stats = None
        self._timed_training_finished_event = None

    def run(self):
        """
        Ejecuta todas las partidas configuradas.

        Devuelve:
        - stats_manager.data si hay StatsManager
        - None si no hay fichero de estadísticas
        """
        show_match_header = not (
            self.games_count == 1
            and any(player.is_human() for player in self.players)
        )

        original_player_ids = [
            player.player_id
            for player in self.players
        ]

        if self._use_ai_timeouts():
            self._start_timed_worker()

        try:
            for match_number in range(1, self.games_count + 1):
                if match_number % 2 == 1:
                    self.players[0].player_id = original_player_ids[0]
                    self.players[1].player_id = original_player_ids[1]
                else:
                    self.players[0].player_id = original_player_ids[1]
                    self.players[1].player_id = original_player_ids[0]

                if self.stats_manager is not None:
                    self.stats_manager.set_player_order(self.players)

                if self._use_ai_timeouts():
                    self._run_match_with_timeouts(
                        match_number=match_number
                    )
                else:
                    match = Match(
                        game=self.game,
                        players=self.players,
                        show_board=self.show_board,
                        stats_manager=self.stats_manager
                    )

                    try:
                        match.run(
                            match_number=match_number,
                            show_match_header=show_match_header
                        )
                    finally:
                        # Guardamos después de cada partida, incluso si ha fallado.
                        if self.stats_manager is not None:
                            self.stats_manager.save()

                # En IA vs IA con timeouts también persistimos inmediatamente
                # el resultado de cada partida antes de continuar con la siguiente.
                if self.stats_manager is not None:
                    self.stats_manager.save()
        finally:
            if self._use_ai_timeouts():
                self._stop_timed_worker()

            for player, player_id in zip(self.players, original_player_ids):
                player.player_id = player_id

            if self.stats_manager is not None:
                self.stats_manager.set_player_order(self.players)

        if self.stats_manager is not None:
            self.stats_manager.save()
            self.print_aggregated_stats()
            return self.stats_manager.data

        return None

    def _use_ai_timeouts(self) -> bool:
        """
        Indica si las partidas se deben ejecutar con límites de tiempo.

        Los límites automáticos se usan para IA vs IA. Las partidas con jugador
        humano mantienen el comportamiento normal.
        """
        return (
            self.move_timeout_seconds is not None
            and self.match_timeout_seconds is not None
            and all(player.is_ai() for player in self.players)
        )

    def _start_timed_worker(self):
        """
        Crea el proceso persistente usado para las partidas IA vs IA con timeout.

        Si ya existe un worker vivo, se reutiliza. Esto permite que las cachés
        globales de los algoritmos permanezcan cargadas entre partidas.
        """
        if (
            self._timed_worker_process is not None
            and self._timed_worker_process.is_alive()
        ):
            return

        # Si quedaron recursos de un worker anterior terminado, los limpiamos.
        self._stop_timed_worker(force=True)

        self._timed_task_queue = multiprocessing.Queue()
        self._timed_output_queue = multiprocessing.Queue()
        self._timed_manager = multiprocessing.Manager()
        self._timed_shared_stats = self._timed_manager.dict()
        self._timed_training_finished_event = multiprocessing.Event()

        self._timed_worker_process = multiprocessing.Process(
            target=_run_timed_match_worker_loop,
            args=(
                self.game.__class__,
                self.show_board,
                self.move_timeout_seconds,
                self._timed_task_queue,
                self._timed_output_queue,
                self._timed_shared_stats,
                self._timed_training_finished_event
            )
        )

        self._timed_worker_process.start()

    def _stop_timed_worker(self, force: bool = False):
        """
        Cierra el proceso persistente.

        Con force=True se termina inmediatamente el proceso completo. Se utiliza
        cuando un movimiento supera su timeout, porque el hilo del algoritmo que
        estaba ejecutándose no se puede matar de forma segura de manera aislada.
        """
        process = self._timed_worker_process

        if process is not None and process.is_alive():
            if force:
                process.terminate()
            else:
                try:
                    self._timed_task_queue.put(None)
                except Exception:
                    pass

                process.join(timeout=1.0)

                if process.is_alive():
                    process.terminate()

            process.join()

        for process_queue in (
            self._timed_task_queue,
            self._timed_output_queue
        ):
            if process_queue is not None:
                try:
                    process_queue.close()
                except Exception:
                    pass

        if self._timed_manager is not None:
            try:
                self._timed_manager.shutdown()
            except Exception:
                pass

        self._timed_worker_process = None
        self._timed_task_queue = None
        self._timed_output_queue = None
        self._timed_manager = None
        self._timed_shared_stats = None
        self._timed_training_finished_event = None

    def _run_match_with_timeouts(self, match_number: int):
        """
        Ejecuta una partida IA vs IA con timeout por movimiento y timeout total.

        La partida se ejecuta en otro proceso para poder terminarla por completo
        si supera el límite global. Las estadísticas y movimientos ya completados
        se mantienen en memoria compartida.
        """
        # El proceso se mantiene vivo entre partidas válidas. Si el worker anterior
        # fue terminado por un timeout, aquí se crea automáticamente uno nuevo.
        self._start_timed_worker()

        output_queue = self._timed_output_queue
        shared_stats = self._timed_shared_stats
        process = self._timed_worker_process

        # Limpiamos cualquier dato de la partida anterior antes de empezar.
        shared_stats.clear()

        player_configs = [
            {
                "name": player.name,
                "player_id": player.player_id,
                "algorithm_fn": player.algorithm_fn,
                "algorithm_params": player.algorithm_params
            }
            for player in self.players
        ]

        training_finished_event = self._timed_training_finished_event
        training_finished_event.clear()

        # Enviamos la partida al worker persistente en lugar de crear un proceso nuevo.
        self._timed_task_queue.put({
            "player_configs": player_configs,
            "match_number": match_number
        })

        # Esperamos a que termine el pre-entrenamiento/carga de MCCFR.
        # Este tiempo NO consume match_timeout_seconds.
        while process.is_alive() and not training_finished_event.wait(timeout=0.1):
            pass

        # El timeout total empieza únicamente después del warmup.
        started_at = time.perf_counter()

        result = None
        match_timed_out = False
        deadline = started_at + self.match_timeout_seconds

        # Esperamos el resultado mientras vigilamos también que el proceso siga vivo.
        # A diferencia de process.join(timeout), esto permite recibir inmediatamente
        # el AlgorithmTimeout enviado por el hijo y matar el proceso en ese momento.
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

        if result is None:
            latest_stats = shared_stats.get("data")
            training_elapsed_time = shared_stats.get("training_elapsed_time", 0.0)

            if match_timed_out:
                # Matamos el proceso completo.
                self._stop_timed_worker(force=True)

                result = {
                    "status": "match_timeout",
                    "valid": False,
                    "reason": (
                        "La partida completa ha superado el límite de tiempo "
                        f"de {self.match_timeout_seconds} segundos."
                    ),
                    "elapsed_time": time.perf_counter() - started_at,
                    "training_elapsed_time": training_elapsed_time,
                    "stats": latest_stats
                }
            else:
                # Si el proceso terminó pero no dejó resultado, lo marcamos como error.
                self._stop_timed_worker(force=True)

                result = {
                    "status": "error",
                    "valid": False,
                    "reason": "El proceso terminó sin devolver resultado.",
                    "elapsed_time": time.perf_counter() - started_at,
                    "training_elapsed_time": training_elapsed_time,
                    "stats": latest_stats
                }

        elif result.get("status") == "move_timeout":
            # El hilo ya ha comunicado qué algoritmo superó el timeout.
            # Lo matamos ahora mismo a nivel de proceso; no esperamos al timeout global.
            self._stop_timed_worker(force=True)

        if self.stats_manager is not None:
            self.stats_manager.merge_external_data(
                external_data=result.get("stats"),
                match_number=match_number,
                failure_status=(
                    None
                    if result.get("valid")
                    else result.get("status", "error")
                ),
                failure_reason=result.get("reason"),
                invalid_algorithm=result.get("invalid_algorithm"),
                invalid_player_id=result.get("invalid_player_id")
            )

        if not result.get("valid"):
            print(
                f"Partida {match_number} inválida: "
                f"{result.get('reason', 'Error desconocido')}"
            )

    def print_aggregated_stats(self):
        """
        Imprime por consola un resumen agregado de todas las partidas.
        Solo tiene sentido si existe StatsManager.
        """
        if self.stats_manager is None:
            return

        summary = self.stats_manager.get_summary()
        p1_name = self.players[0].name
        p2_name = self.players[1].name

        p1_stats = self.stats_manager.get_search_stats_for_player(1)
        p2_stats = self.stats_manager.get_search_stats_for_player(2)

        if self.games_count > 1:
            print("\n=== RESULTADOS AGREGADOS ===")
            print("Partidas:", summary["games"])
            print(f"Victorias {p1_name}:", summary["p1_wins"])
            print(f"Victorias {p2_name}:", summary["p2_wins"])
            print("Empates:", summary["draws"])
            print("Partidas inválidas:", summary.get("invalid_games", 0))

        if self.players[0].is_ai():
            print(f"\n--- Stats {p1_name} ---")

            if (
                "iterations_completed" in p1_stats
                or "training_elapsed_time" in p1_stats
            ):
                print("Nodos visitados (entrenamiento):", p1_stats.get("nodes_visited", 0))
                print("Podas:", p1_stats.get("cutoffs", 0))
                print("Máxima profundidad (entrenamiento):", p1_stats.get("max_depth", 0))
                print("Tiempo de jugadas:", p1_stats.get("elapsed_time", 0.0))
                if p1_stats.get("ai_turns", 0) > 0:
                    print(
                        "Tiempo medio por turno:",
                        p1_stats.get("elapsed_time", 0.0) / p1_stats["ai_turns"]
                    )
                print("Tiempo de entrenamiento:", p1_stats.get("training_elapsed_time", 0.0))
                print("Iteraciones completadas:", p1_stats.get("iterations_completed", 0))
                print("Information Sets:", p1_stats.get("information_sets", 0))
                print("Estados terminales:", p1_stats.get("terminal_states", 0))
                print("Acciones evaluadas:", p1_stats.get("actions_evaluated", 0))
                print("Actualizaciones de regret:", p1_stats.get("regret_updates", 0))
                print("Actualizaciones de estrategia:", p1_stats.get("strategy_updates", 0))
                print("Acciones muestreadas:", p1_stats.get("sampled_actions", 0))
                print(
                    "Information Sets desconocidos:",
                    p1_stats.get("unknown_information_sets", 0)
                )
                print("Cargas desde caché:", p1_stats.get("cache_loads", 0))
                print("Tiempo cargando caché:", p1_stats.get("cache_load_time", 0.0))
            else:
                print("Nodos visitados:", p1_stats["nodes_visited"])
                print("Podas:", p1_stats["cutoffs"])
                print("Máxima profundidad:", p1_stats["max_depth"])
                print("Tiempo total:", p1_stats["elapsed_time"])
                if p1_stats["ai_turns"] > 0:
                    print(
                        "Tiempo medio por turno:",
                        p1_stats["elapsed_time"] / p1_stats["ai_turns"]
                    )

        if self.players[1].is_ai():
            print(f"\n--- Stats {p2_name} ---")

            if (
                "iterations_completed" in p2_stats
                or "training_elapsed_time" in p2_stats
            ):
                print("Nodos visitados (entrenamiento):", p2_stats.get("nodes_visited", 0))
                print("Podas:", p2_stats.get("cutoffs", 0))
                print("Máxima profundidad (entrenamiento):", p2_stats.get("max_depth", 0))
                print("Tiempo de jugadas:", p2_stats.get("elapsed_time", 0.0))
                if p2_stats.get("ai_turns", 0) > 0:
                    print(
                        "Tiempo medio por turno:",
                        p2_stats.get("elapsed_time", 0.0) / p2_stats["ai_turns"]
                    )
                print("Tiempo de entrenamiento:", p2_stats.get("training_elapsed_time", 0.0))
                print("Iteraciones completadas:", p2_stats.get("iterations_completed", 0))
                print("Information Sets:", p2_stats.get("information_sets", 0))
                print("Estados terminales:", p2_stats.get("terminal_states", 0))
                print("Acciones evaluadas:", p2_stats.get("actions_evaluated", 0))
                print("Actualizaciones de regret:", p2_stats.get("regret_updates", 0))
                print("Actualizaciones de estrategia:", p2_stats.get("strategy_updates", 0))
                print("Acciones muestreadas:", p2_stats.get("sampled_actions", 0))
                print(
                    "Information Sets desconocidos:",
                    p2_stats.get("unknown_information_sets", 0)
                )
            else:
                print("Nodos visitados:", p2_stats["nodes_visited"])
                print("Podas:", p2_stats["cutoffs"])
                print("Máxima profundidad:", p2_stats["max_depth"])
                print("Tiempo total:", p2_stats["elapsed_time"])
                if p2_stats["ai_turns"] > 0:
                    print(
                        "Tiempo medio por turno:",
                        p2_stats["elapsed_time"] / p2_stats["ai_turns"]
                    )