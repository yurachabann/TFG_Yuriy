from __future__ import annotations

from core.players.player import Player


class AIPlayer(Player):
    """
    Jugador controlado por IA.

    Encapsula:
    - el nombre visible del jugador
    - el identificador del jugador
    - la función del algoritmo
    - los parámetros opcionales del algoritmo

    Ejemplos de parámetros:
    - max_depth
    - heuristic
    - move_ordering
    - cualquier otro ajuste experimental
    """

    def __init__(
        self,
        name: str,
        player_id: int,
        algorithm_fn,
        algorithm_params: dict | None = None
    ):
        super().__init__(name=name, player_id=player_id)
        self.algorithm_fn = algorithm_fn
        self.algorithm_params = algorithm_params or {}

    def choose_action(self, state, game):
        """
        Pide una acción al algoritmo.

        Convención esperada:
            algorithm_fn(state_or_info_state, model, ai_player, **params) -> (action, stats)
        """
        model = game.create_model()

        # Si el modelo soporta información imperfecta (tiene create_information_state),
        # le pasamos la vista reducida del estado correspondiente a este jugador.
        if hasattr(model, "create_information_state"):
            input_state = model.create_information_state(state, self.player_id)
        else:
            input_state = state

        return self.algorithm_fn(
            input_state,
            model,
            self.player_id,
            **self.algorithm_params
        )

    def is_ai(self) -> bool:
        return True

    def get_algorithm_name(self) -> str:
        return self.name