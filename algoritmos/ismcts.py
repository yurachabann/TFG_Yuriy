from __future__ import annotations
from typing import Optional, Generic, TypeVar
from dataclasses import dataclass, field
import math
import random
import time

from generic.imperfect.forward_model import ImperfectForwardModel, S, A, I


# ============================================================
# STATS
# ============================================================

@dataclass
class ISMCTSStats:
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0


# ============================================================
# TREE NODE PARA ISMCTS
# ============================================================

@dataclass
class ISMCTSNode(Generic[A]):
    """
    Nodo del árbol ISMCTS.
    A diferencia del MCTS estándar, no mantiene un GameState fijo, 
    sino la acción que lo originó y el historial de visitas/recompensas.
    """
    parent: Optional[ISMCTSNode[A]] = None
    action_from_parent: Optional[A] = None
    children: dict[A, ISMCTSNode[A]] = field(default_factory=dict)
    visits: int = 0
    total_reward: float = 0.0

    def best_child_by_uct(self, legal_actions: list[A], exploration_weight: float) -> tuple[A, ISMCTSNode[A]]:
        """
        Devuelve la mejor acción (y su nodo hijo) entre las acciones legalmente 
        disponibles en la determinización actual usando la fórmula UCT.
        """
        best_score = float("-inf")
        best_action = None
        best_child = None

        for action in legal_actions:
            child = self.children.get(action)
            if child is None or child.visits == 0:
                uct_score = float("inf")
            else:
                exploitation = child.total_reward / child.visits
                exploration = exploration_weight * math.sqrt(
                    math.log(self.visits) / child.visits
                )
                uct_score = exploitation + exploration

            if uct_score > best_score:
                best_score = uct_score
                best_action = action
                best_child = child

        return best_action, best_child


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def terminal_reward(state: S, ai_player: int) -> float:
    if state.winner is None:
        return 0.0
    if state.winner == ai_player:
        return 1.0
    return -1.0


def rollout(
    state: S,
    model: ImperfectForwardModel[S, A, I],
    ai_player: int,
    stats: Optional[ISMCTSStats] = None,
    start_depth: int = 0
) -> float:
    """
    Simula la partida aleatoriamente desde la determinización actual hasta el final.
    """
    depth = start_depth
    rollout_state = state.clone()

    while not rollout_state.is_terminal:
        actions = model.compute_available_actions(rollout_state)
        if not actions:
            return 0.0

        action = random.choice(actions)
        model.advance(rollout_state, action)

        depth += 1
        if stats is not None and depth > stats.max_depth:
            stats.max_depth = depth

    return terminal_reward(rollout_state, ai_player)


def backpropagate(node: ISMCTSNode[A], reward: float) -> None:
    """
    Retropropaga la recompensa en el árbol.
    """
    current = node
    while current is not None:
        current.visits += 1
        current.total_reward += reward
        current = current.parent


# ============================================================
# MAIN ISMCTS
# ============================================================

def ismcts(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    ai_player: int,
    iterations: int = 1000,
    exploration_weight: float = math.sqrt(2),
    stats: Optional[ISMCTSStats] = None
) -> Optional[A]:
    """
    Ejecuta Information Set Monte Carlo Tree Search (ISMCTS).
    """
    root = ISMCTSNode[A]()

    if stats is not None:
        stats.nodes_visited += 1

    for _ in range(iterations):
        # 0. DETERMINIZACIÓN
        # Creamos una instancia de estado completo coherente con nuestro estado de información
        det_state = model.determinize(info_state)
        node = root
        depth = 0

        # 1. SELECCIÓN
        # Descendemos por el árbol mientras el estado no sea terminal
        # y todas las acciones legales en det_state ya estén expandidas en el nodo actual.
        while not det_state.is_terminal:
            legal_actions = model.compute_available_actions(det_state)
            if not legal_actions:
                break

            # Comprobar si hay alguna acción legal que aún no hemos expandido
            untried_legal_actions = [a for a in legal_actions if a not in node.children]

            if untried_legal_actions:
                # Hay acciones sin probar en este nodo para este estado determinizado -> romper para expandir
                break

            # Si todas las acciones legales están expandidas, elegimos por UCT
            action, child_node = node.best_child_by_uct(legal_actions, exploration_weight)
            model.advance(det_state, action)
            node = child_node
            depth += 1

            if stats is not None and depth > stats.max_depth:
                stats.max_depth = depth

        # 2. EXPANSIÓN
        # Si el estado no es terminal y hay acciones legales no probadas en el nodo actual
        if not det_state.is_terminal:
            legal_actions = model.compute_available_actions(det_state)
            untried_legal_actions = [a for a in legal_actions if a not in node.children]

            if untried_legal_actions:
                action = random.choice(untried_legal_actions)
                
                # Creamos el nuevo nodo hijo asociado a esta acción
                new_child = ISMCTSNode(parent=node, action_from_parent=action)
                node.children[action] = new_child
                node = new_child

                # Avanzamos la determinización con la acción elegida
                model.advance(det_state, action)
                depth += 1

                if stats is not None:
                    stats.nodes_visited += 1
                    if depth > stats.max_depth:
                        stats.max_depth = depth

        # 3. SIMULACIÓN (ROLLOUT)
        if det_state.is_terminal:
            reward = terminal_reward(det_state, ai_player)
        else:
            reward = rollout(det_state, model, ai_player, stats, start_depth=depth)

        # 4. RETROPROPAGACIÓN
        backpropagate(node, reward)

    # ========================================================
    # ELECCIÓN FINAL
    # ========================================================
    if not root.children:
        # Fallback si no se pudo expandir nada
        sample_det = model.determinize(info_state)
        available = model.compute_available_actions(sample_det)
        return random.choice(available) if available else None

    # Devolvemos la acción con más visitas en la raíz
    best_action = max(root.children.keys(), key=lambda a: root.children[a].visits)
    return best_action


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def choose_ai_move_ismcts(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    ai_player: int,
    iterations: int = 1000,
    exploration_weight: float = math.sqrt(2)
) -> tuple[A, ISMCTSStats]:
    """
    Función de entrada pública compatible con la interfaz de tu MCTS original.
    Recibe el InformationState en lugar del GameState.
    """
    stats = ISMCTSStats()
    start_time = time.perf_counter()

    action = ismcts(
        info_state=info_state,
        model=model,
        ai_player=ai_player,
        iterations=iterations,
        exploration_weight=exploration_weight,
        stats=stats
    )

    stats.elapsed_time = time.perf_counter() - start_time
    return action, stats