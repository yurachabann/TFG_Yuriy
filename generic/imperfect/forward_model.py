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