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