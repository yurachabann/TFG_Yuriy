from __future__ import annotations

from typing import Optional, Generic
from dataclasses import dataclass, field
import math
import random
import time

from generic.forward_model import ForwardModel, S, A


# ============================================================
# STATS
# ============================================================

@dataclass
class SearchStats:
    """
    Estadísticas compatibles con StatsManager.

    nodes_visited:
        Número de nodos creados/visitados por MCTS.

    cutoffs:
        En MCTS no hay poda alfa-beta, así que normalmente será 0.

    max_depth:
        Profundidad máxima alcanzada durante selección, expansión o rollout.

    elapsed_time:
        Tiempo total invertido por el algoritmo.
    """
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0


# ============================================================
# TREE NODE
# ============================================================

@dataclass
class MCTSNode(Generic[S, A]):
    """
    Nodo del árbol MCTS.
    """
    state: S
    parent: Optional["MCTSNode[S, A]"] = None
    action_from_parent: Optional[A] = None
    untried_actions: list[A] = field(default_factory=list)
    children: list["MCTSNode[S, A]"] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0

    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    def best_child_by_uct(self, exploration_weight: float) -> "MCTSNode[S, A]":
        """
        Elige el hijo con mejor UCT:

        UCT = explotación + exploración

        explotación = recompensa_media
        exploración = C * sqrt(log(visitas_padre) / visitas_hijo)
        """
        best_score = float("-inf")
        best_child = None

        for child in self.children:
            if child.visits == 0:
                uct_score = float("inf")
            else:
                exploitation = child.total_reward / child.visits
                exploration = exploration_weight * math.sqrt(
                    math.log(self.visits) / child.visits
                )
                uct_score = exploitation + exploration

            if uct_score > best_score:
                best_score = uct_score
                best_child = child

        return best_child


# ============================================================
# REWARD FUNCTIONS
# ============================================================

def terminal_reward(state: S, ai_player: int) -> float:
    """
    Convierte un estado terminal en recompensa normalizada.

    IA gana   -> +1.0
    empate    ->  0.0
    IA pierde -> -1.0
    """
    if state.winner is None:
        return 0.0

    if state.winner == ai_player:
        return 1.0

    return -1.0


def heuristic_reward(state: S, model: ForwardModel[S, A], ai_player: int) -> float:
    """
    Recompensa aproximada cuando el rollout se corta por profundidad máxima.

    Caso 1:
        Si el modelo tiene evaluate_heuristic(state, ai_player),
        se usa esa heurística y se normaliza a [-1, 1].

    Caso 2:
        Si no existe evaluate_heuristic, devuelve 0.0.
        Así el MCTS sigue siendo genérico.

    Esto permite que 4 en raya aproveche evaluate_heuristic,
    pero que otros juegos sigan funcionando sin tener heurística.
    """
    if not hasattr(model, "evaluate_heuristic"):
        return 0.0

    score = model.evaluate_heuristic(state, ai_player)

    # Normalización suave.
    # Evita que una heurística grande rompa la escala del MCTS.
    return math.tanh(score / 100.0)


# ============================================================
# ROLLOUT
# ============================================================

def rollout(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int,
    stats: Optional[SearchStats] = None,
    start_depth: int = 0,
    max_rollout_depth: Optional[int] = None
) -> float:
    """
    Simulación aleatoria desde el estado actual.

    Si max_rollout_depth es None:
        juega aleatoriamente hasta estado terminal.

    Si max_rollout_depth tiene valor:
        corta el rollout cuando se alcanza esa profundidad máxima.

    Cuando corta por profundidad:
        - si el estado es terminal, usa terminal_reward
        - si no es terminal, usa heuristic_reward si existe
        - si no existe heurística, devuelve 0.0
    """
    depth = start_depth
    rollout_state = state.clone()

    while not rollout_state.is_terminal:
        if max_rollout_depth is not None and depth >= max_rollout_depth:
            if stats is not None:
                stats.cutoffs += 1
            return heuristic_reward(rollout_state, model, ai_player)

        actions = model.compute_available_actions(rollout_state)

        if not actions:
            return 0.0

        action = random.choice(actions)
        model.advance(rollout_state, action)

        depth += 1

        if stats is not None and depth > stats.max_depth:
            stats.max_depth = depth

    return terminal_reward(rollout_state, ai_player)


# ============================================================
# BACKPROPAGATION
# ============================================================

def backpropagate(node: MCTSNode[S, A], reward: float) -> None:
    """
    Retropropaga la recompensa hasta la raíz.

    La recompensa siempre está desde el punto de vista de la IA,
    por eso NO alternamos el signo en cada nivel.
    """
    current = node

    while current is not None:
        current.visits += 1
        current.total_reward += reward
        current = current.parent


# ============================================================
# MAIN MCTS
# ============================================================

def mcts(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int,
    iterations: int = 1000,
    exploration_weight: float = math.sqrt(2),
    max_rollout_depth: Optional[int] = None,
    stats: Optional[SearchStats] = None
) -> Optional[A]:
    """
    Ejecuta Monte Carlo Tree Search.

    Parámetros:
    - iterations:
        número de iteraciones MCTS.

    - exploration_weight:
        constante C de UCT.
        Más alta = explora más.
        Más baja = explota más lo que ya parece bueno.

    - max_rollout_depth:
        profundidad máxima de los rollouts.
        None = rollout hasta terminal.
        Ejemplo: 8, 10, 12...

    Flujo:
    1. Selección
    2. Expansión
    3. Rollout
    4. Backpropagation
    """
    if state.is_terminal:
        return None

    root_actions = model.compute_available_actions(state)

    if not root_actions:
        return None

    root = MCTSNode(
        state=state.clone(),
        parent=None,
        action_from_parent=None,
        untried_actions=root_actions.copy()
    )

    if stats is not None:
        stats.nodes_visited += 1

    for _ in range(iterations):
        node = root
        depth = 0

        # ====================================================
        # 1. SELECCIÓN
        # ====================================================
        while (
            not node.state.is_terminal
            and node.is_fully_expanded()
            and len(node.children) > 0
        ):
            node = node.best_child_by_uct(exploration_weight)
            depth += 1

            if stats is not None and depth > stats.max_depth:
                stats.max_depth = depth

        # ====================================================
        # 2. EXPANSIÓN
        # ====================================================
        if not node.state.is_terminal and node.untried_actions:
            action = random.choice(node.untried_actions)
            node.untried_actions.remove(action)

            next_state = node.state.clone()
            model.advance(next_state, action)

            child_actions = model.compute_available_actions(next_state)

            child = MCTSNode(
                state=next_state,
                parent=node,
                action_from_parent=action,
                untried_actions=child_actions.copy()
            )

            node.children.append(child)
            node = child
            depth += 1

            if stats is not None:
                stats.nodes_visited += 1

                if depth > stats.max_depth:
                    stats.max_depth = depth

        # ====================================================
        # 3. ROLLOUT / SIMULACIÓN
        # ====================================================
        if node.state.is_terminal:
            reward = terminal_reward(node.state, ai_player)
        else:
            reward = rollout(
                state=node.state,
                model=model,
                ai_player=ai_player,
                stats=stats,
                start_depth=depth,
                max_rollout_depth=max_rollout_depth
            )

        # ====================================================
        # 4. BACKPROPAGATION
        # ====================================================
        backpropagate(node, reward)

    # ========================================================
    # ELECCIÓN FINAL
    # ========================================================
    # Se elige el hijo más visitado, no necesariamente el de mejor media.
    # Esto suele ser más estable en MCTS.
    if not root.children:
        return random.choice(root_actions)

    best_child = max(root.children, key=lambda child: child.visits)
    return best_child.action_from_parent


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def choose_ai_move_mcts_max_depth(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int,
    iterations: int = 1000,
    exploration_weight: float = math.sqrt(2),
    max_rollout_depth: Optional[int] = None
) -> tuple[A, SearchStats]:
    """
    Función pública compatible con AIPlayer.

    Convención:
        algorithm_fn(state, model, ai_player, **params) -> (action, stats)

    Ejemplo de uso en AIPlayer:
        AIPlayer(
            name="MCTS 1000 depth 10",
            player_id=2,
            algorithm_fn=choose_ai_move_mcts,
            algorithm_params={
                "iterations": 1000,
                "max_rollout_depth": 10
            }
        )
    """
    stats = SearchStats()
    start_time = time.perf_counter()

    action = mcts(
        state=state,
        model=model,
        ai_player=ai_player,
        iterations=iterations,
        exploration_weight=exploration_weight,
        max_rollout_depth=max_rollout_depth,
        stats=stats
    )

    if action is None:
        actions = model.compute_available_actions(state)

        if not actions:
            raise ValueError("No hay acciones disponibles para elegir.")

        action = random.choice(actions)

    stats.elapsed_time = time.perf_counter() - start_time
    return action, stats