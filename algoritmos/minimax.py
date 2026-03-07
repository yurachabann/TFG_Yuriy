from __future__ import annotations
from typing import TypeVar, Optional, Tuple
import random

from generic.game_state import GameState
from generic.forward_model import ForwardModel
from generic.game_action import GameAction

S = TypeVar("S", bound=GameState)
A = TypeVar("A", bound=GameAction)


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
    depth: int = 0
) -> Tuple[int, Optional[A]]:
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

            score, _ = minimax(next_state, model, ai_player, depth + 1)

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

            score, _ = minimax(next_state, model, ai_player, depth + 1)

            if score < best_score:
                best_score = score
                best_action = action

        return best_score, best_action


def choose_ai_move(state: S, model: ForwardModel[S, A], ai_player: int) -> A:
    _, action = minimax(state, model, ai_player, 0)

    if action is None:
        return random.choice(model.compute_available_actions(state))

    return action