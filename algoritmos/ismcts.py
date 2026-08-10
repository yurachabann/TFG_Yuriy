from __future__ import annotations
from typing import Optional, Generic
from dataclasses import dataclass, field
import math
import random
import time

from generic.imperfect.forward_model import ImperfectForwardModel, S, A, I


# ============================================================
# ESTADÍSTICAS DE BÚSQUEDA
# ============================================================

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
# NODO DEL ÁRBOL PARA ISMCTS (Versión Canónica)
# ============================================================

@dataclass
class ISMCTSNode(Generic[A]):
    """
    Representa un conjunto de información o punto de decisión en el árbol ISMCTS.
    
    A diferencia de MCTS estándar:
    1. No guarda un estado completo determinista, sino información abstracta del árbol.
    2. Registra la disponibilidad ('availability') de cada acción vista desde este nodo.
    """
    parent: Optional[ISMCTSNode[A]] = None
    action_from_parent: Optional[A] = None
    
    # Hijos ya creados/expandidos a partir de cada acción
    children: dict[A, ISMCTSNode[A]] = field(default_factory=dict)
    
    # Visitas reales que ha recibido este nodo
    visits: int = 0
    
    # CORRECCIÓN CANÓNICA:
    # La disponibilidad mide cuántas veces la acción 'a' estuvo disponible (fue legal)
    # mientras estábamos en este nodo padre. Pertenece a la arista (Padre -> Acción).
    availability: dict[A, int] = field(default_factory=dict)
    
    # Recompensa acumulada desde la perspectiva del jugador de la IA
    total_reward: float = 0.0

    def best_child_by_uct(self, legal_actions: list[A], exploration_weight: float) -> tuple[A, ISMCTSNode[A]]:
        """
        Selecciona la mejor acción legal usando la fórmula UCT modificada para ISMCTS.
        
        Fórmula ISMCTS UCT:
            UCT = (Recompensa_hijo / Visitas_hijo) + C * sqrt( ln(Disponibilidad_acción) / Visitas_hijo )
        
        Importante: Usa math.log(availability[action]) en lugar de math.log(parent.visits)
        porque en juegos de información imperfecta una acción no siempre está disponible.
        """
        best_score = float("-inf")
        best_action = None
        best_child = None

        for action in legal_actions:
            child = self.children.get(action)
            
            # Si la acción nunca ha creado un nodo hijo o no se ha visitado,
            # le asignamos prioridad infinita para forzar la exploración inicial.
            if child is None or child.visits == 0:
                uct_score = float("inf")
            else:
                # 1. Componente de Explotación: Calidad promedio estimada de la acción
                exploitation = child.total_reward / child.visits
                
                # 2. Componente de Exploración (ISMCTS):
                # Obtenemos la disponibilidad de la acción desde este nodo (mínimo 1 para evitar log(0))
                action_avail = max(1, self.availability.get(action, 1))
                
                exploration = exploration_weight * math.sqrt(
                    math.log(action_avail) / child.visits
                )
                
                uct_score = exploitation + exploration

            if uct_score > best_score:
                best_score = uct_score
                best_action = action
                best_child = child

        return best_action, best_child


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
    ai_player: int,
    stats: Optional[ISMCTSStats] = None,
    start_depth: int = 0
) -> float:
    """
    Fase de Simulación (Play-out / Rollout):
    Juega la partida con acciones completamente aleatorias desde la determinización actual
    hasta alcanzar un estado final terminal.
    """
    depth = start_depth
    rollout_state = state.clone()

    while not rollout_state.is_terminal:
        actions = model.compute_available_actions(rollout_state)
        if not actions:
            return 0.0

        # Elección aleatoria pura (sin heurísticas)
        action = random.choice(actions)
        model.advance(rollout_state, action)

        depth += 1
        if stats is not None and depth > stats.max_depth:
            stats.max_depth = depth

    return terminal_reward(rollout_state, ai_player)


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
    """
    root = ISMCTSNode[A]()

    if stats is not None:
        stats.nodes_visited += 1

    for _ in range(iterations):
        # ----------------------------------------------------
        # 0. DETERMINIZACIÓN
        # ----------------------------------------------------
        # Convertimos la información incompleta actual en un estado determinista completo.
        det_state = model.determinize(info_state)
        node = root
        visited_nodes_in_sim = [node]  # Guardamos el camino de nodos recorridos en este bucle
        depth = 0

        # ----------------------------------------------------
        # 1. SELECCIÓN
        # ----------------------------------------------------
        # Descendemos por el árbol mientras el estado no sea final.
        while not det_state.is_terminal:
            legal_actions = model.compute_available_actions(det_state)
            if not legal_actions:
                break

            # CORRECCIÓN CANÓNICA:
            # Incrementamos la disponibilidad de cada acción legal EN EL NODO PADRE.
            for a in legal_actions:
                node.availability[a] = node.availability.get(a, 0) + 1

            # Filtramos qué acciones legales aún no han creado un nodo hijo en el árbol
            untried_legal_actions = [a for a in legal_actions if a not in node.children]

            if untried_legal_actions:
                # Hay acciones válidas sin probar -> Salimos del bucle para pasar a Expansión
                break

            # Si todas las acciones legales de este turno ya fueron probadas alguna vez,
            # usamos la fórmula UCT para elegir la mejor rama
            action, child_node = node.best_child_by_uct(legal_actions, exploration_weight)
            
            # Avanzamos el estado simulado y descendemos en el árbol
            model.advance(det_state, action)
            node = child_node
            visited_nodes_in_sim.append(node)
            depth += 1

            if stats is not None and depth > stats.max_depth:
                stats.max_depth = depth

        # ----------------------------------------------------
        # 2. EXPANSIÓN
        # ----------------------------------------------------
        # Si no hemos llegado al final y hay acciones sin probar, expandimos una de ellas.
        if not det_state.is_terminal:
            legal_actions = model.compute_available_actions(det_state)
            untried_legal_actions = [a for a in legal_actions if a not in node.children]

            if untried_legal_actions:
                # Elegimos al azar una de las acciones no exploradas
                action = random.choice(untried_legal_actions)
                
                # Creamos el nuevo nodo hijo
                new_child = ISMCTSNode(parent=node, action_from_parent=action)
                node.children[action] = new_child
                
                # Nos movemos al nuevo nodo hijo
                node = new_child
                visited_nodes_in_sim.append(node)

                # Aplicamos la acción sobre el estado determinizado
                model.advance(det_state, action)
                depth += 1

                if stats is not None:
                    stats.nodes_visited += 1
                    if depth > stats.max_depth:
                        stats.max_depth = depth

        # ----------------------------------------------------
        # 3. SIMULACIÓN (ROLLOUT)
        # ----------------------------------------------------
        # Desde el punto en el que nos quedamos, simulamos acciones aleatorias hasta el final.
        if det_state.is_terminal:
            reward = terminal_reward(det_state, ai_player)
        else:
            reward = rollout(det_state, model, ai_player, stats, start_depth=depth)

        # ----------------------------------------------------
        # 4. RETROPROPAGACIÓN (BACKPROPAGATION)
        # ----------------------------------------------------
        # Actualizamos ÚNICAMENTE los nodos que formaron parte del camino de esta simulación.
        for visited_node in visited_nodes_in_sim:
            visited_node.visits += 1
            visited_node.total_reward += reward

    # ========================================================
    # ELECCIÓN FINAL DE LA ACCIÓN
    # ========================================================
    if not root.children:
        # En caso extremo de no haber podido expandir nada, devuelve una acción aleatoria legal
        sample_det = model.determinize(info_state)
        available = model.compute_available_actions(sample_det)
        return random.choice(available) if available else None

    # En la raíz, la decisión más robusta según MCTS/ISMCTS es seleccionar
    # el hijo que ha sido visitado más veces.
    best_action = max(root.children.keys(), key=lambda a: root.children[a].visits)
    return best_action


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