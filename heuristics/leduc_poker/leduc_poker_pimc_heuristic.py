from generic.heuristic import Heuristic

from juegos.leduc_poker.cards import Card
from juegos.leduc_poker.game_state import LeducPokerGameState
from juegos.leduc_poker.forward_model import LeducPokerForwardModel


class LeducPokerPIMCHeuristic(
    Heuristic[LeducPokerGameState]
):

    def evaluate(
        self,
        state: LeducPokerGameState,
        ai_player: int
    ) -> float:
        model = LeducPokerForwardModel()

        # Si ya estamos en un estado terminal, usamos exactamente la utilidad
        # definida por el ForwardModel del juego.
        if state.is_terminal:
            return model.evaluate_terminal(state, ai_player)

        opponent = 2 if ai_player == 1 else 1

        my_card = state.private_cards[ai_player]
        opponent_card = state.private_cards[opponent]

        if my_card is None or opponent_card is None:
            return 0.0

        # En una determinización conocemos también el orden hipotético del mazo.
        # El ForwardModel revela la carta pública mediante deck.pop(), por lo que
        # antes de la segunda ronda la futura carta pública es deck[-1].
        if state.public_card is not None:
            public_card = state.public_card
        elif state.deck:
            public_card = state.deck[-1]
        else:
            return 0.0

        my_strength = self._hand_strength(
            my_card,
            public_card
        )
        opponent_strength = self._hand_strength(
            opponent_card,
            public_card
        )

        pot = state.pot
        own_contribution = state.contributions[ai_player]

        # Valor estimado si el estado terminase en showdown.
        if my_strength > opponent_strength:
            net_utility = pot - own_contribution
        elif opponent_strength > my_strength:
            net_utility = -own_contribution
        else:
            net_utility = (pot / 2.0) - own_contribution

        normalized = (
            net_utility
            / LeducPokerForwardModel.MAX_PLAYER_CONTRIBUTION
        )

        # Se reservan +1 y -1 para resultados terminales reales.
        return max(-0.99, min(0.99, normalized))

    def _hand_strength(
        self,
        private_card: Card,
        public_card: Card
    ) -> tuple[int, int]:
        """
        Una pareja con la carta pública vence siempre a una carta alta.
        Si ninguno forma pareja, se compara el rango: Rey > Reina > Jota.
        """
        pair = 1 if private_card == public_card else 0
        return pair, private_card.value
