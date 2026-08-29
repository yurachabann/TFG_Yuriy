from __future__ import annotations
from typing import Optional, Generic, Callable
from dataclasses import dataclass, field
import json
import math
import random
import time
from datetime import datetime
from pathlib import Path

from generic.forward_model import ForwardModel, S, A


# ============================================================
# STATS
# ============================================================

@dataclass
class SearchStats:
    """
    Estadísticas de búsqueda, igual idea que en minimax y alpha-beta.

    nodes_visited:
        Número de nodos del árbol MCTS creados/visitados durante la búsqueda.

    cutoffs:
        Aquí no hay poda alfa-beta, así que normalmente será 0.
        Lo dejamos por compatibilidad con StatsManager.

    max_depth:
        Profundidad máxima alcanzada durante selección/expansión/simulación.

    elapsed_time:
        Tiempo total invertido por el algoritmo.

    rollouts:
        Número de simulaciones aleatorias realizadas.
    """
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0
    rollouts: int = 0


# ============================================================
# TREE NODE
# ============================================================

@dataclass
class MCTSNode(Generic[S, A]):
    """
    Nodo del árbol de búsqueda de MCTS.

    state:
        Estado del juego representado por este nodo.

    parent:
        Nodo padre. None si este nodo es la raíz.

    action_from_parent:
        Acción que se aplicó en el padre para llegar a este nodo.

    untried_actions:
        Acciones legales desde este estado que todavía NO se han expandido.

    children:
        Hijos ya expandidos.

    visits:
        Número de veces que este nodo ha sido visitado durante el MCTS.

    total_reward:
        Suma acumulada de recompensas desde el punto de vista de la IA.
        Ejemplo:
        - victoria IA -> +1
        - empate -> 0
        - derrota -> -1
    """
    state: S
    parent: Optional["MCTSNode[S, A]"] = None
    action_from_parent: Optional[A] = None
    untried_actions: list[A] = field(default_factory=list)
    children: list["MCTSNode[S, A]"] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0

    def is_fully_expanded(self) -> bool:
        """
        Un nodo está totalmente expandido cuando ya no quedan
        acciones legales sin probar.
        """
        return len(self.untried_actions) == 0

    def best_child_by_uct(self, exploration_weight: float, maximizing: bool) -> "MCTSNode[S, A]":
        """
        Devuelve el hijo con mejor valor UCT.

        UCT = explotación + exploración

        explotación = reward medio del hijo
        exploración = C * sqrt( ln(visits_padre) / visits_hijo )

        Idea:
        - Si un hijo da buenos resultados, sube.
        - Si un hijo ha sido poco explorado, también sube.
        - En el turno del rival se invierte la explotación, ya que el rival
          intenta minimizar la recompensa de la IA.
        """
        best_score = float("-inf")
        best_child = None

        for child in self.children:
            if child.visits == 0:
                # En teoría no debería ocurrir mucho aquí si el flujo es correcto,
                # pero si ocurre, lo tratamos como prioritario.
                uct_score = float("inf")
            else:
                exploitation = child.total_reward / child.visits
                if not maximizing:
                    exploitation = -exploitation

                exploration = exploration_weight * math.sqrt(
                    math.log(self.visits) / child.visits
                )
                uct_score = exploitation + exploration

            if uct_score > best_score:
                best_score = uct_score
                best_child = child

        return best_child


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def save_stats_json(
    stats: SearchStats,
    file_path: Path
) -> None:
    """
    Guarda las estadísticas actuales en JSON.

    Se sobrescribe el mismo archivo durante la ejecución para que siempre
    contenga las últimas estadísticas disponibles.
    """
    data = {
        "nodes_visited": stats.nodes_visited,
        "cutoffs": stats.cutoffs,
        "max_depth": stats.max_depth,
        "elapsed_time": stats.elapsed_time,
        "rollouts": stats.rollouts
    }

    temp_path = file_path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    temp_path.replace(file_path)

def terminal_reward(state: S, ai_player: int) -> float:
    """
    Convierte un estado terminal en una recompensa simple para MCTS.

    Convención:
    - victoria IA  -> +1.0
    - empate       ->  0.0
    - derrota IA   -> -1.0

    Esto es distinto del minimax clásico, donde se usan valores tipo
    +10-depth o -10+depth. En MCTS suele ser más natural trabajar con
    recompensas normalizadas.
    """
    if state.winner is None:
        return 0.0
    if state.winner == ai_player:
        return 1.0
    return -1.0


def rollout(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int,
    stats: Optional[SearchStats] = None,
    start_depth: int = 0
) -> float:
    """
    Simulación aleatoria (playout / rollout).

    Desde el estado recibido, juega acciones aleatorias hasta llegar
    a un estado terminal.

    Importante:
    - NO usa heurística.
    - Esto hace que el algoritmo sea totalmente genérico.
    - Es la versión clásica y más fácil de entender.

    Devuelve la recompensa final desde el punto de vista de la IA.
    """
    depth = start_depth
    rollout_state = state.clone()

    if stats is not None:
        stats.rollouts += 1

    while not rollout_state.is_terminal:
        actions = model.compute_available_actions(rollout_state)

        # Caso defensivo: si por algún motivo no hay acciones aunque no
        # se haya marcado terminal, lo tratamos como empate.
        if not actions:
            return 0.0

        action = random.choice(actions)
        model.advance(rollout_state, action)

        depth += 1
        if stats is not None and depth > stats.max_depth:
            stats.max_depth = depth

    return terminal_reward(rollout_state, ai_player)


def backpropagate(node: MCTSNode[S, A], reward: float) -> None:
    """
    Retropropaga la recompensa desde el nodo hoja hasta la raíz.

    Todos los nodos del camino:
    - incrementan visitas
    - acumulan la recompensa

    Ojo:
    Como la recompensa siempre está expresada desde la perspectiva
    de la IA que está pensando, NO hace falta alternar signo entre
    niveles del árbol.
    La diferencia entre el turno de la IA y el del rival se gestiona
    durante la selección UCT, maximizando o minimizando la explotación.
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
    stats: Optional[SearchStats] = None,
    stats_callback: Optional[Callable[[int], None]] = None
) -> Optional[A]:
    """
    Ejecuta Monte Carlo Tree Search y devuelve la mejor acción encontrada.

    Parámetros:
    - state: estado actual
    - model: forward model del juego
    - ai_player: identificador del jugador IA
    - iterations: número de iteraciones del MCTS
    - exploration_weight: constante C de UCT

    Flujo de cada iteración:
    1. Selección
    2. Expansión
    3. Simulación
    4. Retropropagación
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
        stats.max_depth = max(stats.max_depth, 0)

    for iteration in range(iterations):
        node = root
        depth = 0

        # ====================================================
        # 1. SELECCIÓN
        # ====================================================
        # Bajamos por el árbol mientras:
        # - el nodo no sea terminal
        # - y esté totalmente expandido
        #
        # Elegimos en cada paso el mejor hijo según UCT.
        while (
            not node.state.is_terminal
            and node.is_fully_expanded()
            and len(node.children) > 0
        ):
            maximizing = node.state.current_player == ai_player
            node = node.best_child_by_uct(exploration_weight, maximizing)
            depth += 1

            if stats is not None and depth > stats.max_depth:
                stats.max_depth = depth

        # ====================================================
        # 2. EXPANSIÓN
        # ====================================================
        # Si el nodo no es terminal y aún quedan acciones sin probar,
        # expandimos una de ellas.
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
        # 3. SIMULACIÓN
        # ====================================================
        # Desde el nodo actual hacemos una partida aleatoria
        # hasta el final.
        if node.state.is_terminal:
            reward = terminal_reward(node.state, ai_player)
        else:
            reward = rollout(node.state, model, ai_player, stats, start_depth=depth)

        # ====================================================
        # 4. RETROPROPAGACIÓN
        # ====================================================
        backpropagate(node, reward)

        if stats_callback is not None:
            stats_callback(iteration + 1)

    # ========================================================
    # ELECCIÓN FINAL
    # ========================================================
    # Al final suele elegirse el hijo más visitado.
    #
    # ¿Por qué no el de mejor reward medio?
    # Porque el más visitado suele ser la decisión más robusta
    # tras el equilibrio exploración/explotación del MCTS.
    if not root.children:
        return random.choice(root_actions)

    best_child = max(root.children, key=lambda child: child.visits)
    return best_child.action_from_parent


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def choose_ai_move_mcts(
    state: S,
    model: ForwardModel[S, A],
    ai_player: int,
    iterations: int = 1000,
    exploration_weight: float = math.sqrt(2),
    save_stats: bool = False
) -> tuple[A, SearchStats]:
    """
    Función pública con el mismo estilo que tus otros algoritmos.

    Devuelve:
    - acción elegida
    - estadísticas
    """
    stats = SearchStats()
    start_time = time.perf_counter()
    stats_file = None

    if save_stats:
        stats_dir = Path("stats")
        stats_dir.mkdir(parents=True, exist_ok=True)
        stats_file = stats_dir / f"mcts_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        save_stats_json(stats, stats_file)

    def update_realtime_stats(_: int) -> None:
        if stats_file is None:
            return

        stats.elapsed_time = time.perf_counter() - start_time
        save_stats_json(stats, stats_file)

    try:
        action = mcts(
            state=state,
            model=model,
            ai_player=ai_player,
            iterations=iterations,
            exploration_weight=exploration_weight,
            stats=stats,
            stats_callback=update_realtime_stats if save_stats else None
        )

        if action is None:
            actions = model.compute_available_actions(state)
            action = random.choice(actions)

        stats.elapsed_time = time.perf_counter() - start_time

        if stats_file is not None:
            save_stats_json(stats, stats_file)

        return action, stats
    except Exception:
        stats.elapsed_time = time.perf_counter() - start_time

        if stats_file is not None:
            save_stats_json(stats, stats_file)

        raise
