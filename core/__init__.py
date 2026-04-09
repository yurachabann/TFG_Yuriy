"""
Core del sistema.

Este paquete contiene:
- game: abstracción base de un juego
- match: ejecución de una partida
- match_runner: ejecución de múltiples partidas
- stats_manager: gestión y persistencia de estadísticas
- players: tipos de jugadores (HumanPlayer, AIPlayer)

Este archivo permite que 'core' sea tratado como un paquete de Python.
"""

# Export opcional de clases principales para imports más limpios

from core.game import Game
from core.match import Match
from core.match_runner import MatchRunner
from core.stats_manager import StatsManager

__all__ = [
    "Game",
    "Match",
    "MatchRunner",
    "StatsManager",
]