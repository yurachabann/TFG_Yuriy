from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
import random
import time

from generic.forward_model import ForwardModel, S, A


@dataclass
class SearchStats:
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0


def alpha_beta(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int,
    alpha: float = float("-inf"),
    beta: float = float("inf"),
    depth: int = 0,
    stats: Optional[SearchStats] = None
) -> tuple[int, Optional[A]]:
    """
    Igual que minimax, pero usando poda alfa-beta.

    alpha = mejor valor garantizado para MAX hasta ahora
    beta  = mejor valor garantizado para MIN hasta ahora

    Si alpha >= beta, se poda la rama porque ya no puede
    influir en la decisión final.
    """
    if stats is not None:
        stats.nodes_visited += 1
        if depth > stats.max_depth:
            stats.max_depth = depth

    if state.is_terminal:
        return model.evaluate_terminal(state, ai_player, depth), None

    actions = model.compute_available_actions(state)
    if not actions:
        return 0, None

    is_ai_turn = (state.current_player == ai_player)

    # CASO MAX

    if is_ai_turn:
        best_score = float("-inf")
        best_action = None

        for action in actions:
            next_state = state.clone()
            model.advance(next_state, action)

            score, _ = alpha_beta(
                next_state,
                model,
                ai_player,
                alpha,
                beta,
                depth + 1,
                stats
            )

            if score > best_score:
                best_score = score
                best_action = action

            # Actualizamos alpha con el mejor valor visto por MAX
            alpha = max(alpha, best_score)

            # Si alpha >= beta, esta rama ya no interesa
            if alpha >= beta:
                if stats is not None:
                    stats.cutoffs += 1
                break

        return int(best_score), best_action

    # CASO MIN

    else:
        best_score = float("inf")
        best_action = None

        for action in actions:
            next_state = state.clone()
            model.advance(next_state, action)

            score, _ = alpha_beta(
                next_state,
                model,
                ai_player,
                alpha,
                beta,
                depth + 1,
                stats
            )

            if score < best_score:
                best_score = score
                best_action = action

            # Actualizamos beta con el mejor valor visto por MIN
            beta = min(beta, best_score)

            # Si alpha >= beta, esta rama ya no interesa
            if alpha >= beta:
                if stats is not None:
                    stats.cutoffs += 1
                break

        return int(best_score), best_action


def choose_ai_move_alpha_beta(state: S, model: ForwardModel[S, A], ai_player: int) -> tuple[A, SearchStats]:
    """
    Función de conveniencia, igual que choose_ai_move de minimax,
    pero usando alfa-beta.
    """
    stats = SearchStats()
    start_time = time.perf_counter()

    _, action = alpha_beta(state, model, ai_player, stats=stats)

    if action is None:
        actions = model.compute_available_actions(state)
        action = random.choice(actions)

    stats.elapsed_time = time.perf_counter() - start_time

    return action, stats