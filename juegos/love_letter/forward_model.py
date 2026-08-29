import random
from generic.imperfect.forward_model import ImperfectForwardModel
from .actions import PlayCardAction
from .cards import DECK_COMPOSITION, Card
from .game_state import LoveLetterGameState
from .information_state import LoveLetterInformationState


class LoveLetterForwardModel(
    ImperfectForwardModel[
        LoveLetterGameState, PlayCardAction, LoveLetterInformationState
    ]
):
    """
    Modelo de avance (Forward Model) para Love Letter bajo un entorno de Información Imperfecta.
    Gestiona las reglas, transiciones de estado, generación de acciones válidas y 
    la determinización.
    """

    def setup_game(self, state: LoveLetterGameState) -> None:
        """
        Inicializa una partida real de Love Letter:
        1. Copia y baraja el mazo completo de 16 cartas.
        2. Retira una carta boca abajo (removed_card) según la regla oficial.
        3. Reparte 1 carta inicial a cada jugador.
        4. Otorga una 2ª carta al primer jugador para iniciar su turno.
        """
        deck = DECK_COMPOSITION.copy()
        random.shuffle(deck)

        # Regla Love Letter: Se aparta 1 carta en secreto al inicio de la ronda
        state.removed_card = deck.pop()

        # Reparto inicial: 1 carta oculta por jugador
        for p in range(1, state.num_players + 1):
            state.hands[p] = [deck.pop()]

        state.deck = deck
        state.current_player = 1
        
        # El jugador inicial roba del mazo para comenzar teniendo 2 cartas
        state.hands[1].append(state.deck.pop())

    def create_initial_state(
        self,
        reference_information_state: LoveLetterInformationState
    ) -> LoveLetterGameState:
        """
        Crea un estado inicial NUEVO e independiente de Love Letter.

        El InformationState recibido se utiliza únicamente para conservar el número
        de jugadores de la configuración actual. No se reutilizan la mano, el mazo,
        los descartes ni ninguna otra información de la partida real.

        setup_game() vuelve a barajar el mazo, retirar una carta y repartir desde cero,
        por lo que cada llamada genera un comienzo aleatorio nuevo.
        """
        state = LoveLetterGameState(
            num_players=len(reference_information_state.eliminated)
        )
        self.setup_game(state)
        return state

    def create_information_state(
        self, state: LoveLetterGameState, player_id: int
    ) -> LoveLetterInformationState:
        """
        Filtra el estado global para crear la vista observada por un jugador específico.
        Solo expone la mano propia y la información pública (descartes, eliminados, etc.).
        """
        return LoveLetterInformationState(
            observer_id=player_id,
            hand=state.hands[player_id].copy(),
            played_cards={
                p: list(cards) for p, cards in state.played_cards.items()
            },
            protected=state.protected.copy(),
            eliminated=state.eliminated.copy(),
            known_cards={
                observer: known.copy()
                for observer, known in state.known_cards.items()
            },
            excluded_cards={
                observer: {
                    target: sorted(cards, key=lambda c: c.value)
                    for target, cards in excluded.items()
                }
                for observer, excluded in state.excluded_cards.items()
            },
            deck_count=len(state.deck),
            current_player=state.current_player,
        )

    def determinize(
        self, info_state: LoveLetterInformationState
    ) -> LoveLetterGameState:
        """
        Genera un mundo hipotético (estado completo simétrico) para el MCTS / ISMCTS:
        1. Preserva todo el conocimiento público y la mano real de la IA observadora.
        2. Reconstruye el pool de cartas no vistas (mazo + manos enemigas + carta retirada).
        3. Mezcla las cartas no vistas y las reparte aleatoriamente entre los rivales activos.
        """
        det_state = LoveLetterGameState(
            num_players=len(info_state.eliminated)
        )
        
        # Copia de variables públicas visibles por todos
        det_state.played_cards = {
            p: list(c) for p, c in info_state.played_cards.items()
        }
        det_state.protected = info_state.protected.copy()
        det_state.eliminated = info_state.eliminated.copy()
        det_state.current_player = info_state.current_player
        det_state.known_cards = {
            observer: known.copy()
            for observer, known in info_state.known_cards.items()
        }
        det_state.excluded_cards = {
            observer: {
                target: set(cards)
                for target, cards in excluded.items()
            }
            for observer, excluded in info_state.excluded_cards.items()
        }

        # 1. Identificar las cartas 100% conocidas por la IA
        known_pool = list(info_state.hand)
        for p_cards in info_state.played_cards.values():
            known_pool.extend(p_cards)
        for p, known_card in info_state.known_cards[info_state.observer_id].items():
            if (
                p != info_state.observer_id
                and not info_state.eliminated[p]
                and known_card is not None
            ):
                known_pool.append(known_card)

        # 2. Calcular las cartas que siguen ocultas (Mazo + Carta Retirada + Manos Enemigas)
        unknown_pool = DECK_COMPOSITION.copy()
        for card in known_pool:
            unknown_pool.remove(card)

        # 3. Barajar el conocimiento no observado para simular una hipótesis de partida
        random.shuffle(unknown_pool)

        # Asignar la mano propia real al observador
        det_state.hands[info_state.observer_id] = list(info_state.hand)

        # 4. Repartir cartas a ciegas a los oponentes vivos
        for p in range(1, det_state.num_players + 1):
            if p == info_state.observer_id:
                continue
            if not info_state.eliminated[p]:
                # Si le toca jugar al rival en la simulación necesita 2 cartas; si no, 1.
                cards_needed = 2 if p == info_state.current_player else 1
                known_card = info_state.known_cards[info_state.observer_id].get(p)
                excluded = set(
                    info_state.excluded_cards[info_state.observer_id].get(p, [])
                )

                if known_card is not None:
                    # La carta conocida representa la carta que el rival ya conservaba antes de robar.
                    det_state.hands[p].append(known_card)
                    cards_needed -= 1
                elif excluded:
                    # Las exclusiones del Guardia se aplican a la carta que ya tenía el rival,
                    # no a una segunda carta desconocida que acaba de robar en su turno.
                    candidates = [
                        card for card in unknown_pool
                        if card not in excluded
                    ]
                    if not candidates:
                        raise ValueError(
                            f"No existe una determinización compatible para el Jugador {p}."
                        )
                    selected_card = random.choice(candidates)
                    unknown_pool.remove(selected_card)
                    det_state.hands[p].append(selected_card)
                    cards_needed -= 1

                for _ in range(cards_needed):
                    selected_card = random.choice(unknown_pool)
                    unknown_pool.remove(selected_card)
                    det_state.hands[p].append(selected_card)

        # 5. La última carta sobrante pasa a ser la carta retirada inicial
        det_state.removed_card = (
            unknown_pool.pop() if unknown_pool else None
        )
        
        # El resto de cartas no vistas conforman el mazo de robar del mundo simulado
        det_state.deck = unknown_pool

        return det_state

    def compute_available_actions(
        self, state: LoveLetterGameState
    ) -> list[PlayCardAction]:
        """
        Calcula todas las decisiones legales que puede tomar el jugador del turno actual:
        - Aplica restricciones obligatorias (Regla de la Condesa).
        - Filtra objetivos válidos (excluye jugadores eliminados o protegidos por la Doncella).
        - Genera combinaciones de cartas, objetivos y adivinanzas del Guardia.
        """
        if state.is_terminal:
            return []

        p = state.current_player
        hand = state.hands[p]
        actions = []

        # REGLA OBLIGATORIA CONDESA: Si se tiene Condesa + Rey o Condesa + Príncipe, se debe jugar la Condesa
        if Card.COUNTESS in hand and (
            Card.KING in hand or Card.PRINCE in hand
        ):
            return [PlayCardAction(card=Card.COUNTESS, player=p)]

        # Lista de jugadores a los que se puede apuntar (activos y sin la protección de la Doncella)
        valid_targets = [
            i
            for i in range(1, state.num_players + 1)
            if not state.eliminated[i] and not state.protected[i]
        ]

        # Analizar cada carta única presente en la mano actual
        for card in set(hand):
            if card == Card.GUARD:
                # El Guardia no puede apuntarse a uno mismo
                targets = [t for t in valid_targets if t != p]
                if targets:
                    for target in targets:
                        # Debe adivinar un valor entre 2 (Sacerdote) y 8 (Princesa)
                        for guess in range(2, 9):
                            actions.append(
                                PlayCardAction(
                                    card=Card.GUARD,
                                    player=p,
                                    target=target,
                                    guess=guess,
                                )
                            )
                else:
                    # Si todos los rivales están protegidos/eliminados, se descarta sin efecto
                    actions.append(
                        PlayCardAction(
                            card=Card.GUARD,
                            player=p,
                            target=None,
                            guess=None,
                        )
                    )
            elif card in (Card.PRIEST, Card.BARON, Card.KING):
                # Cartas que requieren un objetivo rival
                targets = [t for t in valid_targets if t != p]
                if targets:
                    for target in targets:
                        actions.append(
                            PlayCardAction(card=card, player=p, target=target)
                        )
                else:
                    # Si todos los rivales están protegidos/eliminados, se descarte sin efecto
                    actions.append(
                        PlayCardAction(card=card, player=p, target=None)
                    )
            elif card == Card.PRINCE:
                # El Príncipe puede jugarse sobre uno mismo (incluso si estás protegido) o sobre rivales vulnerables
                for target in range(1, state.num_players + 1):
                    if not state.eliminated[target] and (
                        target == p or not state.protected[target]
                    ):
                        actions.append(
                            PlayCardAction(card=card, player=p, target=target)
                        )
            elif card in (Card.HANDMAID, Card.COUNTESS, Card.PRINCESS):
                # Cartas sin objetivo hacia otros jugadores
                actions.append(PlayCardAction(card=card, player=p))

        # Fallback de seguridad: Si por algún motivo no hay acciones válidas, descartar la primera carta
        return (
            actions
            if actions
            else [PlayCardAction(card=hand[0], player=p)]
        )

    def advance(
        self, state: LoveLetterGameState, action: PlayCardAction
    ) -> None:
        """
        Ejecuta la jugada, resuelve los efectos de las cartas, comprueba
        si la partida finaliza y avanza el turno/roba carta si continúa el juego.
        """
        p = state.current_player
        card = action.card

        # Mover la carta jugada de la mano a la pila de descartes públicos
        self._update_knowledge_after_play(state, p, card)
        state.hands[p].remove(card)
        state.played_cards[p].append(card)
        
        # Jugar cualquier carta retira la protección de la Doncella conseguida en el turno anterior
        state.protected[p] = False

        target = action.target

        # -------------------------------------------------------------
        # RESOLUCIÓN DE EFECTOS INDIVIDUALES DE LAS CARTAS
        # -------------------------------------------------------------
        if card == Card.GUARD:
            if target is not None and action.guess is not None:
                guess_card = (
                    action.guess
                    if isinstance(action.guess, Card)
                    else Card(action.guess)
                )
                guess_name = guess_card.name

                # Acierto: Elimina al objetivo
                if guess_card in state.hands[target]:
                    state.eliminated[target] = True
                    self._discard_eliminated_hand(state, target)
                    state.last_action_summary = (
                        f"🎯 Jugador {p} jugó GUARD adivinando '{guess_name}' -> 💥 ¡ACERTÓ! Jugador {target} ELIMINADO"
                    )
                else:
                    state.excluded_cards[p][target].add(guess_card)
                    state.last_action_summary = (
                        f"🎯 Jugador {p} jugó GUARD adivinando '{guess_name}' -> ❌ FALLÓ"
                    )
            else:
                state.last_action_summary = f"Jugador {p} descartó GUARD sin objetivo"

        elif card == Card.PRIEST:
            if target is not None:
                state.known_cards[p][target] = state.hands[target][0]
                state.excluded_cards[p][target].clear()
                state.last_action_summary = (
                    f"Jugador {p} jugó PRIEST y miró la mano del Jugador {target}"
                )
            else:
                state.last_action_summary = f"Jugador {p} descartó PRIEST sin efecto"

        elif card == Card.BARON:
            if target is not None:
                my_card = state.hands[p][0]
                target_card = state.hands[target][0]
                state.known_cards[p][target] = target_card
                state.known_cards[target][p] = my_card
                state.excluded_cards[p][target].clear()
                state.excluded_cards[target][p].clear()
                # Compara en secreto los valores de las manos
                if my_card.value > target_card.value:
                    state.eliminated[target] = True
                    self._discard_eliminated_hand(state, target)
                    state.last_action_summary = (
                        f"Jugador {p} jugó BARON ({my_card.name}) y eliminó a Jugador {target} ({target_card.name})"
                    )
                elif target_card.value > my_card.value:
                    state.eliminated[p] = True
                    self._discard_eliminated_hand(state, p)
                    state.last_action_summary = (
                        f"Jugador {p} jugó BARON ({my_card.name}) y fue eliminado por Jugador {target} ({target_card.name})"
                    )
                else:
                    state.last_action_summary = (
                        f"Jugador {p} jugó BARON y empató con Jugador {target}"
                    )
            else:
                state.last_action_summary = f"Jugador {p} descartó BARON sin efecto"

        elif card == Card.HANDMAID:
            # Concede inmunidad al jugador hasta su siguiente turno
            state.protected[p] = True
            state.last_action_summary = f"Jugador {p} jugó HANDMAID"

        elif card == Card.PRINCE:
            if target is not None:
                # Obliga a descartar la mano actual
                discarded = state.hands[target].pop()
                state.played_cards[target].append(discarded)
                self._clear_player_knowledge(state, target)

                # Si el jugador se ve obligado a descartar la Princesa, cae eliminado inmediatamente
                if discarded == Card.PRINCESS:
                    state.eliminated[target] = True
                    state.last_action_summary = (
                        f"Jugador {p} obligó a Jugador {target} a descartar PRINCESS -> 💥 ¡ELIMINADO!"
                    )
                else:
                    # Roba una nueva carta del mazo. Si no quedan, roba la carta apartada al inicio.
                    if state.deck:
                        state.hands[target].append(state.deck.pop())
                    elif state.removed_card is not None:
                        state.hands[target].append(state.removed_card)
                        state.removed_card = None

                    state.last_action_summary = (
                        f"Jugador {p} obligó a Jugador {target} a descartar {discarded.name} y robar otra"
                    )
            else:
                state.last_action_summary = f"Jugador {p} descartó PRINCE sin efecto"

        elif card == Card.KING:
            if target is not None:
                # Intercambia las manos entre el jugador del turno y el objetivo
                state.hands[p], state.hands[target] = (
                    state.hands[target],
                    state.hands[p],
                )
                self._swap_player_knowledge(state, p, target)
                state.known_cards[p][target] = state.hands[target][0]
                state.known_cards[target][p] = state.hands[p][0]
                state.excluded_cards[p][target].clear()
                state.excluded_cards[target][p].clear()
                state.last_action_summary = (
                    f"Jugador {p} jugó KING e intercambió su mano con Jugador {target}"
                )
            else:
                state.last_action_summary = f"Jugador {p} descartó KING sin efecto"

        elif card == Card.COUNTESS:
            state.last_action_summary = f"Jugador {p} descartó COUNTESS"

        elif card == Card.PRINCESS:
            # Descartar voluntaria o involuntariamente a la Princesa provoca la eliminación del jugador
            state.eliminated[p] = True
            self._discard_eliminated_hand(state, p)
            state.last_action_summary = f"Jugador {p} descartó PRINCESS y quedó ELIMINADO"

        # -------------------------------------------------------------
        # EVALUACIÓN DE FIN DE PARTIDA Y CAMBIO DE TURNO
        # -------------------------------------------------------------
        active_players = [
            i for i in range(1, state.num_players + 1) if not state.eliminated[i]
        ]

        # CONDICIÓN DE VICTORIA 1: Solo queda un jugador con vida en la ronda
        if len(active_players) == 1:
            state.is_terminal = True
            state.winner = active_players[0]
            return

        # Búsqueda del siguiente jugador activo (salta jugadores eliminados)
        next_p = 2 if state.current_player == 1 else 1
        while state.eliminated[next_p]:
            next_p = 2 if next_p == 1 else 1

        # CONDICIÓN DE CONTINUIDAD / VICTORIA 2:
        if len(state.deck) > 0:
            # Si hay cartas en el mazo, avanza el turno y el nuevo jugador roba carta
            state.current_player = next_p
            state.hands[next_p].append(state.deck.pop())
        else:
            # Si el mazo se vacía, la ronda termina inmediatamente y gana la carta con mayor valor en mano (Showdown)
            state.is_terminal = True
            max_val = max(state.hands[x][0].value for x in active_players)
            winners = [x for x in active_players if state.hands[x][0].value == max_val]
            state.winner = winners[0] if len(winners) == 1 else None


    def _update_knowledge_after_play(
        self, state: LoveLetterGameState, player: int, card: Card
    ) -> None:
        for observer in range(1, state.num_players + 1):
            if observer == player:
                continue

            known_card = state.known_cards[observer][player]
            excluded = state.excluded_cards[observer][player]

            if known_card is not None:
                # Si juega una carta distinta de la conocida, necesariamente jugó la carta recién robada
                # y la carta conocida sigue siendo la que conserva en la mano.
                if known_card != card:
                    continue

                # Si juega la misma carta que conocíamos, ya no podemos saber si jugó la carta antigua
                # o una copia igual recién robada, así que el conocimiento exacto deja de ser válido.
                state.known_cards[observer][player] = None
                excluded.clear()
                continue

            # Un Guardia fallido solo permite conservar la exclusión si la carta jugada estaba excluida:
            # en ese caso sabemos que esa carta tuvo que ser la recién robada y conserva la carta antigua.
            if card not in excluded:
                excluded.clear()

    def _clear_player_knowledge(
        self, state: LoveLetterGameState, player: int
    ) -> None:
        for observer in range(1, state.num_players + 1):
            state.known_cards[observer][player] = None
            state.excluded_cards[observer][player].clear()

    def _swap_player_knowledge(
        self, state: LoveLetterGameState, player: int, target: int
    ) -> None:
        for observer in range(1, state.num_players + 1):
            state.known_cards[observer][player], state.known_cards[observer][target] = (
                state.known_cards[observer][target],
                state.known_cards[observer][player],
            )
            state.excluded_cards[observer][player], state.excluded_cards[observer][target] = (
                state.excluded_cards[observer][target],
                state.excluded_cards[observer][player],
            )

    def _discard_eliminated_hand(
        self, state: LoveLetterGameState, player: int
    ) -> None:
        while state.hands[player]:
            state.played_cards[player].append(state.hands[player].pop())

        self._clear_player_knowledge(state, player)

    def evaluate_terminal(self, state: LoveLetterGameState, player_id: int) -> float:
        """
        Retorna la recompensa terminal para MCTS desde el punto de vista de `player_id`:
         +1.0 si es el ganador.
         -1.0 si perdió.
          0.0 si hubo empate.
        """
        if state.winner is None:
            return 0.0
        return 1.0 if state.winner == player_id else -1.0