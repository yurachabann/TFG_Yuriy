from __future__ import annotations
from typing import Optional, Generic, Any
from dataclasses import dataclass, field
import math
import random
import time

from generic.imperfect.forward_model import ImperfectForwardModel, S, A, I

@dataclass
class ISMCTSStats:
    """
    Guarda métricas de rendimiento del algoritmo durante la ejecución.
    
    - nodes_visited: Número total de nodos creados/añadidos al árbol.
    - cutoffs: Inexistente en MCTS/ISMCTS (se mantiene por compatibilidad con la interfaz).
    - max_depth: Profundidad máxima alcanzada durante la simulación.
    - elapsed_time: Tiempo total de cálculo en segundos.
    """
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0


# ============================================================
# NODO DEL ÁRBOL PARA ISMCTS 
# ============================================================

def _to_hashable(obj: Any) -> Any:
    """
    Convierte un InformationState en una representación inmutable para poder
    utilizarlo como parte de la clave de los nodos del árbol.

    Esto permite distinguir correctamente situaciones en las que una misma
    acción produce observaciones diferentes para el jugador raíz.
    """
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return tuple(_to_hashable(x) for x in obj)
    if isinstance(obj, (set, frozenset)):
        return frozenset(_to_hashable(x) for x in obj)
    if isinstance(obj, dict):
        return tuple(
            sorted(
                (_to_hashable(k),_to_hashable(v))
                for k, v in obj.items()
            )
        )
    if hasattr(obj, "__dict__"):
        return tuple(
            sorted(
                (k,_to_hashable(v))
                for k, v in obj.__dict__.items()
            )
        )
    return repr(obj)


@dataclass
class ISMCTSNode(Generic[A]):
    """
    Representa un conjunto de información o punto de decisión en el árbol ISMCTS.

    A diferencia de MCTS estándar:
    1. No guarda un estado completo determinista, sino la clave del InformationState
       observado por el jugador raíz.
    2. Una misma acción puede conducir a hijos distintos si produce observaciones
       diferentes para el jugador raíz.
    3. Registra la disponibilidad ('availability') de cada acción vista desde este nodo.
    """
    parent: Optional[ISMCTSNode[A]] = None
    action_from_parent: Optional[A] = None

    # InformationState del jugador raíz asociado a este nodo.
    information_state_key: Optional[Any] = None
    # Jugador que ejecutó action_from_parent para llegar a este nodo.
    # En SO-ISMCTS la recompensa almacenada en el nodo se interpreta desde
    # la perspectiva de este jugador, no siempre desde la perspectiva de la IA raíz.
    player_just_moved: Optional[int] = None
    # Los hijos se identifican mediante:
    # (acción realizada, InformationState resultante del jugador raíz).
    #
    # De esta forma, por ejemplo, jugar PRIEST y descubrir una PRINCESS no comparte
    # necesariamente el mismo nodo que jugar PRIEST y descubrir un GUARD.
    children: dict[tuple[A, Any], ISMCTSNode[A]] = field(default_factory=dict)
    # Visitas reales que ha recibido este nodo
    visits: int = 0
    # La disponibilidad mide cuántas veces la acción 'a' estuvo disponible (fue legal)
    # mientras estábamos en este nodo padre.
    availability: dict[A, int] = field(default_factory=dict)
    # Recompensa acumulada desde la perspectiva de player_just_moved.
    total_reward: float = 0.0

    def get_action_stats(self, action: A) -> tuple[int, float]:
        """
        Agrega visitas y recompensa de todos los hijos producidos por una acción.

        Una acción puede tener varios hijos porque puede producir observaciones
        diferentes según la determinización utilizada.
        """
        visits = 0
        total_reward = 0.0

        for (child_action, _), child in self.children.items():
            if child_action == action:
                visits += child.visits
                total_reward += child.total_reward

        return visits, total_reward

    def best_action_by_uct(
        self,
        legal_actions: list[A],
        exploration_weight: float
    ) -> A:
        """
        Selecciona la mejor acción legal usando UCT modificado para ISMCTS.

        Las estadísticas de explotación se agregan entre todos los posibles
        InformationStates resultantes de una misma acción. La disponibilidad
        continúa perteneciendo a la acción en el nodo padre.
        """
        best_score = float("-inf")
        best_action = None

        for action in legal_actions:
            action_visits, action_total_reward = self.get_action_stats(action)

            if action_visits == 0:
                uct_score = float("inf")
            else:
                exploitation = action_total_reward / action_visits
                action_avail = max(1, self.availability.get(action, 1))
                exploration = exploration_weight * math.sqrt(math.log(action_avail) / action_visits)
                uct_score = exploitation + exploration

            if uct_score > best_score:
                best_score = uct_score
                best_action = action

        return best_action


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def terminal_reward(state: S, ai_player: int) -> float:
    """
    Devuelve la recompensa según el resultado final del estado terminal.
    Perspectiva de la IA: +1.0 (Victoria), -1.0 (Derrota), 0.0 (Empate).
    """
    if state.winner is None:
        return 0.0
    if state.winner == ai_player:
        return 1.0
    return -1.0


def rollout(
    state: S,
    model: ImperfectForwardModel[S, A, I],
    stats: Optional[ISMCTSStats] = None,
    start_depth: int = 0
) -> S:
    """
    Fase de Simulación (Play-out / Rollout):
    Juega la partida con acciones completamente aleatorias desde la determinización actual
    hasta alcanzar un estado final terminal.

    Devuelve el estado final simulado. La recompensa se calcula después, durante
    la retropropagación, desde la perspectiva del jugador asociado a cada nodo.
    """
    depth = start_depth
    rollout_state = state.clone()

    while not rollout_state.is_terminal:
        actions = model.compute_available_actions(rollout_state)
        if not actions:
            return rollout_state

        # Elección aleatoria pura (sin heurísticas)
        action = random.choice(actions)
        model.advance(rollout_state, action)

        depth += 1
        if stats is not None and depth > stats.max_depth:
            stats.max_depth = depth

    return rollout_state


# ============================================================
# ALGORITMO PRINCIPAL ISMCTS
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
    Ejecuta Single Observer Information Set Monte Carlo Tree Search (SO-ISMCTS).

    El árbol se construye desde el punto de vista del jugador raíz (ai_player).
    Los nodos distinguen los InformationStates observables por ese jugador, de
    forma que una misma acción puede conducir a nodos diferentes cuando produce
    información privada diferente.
    """
    root = ISMCTSNode[A](information_state_key=_to_hashable(info_state))

    if stats is not None:
        stats.nodes_visited += 1

    for _ in range(iterations):
        # ----------------------------------------------------
        # 0. DETERMINIZACIÓN
        # ----------------------------------------------------
        # Convertimos la información incompleta actual en un estado determinista completo.
        det_state = model.determinize(info_state)
        node = root
        visited_nodes_in_sim = [node]
        depth = 0

        # Candidatos que pueden utilizarse directamente en la fase de expansión.
        expansion_candidates = []

        # ----------------------------------------------------
        # 1. SELECCIÓN
        # ----------------------------------------------------
        while not det_state.is_terminal:
            legal_actions = model.compute_available_actions(det_state)
            if not legal_actions:
                break

            # Cada acción legal ha estado disponible una vez más en esta visita al nodo.
            for action in legal_actions:
                node.availability[action] = node.availability.get(action, 0) + 1

            # Para cada acción calculamos qué InformationState observaría el jugador raíz
            # después de aplicarla en esta determinización.
            transitions = {}

            for action in legal_actions:
                next_state = det_state.clone()
                model.advance(next_state, action)

                next_info_state = model.create_information_state(next_state,ai_player)
                next_info_key = _to_hashable(next_info_state)
                child_key = (action, next_info_key)

                transitions[action] = (
                    next_state,
                    next_info_key,
                    child_key
                )

                if child_key not in node.children:
                    expansion_candidates.append(
                        (action,next_state,next_info_key,child_key)
                    )

            # Si existe al menos una transición compatible todavía no expandida,
            # pasamos a la fase de expansión.
            if expansion_candidates:
                break

            # Todas las transiciones compatibles ya existen:
            # seleccionamos la acción con mejor UCT agregado.
            action = node.best_action_by_uct(
                legal_actions,
                exploration_weight
            )

            next_state, _, child_key = transitions[action]

            det_state = next_state
            node = node.children[child_key]
            visited_nodes_in_sim.append(node)
            depth += 1

            if stats is not None and depth > stats.max_depth:
                stats.max_depth = depth

        # ----------------------------------------------------
        # 2. EXPANSIÓN
        # ----------------------------------------------------
        if not det_state.is_terminal and expansion_candidates:
            action, next_state, next_info_key, child_key = random.choice(
                expansion_candidates
            )

            # El jugador que realiza la acción se obtiene antes de avanzar.
            player_just_moved = model.get_current_player(det_state)

            new_child = ISMCTSNode(
                parent=node,
                action_from_parent=action,
                information_state_key=next_info_key,
                player_just_moved=player_just_moved
            )

            node.children[child_key] = new_child

            det_state = next_state
            node = new_child
            visited_nodes_in_sim.append(node)
            depth += 1

            if stats is not None:
                stats.nodes_visited += 1
                if depth > stats.max_depth:
                    stats.max_depth = depth

        # ----------------------------------------------------
        # 3. SIMULACIÓN (ROLLOUT)
        # ----------------------------------------------------
        if det_state.is_terminal:
            terminal_state = det_state
        else:
            terminal_state = rollout(det_state,model,stats,start_depth=depth)

        # ----------------------------------------------------
        # 4. RETROPROPAGACIÓN (BACKPROPAGATION)
        # ----------------------------------------------------
        for visited_node in visited_nodes_in_sim:
            visited_node.visits += 1

            if visited_node.player_just_moved is not None:
                reward = terminal_reward(terminal_state,visited_node.player_just_moved)
                visited_node.total_reward += reward

    # ========================================================
    # ELECCIÓN FINAL DE LA ACCIÓN
    # ========================================================
    if not root.children:
        sample_det = model.determinize(info_state)
        available = model.compute_available_actions(sample_det)
        return random.choice(available) if available else None

    # Una acción puede tener varios hijos por producir diferentes observaciones.
    # Para la decisión final sumamos las visitas de todos sus hijos.
    root_actions = {}

    for (action, _), child in root.children.items():
        root_actions[action] = root_actions.get(action, 0) + child.visits

    return max(root_actions.keys(), key=lambda action: root_actions[action])


# ============================================================
# PUNTO DE ENTRADA PÚBLICO
# ============================================================

def choose_ai_move_ismcts(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    ai_player: int,
    iterations: int = 1000,
    exploration_weight: float = math.sqrt(2)
) -> tuple[A, ISMCTSStats]:
    """
    Función envoltorio principal para llamar a ISMCTS y medir tiempos/estadísticas.
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