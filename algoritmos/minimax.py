from __future__ import annotations
from typing import TypeVar, Optional, Tuple
from dataclasses import dataclass
import random
import time

from generic.game_state import GameState
from generic.forward_model import ForwardModel
from generic.game_action import GameAction

S = TypeVar("S", bound=GameState)
A = TypeVar("A", bound=GameAction)


@dataclass
class SearchStats:
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0


def evaluate_terminal(state: GameState, ai_player: int, depth: int) -> int:
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
) -> Tuple[int, Optional[A]]:
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

    if is_ai_turn:
        best_score = -10**9
        best_action = None

        for action in actions:
            next_state = state.clone()
            model.advance(next_state, action)

            score, _ = minimax(next_state, model, ai_player, depth + 1, stats)

            if score > best_score:
                best_score = score
                best_action = action

        return best_score, best_action

    else:
        best_score = 10**9
        best_action = None

        for action in actions:
            next_state = state.clone()
            model.advance(next_state, action)

            score, _ = minimax(next_state, model, ai_player, depth + 1, stats)

            if score < best_score:
                best_score = score
                best_action = action

        return best_score, best_action


def choose_ai_move(state: S, model: ForwardModel[S, A], ai_player: int) -> Tuple[A, SearchStats]:
    stats = SearchStats()
    start_time = time.perf_counter()

    _, action = minimax(state, model, ai_player, 0, stats)

    if action is None:
        action = random.choice(model.compute_available_actions(state))

    stats.elapsed_time = time.perf_counter() - start_time

    return action, stats