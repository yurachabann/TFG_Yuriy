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

    def __init__(self, file_path: str, game_name: str, players: list, save_decisions: bool = True):
        self.file_path = file_path
        self.game_name = game_name
        self.players = players
        self.save_decisions = save_decisions
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
                "draws": 0
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

        entry["nodes_visited"] += getattr(stats, "nodes_visited", 0)
        entry["cutoffs"] += getattr(stats, "cutoffs", 0)
        entry["elapsed_time"] += getattr(stats, "elapsed_time", 0.0)
        entry["max_depth"] = max(entry["max_depth"], getattr(stats, "max_depth", 0))
        entry["ai_turns"] += 1

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

        match_data = {
            "match_number": match_number,
            "player1": self.current_player_names[1],
            "player2": self.current_player_names[2],
            "winner": winner
        }

        if self.save_decisions:
            match_data["decisions"] = self._make_json_safe(decisions or [])

        self.data["matches"].append(match_data)

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