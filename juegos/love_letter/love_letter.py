# dataclass genera automáticamente el constructor y otros métodos
# útiles para las clases que almacenan datos.
from dataclasses import dataclass
# Optional indica que un atributo puede contener un valor o None.
from typing import Optional
# random se utiliza para barajar la baraja al comenzar la ronda.
import random

# Clases genéricas del framework. Love Letter implementa versiones
# concretas de estado, acción y forward model.
from generic.game_state import GameState
from generic.game_action import GameAction
from generic.forward_model import ForwardModel


# ============================================================
# CONSTANTS
# ============================================================

# Guardia (valor 1):
# eliges una carta del 2 al 8 e intentas adivinar la carta del rival.
# Si aciertas, el rival queda eliminado.
GUARD = 1
# Sacerdote (valor 2):
# permite ver la carta que tiene el rival.
PRIEST = 2
# Barón (valor 3):
# compara tu carta restante con la carta del rival.
# El jugador con la carta de menor valor queda eliminado.
BARON = 3
# Doncella (valor 4):
# te protege de los efectos de las cartas del rival
# hasta el comienzo de tu siguiente turno.
HANDMAID = 4
# Príncipe (valor 5):
# obliga a un jugador, incluido tú mismo, a descartar su carta
# y robar otra. Si descarta la Princesa, queda eliminado.
PRINCE = 5
# Rey (valor 6):
# intercambia tu carta restante con la carta del rival.
KING = 6
# Condesa (valor 7):
# no tiene efecto al jugarse.
# Debe jugarse obligatoriamente si está en la mano
# junto con el Rey o el Príncipe.
COUNTESS = 7
# Princesa (valor 8):
# es la carta de mayor valor.
# Si la juegas o la descartas, quedas eliminado.
PRINCESS = 8

# Traduce el valor numérico de cada carta a un nombre legible.
CARD_NAMES = {
    GUARD: "Guardia",
    PRIEST: "Sacerdote",
    BARON: "Barón",
    HANDMAID: "Doncella",
    PRINCE: "Príncipe",
    KING: "Rey",
    COUNTESS: "Condesa",
    PRINCESS: "Princesa"
}

# Composición completa de la baraja clásica de 16 cartas.
# La multiplicación de listas crea las copias de cada tipo.
CLASSIC_DECK = (
    [GUARD] * 5
    + [PRIEST] * 2
    + [BARON] * 2
    + [HANDMAID] * 2
    + [PRINCE] * 2
    + [KING]
    + [COUNTESS]
    + [PRINCESS]
)


# ============================================================
# HELPERS
# ============================================================

# Función auxiliar exclusiva para una partida de dos jugadores.
def other_player(player: int) -> int:
    """
    Devuelve el jugador contrario.
    """
    # Si el jugador es 2 devuelve 1; en caso contrario devuelve 2.
    return 1 if player == 2 else 2


# Devuelve una etiqueta más clara para mostrar cada jugador por consola.
# En el modo Humano vs IA del framework, el jugador 1 es el humano
# y el jugador 2 es la inteligencia artificial.
def player_label(player: int) -> str:
    """
    Devuelve el nombre visible del jugador.
    """
    if player == 1:
        return "Jugador 1 (Humano)"

    return "Jugador 2 (IA)"


# Convierte una carta numérica en el texto mostrado por consola.
def card_name(card: int) -> str:
    """
    Devuelve el nombre visible de una carta.
    """
    # get evita un error si se recibe un valor de carta desconocido.
    return CARD_NAMES.get(card, f"Carta {card}")


# ============================================================
# GAME STATE
# ============================================================

# dataclass crea automáticamente el __init__ del estado.
@dataclass
class LoveLetterGameState(GameState):
    """
    Estado de una ronda de Love Letter para dos jugadores.
    """
    # Mano de cada jugador. Al comenzar su turno, el jugador activo
    # normalmente tiene dos cartas.
    hands: Optional[dict[int, list[int]]] = None
    # Cartas que todavía quedan disponibles para robar.
    deck: Optional[list[int]] = None
    # Carta retirada boca abajo al principio de la ronda.
    reserve_card: Optional[int] = None
    # Tres cartas retiradas boca arriba en la variante de dos jugadores.
    removed_face_up: Optional[list[int]] = None
    # Historial público de cartas jugadas o descartadas.
    discarded: Optional[dict[int, list[int]]] = None
    # Indica si cada jugador está protegido por una Doncella.
    protected: Optional[dict[int, bool]] = None
    # Indica si cada jugador sigue participando en la ronda.
    alive: Optional[dict[int, bool]] = None
    # Información obtenida mediante Sacerdote.
    # El índice representa al jugador cuya carta fue revelada.
    known_hands: Optional[dict[int, Optional[int]]] = None
    # Jugador al que le corresponde realizar la siguiente acción.
    current_player: int = 1
    # True cuando ya no pueden realizarse más acciones.
    is_terminal: bool = False
    # 1 o 2 cuando hay ganador; None si no está decidido o hay empate.
    winner: Optional[int] = None

    # Describe el último efecto ocurrido en la partida.
    # Se guarda en el estado en vez de imprimirlo directamente dentro
    # del forward model, porque los algoritmos simulan muchas jugadas.
    last_event: Optional[str] = None

    def __post_init__(self):
        """
        Si no se pasa un estado ya creado, prepara una ronda nueva.
        """
        # Si no se recibió una mano, se está creando una ronda nueva.
        # Los clones sí proporcionan todos los atributos.
        if self.hands is None:
            self.setup_initial_state()

    def setup_initial_state(self):
        """
        Prepara una partida clásica de Love Letter para dos jugadores.
        """
        # Se copia la constante para no modificar CLASSIC_DECK.
        cards = CLASSIC_DECK.copy()
        # Se aleatoriza el orden de las cartas.
        random.shuffle(cards)

        # Se retira una carta boca abajo.
        self.reserve_card = cards.pop()
        # En una partida de dos jugadores se retiran tres boca arriba.
        self.removed_face_up = [cards.pop(), cards.pop(), cards.pop()]

        # Se reparte una carta inicial a cada jugador.
        self.hands = {
            1: [cards.pop()],
            2: [cards.pop()]
        }

        # Las cartas restantes forman el mazo de robo.
        self.deck = cards
        # Todavía no existe ningún descarte.
        self.discarded = {1: [], 2: []}
        # Ningún jugador comienza protegido.
        self.protected = {1: False, 2: False}
        # Ambos jugadores comienzan vivos.
        self.alive = {1: True, 2: True}
        # Al principio nadie conoce la carta del rival.
        self.known_hands = {1: None, 2: None}
        # El jugador 1 será el primero en actuar.
        self.current_player = 1
        self.is_terminal = False
        self.winner = None

        # Al comenzar la ronda todavía no ha ocurrido ningún efecto.
        self.last_event = None

        # Para comenzar el turno necesita dos cartas entre las que elegir.
        # El jugador inicial comienza su turno con dos cartas.
        self.hands[1].append(self.deck.pop())

    def clone(self):
        """
        Devuelve una copia profunda del estado.
        Muy importante para los algoritmos de búsqueda.
        """
        # Se copian listas y diccionarios para que el algoritmo pueda
        # modificar el clon sin alterar el estado original.
        return LoveLetterGameState(
            hands={1: self.hands[1].copy(), 2: self.hands[2].copy()},
            deck=self.deck.copy(),
            reserve_card=self.reserve_card,
            removed_face_up=self.removed_face_up.copy(),
            discarded={1: self.discarded[1].copy(), 2: self.discarded[2].copy()},
            protected=self.protected.copy(),
            alive=self.alive.copy(),
            known_hands=self.known_hands.copy(),
            current_player=self.current_player,
            is_terminal=self.is_terminal,
            winner=self.winner,
            last_event=self.last_event
        )


# ============================================================
# ACTION
# ============================================================

# Acción concreta que hereda de GameAction, igual que SetCellAction
# en el juego de tres en raya.
@dataclass
class PlayCardAction(GameAction):
    """
    Acción del juego de Love Letter.
    """
    # Carta que se juega y se descarta.
    card: int
    # Jugador que ejecuta la acción.
    player: int
    # Jugador objetivo; None si la carta no necesita objetivo.
    target: Optional[int] = None
    # Carta adivinada con Guardia; None para las demás cartas.
    guess: Optional[int] = None


# ============================================================
# FORWARD MODEL
# ============================================================

# El forward model contiene todas las reglas y transiciones del juego.
# No decide cuál es la mejor acción; eso corresponde al algoritmo.
class LoveLetterForwardModel(ForwardModel[LoveLetterGameState, PlayCardAction]):
    """
    Forward model de Love Letter.
    """

    # Valor terminal suficientemente alto para dominar la heurística.
    WIN_SCORE = 100000

    def compute_available_actions(self, state: LoveLetterGameState) -> list[PlayCardAction]:
        """
        Devuelve todas las acciones legales posibles desde el estado actual.
        """
        # Un estado terminal no tiene acciones legales.
        if state.is_terminal:
            return []

        # Solo se generan acciones para el jugador cuyo turno está activo.
        player = state.current_player

        # Un jugador eliminado no puede realizar movimientos.
        if not state.alive[player]:
            return []

        # Al comenzar su turno debe tener la carta conservada y la robada.
        hand = state.hands[player]

        # Esta validación detecta estados inconsistentes durante la búsqueda.
        if len(hand) != 2:
            raise ValueError(
                f"El jugador {player} debe tener exactamente dos cartas antes de jugar."
            )

        # Primero se aplica la regla obligatoria de la Condesa.
        playable_cards = self.get_playable_cards(hand)
        # Aquí se acumulan todas las combinaciones legales.
        actions = []

        # set evita repetir acciones si la mano contiene dos cartas iguales.
        # sorted mantiene un orden estable para mostrar las opciones.
        for card in sorted(set(playable_cards)):
            actions.extend(self.get_actions_for_card(state, player, card))

        return actions

    def get_playable_cards(self, hand: list[int]) -> list[int]:
        """
        Si hay Condesa junto con Rey o Príncipe, debe jugarse la Condesa.
        """
        # Condesa junto con Rey o Príncipe obliga a jugar Condesa.
        if COUNTESS in hand and (KING in hand or PRINCE in hand):
            return [COUNTESS]

        # En cualquier otro caso pueden jugarse ambas cartas de la mano.
        return hand.copy()

    def get_actions_for_card(
        self,
        state: LoveLetterGameState,
        player: int,
        card: int
    ) -> list[PlayCardAction]:
        """
        Genera todas las acciones posibles para una carta concreta.
        """
        # En una partida de dos jugadores solo existe un rival posible.
        opponent = other_player(player)
        # El rival solo puede recibir efectos si está vivo y sin protección.
        opponent_can_be_targeted = (
            state.alive[opponent]
            and not state.protected[opponent]
        )

        # Guardia: se generan siete acciones, una por cada posible
        # adivinanza entre Sacerdote (2) y Princesa (8).
        if card == GUARD:
            # Si el rival está protegido, la Guardia se juega sin efecto.
            if not opponent_can_be_targeted:
                return [PlayCardAction(card, player)]

            return [
                PlayCardAction(card, player, opponent, guess)
                for guess in range(PRIEST, PRINCESS + 1)
            ]

        # Sacerdote, Barón y Rey solo pueden apuntar al rival.
        if card in (PRIEST, BARON, KING):
            if opponent_can_be_targeted:
                return [PlayCardAction(card, player, opponent)]

            return [PlayCardAction(card, player)]

        # Príncipe puede apuntar al propio jugador o al rival.
        if card == PRINCE:
            actions = [PlayCardAction(card, player, player)]

            if opponent_can_be_targeted:
                actions.append(PlayCardAction(card, player, opponent))

            return actions

        # Doncella, Condesa y Princesa no necesitan objetivo.
        return [PlayCardAction(card, player)]

    def advance(self, state: LoveLetterGameState, action: PlayCardAction) -> None:
        """
        Aplica una acción al estado.
        """
        # No se modifica un estado que ya ha terminado.
        if state.is_terminal:
            return

        # La acción debe pertenecer al jugador cuyo turno está activo.
        if action.player != state.current_player:
            raise ValueError(
                f"Turno inválido: action.player={action.player}, "
                f"pero current_player={state.current_player}."
            )

        # Se verifica que carta, objetivo y adivinanza forman
        # una de las acciones legales generadas por el modelo.
        if action not in self.compute_available_actions(state):
            raise ValueError(f"Acción no válida: {action}")

        # Se guardan ambos identificadores para simplificar el avance.
        player = action.player
        next_player = other_player(player)

        # Se guarda la carta que había sido revelada mediante Sacerdote.
        # La información solo debe borrarse si la carta conservada cambia.
        known_card_before = state.known_hands[player]

        # La carta jugada sale de la mano.
        state.hands[player].remove(action.card)

        # La carta jugada pasa al descarte público.
        state.discarded[player].append(action.card)

        # Si el jugador conserva exactamente la carta que ya se conocía,
        # la información sigue siendo válida. En caso contrario se borra.
        if (
            known_card_before is not None
            and state.hands[player]
            and state.hands[player][0] != known_card_before
        ):
            state.known_hands[player] = None

        # Se aplica el efecto específico de la carta.
        self.apply_card_effect(state, action)
        # Algunos efectos pueden eliminar inmediatamente a un jugador.
        self.update_terminal_status(state)

        # Si hubo una eliminación, no se cambia de turno ni se roba.
        if state.is_terminal:
            return

        # La protección termina al comenzar el nuevo turno del protegido.
        state.protected[next_player] = False
        # El turno pasa al jugador contrario.
        state.current_player = next_player

        # Si no queda ninguna carta para robar, se comparan las manos.
        if len(state.deck) == 0:
            self.resolve_showdown(state)
            return

        # El nuevo jugador activo roba y pasa a tener dos cartas.
        state.hands[next_player].append(state.deck.pop())

    def apply_card_effect(self, state: LoveLetterGameState, action: PlayCardAction) -> None:
        """
        Aplica el efecto de la carta jugada.

        El resultado se guarda en state.last_event en vez de imprimirse
        directamente. Esto evita mostrar mensajes de las jugadas simuladas
        internamente por Minimax, Alpha-Beta o MCTS.
        """
        # Variables locales para hacer más legible cada efecto.
        card = action.card
        player = action.player
        target = action.target

        # GUARDIA: elimina al objetivo si la adivinanza coincide.
        if card == GUARD:
            if target is None:
                state.last_event = (
                    f"Jugador {player} juega Guardia, pero no puede "
                    f"elegir un objetivo."
                )
                return

            # El objetivo conserva una única carta en este momento.
            target_card = state.hands[target][0]

            if target_card == action.guess:
                state.last_event = (
                    f"Guardia acierta: el jugador {target} tenía "
                    f"{card_name(target_card)} ({target_card}) y queda eliminado."
                )
                self.eliminate_player(state, target)
            else:
                # Al fallar no se muestra la carta real del rival,
                # porque esa información debe seguir siendo secreta.
                state.last_event = (
                    f"Guardia falla: el jugador {target} no tenía "
                    f"{card_name(action.guess)} ({action.guess})."
                )

            return

        # SACERDOTE: guarda en el estado la carta conocida del objetivo.
        if card == PRIEST:
            if target is not None:
                revealed_card = state.hands[target][0]
                state.known_hands[target] = revealed_card
                state.last_event = (
                    f"Sacerdote revela que el jugador {target} tiene "
                    f"{card_name(revealed_card)} ({revealed_card})."
                )
            else:
                state.last_event = (
                    f"Jugador {player} juega Sacerdote sin objetivo."
                )
            return

        # BARÓN: compara las cartas conservadas; pierde la más baja.
        if card == BARON:
            if target is None:
                state.last_event = (
                    f"Jugador {player} juega Barón sin objetivo."
                )
                return

            player_card = state.hands[player][0]
            target_card = state.hands[target][0]

            if player_card > target_card:
                state.last_event = (
                    f"Barón: el jugador {player} gana la comparación "
                    f"{card_name(player_card)} ({player_card}) contra "
                    f"{card_name(target_card)} ({target_card}). "
                    f"El jugador {target} queda eliminado."
                )
                self.eliminate_player(state, target)

            elif target_card > player_card:
                state.last_event = (
                    f"Barón: el jugador {target} gana la comparación "
                    f"{card_name(target_card)} ({target_card}) contra "
                    f"{card_name(player_card)} ({player_card}). "
                    f"El jugador {player} queda eliminado."
                )
                self.eliminate_player(state, player)

            else:
                state.last_event = (
                    f"Barón: ambos jugadores conservan "
                    f"{card_name(player_card)} ({player_card}). "
                    f"No se elimina a nadie."
                )

            return

        # DONCELLA: protege al jugador hasta su siguiente turno.
        if card == HANDMAID:
            state.protected[player] = True
            state.last_event = (
                f"Jugador {player} juega Doncella y queda protegido "
                f"hasta su siguiente turno."
            )
            return

        # PRÍNCIPE: obliga al objetivo a descartar y robar.
        if card == PRINCE:
            if target is not None:
                # Se guarda antes de aplicar el efecto porque apply_prince
                # elimina la carta de la mano del objetivo.
                discarded_card = state.hands[target][0]

                state.last_event = (
                    f"Jugador {player} usa Príncipe contra el jugador {target}. "
                    f"El objetivo descarta {card_name(discarded_card)} "
                    f"({discarded_card})."
                )

                self.apply_prince(state, target)

                # Si la carta descartada era la Princesa,
                # apply_prince elimina al objetivo.
                if discarded_card == PRINCESS:
                    state.last_event += (
                        f" El jugador {target} queda eliminado "
                        f"por descartar la Princesa."
                    )
                else:
                    state.last_event += " Después roba una carta nueva."
            else:
                state.last_event = (
                    f"Jugador {player} juega Príncipe sin objetivo."
                )
            return

        # REY: intercambia las cartas conservadas por ambos jugadores.
        if card == KING:
            if target is not None:
                state.hands[player], state.hands[target] = (
                    state.hands[target],
                    state.hands[player]
                )

                # Tras el intercambio, la información obtenida antes
                # mediante Sacerdote deja de ser válida.
                state.known_hands[player] = None
                state.known_hands[target] = None

                state.last_event = (
                    f"Jugador {player} juega Rey e intercambia su carta "
                    f"con el jugador {target}."
                )
            else:
                state.last_event = (
                    f"Jugador {player} juega Rey sin objetivo."
                )
            return

        # CONDESA: no tiene efecto adicional al descartarse.
        if card == COUNTESS:
            state.last_event = (
                f"Jugador {player} descarta la Condesa. "
                f"La carta no produce ningún efecto."
            )
            return

        # PRINCESA: quien la descarta queda eliminado.
        if card == PRINCESS:
            state.last_event = (
                f"Jugador {player} descarta la Princesa y queda eliminado."
            )
            self.eliminate_player(state, player)
            return

        # Esta excepción protege frente a valores de carta inválidos.
        raise ValueError(f"Carta desconocida: {card}")

    def apply_prince(self, state: LoveLetterGameState, target: int) -> None:
        """
        El objetivo descarta su carta y roba otra.
        """
        # Se extrae la única carta que conserva el objetivo.
        discarded_card = state.hands[target].pop()
        # El descarte se añade al historial público.
        state.discarded[target].append(discarded_card)
        # La información previa de Sacerdote ya no representa su nueva mano.
        state.known_hands[target] = None

        # Descartar la Princesa provoca eliminación inmediata.
        if discarded_card == PRINCESS:
            self.eliminate_player(state, target)
            return

        # Normalmente el objetivo roba una carta del mazo.
        if len(state.deck) > 0:
            state.hands[target].append(state.deck.pop())
        # Si el mazo está vacío, utiliza la carta reservada boca abajo.
        elif state.reserve_card is not None:
            state.hands[target].append(state.reserve_card)
            state.reserve_card = None

    def eliminate_player(self, state: LoveLetterGameState, player: int) -> None:
        """
        Elimina a un jugador de la ronda.
        """
        # El jugador deja de participar y pierde cualquier protección.
        state.alive[player] = False
        state.protected[player] = False
        state.known_hands[player] = None

        # Si todavía conservaba una carta, también pasa al descarte.
        if len(state.hands[player]) > 0:
            state.discarded[player].extend(state.hands[player])
            state.hands[player].clear()

    def update_terminal_status(self, state: LoveLetterGameState) -> None:
        """
        Comprueba si solo queda un jugador vivo.
        """
        # Se recopilan los jugadores que todavía siguen vivos.
        alive_players = [player for player in (1, 2) if state.alive[player]]

        # En una partida de dos jugadores, el único superviviente gana.
        if len(alive_players) == 1:
            state.is_terminal = True
            state.winner = alive_players[0]

    def resolve_showdown(self, state: LoveLetterGameState) -> None:
        """
        Resuelve el final cuando se acaba el mazo.
        """
        # El agotamiento del mazo termina inmediatamente la ronda.
        state.is_terminal = True

        # Cada jugador vivo conserva exactamente una carta.
        card_player_1 = state.hands[1][0]
        card_player_2 = state.hands[2][0]

        # La carta de mayor valor gana la comparación.
        if card_player_1 > card_player_2:
            state.winner = 1
            return

        if card_player_2 > card_player_1:
            state.winner = 2
            return

        # Si las cartas empatan, se compara la suma de los descartes.
        discarded_value_player_1 = sum(state.discarded[1])
        discarded_value_player_2 = sum(state.discarded[2])

        # Gana quien haya descartado una suma mayor.
        if discarded_value_player_1 > discarded_value_player_2:
            state.winner = 1
        elif discarded_value_player_2 > discarded_value_player_1:
            state.winner = 2
            # Si también empatan los descartes, no existe ganador.
        else:
            state.winner = None

    def evaluate_terminal(
        self,
        state: LoveLetterGameState,
        ai_player: int,
        depth: int
    ) -> int:
        """
        Evalúa un estado terminal para minimax.
        """
        # Un empate tiene valor neutro para el algoritmo.
        if state.winner is None:
            return 0

        # Se resta depth para preferir victorias más rápidas.
        if state.winner == ai_player:
            return self.WIN_SCORE - depth

        # Se suma depth para preferir derrotas más tardías.
        return -self.WIN_SCORE + depth


# ============================================================
# CONSOLE HELPERS
# ============================================================

def print_board(state: LoveLetterGameState):
    """
    Muestra el estado actual de Love Letter por consola.

    Nota:
    se muestran ambas manos para facilitar pruebas y depuración.
    En una versión real para jugadores humanos debería ocultarse
    la mano del rival.
    """
    print()
    print("=== LOVE LETTER ===")
    print("Jugador actual:", player_label(state.current_player))
    print("Cartas restantes:", len(state.deck))

    # Las cartas retiradas boca arriba son información pública.
    removed_cards = ", ".join(
        f"{card_name(card)} ({card})"
        for card in state.removed_face_up
    )

    print("Cartas retiradas:", removed_cards)

    # Se imprime la información de cada jugador.
    for player in (1, 2):
        # Convierte la mano numérica en texto legible.
        hand = ", ".join(
            f"{card_name(card)} ({card})"
            for card in state.hands[player]
        )

        # Convierte el historial de descartes en texto legible.
        discarded = ", ".join(
            f"{card_name(card)} ({card})"
            for card in state.discarded[player]
        )

        print(
            f"{player_label(player)}: "
            f"mano=[{hand}], "
            f"protegido={state.protected[player]}, "
            f"vivo={state.alive[player]}"
        )

        print(f"Descartes de {player_label(player)}: [{discarded}]")

    # Se muestra el último efecto que ocurrió realmente en la partida.
    if state.last_event is not None:
        print()
        print("Último efecto:", state.last_event)

    # known_hands usa como clave el jugador cuya carta se conoce.
    #
    # known_hands[1] contiene la carta conocida del jugador 1.
    # known_hands[2] contiene la carta conocida del jugador 2.
    for player in (1, 2):
        known_card = state.known_hands[player]

        if known_card is not None:
            observer = other_player(player)

            print(
                f"{player_label(observer)} conoce la carta de "
                f"{player_label(player)}: "
                f"{card_name(known_card)} ({known_card})"
            )

    print()


def read_human_move(state: LoveLetterGameState):
    """
    Lee una acción humana válida y devuelve:
        card, target, guess
    """
    # Se reutiliza el forward model para mostrar únicamente
    # acciones que cumplen todas las reglas.
    model = LoveLetterForwardModel()
    actions = model.compute_available_actions(state)

    print("Acciones disponibles:")

    # enumerate asigna números visibles comenzando por 1.
    for index, action in enumerate(actions, start=1):
        text = f"{card_name(action.card)} ({action.card})"

        # Algunas cartas necesitan indicar un jugador objetivo.
        if action.target is not None:
            text += f" -> {player_label(action.target)}"

        # Guardia también necesita mostrar la carta adivinada.
        if action.guess is not None:
            text += f", adivina {card_name(action.guess)} ({action.guess})"

        print(f"{index}. {text}")

    # El bucle continúa hasta recibir una opción válida.
    while True:
        try:
            selected = int(input("Selecciona acción: ").strip())
        except ValueError:
            print("Formato inválido")
            continue

        if not (1 <= selected <= len(actions)):
            print("Opción fuera de rango")
            continue

        # Se resta 1 porque los índices de las listas empiezan en 0.
        action = actions[selected - 1]
        # Game.create_action_from_move convertirá esta tupla
        # en un objeto PlayCardAction.
        return action.card, action.target, action.guess