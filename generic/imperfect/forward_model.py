from abc import abstractmethod

from generic.forward_model import ForwardModel


class ImperfectForwardModel(ForwardModel):
    """
    Forward model para juegos de información imperfecta.

    Además de la funcionalidad de un ForwardModel convencional,
    permite generar el estado observable y realizar
    determinizaciones del juego.
    """

    @abstractmethod
    def create_information_state(
        self,
        state,
        player_id
    ):
        """
        Devuelve la información observable por el jugador.
        """
        pass

    @abstractmethod
    def determinize(
        self,
        information_state
    ):
        """
        Genera un estado completo compatible con la información
        conocida por el jugador.
        """
        pass