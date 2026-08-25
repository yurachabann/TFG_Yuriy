from __future__ import annotations

from core.match import Match
from core.stats_manager import StatsManager


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
        stats_file: str | None = None
    ):
        self.game = game
        self.players = players
        self.games_count = games_count
        self.show_board = show_board
        self.stats_file = stats_file

        self.stats_manager = None
        if self.stats_file:
            self.stats_manager = StatsManager(
                file_path=self.stats_file,
                game_name=self.game.name,
                players=self.players
            )

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

                match = Match(
                    game=self.game,
                    players=self.players,
                    show_board=self.show_board,
                    stats_manager=self.stats_manager
                )
                match.run(match_number=match_number, show_match_header=show_match_header)
        finally:
            for player, player_id in zip(self.players, original_player_ids):
                player.player_id = player_id

            if self.stats_manager is not None:
                self.stats_manager.set_player_order(self.players)

        if self.stats_manager is not None:
            self.stats_manager.save()
            self.print_aggregated_stats()
            return self.stats_manager.data

        return None

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

        if self.players[0].is_ai():
            print(f"\n--- Stats {p1_name} ---")
            print("Nodos visitados:", p1_stats["nodes_visited"])
            print("Cutoffs:", p1_stats["cutoffs"])
            print("Máxima profundidad:", p1_stats["max_depth"])
            print("Tiempo total:", p1_stats["elapsed_time"])
            if p1_stats["ai_turns"] > 0:
                print("Tiempo medio por turno:", p1_stats["elapsed_time"] / p1_stats["ai_turns"])

        if self.players[1].is_ai():
            print(f"\n--- Stats {p2_name} ---")
            print("Nodos visitados:", p2_stats["nodes_visited"])
            print("Cutoffs:", p2_stats["cutoffs"])
            print("Máxima profundidad:", p2_stats["max_depth"])
            print("Tiempo total:", p2_stats["elapsed_time"])
            if p2_stats["ai_turns"] > 0:
                print("Tiempo medio por turno:", p2_stats["elapsed_time"] / p2_stats["ai_turns"])