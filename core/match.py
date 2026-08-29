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
        self.mccfr_warmup_stats = []
        self.mccfr_warmup_completed = False

    def warmup_mccfr(self):
        """
        Ejecuta el pre-entrenamiento MCCFR una sola vez.

        TournamentRunner puede llamar a este método antes de iniciar el
        temporizador de la partida. Match.run() también lo llama para mantener
        el mismo comportamiento en las partidas normales.
        """
        if self.mccfr_warmup_completed:
            return self.mccfr_warmup_stats

        self.mccfr_warmup_stats = self._warmup_mccfr_if_needed()
        self.mccfr_warmup_completed = True

        return self.mccfr_warmup_stats

    def _warmup_mccfr_if_needed(self):
        """
        Si alguno de los jugadores usa MCCFR, entrena el agente en el
        estado raíz inicial (antes de que nadie haga ningún movimiento).
        """
        warmup_stats = []

        for player in self.players.values():
            if player.is_ai() and "mccfr" in getattr(player.algorithm_fn, "__name__", ""):
                # Generamos el estado de información inicial del juego
                initial_info = self.model.create_information_state(
                    self.state,
                    player_id=player.player_id
                )
                # Forzamos el entrenamiento al inicio
                _, stats = player.algorithm_fn(
                    initial_info,
                    self.model,
                    **player.algorithm_params
                )
                warmup_stats.append((player.player_id, stats))

        return warmup_stats

    def run(self, match_number: int = 1, show_match_header: bool = True):
        """
        Ejecuta la partida completa y devuelve el estado final.
        """
        if show_match_header:
            print(f"\n=== Partida {match_number}: {self.game.name} ===")

        # En partidas normales el warmup se sigue ejecutando automáticamente.
        # En TournamentRunner ya habrá sido ejecutado antes de iniciar el timeout
        # de partida, y este método simplemente devolverá las estadísticas guardadas.
        self.warmup_mccfr()

        if self.stats_manager is not None:
            self.stats_manager.start_match(match_number)

            # MCCFR entrena antes de realizar el primer movimiento. Registramos
            # esas métricas dentro de las search_stats de esta misma partida.
            for player_id, stats in self.mccfr_warmup_stats:
                self.stats_manager.record_ai_training(player_id, stats)

        if self.show_board:
            self.game.print_board(self.state)

        decisions = []
        turn_number = 1

        try:
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

                # Guardamos el movimiento inmediatamente después de aplicarlo.
                # De esta forma, si la partida falla más adelante, los movimientos
                # completados hasta ese momento ya están dentro del StatsManager.
                if (
                    self.stats_manager is not None
                    and current_player.is_ai()
                    and self.stats_manager.save_decisions
                ):
                    self.stats_manager.record_decision(decisions[-1])

                # Mostrar por consola la acción de la IA si se quiere
                if self.show_board and current_player.is_ai():
                    print(f"[Jugador {current_player_id} - {current_player.name}]")
                    self.game.print_ai_action(action)

                if self.show_board:
                    self.game.print_board(self.state)

                turn_number += 1

        except Exception as exc:
            # Si una partida falla, conservamos igualmente todos los movimientos
            # y estadísticas que sí llegaron a completarse antes del error/timeout.
            if self.stats_manager is not None:
                status = (
                    "move_timeout"
                    if exc.__class__.__name__ == "AlgorithmTimeout"
                    else "error"
                )

                self.stats_manager.record_match_failure(
                    match_number=match_number,
                    status=status,
                    reason=str(exc),
                    invalid_algorithm=getattr(exc, "algorithm_name", None),
                    invalid_player_id=getattr(exc, "player_id", None)
                )

            raise

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