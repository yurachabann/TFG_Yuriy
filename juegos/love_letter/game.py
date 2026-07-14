# Clase base común para todos los juegos del framework.
# LoveLetterGame heredará de ella y proporcionará la implementación
# concreta de los métodos necesarios.
from core.game import Game

# Se importan las clases y funciones propias de Love Letter.
#
# LoveLetterGameState:
#     representa el estado completo de la partida.
#
# LoveLetterForwardModel:
#     contiene las reglas, genera acciones y avanza el estado.
#
# PlayCardAction:
#     representa una acción concreta de jugar una carta.
#
# print_board:
#     muestra el estado por consola.
#
# read_human_move:
#     permite que un jugador humano elija una acción válida.
from juegos.love_letter.love_letter import (
    LoveLetterGameState,
    LoveLetterForwardModel,
    PlayCardAction,
    print_board,
    read_human_move
)


class LoveLetterGame(Game):
    """
    Adaptador que conecta Love Letter con el framework genérico.

    Esta clase no implementa las reglas internas del juego.
    Esa responsabilidad pertenece a LoveLetterForwardModel.

    Su función es indicar al framework:

    - cómo crear el estado inicial;
    - cómo crear el forward model;
    - cómo leer una jugada humana;
    - cómo convertir una entrada humana en una acción;
    - cómo mostrar el estado;
    - cómo mostrar la acción elegida por una IA.

    Gracias a esta clase, Match, MatchRunner y los jugadores
    pueden trabajar con Love Letter igual que con Tic Tac Toe,
    Connect Four o Damas.
    """

    def __init__(self):
        """
        Inicializa el juego con el nombre que se mostrará
        en menús, partidas y resultados.
        """

        # Se llama al constructor de la clase base Game.
        super().__init__("Love Letter")

    def create_state(self):
        """
        Crea y devuelve el estado inicial de una ronda nueva.

        LoveLetterGameState se encarga internamente de:
        - crear la baraja;
        - barajarla;
        - retirar cartas;
        - repartir las manos;
        - elegir el jugador inicial.
        """

        return LoveLetterGameState()

    def create_model(self):
        """
        Crea y devuelve el forward model de Love Letter.

        El forward model contiene:
        - generación de acciones legales;
        - aplicación de efectos;
        - cambio de turno;
        - detección del final;
        - evaluación de estados terminales.
        """

        return LoveLetterForwardModel()

    def read_human_move(self, state):
        """
        Solicita una acción al jugador humano.

        La función read_human_move muestra todas las acciones legales
        y devuelve una tupla con:

            card, target, guess

        card:
            carta elegida.

        target:
            jugador objetivo o None.

        guess:
            carta adivinada con Guardia o None.
        """

        return read_human_move(state)

    def create_action_from_move(self, move, player_id: int):
        """
        Convierte la entrada del jugador humano en un PlayCardAction.

        El framework trabaja con objetos GameAction.
        read_human_move devuelve una tupla sencilla, por lo que aquí
        se transforma en la acción concreta de Love Letter.
        """

        # Se separan los tres valores recibidos.
        card, target, guess = move

        # Se construye la acción concreta.
        #
        # PlayCardAction hereda de GameAction, por lo que puede ser
        # utilizada por Match y por el forward model genérico.
        return PlayCardAction(
            card=card,
            player=player_id,
            target=target,
            guess=guess
        )

    def print_board(self, state):
        """
        Muestra el estado actual de Love Letter por consola.

        Se delega la impresión a la función definida
        en love_letter.py.
        """

        print_board(state)

    def print_ai_action(self, action):
        """
        Muestra por consola la acción elegida por una IA.

        Se imprimen:
        - la carta jugada;
        - el jugador objetivo;
        - la adivinanza utilizada con Guardia.

        target y guess pueden ser None cuando la carta
        no necesita esos datos.
        """

        print(
            "IA juega carta:",
            action.card,
            "objetivo:",
            action.target,
            "adivinanza:",
            action.guess
        )