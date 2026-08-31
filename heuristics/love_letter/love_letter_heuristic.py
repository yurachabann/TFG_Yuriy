from __future__ import annotations

from juegos.love_letter.cards import Card
from juegos.love_letter.game_state import LoveLetterGameState


class LoveLetterPIMCHeuristic:

    def __init__(
        self,
        eliminated_score: float = 10000.0,
        hand_value_weight: float = 20.0,
        protection_weight: float = 80.0,
        guard_threat_penalty: float = 500.0,
        baron_threat_penalty: float = 700.0,
        prince_princess_threat_penalty: float = 900.0
    ):
        # Puntuación interna utilizada como referencia para normalizar la heurística.
        # La victoria/derrota terminal real sigue siendo +1.0 / -1.0 en el ForwardModel.
        self.eliminated_score = eliminated_score

        # Peso que se aplica al valor numérico de la carta que conserva el jugador.
        # Cuanto mayor sea este valor, más importancia dará la heurística a tener una carta alta.
        self.hand_value_weight = hand_value_weight

        # Valor que se suma si la IA está protegida por HANDMAID.
        # También se usa como penalización si es el rival quien está protegido.
        self.protection_weight = protection_weight

        # Penalización aplicada si el rival puede amenazarnos con un GUARD
        # y, en la determinización actual, podría adivinar correctamente nuestra carta.
        self.guard_threat_penalty = guard_threat_penalty

        # Penalización aplicada si el rival tiene BARON y puede conservar
        # una carta de valor superior a la nuestra, pudiendo eliminarnos.
        self.baron_threat_penalty = baron_threat_penalty

        # Penalización aplicada si nosotros conservamos PRINCESS
        # y el rival tiene PRINCE, ya que podría obligarnos a descartarla y eliminarnos.
        self.prince_princess_threat_penalty = prince_princess_threat_penalty


    def evaluate(self, state: LoveLetterGameState, ai_player: int) -> float:
        """
        Evalúa un estado no terminal desde la perspectiva de ai_player.

        La puntuación final se normaliza al rango [-0.99, 0.99] para que
        una victoria terminal (+1.0) siempre sea mejor que cualquier estado
        no terminal y una derrota terminal (-1.0) siempre sea peor.
        """
        enemy_id = 2 if ai_player == 1 else 1

        # ------------------------------------------------------------
        # 1. ELIMINACIÓN
        # ------------------------------------------------------------
        if state.eliminated[ai_player]:
            return -0.99

        if state.eliminated[enemy_id]:
            return 0.99

        score = 0.0

        my_hand = state.hands[ai_player]
        enemy_hand = state.hands[enemy_id]

        # ------------------------------------------------------------
        # 2. VALOR DE LA CARTA CONSERVADA
        # ------------------------------------------------------------
        # Cuanto menos mazo queda, más importante es conservar una
        # carta alta para ganar por valor cuando termine la ronda.
        deck_progress = 1.0 / (len(state.deck) + 1)
        showdown_multiplier = 1.0 + (deck_progress * 4.0)

        if my_hand:
            # Busca la carta con el valor más alto dentro de nuestra mano.
            my_best_card = max(my_hand, key=lambda card: card.value)

            score += (
                my_best_card.value
                * self.hand_value_weight
                * showdown_multiplier
            )

        if enemy_hand:
            # Busca la carta con el valor más alto dentro de la mano rival.
            enemy_best_card = max(
                enemy_hand,
                key=lambda card: card.value
            )

            score -= (
                enemy_best_card.value
                * self.hand_value_weight
                * showdown_multiplier
            )

        # ------------------------------------------------------------
        # 3. PROTECCIÓN DE LA DONCELLA
        # ------------------------------------------------------------
        if state.protected[ai_player]:
            score += self.protection_weight

        if state.protected[enemy_id]:
            score -= self.protection_weight

        # ------------------------------------------------------------
        # 4. AMENAZAS INMEDIATAS DEL RIVAL
        # ------------------------------------------------------------
        # Con profundidad 1, normalmente Alpha-Beta evalúa el estado
        # justo después de nuestra acción. En ese momento puede ser ya
        # el turno rival y haber robado su segunda carta.
        if (
            not state.protected[ai_player]
            and state.current_player == enemy_id
            and my_hand
            and enemy_hand
        ):
            my_card = my_hand[0]

            # Guardia:
            # Si el rival tiene Guardia y nuestra carta no es Guardia,
            # en esta determinización puede adivinarla correctamente.
            if (
                Card.GUARD in enemy_hand
                and my_card != Card.GUARD
            ):
                score -= self.guard_threat_penalty

            # Barón:
            # Si el rival puede jugar Barón y conservar una carta de
            # mayor valor que la nuestra, puede eliminarnos.
            if Card.BARON in enemy_hand:
                remaining_cards = enemy_hand.copy()
                remaining_cards.remove(Card.BARON)

                if (
                    remaining_cards
                    and remaining_cards[0].value > my_card.value
                ):
                    score -= self.baron_threat_penalty

            # Príncipe contra Princesa:
            # Si conservamos la Princesa y el rival tiene Príncipe,
            # puede obligarnos a descartarla y eliminarnos.
            if (
                my_card == Card.PRINCESS
                and Card.PRINCE in enemy_hand
            ):
                score -= self.prince_princess_threat_penalty

        # ------------------------------------------------------------
        # 5. NORMALIZACIÓN
        # ------------------------------------------------------------
        # Los pesos anteriores trabajan internamente con valores del orden
        # de centenas/millares. Los dividimos por eliminated_score para
        # llevar la evaluación a una escala compatible con evaluate_terminal,
        # que devuelve +1.0 para victoria y -1.0 para derrota.
        normalized_score = score / self.eliminated_score

        # Se limita a [-0.99, 0.99] para reservar exactamente +1.0 y -1.0
        # a los estados terminales reales.
        return max(-0.99, min(0.99, normalized_score))
