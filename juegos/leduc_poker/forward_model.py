import random

from generic.imperfect.forward_model import ImperfectForwardModel

from .actions import PokerAction, PokerActionType
from .cards import Card, DECK_COMPOSITION
from .game_state import LeducPokerGameState
from .information_state import LeducPokerInformationState


class LeducPokerForwardModel(
    ImperfectForwardModel[
        LeducPokerGameState,
        PokerAction,
        LeducPokerInformationState
    ]
):
    """
    Forward Model de Leduc Poker para 2 jugadores.

    Reglas implementadas:
    - Mazo de 6 cartas: J, J, Q, Q, K, K.
    - Ante de 1 ficha por jugador.
    - Una carta privada por jugador.
    - Dos rondas de apuestas.
    - Una carta pública entre ambas rondas.
    - Apuesta/subida fija de 2 fichas en la primera ronda y 4 en la segunda.
    - Máximo de dos apuestas agresivas por ronda: BET + RAISE.
    """

    ANTE = 1
    FIRST_ROUND_BET = 2
    SECOND_ROUND_BET = 4
    MAX_BETS_PER_ROUND = 2

    # Con las reglas anteriores, el máximo que puede haber invertido un jugador
    # al terminar una mano es: 1 de ante + 4 en la primera ronda + 8 en la segunda = 13.
    # Se utiliza para normalizar la utilidad terminal al intervalo [-1, 1].
    MAX_PLAYER_CONTRIBUTION = 13

    def setup_game(self, state: LeducPokerGameState) -> None:
        """Inicializa una mano nueva e independiente de Leduc Poker."""
        if state.num_players != 2:
            raise ValueError("Leduc Poker está implementado para exactamente 2 jugadores.")

        deck = DECK_COMPOSITION.copy()
        random.shuffle(deck)

        state.private_cards = {
            1: deck.pop(),
            2: deck.pop()
        }
        state.deck = deck
        state.public_card = None

        state.current_player = 1
        state.betting_round = 1

        state.contributions = {
            1: self.ANTE,
            2: self.ANTE
        }
        state.round_contributions = {1: 0, 2: 0}
        state.current_bet = 0
        state.bets_in_round = 0
        state.consecutive_checks = 0
        state.action_history = []

        state.is_terminal = False
        state.winner = None
        state.folded_player = None
        state.last_action_summary = None

    def create_initial_state(
        self,
        reference_information_state: LeducPokerInformationState
    ) -> LeducPokerGameState:
        """
        Crea una mano completamente nueva para el entrenamiento global de MCCFR.

        El InformationState recibido solo se usa para conservar la configuración
        estructural. No se reutiliza ninguna carta privada de la partida real.
        """
        state = LeducPokerGameState(num_players=reference_information_state.num_players)
        self.setup_game(state)
        return state

    def create_information_state(
        self,
        state: LeducPokerGameState,
        player_id: int
    ) -> LeducPokerInformationState:
        """
        Construye la vista observable por player_id.

        La carta privada del rival y el orden del mazo permanecen ocultos.
        El historial de apuestas sí es público y, por tanto, forma parte del
        InformationState utilizado por MCCFR e ISMCTS.
        """
        private_card = state.private_cards[player_id]
        if private_card is None:
            raise ValueError(f"El Jugador {player_id} no tiene carta privada.")

        return LeducPokerInformationState(
            observer_id=player_id,
            num_players=state.num_players,
            private_card=private_card,
            public_card=state.public_card,
            betting_round=state.betting_round,
            current_player=state.current_player,
            contributions=state.contributions.copy(),
            round_contributions=state.round_contributions.copy(),
            current_bet=state.current_bet,
            bets_in_round=state.bets_in_round,
            consecutive_checks=state.consecutive_checks,
            action_history=state.action_history.copy(),
            deck_count=len(state.deck)
        )

    def determinize(
        self,
        info_state: LeducPokerInformationState
    ) -> LeducPokerGameState:
        """
        Genera un estado completo compatible con la información del observador.

        Se conserva:
        - su carta privada;
        - la carta pública si ya se ha revelado;
        - todo el historial y estado público de apuestas.

        Se vuelve a muestrear:
        - la carta privada del rival;
        - el orden de las cartas todavía ocultas.
        """
        observer = info_state.observer_id
        opponent = 2 if observer == 1 else 1

        unknown_cards = DECK_COMPOSITION.copy()
        unknown_cards.remove(info_state.private_card)

        if info_state.public_card is not None:
            unknown_cards.remove(info_state.public_card)

        random.shuffle(unknown_cards)
        opponent_card = unknown_cards.pop()
        random.shuffle(unknown_cards)

        det_state = LeducPokerGameState(num_players=info_state.num_players)
        det_state.private_cards[observer] = info_state.private_card
        det_state.private_cards[opponent] = opponent_card
        det_state.public_card = info_state.public_card
        det_state.deck = unknown_cards

        det_state.current_player = info_state.current_player
        det_state.betting_round = info_state.betting_round
        det_state.contributions = info_state.contributions.copy()
        det_state.round_contributions = info_state.round_contributions.copy()
        det_state.current_bet = info_state.current_bet
        det_state.bets_in_round = info_state.bets_in_round
        det_state.consecutive_checks = info_state.consecutive_checks
        det_state.action_history = info_state.action_history.copy()

        det_state.is_terminal = False
        det_state.winner = None
        det_state.folded_player = None
        det_state.last_action_summary = None

        expected_deck_count = info_state.deck_count
        if len(det_state.deck) != expected_deck_count:
            raise ValueError(
                "La determinización generó un número de cartas ocultas incompatible "
                "con el InformationState."
            )

        return det_state

    def compute_available_actions(
        self,
        state: LeducPokerGameState
    ) -> list[PokerAction]:
        """Devuelve las acciones legales del jugador actual."""
        if state.is_terminal:
            return []

        player = state.current_player
        to_call = self._amount_to_call(state, player)

        if to_call == 0:
            actions = [
                PokerAction(PokerActionType.CHECK, player),
                PokerAction(PokerActionType.BET, player)
            ]
            return actions

        actions = [
            PokerAction(PokerActionType.FOLD, player),
            PokerAction(PokerActionType.CALL, player)
        ]

        if state.bets_in_round < self.MAX_BETS_PER_ROUND:
            actions.append(
                PokerAction(PokerActionType.RAISE, player)
            )

        return actions

    def advance(
        self,
        state: LeducPokerGameState,
        action: PokerAction
    ) -> None:
        """Aplica una acción legal y avanza la mano."""
        if state.is_terminal:
            return

        player = state.current_player
        opponent = self._other_player(player)

        if action.player != player:
            raise ValueError(
                f"La acción pertenece al Jugador {action.player}, "
                f"pero el turno actual es del Jugador {player}."
            )

        legal_actions = self.compute_available_actions(state)
        if action not in legal_actions:
            raise ValueError(f"Acción ilegal en el estado actual: {action}")

        action_type = action.action_type
        round_label = f"R{state.betting_round}"
        state.action_history.append(
            f"{round_label}:P{player}:{action_type.value}"
        )

        if action_type == PokerActionType.CHECK:
            state.consecutive_checks += 1
            state.last_action_summary = f"Jugador {player} hace CHECK"

            if state.consecutive_checks >= 2:
                self._finish_betting_round(state)
            else:
                state.current_player = opponent
            return

        # Cualquier acción distinta de CHECK rompe la secuencia CHECK-CHECK.
        state.consecutive_checks = 0

        if action_type == PokerActionType.BET:
            bet_size = self._bet_size(state)
            self._put_chips(state, player, bet_size)
            state.current_bet = state.round_contributions[player]
            state.bets_in_round += 1
            state.last_action_summary = (
                f"Jugador {player} hace BET de {bet_size} fichas"
            )
            state.current_player = opponent
            return

        if action_type == PokerActionType.CALL:
            to_call = self._amount_to_call(state, player)
            self._put_chips(state, player, to_call)
            state.last_action_summary = (
                f"Jugador {player} hace CALL de {to_call} fichas"
            )
            self._finish_betting_round(state)
            return

        if action_type == PokerActionType.RAISE:
            to_call = self._amount_to_call(state, player)
            raise_size = self._bet_size(state)
            self._put_chips(state, player, to_call + raise_size)
            state.current_bet = state.round_contributions[player]
            state.bets_in_round += 1
            state.last_action_summary = (
                f"Jugador {player} hace RAISE: iguala {to_call} y sube {raise_size}"
            )
            state.current_player = opponent
            return

        if action_type == PokerActionType.FOLD:
            state.folded_player = player
            state.winner = opponent
            state.is_terminal = True
            state.last_action_summary = (
                f"Jugador {player} hace FOLD. Jugador {opponent} gana el bote."
            )
            return

        raise ValueError(f"Tipo de acción no soportado: {action_type}")

    def evaluate_terminal(
        self,
        state: LeducPokerGameState,
        player_id: int,
        depth: int = 0
    ) -> float:
        """
        Devuelve la utilidad neta normalizada del jugador en [-1, 1].

        No basta con devolver simplemente +1 por ganar y -1 por perder, porque en
        Poker una mano ganada después de invertir muchas fichas no tiene el mismo
        valor que una mano ganada con un bote pequeño. Se utiliza el beneficio neto:

        - ganador: bote recibido - fichas propias aportadas;
        - perdedor: -fichas propias aportadas;
        - empate: mitad del bote - fichas propias aportadas.

        La utilidad se divide entre 13, que es la máxima contribución posible de un
        jugador con esta estructura de apuestas.
        """
        if not state.is_terminal:
            return 0.0

        own_contribution = state.contributions[player_id]
        pot = state.pot

        if state.winner is None:
            net_utility = (pot / 2.0) - own_contribution
        elif state.winner == player_id:
            net_utility = pot - own_contribution
        else:
            net_utility = -own_contribution

        normalized = net_utility / self.MAX_PLAYER_CONTRIBUTION
        return max(-1.0, min(1.0, normalized))

    # ============================================================
    # MÉTODOS AUXILIARES DE APUESTAS Y SHOWDOWN
    # ============================================================

    def _finish_betting_round(self, state: LeducPokerGameState) -> None:
        """Finaliza la ronda actual, revela la carta pública o resuelve showdown."""
        if state.betting_round == 1:
            if not state.deck:
                raise ValueError("No quedan cartas para revelar la carta pública.")

            state.public_card = state.deck.pop()
            state.action_history.append(
                f"PUBLIC:{state.public_card.name}"
            )

            state.betting_round = 2
            state.current_player = 1
            state.round_contributions = {1: 0, 2: 0}
            state.current_bet = 0
            state.bets_in_round = 0
            state.consecutive_checks = 0
            state.last_action_summary = (
                f"Finaliza la ronda 1. Se revela {state.public_card.name}."
            )
            return

        self._resolve_showdown(state)

    def _resolve_showdown(self, state: LeducPokerGameState) -> None:
        """Compara las manos y termina la partida."""
        if state.public_card is None:
            raise ValueError("No puede haber showdown sin carta pública.")

        strength_1 = self._hand_strength(
            state.private_cards[1],
            state.public_card
        )
        strength_2 = self._hand_strength(
            state.private_cards[2],
            state.public_card
        )

        if strength_1 > strength_2:
            state.winner = 1
        elif strength_2 > strength_1:
            state.winner = 2
        else:
            state.winner = None

        state.is_terminal = True

        if state.winner is None:
            state.last_action_summary = "SHOWDOWN: empate, el bote se reparte."
        else:
            state.last_action_summary = (
                f"SHOWDOWN: gana el Jugador {state.winner}."
            )

    def _hand_strength(
        self,
        private_card: Card | None,
        public_card: Card
    ) -> tuple[int, int]:
        """
        Devuelve una tupla comparable:
        - (1, rango) si existe pareja con la carta pública;
        - (0, rango) si solo existe carta alta.
        """
        if private_card is None:
            raise ValueError("No se puede evaluar una mano sin carta privada.")

        is_pair = 1 if private_card == public_card else 0
        return is_pair, private_card.value

    def _bet_size(self, state: LeducPokerGameState) -> int:
        return (
            self.FIRST_ROUND_BET
            if state.betting_round == 1
            else self.SECOND_ROUND_BET
        )

    def _amount_to_call(
        self,
        state: LeducPokerGameState,
        player: int
    ) -> int:
        return max(
            0,
            state.current_bet - state.round_contributions[player]
        )

    def _put_chips(
        self,
        state: LeducPokerGameState,
        player: int,
        amount: int
    ) -> None:
        state.contributions[player] += amount
        state.round_contributions[player] += amount

    def _other_player(self, player: int) -> int:
        return 2 if player == 1 else 1
