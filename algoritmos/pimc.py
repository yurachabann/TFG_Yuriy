from __future__ import annotations
from typing import Optional, Any
from dataclasses import dataclass
import random
import time

from generic.imperfect.forward_model import ImperfectForwardModel, S, A, I
from algoritmos.minmax_ab_depth_limit import choose_ai_move_alpha_beta_depth_limit


@dataclass
class SearchStats:
    """Métricas de rendimiento acumuladas durante la ejecución de PIMC."""
    determinizations: int = 0
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0


def pimc(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    ai_player: int,
    heuristic: Any,
    samples: int = 30,
    depth: int = 5,
    stats: Optional[SearchStats] = None
) -> Optional[A]:
    """
    Ejecuta Perfect Information Monte Carlo (PIMC).
    
    Genera `samples` determinizaciones y llama a choose_ai_move_alpha_beta_depth_limit
    para cada una, agregando las decisiones y las estadísticas de búsqueda.
    """
    action_votes: dict[A, int] = {}

    for _ in range(samples):
        # 1. Determinización del estado con información incompleta
        det_state = model.determinize(info_state)

        # 2. Resolución del estado determinizado mediante Alfa-Beta
        action, ab_stats = choose_ai_move_alpha_beta_depth_limit(
            state=det_state,
            model=model,
            ai_player=ai_player,
            heuristic=heuristic,
            max_depth=depth
        )

        # 3. Agregación de determinizaciones y estadísticas de Alfa-Beta
        if stats is not None:
            stats.determinizations += 1
            stats.nodes_visited += ab_stats.nodes_visited
            stats.cutoffs += ab_stats.cutoffs
            if ab_stats.max_depth > stats.max_depth:
                stats.max_depth = ab_stats.max_depth

        # 4. Conteo de votos
        if action is not None:
            action_votes[action] = action_votes.get(action, 0) + 1

    if not action_votes:
        sample_state = model.determinize(info_state)
        legal_actions = model.compute_available_actions(sample_state)
        return random.choice(legal_actions) if legal_actions else None

    # Se devuelve la acción con mayor número de votos
    return max(action_votes.keys(), key=lambda a: action_votes[a])


def choose_ai_move_pimc(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    ai_player: int,
    heuristic: Any,
    samples: int = 30,
    depth: int = 5
) -> tuple[A, SearchStats]:
    """
    Punto de entrada principal para PIMC.
    Devuelve la mejor acción y el objeto SearchStats de PIMC completo.
    """
    stats = SearchStats()
    start_time = time.perf_counter()

    action = pimc(
        info_state=info_state,
        model=model,
        ai_player=ai_player,
        heuristic=heuristic,
        samples=samples,
        depth=depth,
        stats=stats
    )

    stats.elapsed_time = time.perf_counter() - start_time
    return action, stats