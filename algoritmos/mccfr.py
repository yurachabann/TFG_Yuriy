from __future__ import annotations
from typing import Optional, Generic, Dict, Any
from dataclasses import dataclass, field
import random
import time

from generic.imperfect.forward_model import ImperfectForwardModel, S, A, I


# ============================================================
# HELPER PARA ESTRUCTURAS DE DATOS INMUTABLES (HASHABLE KEYS)
# ============================================================

def _to_hashable(obj: Any) -> Any:
    """
    Transforma recursivamente estructuras de datos mutables (listas, diccionarios, 
    dataclasses de estados de información) en representaciones inmutables 
    (tuplas y frozensets) para ser utilizadas como claves en la tabla hash de MCCFR.
    
    Esto evita el error 'TypeError: unhashable type' cuando los estados de
    información contienen colecciones mutables.
    """
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return tuple(_to_hashable(x) for x in obj)
    if isinstance(obj, dict):
        return tuple(sorted((k, _to_hashable(v)) for k, v in obj.items()))
    if hasattr(obj, "__dict__"):
        return tuple(sorted((k, _to_hashable(v)) for k, v in obj.__dict__.items()))
    return repr(obj)


# ============================================================
# ESTADÍSTICAS DE ENTRENAMIENTO / BÚSQUEDA
# ============================================================

@dataclass
class MCCFRStats:
    """
    Estructura de datos para almacenar métricas durante la fase de aprendizaje/inferencia:
    - nodes_visited: Número de conjuntos de información (Information Sets) en memoria.
    - iterations_completed: Iteraciones de simulación ejecutadas.
    - elapsed_time: Tiempo total de cómputo transcurrido.
    """
    nodes_visited: int = 0
    iterations_completed: int = 0
    elapsed_time: float = 0.0


# ============================================================
# CONJUNTO DE INFORMACIÓN (INFORMATION SET / NODE)
# ============================================================

@dataclass
class MCCFRNode(Generic[A]):
    """
    Representa un nodo o Information Set en la memoria del agente MCCFR.
    
    Almacena dos acumuladores clave:
    1. regret_sum: R(I, a) -> Arrepentimiento acumulado para cada acción posible.
    2. strategy_sum: Acumulaciones ponderadas de la estrategia para obtener
                     la estrategia promedio que aproxima el Equilibrio de Nash.
    """
    legal_actions: list[A]
    regret_sum: dict[A, float] = field(default_factory=dict)
    strategy_sum: dict[A, float] = field(default_factory=dict)

    def __post_init__(self):
        """Inicializa las tablas de arrepentimiento y estrategia acumulada a cero."""
        for a in self.legal_actions:
            if a not in self.regret_sum:
                self.regret_sum[a] = 0.0
            if a not in self.strategy_sum:
                self.strategy_sum[a] = 0.0

    def get_strategy(self) -> dict[A, float]:
        """
        Calcula la estrategia actual aplicando el algoritmo Regret Matching:
        - Asigna probabilidades proporcionales a los arrepentimientos positivos R+(I, a).
        - Si no existen arrepentimientos positivos, asigna una distribución uniforme.
        """
        regret_sum_pos = {a: max(0.0, self.regret_sum[a]) for a in self.legal_actions}
        total_pos = sum(regret_sum_pos.values())

        strategy = {}
        num_actions = len(self.legal_actions)

        if total_pos > 0:
            for a in self.legal_actions:
                strategy[a] = regret_sum_pos[a] / total_pos
        else:
            for a in self.legal_actions:
                strategy[a] = 1.0 / num_actions

        return strategy

    def get_average_strategy(self) -> dict[A, float]:
        """
        Calcula la estrategia promedio normalizada a partir de strategy_sum.
        Esta distribución representa la estrategia óptima (inexplotable) aprendida.
        """
        total_strategy = sum(self.strategy_sum.values())
        avg_strategy = {}
        num_actions = len(self.legal_actions)

        if total_strategy > 0:
            for a in self.legal_actions:
                avg_strategy[a] = self.strategy_sum[a] / total_strategy
        else:
            for a in self.legal_actions:
                avg_strategy[a] = 1.0 / num_actions

        return avg_strategy


# ============================================================
# AGENTE ENTRENADOR DE MCCFR (EXTERNAL SAMPLING)
# ============================================================

class MCCFRAgent(Generic[S, A, I]):
    """
    Agente que aplica el algoritmo Monte Carlo Counterfactual Regret Minimization (MCCFR)
    utilizando la técnica de muestreo External Sampling.
    """

    def __init__(self, model: ImperfectForwardModel[S, A, I]):
        self.model = model
        # Diccionario que mapea la clave inmutable del InformationSet -> MCCFRNode
        self.nodes: Dict[Any, MCCFRNode[A]] = {}

    def _get_node(self, info_state: I, legal_actions: list[A]) -> MCCFRNode[A]:
        """Recupera el nodo asociado al Information Set o crea uno nuevo si no existe."""
        key = _to_hashable(info_state)
        if key not in self.nodes:
            self.nodes[key] = MCCFRNode(legal_actions=legal_actions)
        return self.nodes[key]

    def external_sampling_cfr(
        self,
        state: S,
        traverser: int,
        stats: Optional[MCCFRStats] = None
    ) -> float:
        """
        Proceso recursivo de exploración External Sampling MCCFR:
        - Turno del explorador (traverser): Evalúa TODAS sus acciones.
        - Turno del oponente o azar: Muestrea UNA ÚNICA acción según su estrategia.
        """
        # 1. Caso base: Estado terminal alcanzado
        if state.is_terminal:
            if state.winner is None:
                return 0.0
            return 1.0 if state.winner == traverser else -1.0

        current_player = getattr(state, "current_player", 0)
        legal_actions = self.model.compute_available_actions(state)

        if not legal_actions:
            return 0.0

        # Obtener la perspectiva observable (Information State) del jugador activo
        info_state = self.model.create_information_state(state, current_player)
        node = self._get_node(info_state, legal_actions)

        if stats is not None:
            stats.nodes_visited = len(self.nodes)

        strategy = node.get_strategy()

        # ====================================================
        # A. JUGADOR EXPLORADOR (Traverser) -> Rama completa
        # ====================================================
        if current_player == traverser:
            action_utilities: dict[A, float] = {}
            node_utility = 0.0

            # Explora todas las decisiones posibles para calcular sus utilidades
            for action in legal_actions:
                next_state = state.clone()
                self.model.advance(next_state, action)

                action_utilities[action] = self.external_sampling_cfr(
                    next_state, traverser, stats
                )
                node_utility += strategy[action] * action_utilities[action]

            # Actualiza la tabla de arrepentimiento acumulado (Regrets)
            for action in legal_actions:
                regret = action_utilities[action] - node_utility
                node.regret_sum[action] += regret

            return node_utility

        # ====================================================
        # B. OPONENTE O EVENTOS DE AZAR -> Muestreo único
        # ====================================================
        else:
            actions = list(strategy.keys())
            probabilities = list(strategy.values())
            sampled_action = random.choices(actions, weights=probabilities, k=1)[0]

            # Acumula la frecuencia de la estrategia del oponente para el promedio
            for a in legal_actions:
                node.strategy_sum[a] += strategy[a]

            next_state = state.clone()
            self.model.advance(next_state, sampled_action)

            return self.external_sampling_cfr(next_state, traverser, stats)

    def train(
        self,
        initial_info_state: I,
        num_players: int = 2,
        iterations: int = 10000,
        stats: Optional[MCCFRStats] = None
    ) -> None:
        """
        Bucle principal de entrenamiento previo (Offline).
        Alterna qué jugador asume el rol de explorador (traverser) en cada iteración.
        """
        for i in range(iterations):
            traverser = i % num_players
            root_state = self.model.determinize(initial_info_state)
            self.external_sampling_cfr(root_state, traverser, stats)

            if stats is not None:
                stats.iterations_completed += 1


# ============================================================
# EVALUACIÓN Y PUNTO DE ENTRADA DINÁMICO
# ============================================================

def choose_ai_move_mccfr(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    agent: MCCFRAgent[S, A, I],
    deterministic: bool = False
) -> tuple[Optional[A], MCCFRStats]:
    """
    Función de inferencia en tiempo de juego (Online):
    Consulta la estrategia aprendida en el agente MCCFR y devuelve la tupla (acción, stats)
    compatible con la llamada en Match.py.
    """
    stats = MCCFRStats()
    stats.nodes_visited = len(agent.nodes)

    sample_det = model.determinize(info_state)
    legal_actions = model.compute_available_actions(sample_det)

    if not legal_actions:
        return None, stats

    key = _to_hashable(info_state)
    # Si el estado no fue explorado durante el entrenamiento, se elige una jugada aleatoria
    if key not in agent.nodes:
        return random.choice(legal_actions), stats

    node = agent.nodes[key]
    avg_strategy = node.get_average_strategy()

    if deterministic:
        # Modo determinista: Selecciona la acción con mayor probabilidad (argmax)
        best_action = max(legal_actions, key=lambda a: avg_strategy.get(a, 0.0))
        return best_action, stats
    else:
        # Modo estocástico: Muestrea según la distribución de probabilidad (Equilibrio de Nash)
        actions = legal_actions
        weights = [avg_strategy.get(a, 0.0) for a in actions]
        chosen_action = random.choices(actions, weights=weights, k=1)[0]
        return chosen_action, stats


# Caché global basada en la CLASE del modelo (evita reentrenar tras clones o avances de estado)
_MCCFR_CACHE: dict[type, MCCFRAgent] = {}

def choose_ai_move_mccfr_dynamic(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    *args,
    **kwargs
) -> tuple[Optional[A], MCCFRStats]:
    """
    Wrapper dinámico compatible con entornos de selección de juego en runtime:
    Si la clase del juego no tiene un agente precalculado en caché, ejecuta la fase 
    de entrenamiento previo automáticamente antes del primer movimiento.
    Devuelve siempre una tupla (action, stats) para desempaquetar limpiamente en Match.py.
    """
    global _MCCFR_CACHE
    
    # Usamos la clase del modelo como clave (ej: LoveLetterForwardModel) para independizarnos del id de memoria
    model_key = type(model)

    # Extrae el número de iteraciones si fue proporcionado por kwargs o args posicionales
    iterations = 5000
    if "iterations" in kwargs:
        iterations = kwargs["iterations"]
    elif len(args) > 0 and isinstance(args[0], int):
        iterations = args[0]

    deterministic = kwargs.get("deterministic", False)

    start_time = time.perf_counter()

    # Entrenamiento bajo demanda (Lazy Initialisation por Tipo de Juego)
    if model_key not in _MCCFR_CACHE:
        print(f"\n[MCCFR] Entrenando agente para {model_key.__name__} ({iterations} iteraciones)...")
        agent = MCCFRAgent(model=model)
        agent.train(initial_info_state=info_state, iterations=iterations)
        _MCCFR_CACHE[model_key] = agent
        print("[MCCFR] ¡Entrenamiento completado con éxito!\n")

    agent = _MCCFR_CACHE[model_key]

    # Obtenemos la jugada y sus estadísticas
    action, stats = choose_ai_move_mccfr(
        info_state=info_state,
        model=model,
        agent=agent,
        deterministic=deterministic
    )

    stats.iterations_completed = iterations
    stats.elapsed_time = time.perf_counter() - start_time

    return action, stats