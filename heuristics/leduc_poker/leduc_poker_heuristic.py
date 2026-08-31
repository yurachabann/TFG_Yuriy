from generic.heuristic import Heuristic

from juegos.leduc_poker.cards import Card, DECK_COMPOSITION
from juegos.leduc_poker.game_state import LeducPokerGameState
from juegos.leduc_poker.forward_model import LeducPokerForwardModel


class LeducPokerHeuristic(
    Heuristic[LeducPokerGameState]
):
    """
    Heurística para ISMCTS con límite de rollout en Leduc Poker.

    No consulta la carta privada real del rival. Calcula el valor esperado de
    llegar a showdown utilizando únicamente la información que conocería el
    jugador evaluado: su carta privada, la carta pública y el bote actual.
    """

    def evaluate(
        self,
        state: LeducPokerGameState,
        ai_player: int
    ) -> float:
        if state.is_terminal:
            model = LeducPokerForwardModel()
            value = model.evaluate_terminal(state, ai_player)
            return max(-0.99, min(0.99, value))

        my_card = state.private_cards[ai_player]
        if my_card is None:
            return 0.0

        scenarios = self._possible_showdown_scenarios(
            my_card=my_card,
            public_card=state.public_card
        )

        if not scenarios:
            return 0.0

        pot = state.pot
        own_contribution = state.contributions[ai_player]
        expected_net = 0.0

        for opponent_card, public_card in scenarios:
            my_strength = self._hand_strength(my_card, public_card)
            opponent_strength = self._hand_strength(
                opponent_card,
                public_card
            )

            if my_strength > opponent_strength:
                scenario_net = pot - own_contribution
            elif opponent_strength > my_strength:
                scenario_net = -own_contribution
            else:
                scenario_net = (pot / 2.0) - own_contribution

            expected_net += scenario_net

        expected_net /= len(scenarios)

        normalized = (
            expected_net
            / LeducPokerForwardModel.MAX_PLAYER_CONTRIBUTION
        )

        # +1 / -1 quedan reservados para utilidades terminales reales.
        return max(-0.99, min(0.99, normalized))

    def _possible_showdown_scenarios(
        self,
        my_card: Card,
        public_card: Card | None
    ) -> list[tuple[Card, Card]]:
        """
        Enumera escenarios compatibles sin utilizar la carta oculta real del rival.

        Antes de revelar la carta pública se consideran todas las combinaciones
        posibles de carta rival + futura carta pública. Después de revelarla,
        solamente varía la carta privada del rival.
        """
        remaining = DECK_COMPOSITION.copy()
        remaining.remove(my_card)

        scenarios = []

        if public_card is not None:
            remaining.remove(public_card)
            for opponent_card in remaining:
                scenarios.append((opponent_card, public_card))
            return scenarios

        # Cada carta física restante puede ser la carta del rival y cualquiera
        # de las otras cartas puede convertirse después en la carta pública.
        for opponent_index, opponent_card in enumerate(remaining):
            after_opponent = remaining.copy()
            after_opponent.pop(opponent_index)

            for future_public in after_opponent:
                scenarios.append((opponent_card, future_public))

        return scenarios

    def _hand_strength(
        self,
        private_card: Card,
        public_card: Card
    ) -> tuple[int, int]:
        pair = 1 if private_card == public_card else 0
        return pair, private_card.value
