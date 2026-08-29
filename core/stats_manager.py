from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path


class StatsManager:
    """
    Gestor de estadísticas.

    Responsabilidades:
    - Llevar estadísticas agregadas de una o varias partidas
    - Registrar resultados durante la ejecución
    - Guardar todo en un fichero JSON

    Idea:
    - Match le va notificando lo que ocurre
    - MatchRunner, al final, llama a save()

    Si no se crea StatsManager, entonces no se guarda nada.
    """

    def __init__(self, file_path: str, game_name: str, players: list, save_decisions: bool = True, on_stats_update=None):
        self.file_path = file_path
        self.game_name = game_name
        self.players = players
        self.save_decisions = save_decisions
        self.on_stats_update = on_stats_update
        self.original_player_keys = {
            id(player): str(index + 1)
            for index, player in enumerate(players)
        }
        self.current_player_keys = {}
        self.current_player_names = {}
        self.set_player_order(players)

        # Estructura interna de datos que luego se exportará a JSON
        self.data = {
            "game": self.game_name,
            "players": {
                str(player.player_id): player.name
                for player in players
            },
            "summary": {
                "games": 0,
                "p1_wins": 0,
                "p2_wins": 0,
                "draws": 0,
                "invalid_games": 0,
                "errors": 0
            },
            "search_stats": {
                "1": {
                    "nodes_visited": 0,
                    "cutoffs": 0,
                    "elapsed_time": 0.0,
                    "max_depth": 0,
                    "ai_turns": 0
                },
                "2": {
                    "nodes_visited": 0,
                    "cutoffs": 0,
                    "elapsed_time": 0.0,
                    "max_depth": 0,
                    "ai_turns": 0
                }
            },
            "matches": []
        }

    def set_player_order(self, players: list):
        """
        Actualiza qué algoritmo ocupa actualmente los IDs 1 y 2.
        """
        self.current_player_keys = {
            player.player_id: self.original_player_keys[id(player)]
            for player in players
        }
        self.current_player_names = {
            player.player_id: player.name
            for player in players
        }

    def record_ai_turn(self, player_id: int, stats):
        """
        Registra estadísticas de búsqueda de una IA en un turno.

        Se espera que 'stats' tenga atributos como:
        - nodes_visited
        - cutoffs
        - elapsed_time
        - max_depth

        Si stats es None, no hace nada.
        """
        if stats is None:
            return

        player_key = self.current_player_keys[player_id]
        entry = self.data["search_stats"][player_key]

        self._accumulate_stats(entry, stats)
        entry["ai_turns"] += 1

        # Además de las estadísticas globales, guardamos las estadísticas
        # correspondientes a esta partida concreta. Así una partida que falle
        # conserva sus propios nodos, rollouts, profundidad, tiempo, etc.
        if self.data["matches"]:
            current_match = self.data["matches"][-1]

            if current_match.get("status") == "in_progress":
                match_entry = current_match["search_stats"][player_key]
                self._accumulate_stats(match_entry, stats)
                match_entry["ai_turns"] += 1

        self._notify_update()

    def record_ai_training(self, player_id: int, stats):
        """
        Registra estadísticas producidas durante el entrenamiento previo de una IA.

        Se guardan dentro de search_stats igual que las métricas de búsqueda de
        los demás algoritmos, pero no incrementan ai_turns porque el entrenamiento
        ocurre antes de elegir un movimiento real de la partida.

        El tiempo del warmup no se suma a elapsed_time. De esta forma:
        - elapsed_time contiene únicamente tiempo de decisiones reales;
        - training_elapsed_time contiene únicamente tiempo de entrenamiento MCCFR;
        - cache_load_time contiene únicamente tiempo de carga de la caché persistente.
        """
        if stats is None:
            return

        player_key = self.current_player_keys[player_id]
        entry = self.data["search_stats"][player_key]

        self._accumulate_training_stats(entry, stats)

        if self.data["matches"]:
            current_match = self.data["matches"][-1]

            if current_match.get("status") == "in_progress":
                match_entry = current_match["search_stats"][player_key]
                self._accumulate_training_stats(match_entry, stats)

        self._notify_update()

    def start_match(self, match_number: int):
        """
        Registra el inicio de una partida.

        Se crea la entrada antes de ejecutar el primer movimiento para que,
        si la partida termina por timeout o error, los datos parciales sigan
        estando disponibles.
        """
        existing_match = self._find_match(match_number)

        if existing_match is not None:
            return

        match_data = {
            "match_number": match_number,
            "status": "in_progress",
            "valid": False,
            "player1": self.current_player_names[1],
            "player2": self.current_player_names[2],
            "winner": None,
            "search_stats": {
                "1": {
                    "nodes_visited": 0,
                    "cutoffs": 0,
                    "elapsed_time": 0.0,
                    "max_depth": 0,
                    "ai_turns": 0
                },
                "2": {
                    "nodes_visited": 0,
                    "cutoffs": 0,
                    "elapsed_time": 0.0,
                    "max_depth": 0,
                    "ai_turns": 0
                }
            }
        }

        if self.save_decisions:
            match_data["decisions"] = []

        self.data["matches"].append(match_data)
        self._notify_update()

    def record_decision(self, decision):
        """
        Guarda un movimiento inmediatamente después de que se haya aplicado.

        Así los movimientos ya completados no se pierden si la partida termina
        posteriormente por timeout o por cualquier otro error.
        """
        if not self.save_decisions or not self.data["matches"]:
            return

        current_match = self.data["matches"][-1]

        if current_match.get("status") != "in_progress":
            return

        current_match.setdefault("decisions", []).append(
            self._make_json_safe(decision)
        )

        self._notify_update()

    def record_match_failure(
        self,
        match_number: int,
        status: str,
        reason: str,
        invalid_algorithm: str | None = None,
        invalid_player_id: int | None = None
    ):
        """
        Registra una partida que no ha podido terminar correctamente.

        Los movimientos y estadísticas registrados antes del fallo se conservan.
        """
        match_data = self._find_match(match_number)

        if match_data is None:
            self.start_match(match_number)
            match_data = self._find_match(match_number)

        match_data["status"] = status
        match_data["valid"] = False
        match_data["winner"] = None
        match_data["reason"] = reason

        if invalid_algorithm is not None:
            match_data["invalid_algorithm"] = invalid_algorithm

        if invalid_player_id is not None:
            match_data["invalid_player_id"] = invalid_player_id

        self.data["summary"]["invalid_games"] += 1

        if status == "error":
            self.data["summary"]["errors"] += 1

        self._notify_update()

    def record_match_result(
        self,
        match_number: int,
        winner: int | None,
        decisions: list | None = None
    ):
        """
        Registra el resultado final de una partida.
        """
        self.data["summary"]["games"] += 1

        if winner is None:
            self.data["summary"]["draws"] += 1
        else:
            winner_key = self.current_player_keys[winner]

            if winner_key == "1":
                self.data["summary"]["p1_wins"] += 1
            elif winner_key == "2":
                self.data["summary"]["p2_wins"] += 1

        match_data = self._find_match(match_number)

        if match_data is None:
            match_data = {
                "match_number": match_number,
                "player1": self.current_player_names[1],
                "player2": self.current_player_names[2]
            }
            self.data["matches"].append(match_data)

        match_data["status"] = "valid"
        match_data["valid"] = True
        match_data["winner"] = winner
        match_data.pop("reason", None)
        match_data.pop("invalid_algorithm", None)
        match_data.pop("invalid_player_id", None)

        if self.save_decisions:
            match_data["decisions"] = self._make_json_safe(decisions or [])

        self._notify_update()

    def merge_external_data(
        self,
        external_data: dict | None,
        match_number: int,
        failure_status: str | None = None,
        failure_reason: str | None = None,
        invalid_algorithm: str | None = None,
        invalid_player_id: int | None = None
    ):
        """
        Incorpora a este StatsManager las estadísticas de una partida ejecutada
        en otro proceso.

        Si el proceso fue terminado por timeout de partida, la última entrada
        'in_progress' se convierte en una partida inválida sin perder los
        movimientos ni las estadísticas ya registradas.
        """
        if external_data is None:
            external_data = {}

        external_search_stats = external_data.get("search_stats", {})

        for player_key in ("1", "2"):
            source = external_search_stats.get(player_key, {})
            target = self.data["search_stats"][player_key]

            self._merge_stats_dict(target, source)

        external_summary = external_data.get("summary", {})

        for key in (
            "games",
            "p1_wins",
            "p2_wins",
            "draws",
            "invalid_games",
            "errors"
        ):
            self.data["summary"][key] += external_summary.get(key, 0)

        matches = self._make_json_safe(
            external_data.get("matches", [])
        )

        if matches:
            match_data = matches[-1]

            if failure_status is not None and match_data.get("status") == "in_progress":
                match_data["status"] = failure_status
                match_data["valid"] = False
                match_data["winner"] = None
                match_data["reason"] = failure_reason or ""

                if invalid_algorithm is not None:
                    match_data["invalid_algorithm"] = invalid_algorithm

                if invalid_player_id is not None:
                    match_data["invalid_player_id"] = invalid_player_id

                self.data["summary"]["invalid_games"] += 1

                if failure_status == "error":
                    self.data["summary"]["errors"] += 1

            self.data["matches"].append(match_data)

        else:
            match_data = {
                "match_number": match_number,
                "status": failure_status or "error",
                "valid": False,
                "player1": self.current_player_names[1],
                "player2": self.current_player_names[2],
                "winner": None,
                "reason": failure_reason or "La partida terminó sin devolver datos."
            }

            if self.save_decisions:
                match_data["decisions"] = []

            if invalid_algorithm is not None:
                match_data["invalid_algorithm"] = invalid_algorithm

            if invalid_player_id is not None:
                match_data["invalid_player_id"] = invalid_player_id

            self.data["matches"].append(match_data)
            self.data["summary"]["invalid_games"] += 1

            if match_data["status"] == "error":
                self.data["summary"]["errors"] += 1

        self._notify_update()

    def _accumulate_training_stats(self, entry: dict, stats):
        """
        Acumula las métricas del pre-entrenamiento sin mezclar su elapsed_time
        con el tiempo empleado por la IA durante los movimientos reales.

        unknown_information_sets tampoco se suma aquí porque el warmup obtiene
        una acción que se descarta y no representa una decisión de la partida.

        Las métricas que describen el entrenamiento original se conservan como
        un único snapshot. Esto evita multiplicarlas por el número de partidas
        cuando cada proceso vuelve a cargar la misma caché persistente.
        """
        stats_values = (
            vars(stats)
            if hasattr(stats, "__dict__")
            else {}
        )

        training_snapshot_keys = {
            "nodes_visited",
            "cutoffs",
            "max_depth",
            "iterations_completed",
            "information_sets",
            "terminal_states",
            "actions_evaluated",
            "regret_updates",
            "strategy_updates",
            "sampled_actions",
            "training_elapsed_time"
        }

        cumulative_runtime_keys = {
            "cache_loads",
            "cache_load_time"
        }

        for key, value in stats_values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue

            if key in ("elapsed_time", "unknown_information_sets"):
                continue

            if key in training_snapshot_keys:
                entry[key] = max(entry.get(key, 0), value)
            elif key in cumulative_runtime_keys:
                entry[key] = entry.get(key, 0) + value
            elif key.startswith("max_"):
                entry[key] = max(entry.get(key, 0), value)
            else:
                entry[key] = entry.get(key, 0) + value

    def _accumulate_stats(self, entry: dict, stats):
        """
        Acumula todas las métricas numéricas expuestas por el objeto de estadísticas.

        Se mantienen los campos comunes existentes y, si un algoritmo ofrece
        métricas adicionales como rollouts, también se guardan automáticamente.
        """
        stats_values = (
            vars(stats)
            if hasattr(stats, "__dict__")
            else {}
        )

        for key, value in stats_values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue

            if key.startswith("max_") or key == "information_sets":
                entry[key] = max(entry.get(key, 0), value)
            else:
                entry[key] = entry.get(key, 0) + value

    def _merge_stats_dict(self, target: dict, source: dict):
        """
        Combina dos bloques de estadísticas ya serializados.

        Cuando el bloque contiene métricas MCCFR de entrenamiento, las métricas
        del entrenamiento original se conservan una sola vez. En cambio, el tiempo
        de jugadas, los turnos, las cargas de caché y los Information Sets desconocidos
        sí se acumulan entre partidas.
        """
        is_mccfr_training_block = (
            source.get("iterations_completed", 0) > 0
            or "training_elapsed_time" in source
        )

        mccfr_training_snapshot_keys = {
            "nodes_visited",
            "cutoffs",
            "max_depth",
            "iterations_completed",
            "information_sets",
            "terminal_states",
            "actions_evaluated",
            "regret_updates",
            "strategy_updates",
            "sampled_actions",
            "training_elapsed_time"
        }

        for key, value in source.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue

            if is_mccfr_training_block and key in mccfr_training_snapshot_keys:
                target[key] = max(target.get(key, 0), value)
            elif key.startswith("max_") or key == "information_sets":
                target[key] = max(target.get(key, 0), value)
            else:
                target[key] = target.get(key, 0) + value

    def _find_match(self, match_number: int):
        for match_data in reversed(self.data["matches"]):
            if match_data.get("match_number") == match_number:
                return match_data

        return None

    def _notify_update(self):
        if self.on_stats_update is not None:
            self.on_stats_update(self.data)

    def _make_json_safe(self, value):
        """
        Convierte acciones y otros objetos de Python a una estructura
        que se pueda guardar directamente en JSON.
        """
        if isinstance(value, Enum):
            return self._make_json_safe(value.value)

        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if is_dataclass(value):
            return self._make_json_safe(asdict(value))

        if isinstance(value, dict):
            return {
                str(key): self._make_json_safe(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple, set)):
            return [
                self._make_json_safe(item)
                for item in value
            ]

        if hasattr(value, "__dict__"):
            return {
                key: self._make_json_safe(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }

        return str(value)

    def get_summary(self) -> dict:
        """
        Devuelve el resumen agregado.
        Útil para que MatchRunner lo imprima o lo use sin tocar self.data directamente.
        """
        return self.data["summary"]

    def get_search_stats_for_player(self, player_id: int) -> dict:
        return self.data["search_stats"][str(player_id)]

    def save(self):
        """
        Guarda el contenido en JSON.
        Si hace falta, crea las carpetas intermedias.
        """
        path = Path(self.file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)