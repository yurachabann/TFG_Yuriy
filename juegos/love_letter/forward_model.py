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

    def setup_game(self, state: LoveLetterGameState) -> None:
        deck = DECK_COMPOSITION.copy()
        random.shuffle(deck)

        state.removed_card = deck.pop()

        # Asignar 1 carta a los jugadores 1 y 2
        for p in range(1, state.num_players + 1):
            state.hands[p] = [deck.pop()]

        state.deck = deck
        state.current_player = 1  # El primer jugador es el 1
        state.hands[1].append(state.deck.pop())

    def create_information_state(
        self, state: LoveLetterGameState, player_id: int
    ) -> LoveLetterInformationState:
        return LoveLetterInformationState(
            observer_id=player_id,
            hand=state.hands[player_id].copy(),
            played_cards={
                p: list(cards) for p, cards in state.played_cards.items()
            },
            protected=state.protected.copy(),
            eliminated=state.eliminated.copy(),
            deck_count=len(state.deck),
            current_player=state.current_player,
        )

    def determinize(
        self, info_state: LoveLetterInformationState
    ) -> LoveLetterGameState:
        det_state = LoveLetterGameState(
            num_players=len(info_state.eliminated)
        )
        det_state.played_cards = {
            p: list(c) for p, c in info_state.played_cards.items()
        }
        det_state.protected = info_state.protected.copy()
        det_state.eliminated = info_state.eliminated.copy()
        det_state.current_player = info_state.current_player

        known_pool = list(info_state.hand)
        for p_cards in info_state.played_cards.values():
            known_pool.extend(p_cards)

        unknown_pool = DECK_COMPOSITION.copy()
        for card in known_pool:
            unknown_pool.remove(card)

        random.shuffle(unknown_pool)

        det_state.hands[info_state.observer_id] = list(info_state.hand)

        for p in range(1, det_state.num_players + 1):
            if p == info_state.observer_id:
                continue
            if not info_state.eliminated[p]:
                cards_needed = 2 if p == info_state.current_player else 1
                det_state.hands[p] = [
                    unknown_pool.pop() for _ in range(cards_needed)
                ]

        det_state.removed_card = (
            unknown_pool.pop() if unknown_pool else None
        )
        det_state.deck = unknown_pool

        return det_state

    def compute_available_actions(
        self, state: LoveLetterGameState
    ) -> list[PlayCardAction]:
        if state.is_terminal:
            return []

        p = state.current_player
        hand = state.hands[p]
        actions = []

        # Regla de la Condesa: Obligada a jugarse si hay Rey o Príncipe en mano
        if Card.COUNTESS in hand and (
            Card.KING in hand or Card.PRINCE in hand
        ):
            return [PlayCardAction(card=Card.COUNTESS, player=p)]

        # Objetivos válidos en base 1 (no eliminados y no protegidos)
        valid_targets = [
            i
            for i in range(1, state.num_players + 1)
            if not state.eliminated[i] and not state.protected[i]
        ]

        for card in set(hand):
            if card == Card.GUARD:
                targets = [t for t in valid_targets if t != p]
                for target in targets:
                    for guess in range(2, 9):
                        actions.append(
                            PlayCardAction(
                                card=Card.GUARD,
                                player=p,
                                target=target,
                                guess=guess,  # Homogéneo con input humano
                            )
                        )
            elif card in (Card.PRIEST, Card.BARON, Card.KING):
                targets = [t for t in valid_targets if t != p]
                if targets:
                    for target in targets:
                        actions.append(
                            PlayCardAction(card=card, player=p, target=target)
                        )
                else:
                    # Si todos están protegidos, se descarte sin efecto
                    actions.append(
                        PlayCardAction(card=card, player=p, target=None)
                    )
            elif card == Card.PRINCE:
                for target in range(1, state.num_players + 1):
                    if not state.eliminated[target] and (
                        target == p or not state.protected[target]
                    ):
                        actions.append(
                            PlayCardAction(card=card, player=p, target=target)
                        )
            elif card in (Card.HANDMAID, Card.COUNTESS, Card.PRINCESS):
                actions.append(PlayCardAction(card=card, player=p))

        return (
            actions
            if actions
            else [PlayCardAction(card=hand[0], player=p)]
        )

    def advance(
        self, state: LoveLetterGameState, action: PlayCardAction
    ) -> None:
        p = state.current_player
        card = action.card

        state.hands[p].remove(card)
        state.played_cards[p].append(card)
        state.protected[p] = False

        target = action.target

        # -------------------------------------------------------------
        # RESOLUCIÓN DE EFECTOS Y REGISTRO DE EVENTO
        # -------------------------------------------------------------
        if card == Card.GUARD:
            if target is not None and action.guess is not None:
                guess_card = (
                    action.guess
                    if isinstance(action.guess, Card)
                    else Card(action.guess)
                )
                guess_name = guess_card.name

                if guess_card in state.hands[target]:
                    state.eliminated[target] = True
                    state.last_action_summary = (
                        f"🎯 Jugador {p} jugó GUARD adivinando '{guess_name}' -> 💥 ¡ACERTÓ! Jugador {target} ha sido ELIMINADO"
                    )
                else:
                    state.last_action_summary = (
                        f"🎯 Jugador {p} jugó GUARD adivinando '{guess_name}' -> ❌ FALLÓ"
                    )
            else:
                state.last_action_summary = f"Jugador {p} descartó GUARD sin objetivo (protegidos)"

        elif card == Card.PRIEST:
            if target is not None:
                state.last_action_summary = (
                    f"Jugador {p} jugó PRIEST y miró en secreto la mano del Jugador {target}"
                )
            else:
                state.last_action_summary = f"Jugador {p} descartó PRIEST sin efecto"

        elif card == Card.BARON:
            if target is not None:
                my_card = state.hands[p][0]
                target_card = state.hands[target][0]
                if my_card.value > target_card.value:
                    state.eliminated[target] = True
                    state.last_action_summary = (
                        f"Jugador {p} jugó BARON (tenía {my_card.name}) y ganó el duelo contra Jugador {target} ({target_card.name}) -> 💥 Jugador {target} ELIMINADO"
                    )
                elif target_card.value > my_card.value:
                    state.eliminated[p] = True
                    state.last_action_summary = (
                        f"Jugador {p} jugó BARON (tenía {my_card.name}) y perdió el duelo contra Jugador {target} ({target_card.name}) -> 💀 Jugador {p} ELIMINADO"
                    )
                else:
                    state.last_action_summary = (
                        f"Jugador {p} jugó BARON y empató en el duelo contra Jugador {target} (ambos tenían {my_card.name})"
                    )
            else:
                state.last_action_summary = f"Jugador {p} descartó BARON sin efecto"

        elif card == Card.HANDMAID:
            state.protected[p] = True
            state.last_action_summary = f"Jugador {p} jugó HANDMAID (Se protege este turno)"

        elif card == Card.PRINCE:
            if target is not None:
                discarded = state.hands[target].pop()
                state.played_cards[target].append(discarded)

                if discarded == Card.PRINCESS:
                    state.eliminated[target] = True
                    state.last_action_summary = (
                        f"Jugador {p} obligó a Jugador {target} a descartar {discarded.name} -> 💥 ¡Jugador {target} ELIMINADO!"
                    )
                else:
                    if state.deck:
                        state.hands[target].append(state.deck.pop())
                    else:
                        state.hands[target].append(state.removed_card)
                    state.last_action_summary = (
                        f"Jugador {p} obligó a Jugador {target} a descartar {discarded.name} y robar otra carta"
                    )
            else:
                state.last_action_summary = f"Jugador {p} descartó PRINCE sin efecto"

        elif card == Card.KING:
            if target is not None:
                state.hands[p], state.hands[target] = (
                    state.hands[target],
                    state.hands[p],
                )
                state.last_action_summary = (
                    f"Jugador {p} jugó KING e intercambió su mano con Jugador {target}"
                )
            else:
                state.last_action_summary = f"Jugador {p} descartó KING sin efecto"

        elif card == Card.COUNTESS:
            state.last_action_summary = f"Jugador {p} descartó COUNTESS"

        elif card == Card.PRINCESS:
            state.eliminated[p] = True
            state.last_action_summary = f"Jugador {p} descartó PRINCESS y quedó ELIMINADO"

        # -------------------------------------------------------------
        # COMPROBACIÓN DE CONDICIONES DE FIN DE PARTIDA
        # -------------------------------------------------------------
        active_players = [
            i for i in range(1, state.num_players + 1) if not state.eliminated[i]
        ]

        if len(active_players) == 1:
            state.is_terminal = True
            state.winner = active_players[0]
            return

        if len(state.deck) == 0:
            state.is_terminal = True
            max_val = max(state.hands[x][0].value for x in active_players)
            winners = [x for x in active_players if state.hands[x][0].value == max_val]
            state.winner = winners[0] if len(winners) == 1 else None
            return

        # Avanzar turno (Base 1)
        next_p = 2 if state.current_player == 1 else 1
        while state.eliminated[next_p]:
            next_p = 2 if next_p == 1 else 1

        state.current_player = next_p
        state.hands[next_p].append(state.deck.pop())

    def evaluate_terminal(self, state: LoveLetterGameState, player_id: int) -> float:
        if state.winner is None:
            return 0.0
        if state.winner == player_id:
            return 1.0
        return -1.0