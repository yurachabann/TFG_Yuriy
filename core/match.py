from __future__ import annotations


class Match:
    """
    Representa UNA sola partida.

    Responsabilidades:
    - Crear estado y modelo
    - Ejecutar la partida turno a turno
    - Pedir acciones a los jugadores
    - Aplicar acciones al estado
    - Notificar al StatsManager si existe

    Importante:
    - Match NO pregunta al usuario qué juego quiere
    - Match NO decide qué jugadores hay
    - Match solo ejecuta una partida con los objetos recibidos
    """

    def __init__(self, game, players: list, show_board: bool = True, stats_manager=None):
        self.game = game
        self.players = {player.player_id: player for player in players}
        self.show_board = show_board
        self.stats_manager = stats_manager

        self.state = self.game.create_state()
        self.model = self.game.create_model()

        # ============================================================
        # PRE-ENTRENAMIENTO (Si hay algún jugador MCCFR)
        # ============================================================
        self._warmup_mccfr_if_needed()

    def _warmup_mccfr_if_needed(self):
        """
        Si alguno de los jugadores usa MCCFR, entrena el agente en el
        estado raíz inicial (antes de que nadie haga ningún movimiento).
        """
        for player in self.players.values():
            if player.is_ai() and "mccfr" in getattr(player.algorithm_fn, "__name__", ""):
                # Generamos el estado de información inicial del juego
                initial_info = self.model.create_information_state(
                    self.state,
                    player_id=player.player_id
                )
                # Forzamos el entrenamiento al inicio
                player.algorithm_fn(initial_info, self.model, **player.algorithm_params)

    def run(self, match_number: int = 1, show_match_header: bool = True):
        """
        Ejecuta la partida completa y devuelve el estado final.
        """
        if show_match_header:
            print(f"\n=== Partida {match_number}: {self.game.name} ===")

        if self.show_board:
            self.game.print_board(self.state)

        decisions = []
        turn_number = 1

        while not self.state.is_terminal:
            current_player_id = self.state.current_player
            current_player = self.players[current_player_id]

            # El jugador decide la acción
            action, stats = current_player.choose_action(self.state, self.game)

            # Si hay estadísticas y el jugador es IA, las registramos
            if self.stats_manager is not None and current_player.is_ai():
                self.stats_manager.record_ai_turn(current_player_id, stats)
                if self.stats_manager.save_decisions:
                    decisions.append({
                        "turn_number": turn_number,
                        "player_id": current_player_id,
                        "player_name": current_player.name,
                        "action": action
                    })

            # Aplicamos la acción al estado
            self.model.advance(self.state, action)

            # Mostrar por consola la acción de la IA si se quiere
            if self.show_board and current_player.is_ai():
                print(f"[Jugador {current_player_id} - {current_player.name}]")
                self.game.print_ai_action(action)

            if self.show_board:
                self.game.print_board(self.state)

            turn_number += 1

        # Registrar resultado final
        if self.stats_manager is not None:
            self.stats_manager.record_match_result(
                match_number,
                self.state.winner,
                decisions
            )

        # Mostrar resultado por consola
        if self.state.winner is None:
            print("Empate")
        else:
            winner_player = self.players[self.state.winner]
            print(f"Gana jugador {self.state.winner} ({winner_player.name})")

        return self.state