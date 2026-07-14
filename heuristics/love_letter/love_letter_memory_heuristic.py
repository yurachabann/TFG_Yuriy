from collections import Counter

from generic.heuristic import Heuristic

from juegos.love_letter.love_letter import (
    LoveLetterGameState,
    CLASSIC_DECK,
    GUARD,
    PRIEST,
    BARON,
    HANDMAID,
    PRINCE,
    KING,
    COUNTESS,
    PRINCESS,
    other_player
)


class LoveLetterMemoryHeuristic(Heuristic[LoveLetterGameState]):
    """
    Heurística para evaluar estados no terminales de Love Letter.

    Esta heurística intenta medir si un estado es favorable para la IA
    utilizando únicamente la información que debería conocer:

    - cartas descartadas;
    - cartas retiradas boca arriba;
    - cartas de su propia mano;
    - carta rival conocida mediante Sacerdote;
    - protección de Doncella;
    - cartas que todavía podrían estar ocultas;
    - oportunidades tácticas con Guardia, Barón y Príncipe.

    Los estados terminales no se evalúan aquí.
    Se evalúan en LoveLetterForwardModel.evaluate_terminal().
    """

    # Peso de la diferencia entre el valor de nuestra carta
    # y el valor estimado de la carta rival.
    CARD_VALUE_WEIGHT = 100.0

    # Bonificación por estar protegido con Doncella.
    PROTECTION_BONUS = 80.0

    # Bonificación por conocer la carta rival mediante Sacerdote.
    KNOWN_HAND_BONUS = 120.0

    # Valor máximo de una oportunidad favorable con Guardia.
    GUARD_OPPORTUNITY_WEIGHT = 250.0

    # Peso aplicado a la diferencia de cartas al valorar el Barón.
    BARON_OPPORTUNITY_WEIGHT = 120.0

    # Valor de poder obligar al rival a descartar la Princesa.
    PRINCE_OPPORTUNITY_WEIGHT = 140.0

    # Pequeña bonificación por tener dos cartas diferentes,
    # ya que ofrece más posibilidades de elección.
    FLEXIBILITY_WEIGHT = 15.0

    def evaluate(
        self,
        state: LoveLetterGameState,
        ai_player: int
    ) -> float:
        """
        Evalúa un estado no terminal desde el punto de vista de ai_player.

        Un resultado positivo indica que el estado favorece a la IA.
        Un resultado negativo indica que favorece al rival.
        """

        # Obtenemos el identificador del jugador rival.
        opponent = other_player(ai_player)

        # Mano actual de la IA.
        # Normalmente tendrá una carta, pero durante su turno puede tener dos.
        ai_hand = state.hands[ai_player]

        # Si la IA tiene dos cartas, consideramos inicialmente
        # que podría conservar la de mayor valor.
        ai_best_card = max(ai_hand)

        # Calculamos las cartas que todavía podrían estar ocultas.
        unknown_cards = self.get_unknown_cards(
            state=state,
            ai_player=ai_player
        )

        # Comprobamos si la IA conoce la carta del rival
        # gracias al efecto del Sacerdote.
        known_opponent_card = state.known_hands[opponent]

        if known_opponent_card is not None:
            # Si conocemos la carta rival, usamos su valor real.
            opponent_estimated_value = float(known_opponent_card)
        else:
            # Si no la conocemos, usamos el valor medio
            # de todas las cartas que todavía podrían estar ocultas.
            opponent_estimated_value = self.average_card_value(
                unknown_cards
            )

        # --------------------------------------------------------
        # VALOR BASE DE LA MANO
        # --------------------------------------------------------

        # Comparamos nuestra mejor carta con la carta estimada del rival.
        #
        # Ejemplo:
        # nuestra carta = 7
        # carta rival estimada = 4
        #
        # diferencia = 3
        # puntuación = 3 * 100 = 300
        score = (
            ai_best_card - opponent_estimated_value
        ) * self.CARD_VALUE_WEIGHT

        # --------------------------------------------------------
        # PROTECCIÓN DE DONCELLA
        # --------------------------------------------------------

        # Estar protegido es favorable porque el rival
        # no puede utilizar cartas contra nosotros.
        if state.protected[ai_player]:
            score += self.PROTECTION_BONUS

        # Si el rival está protegido, tenemos menos opciones ofensivas.
        if state.protected[opponent]:
            score -= self.PROTECTION_BONUS

        # --------------------------------------------------------
        # INFORMACIÓN DEL SACERDOTE
        # --------------------------------------------------------

        # Conocer la carta rival permite tomar mejores decisiones.
        if known_opponent_card is not None:
            score += self.KNOWN_HAND_BONUS

        # Si el rival conoce nuestra carta, estamos en desventaja.
        if state.known_hands[ai_player] is not None:
            score -= self.KNOWN_HAND_BONUS

        # --------------------------------------------------------
        # OPORTUNIDADES TÁCTICAS
        # --------------------------------------------------------

        # Valora si tenemos Guardia y existe una buena posibilidad
        # de adivinar correctamente la carta rival.
        score += self.evaluate_guard_opportunity(
            state=state,
            ai_player=ai_player,
            unknown_cards=unknown_cards,
            known_opponent_card=known_opponent_card
        )

        # Valora si tenemos Barón y nuestra carta restante
        # probablemente sea superior a la del rival.
        score += self.evaluate_baron_opportunity(
            state=state,
            ai_player=ai_player,
            opponent_estimated_value=opponent_estimated_value
        )

        # Valora si tenemos Príncipe y existe posibilidad
        # de obligar al rival a descartar la Princesa.
        score += self.evaluate_prince_opportunity(
            state=state,
            ai_player=ai_player,
            unknown_cards=unknown_cards,
            known_opponent_card=known_opponent_card
        )

        # Tener dos cartas diferentes ofrece más flexibilidad
        # que tener dos cartas iguales.
        score += (
            len(set(ai_hand))
            * self.FLEXIBILITY_WEIGHT
        )

        # --------------------------------------------------------
        # PRINCESA
        # --------------------------------------------------------

        # Conservar la Princesa es bueno porque tiene el valor más alto.
        if PRINCESS in ai_hand:
            score += 120.0

            # Sin embargo, si todavía puede quedar un Príncipe
            # y no estamos protegidos, existe riesgo de eliminación.
            if (
                self.card_may_still_exist(PRINCE, unknown_cards)
                and not state.protected[ai_player]
            ):
                score -= 70.0

        # --------------------------------------------------------
        # CONDESA
        # --------------------------------------------------------

        # Si tenemos Condesa junto con Rey o Príncipe,
        # las reglas obligan a jugar la Condesa.
        #
        # Esto reduce nuestra libertad de elección,
        # por lo que aplicamos una pequeña penalización.
        if (
            COUNTESS in ai_hand
            and (KING in ai_hand or PRINCE in ai_hand)
        ):
            score -= 40.0

        return float(score)

    def get_unknown_cards(
        self,
        state: LoveLetterGameState,
        ai_player: int
    ) -> list[int]:
        """
        Calcula qué cartas todavía podrían estar ocultas.

        Empieza con la baraja completa y elimina toda la información
        visible para la IA:

        - cartas retiradas boca arriba;
        - descartes del jugador 1;
        - descartes del jugador 2;
        - cartas de la propia mano.

        No elimina la carta real del rival porque normalmente
        es información oculta.
        """

        # Counter guarda cuántas copias quedan de cada carta.
        #
        # Ejemplo:
        # Guardia: 5
        # Sacerdote: 2
        # Princesa: 1
        remaining = Counter(CLASSIC_DECK)

        # Lista con todas las cartas visibles para la IA.
        visible_cards = []

        # Cartas retiradas boca arriba al comenzar la partida.
        visible_cards.extend(state.removed_face_up)

        # Cartas jugadas o descartadas por ambos jugadores.
        visible_cards.extend(state.discarded[1])
        visible_cards.extend(state.discarded[2])

        # Cartas que tiene actualmente la propia IA.
        visible_cards.extend(state.hands[ai_player])

        # Restamos las cartas visibles de la baraja original.
        for card in visible_cards:
            if remaining[card] > 0:
                remaining[card] -= 1

        # Convertimos el Counter de nuevo en una lista.
        #
        # Ejemplo:
        # {1: 2, 2: 1}
        #
        # se convierte en:
        # [1, 1, 2]
        unknown_cards = []

        for card, amount in remaining.items():
            unknown_cards.extend([card] * amount)

        return unknown_cards

    def average_card_value(
        self,
        cards: list[int]
    ) -> float:
        """
        Devuelve el valor medio de una lista de cartas.

        Se utiliza para estimar la carta del rival
        cuando no la conocemos.
        """

        if not cards:
            return 0.0

        return sum(cards) / len(cards)

    def probability_of_card(
        self,
        card: int,
        unknown_cards: list[int]
    ) -> float:
        """
        Calcula la probabilidad estimada de que una carta desconocida
        sea del tipo indicado.

        Ejemplo:

        unknown_cards = [1, 1, 2, 3]

        probabilidad de Guardia:
        2 / 4 = 0.5
        """

        if not unknown_cards:
            return 0.0

        return unknown_cards.count(card) / len(unknown_cards)

    def card_may_still_exist(
        self,
        card: int,
        unknown_cards: list[int]
    ) -> bool:
        """
        Indica si todavía puede quedar al menos una copia
        de una carta entre las cartas ocultas.
        """

        return card in unknown_cards

    def evaluate_guard_opportunity(
        self,
        state: LoveLetterGameState,
        ai_player: int,
        unknown_cards: list[int],
        known_opponent_card
    ) -> float:
        """
        Evalúa si tener una Guardia representa una buena oportunidad.

        Casos:
        - si no tenemos Guardia, devuelve 0;
        - si el rival está protegido, devuelve 0;
        - si conocemos la carta rival, la oportunidad puede ser segura;
        - si no la conocemos, utiliza probabilidades.
        """

        # No podemos aprovechar Guardia si no está en nuestra mano.
        if GUARD not in state.hands[ai_player]:
            return 0.0

        opponent = other_player(ai_player)

        # No podemos utilizar Guardia contra un rival protegido.
        if state.protected[opponent]:
            return 0.0

        # Si conocemos la carta rival mediante Sacerdote,
        # podemos adivinarla con seguridad.
        if known_opponent_card is not None:

            # Guardia no permite adivinar otra Guardia.
            if known_opponent_card != GUARD:
                return self.GUARD_OPPORTUNITY_WEIGHT

            return 0.0

        # Si no conocemos la carta rival,
        # buscamos cuál de las cartas 2-8 es más probable.
        best_probability = 0.0

        for card in range(PRIEST, PRINCESS + 1):
            probability = self.probability_of_card(
                card,
                unknown_cards
            )

            best_probability = max(
                best_probability,
                probability
            )

        # Cuanto mayor sea la probabilidad de acertar,
        # mayor será la puntuación.
        return (
            best_probability
            * self.GUARD_OPPORTUNITY_WEIGHT
        )

    def evaluate_baron_opportunity(
        self,
        state: LoveLetterGameState,
        ai_player: int,
        opponent_estimated_value: float
    ) -> float:
        """
        Evalúa si jugar Barón parece favorable.

        El Barón compara la carta restante de ambos jugadores.
        Si nuestra carta restante parece más alta,
        la evaluación será positiva.
        """

        # No podemos jugar Barón si no está en nuestra mano.
        if BARON not in state.hands[ai_player]:
            return 0.0

        opponent = other_player(ai_player)

        # Barón no puede afectar a un rival protegido.
        if state.protected[opponent]:
            return 0.0

        # Copiamos la mano para no modificar el estado real.
        remaining_cards = state.hands[ai_player].copy()

        # Simulamos que jugamos el Barón.
        remaining_cards.remove(BARON)

        # En condiciones normales debe quedar una carta.
        if not remaining_cards:
            return 0.0

        # Esta sería la carta que conservaríamos tras jugar Barón.
        retained_card = remaining_cards[0]

        # Comparamos nuestra carta con el valor estimado rival.
        difference = retained_card - opponent_estimated_value

        # Si la diferencia es positiva, Barón parece favorable.
        # Si es negativa, existe riesgo de perder.
        return difference * self.BARON_OPPORTUNITY_WEIGHT

    def evaluate_prince_opportunity(
        self,
        state: LoveLetterGameState,
        ai_player: int,
        unknown_cards: list[int],
        known_opponent_card
    ) -> float:
        """
        Evalúa si utilizar Príncipe contra el rival puede ser favorable.

        El mejor caso es cuando sabemos que el rival tiene la Princesa,
        porque obligarlo a descartarla lo elimina inmediatamente.
        """

        # No podemos aprovechar Príncipe si no está en nuestra mano.
        if PRINCE not in state.hands[ai_player]:
            return 0.0

        opponent = other_player(ai_player)

        # No podemos utilizar Príncipe contra un rival protegido.
        if state.protected[opponent]:
            return 0.0

        # Si sabemos que el rival tiene la Princesa,
        # jugar Príncipe contra él produce una eliminación segura.
        if known_opponent_card == PRINCESS:
            return self.PRINCE_OPPORTUNITY_WEIGHT

        # Si no conocemos la carta rival,
        # estimamos la probabilidad de que tenga la Princesa.
        princess_probability = self.probability_of_card(
            PRINCESS,
            unknown_cards
        )

        # Cuanto más probable sea que tenga la Princesa,
        # más atractiva resulta la acción con Príncipe.
        return (
            princess_probability
            * self.PRINCE_OPPORTUNITY_WEIGHT
        )