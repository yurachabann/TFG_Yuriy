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


def evaluate_terminal(state: S, ai_player: int, depth: int) -> int:
    if state.winner is None:
        return 0
    if state.winner == ai_player:
        return 10 - depth
    return -10 + depth


def minimax(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int,
    depth: int = 0,
    stats: Optional[SearchStats] = None
) -> tuple[int, Optional[A]]:

    if stats is not None:
        stats.nodes_visited += 1
        if depth > stats.max_depth:
            stats.max_depth = depth

    if state.is_terminal:
        return evaluate_terminal(state, ai_player, depth), None

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

            score, _ = minimax(
                next_state,
                model,
                ai_player,
                depth + 1,
                stats
            )

            if score > best_score:
                best_score = score
                best_action = action

        return int(best_score), best_action
    
    # CASO MIN (RIVAL)

    else:
        best_score = float("inf")
        best_action = None

        for action in actions:
            next_state = state.clone()
            model.advance(next_state, action)

            score, _ = minimax(
                next_state,
                model,
                ai_player,
                depth + 1,
                stats
            )

            if score < best_score:
                best_score = score
                best_action = action

        return int(best_score), best_action


def choose_ai_move(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int
) -> tuple[A, SearchStats]:

    stats = SearchStats()
    start_time = time.perf_counter()

    _, action = minimax(state, model, ai_player, 0, stats)

    if action is None:
        actions = model.compute_available_actions(state)
        action = random.choice(actions)

    stats.elapsed_time = time.perf_counter() - start_time

    return action, stats