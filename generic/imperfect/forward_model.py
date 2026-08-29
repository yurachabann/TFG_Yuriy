from abc import abstractmethod
from typing import Generic, TypeVar

from generic.forward_model import ForwardModel

# Definimos las variables de tipo para el Estado, Acción e InformationState
S = TypeVar("S")
A = TypeVar("A")
I = TypeVar("I")


class ImperfectForwardModel(ForwardModel[S, A], Generic[S, A, I]):
    """
    Forward model para juegos de información imperfecta.
    """

    @abstractmethod
    def create_information_state(
        self,
        state: S,
        player_id: int
    ) -> I:
        """
        Devuelve la información observable por el jugador.
        """
        pass

    @abstractmethod
    def determinize(
        self,
        information_state: I
    ) -> S:
        """
        Genera un estado completo compatible con la información
        conocida por el jugador.
        """
        pass

    def create_initial_state(
        self,
        reference_information_state: I
    ) -> S:
        """
        Crea un estado inicial completo NUEVO del juego.

        Este método se utiliza durante el entrenamiento global de algoritmos
        como MCCFR. El InformationState recibido se usa únicamente como referencia
        para descubrir el tipo y la configuración estructural del juego.

        La información privada concreta de la partida actual no se reutiliza como
        raíz del entrenamiento. Después de crear un estado vacío, setup_game(state)
        debe generar un comienzo nuevo e independiente.
        """
        sample_state = self.determinize(reference_information_state)
        state_type = type(sample_state)
        constructor_kwargs = {}

        # Conservamos únicamente parámetros estructurales del juego.
        # No copiamos manos, mazos, barcos, puntuaciones ni otra información privada.
        for attribute in ("num_players", "grid_size"):
            if hasattr(sample_state, attribute):
                constructor_kwargs[attribute] = getattr(sample_state, attribute)

        try:
            initial_state = state_type(**constructor_kwargs)
        except TypeError:
            # Fallback para estados cuyo constructor no acepte esos parámetros.
            initial_state = state_type()

        setup_game = getattr(self, "setup_game", None)
        if setup_game is None or not callable(setup_game):
            raise NotImplementedError(
                f"{type(self).__name__} debe implementar setup_game(state) "
                "para poder crear un estado inicial nuevo."
            )

        # setup_game debe realizar de nuevo todos los eventos aleatorios iniciales:
        # barajado, reparto, colocación de elementos ocultos, etc.
        setup_game(initial_state)

        return initial_state

    def get_current_player(self, state: S) -> int:
        """
        Devuelve el ID del jugador al que le toca mover en el estado actual.
        
        Implementación por defecto: lee el atributo 'current_player' de GameState.
        Se puede sobrescribir en clases hijas si el juego requiere una lógica especial.
        """
        if hasattr(state, "current_player"):
            return state.current_player
        
        raise NotImplementedError(
            "El estado recibido no tiene el atributo 'current_player'. "
            "Debes implementar 'get_current_player' en tu ForwardModel."
        )