from __future__ import annotations
from typing import Optional, Generic, Dict, Any
from dataclasses import dataclass, field
import random
import time
import pickle
import hashlib
import re
from pathlib import Path

from generic.imperfect.forward_model import ImperfectForwardModel, S, A, I


# ============================================================
# HELPER PARA ESTRUCTURAS DE DATOS INMUTABLES (HASHABLE KEYS)
# ============================================================

def _to_hashable(obj: Any) -> Any:
    """
    Transforma recursivamente estructuras de datos mutables (listas, diccionarios, 
    sets y dataclasses de estados de información) en representaciones inmutables 
    basadas en tuplas para ser utilizadas como claves en la tabla hash de MCCFR.
    
    Esto evita el error 'TypeError: unhashable type' cuando los estados de
    información contienen colecciones mutables.
    """
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    if isinstance(obj, (list, tuple)):
        return tuple(_to_hashable(x) for x in obj)
    if isinstance(obj, set):
        return tuple(
            sorted(
                (_to_hashable(x) for x in obj),
                key=repr
            )
        )
    if isinstance(obj, dict):
        return tuple(sorted((k, _to_hashable(v)) for k, v in obj.items()))
    if hasattr(obj, "__dict__"):
        return tuple(sorted((k, _to_hashable(v)) for k, v in obj.__dict__.items()))
    return repr(obj)


def _get_initial_state_spec(
    model: ImperfectForwardModel[S, A, I],
    reference_info_state: I
) -> tuple[type, dict]:
    """
    Obtiene una sola vez el tipo de GameState y sus parámetros estructurales.

    Se usa una determinización únicamente para descubrir el tipo/configuración del
    estado. La determinización NO se utiliza como raíz del entrenamiento MCCFR.
    """
    sample_state = model.determinize(reference_info_state)
    state_type = type(sample_state)
    constructor_kwargs = {}

    # Conservamos únicamente parámetros que describen la configuración del juego,
    # nunca manos, mazos, barcos, puntuaciones u otra información de la partida actual.
    for attribute in ("num_players", "grid_size"):
        if hasattr(sample_state, attribute):
            constructor_kwargs[attribute] = getattr(sample_state, attribute)

    return state_type, constructor_kwargs


def _create_fresh_initial_state(
    model: ImperfectForwardModel[S, A, I],
    reference_info_state: I
) -> S:
    """
    Crea un estado NUEVO desde el inicio real del juego para entrenar MCCFR.

    La versión anterior hacía model.determinize(reference_info_state) en cada
    iteración y entrenaba desde el estado de información del turno actual. Eso
    condicionaba el entrenamiento a la información privada observada en ese turno.

    Para External Sampling MCCFR queremos empezar cada traversal desde una partida
    nueva mediante create_initial_state().

    El ForwardModel es el responsable de crear un comienzo independiente y de
    ejecutar de nuevo los eventos aleatorios iniciales del juego mediante setup_game().
    """
    return model.create_initial_state(reference_info_state)


def _get_cache_key(
    model: ImperfectForwardModel[S, A, I],
    reference_info_state: I
) -> tuple:
    """
    Genera una clave de caché que diferencia no solo la clase del modelo, sino
    también configuraciones como número de jugadores o tamaño de tablero.
    """
    _, constructor_kwargs = _get_initial_state_spec(model, reference_info_state)
    configuration = tuple(sorted(constructor_kwargs.items()))
    return type(model), configuration


# ============================================================
# ESTADÍSTICAS DE ENTRENAMIENTO / BÚSQUEDA
# ============================================================

@dataclass
class MCCFRStats:
    """
    Estructura de datos para almacenar métricas durante la fase de aprendizaje/inferencia:
    - nodes_visited: Número total de estados recorridos por los traversals de entrenamiento.
    - cutoffs: Se mantiene a 0 por compatibilidad con StatsManager; MCCFR no realiza poda.
    - max_depth: Profundidad máxima alcanzada por un traversal durante el entrenamiento.
    - elapsed_time: Tiempo total de cómputo transcurrido en la llamada.
    - iterations_completed: Iteraciones de entrenamiento completadas en esta llamada.
    - information_sets: Número de Information Sets distintos almacenados por el agente.
    - terminal_states: Número de estados terminales alcanzados durante el entrenamiento.
    - actions_evaluated: Número de transiciones/acciones realmente evaluadas.
    - regret_updates: Número de valores de regret_sum actualizados.
    - strategy_updates: Número de valores de strategy_sum actualizados.
    - sampled_actions: Número de acciones muestreadas en ramas del oponente.
    - training_elapsed_time: Tiempo dedicado exclusivamente al entrenamiento MCCFR.
    - cache_loads: Número de cargas realizadas desde la caché persistente.
    - cache_load_time: Tiempo total dedicado a cargar la caché persistente.
    - unknown_information_sets: Número de decisiones reales en las que MCCFR tuvo que
      usar el fallback aleatorio porque no conocía el Information Set.
    """
    nodes_visited: int = 0
    cutoffs: int = 0
    max_depth: int = 0
    elapsed_time: float = 0.0
    iterations_completed: int = 0
    information_sets: int = 0
    terminal_states: int = 0
    actions_evaluated: int = 0
    regret_updates: int = 0
    strategy_updates: int = 0
    sampled_actions: int = 0
    training_elapsed_time: float = 0.0
    cache_loads: int = 0
    cache_load_time: float = 0.0
    unknown_information_sets: int = 0


def _restore_cached_training_stats(cached_stats) -> MCCFRStats:
    """
    Reconstruye las estadísticas de entrenamiento guardadas junto a la caché.

    También mantiene compatibilidad con cachés creadas antes de separar
    training_elapsed_time de elapsed_time. En esas cachés antiguas,
    elapsed_time representaba el tiempo de entrenamiento.
    """
    restored_stats = MCCFRStats()

    if cached_stats is None:
        return restored_stats

    if isinstance(cached_stats, dict):
        cached_values = cached_stats
    elif hasattr(cached_stats, "__dict__"):
        cached_values = vars(cached_stats)
    else:
        return restored_stats

    for key in vars(restored_stats):
        if key in cached_values:
            value = cached_values[key]

            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue

            setattr(restored_stats, key, value)

    # Compatibilidad con cachés antiguas:
    # antes elapsed_time guardaba directamente el tiempo de entrenamiento.
    if (
        restored_stats.training_elapsed_time <= 0.0
        and restored_stats.iterations_completed > 0
        and isinstance(cached_values.get("elapsed_time"), (int, float))
    ):
        restored_stats.training_elapsed_time = cached_values["elapsed_time"]

    # elapsed_time se reserva para el tiempo de las decisiones reales.
    # Los contadores de caché y los fallbacks pertenecen a la ejecución actual,
    # por lo que nunca se restauran como parte del entrenamiento histórico.
    restored_stats.elapsed_time = 0.0
    restored_stats.cache_loads = 0
    restored_stats.cache_load_time = 0.0
    restored_stats.unknown_information_sets = 0

    return restored_stats


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
        stats: Optional[MCCFRStats] = None,
        depth: int = 0
    ) -> float:
        """
        Proceso recursivo de exploración External Sampling MCCFR:
        - Turno del explorador (traverser): Evalúa TODAS sus acciones.
        - Turno del oponente o azar: Muestrea UNA ÚNICA acción según su estrategia.
        """
        if stats is not None:
            stats.nodes_visited += 1
            stats.max_depth = max(stats.max_depth, depth)

        # 1. Caso base: Estado terminal alcanzado
        if state.is_terminal:
            if stats is not None:
                stats.terminal_states += 1
            return self.model.evaluate_terminal(state, traverser)

        current_player = self.model.get_current_player(state)
        legal_actions = self.model.compute_available_actions(state)

        if not legal_actions:
            return 0.0

        # Obtener la perspectiva observable (Information State) del jugador activo
        info_state = self.model.create_information_state(state, current_player)
        node = self._get_node(info_state, legal_actions)

        if stats is not None:
            stats.information_sets = len(self.nodes)

        strategy = node.get_strategy()

        # ====================================================
        # A. JUGADOR EXPLORADOR (Traverser) -> Rama completa
        # ====================================================
        if current_player == traverser:
            action_utilities: dict[A, float] = {}
            node_utility = 0.0

            # Explora todas las decisiones posibles para calcular sus utilidades
            for action in legal_actions:
                if stats is not None:
                    stats.actions_evaluated += 1

                next_state = state.clone()
                self.model.advance(next_state, action)

                action_utilities[action] = self.external_sampling_cfr(
                    next_state,
                    traverser,
                    stats,
                    depth + 1
                )
                node_utility += strategy[action] * action_utilities[action]

            # Actualiza la tabla de arrepentimiento acumulado (Regrets)
            for action in legal_actions:
                regret = action_utilities[action] - node_utility
                node.regret_sum[action] += regret

                if stats is not None:
                    stats.regret_updates += 1

            return node_utility

        # ====================================================
        # B. OPONENTE O EVENTOS DE AZAR -> Muestreo único
        # ====================================================
        else:
            actions = list(strategy.keys())
            probabilities = list(strategy.values())
            sampled_action = random.choices(actions, weights=probabilities, k=1)[0]

            if stats is not None:
                stats.sampled_actions += 1
                stats.actions_evaluated += 1

            # Acumula la frecuencia de la estrategia del oponente para el promedio
            num_players = getattr(state, "num_players", 2)
            average_player = (traverser % num_players) + 1
            if current_player == average_player:
                for a in legal_actions:
                    node.strategy_sum[a] += strategy[a]

                    if stats is not None:
                        stats.strategy_updates += 1

            next_state = state.clone()
            self.model.advance(next_state, sampled_action)

            return self.external_sampling_cfr(
                next_state,
                traverser,
                stats,
                depth + 1
            )

    def train(
        self,
        initial_info_state: I,
        num_players: int = 2,
        iterations: int = 10000,
        stats: Optional[MCCFRStats] = None
    ) -> None:
        """
        Bucle principal de entrenamiento previo (Offline).

        CORRECCIÓN CANÓNICA:
        - Cada iteración utiliza un único jugador como traverser.
        - El traverser se alterna entre los jugadores durante el entrenamiento.
        - Cada traversal comienza desde un estado inicial NUEVO del juego.
        - No se entrena condicionado al InformationState privado del turno actual.

        initial_info_state se mantiene en la firma únicamente para conservar la
        configuración estructural del juego sin cambiar la interfaz pública del framework.
        """
        for i in range(iterations):
            # Se crea una partida completamente nueva en CADA iteración.
            # En Love Letter esto vuelve a barajar, retirar una carta y repartir desde cero.
            root_state = _create_fresh_initial_state(
                self.model,
                initial_info_state
            )

            state_num_players = getattr(root_state, "num_players", num_players)
            traverser = (i % state_num_players) + 1

            self.external_sampling_cfr(root_state, traverser, stats)

            if stats is not None:
                stats.iterations_completed += 1
                stats.information_sets = len(self.nodes)


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
    stats.information_sets = len(agent.nodes)

    sample_det = model.determinize(info_state)
    legal_actions = model.compute_available_actions(sample_det)

    if not legal_actions:
        return None, stats

    key = _to_hashable(info_state)
    # Si el InformationSet no fue explorado durante el entrenamiento, se utiliza
    # una acción aleatoria como fallback. Esto puede ocurrir en estados muy raros.
    if key not in agent.nodes:
        stats.unknown_information_sets += 1
        return random.choice(legal_actions), stats

    node = agent.nodes[key]
    avg_strategy = node.get_average_strategy()

   # print("\n[MCCFR] Estrategia promedio aprendida:")
    #for action in legal_actions:
     #   probability = avg_strategy.get(action, 0.0)
      #  print(f"  {action} -> {probability:.2%}")

    if deterministic:
        # Modo determinista: Selecciona la acción con mayor probabilidad (argmax)
        best_action = max(legal_actions, key=lambda a: avg_strategy.get(a, 0.0))
        return best_action, stats
    else:
        # Modo estocástico: Muestrea según la distribución de probabilidad (Equilibrio de Nash)
        actions = legal_actions
        weights = [avg_strategy.get(a, 0.0) for a in actions]

        # Defensa adicional: random.choices no acepta una suma de pesos igual a 0.
        # Si el InformationSet existe pero ninguna acción legal tiene peso aprendido,
        # usamos una distribución uniforme.
        if sum(weights) <= 0.0:
            return random.choice(actions), stats

        chosen_action = random.choices(actions, weights=weights, k=1)[0]
        return chosen_action, stats


# ============================================================
# CACHÉ PERSISTENTE DE ENTRENAMIENTO
# ============================================================

# La caché en memoria (_MCCFR_CACHE) evita reentrenar durante una misma ejecución.
# Además, esta carpeta guarda los nodos entrenados en disco para poder recuperarlos
# aunque se cierre Python o se reinicie el proyecto.
#
# Se crea junto a este archivo:
#     <carpeta_de_mccfr>/mccfr_cache/
_MCCFR_CACHE_DIR = Path(__file__).resolve().parent / "mccfr_cache"

# Versión del formato persistente. Si en el futuro cambia la estructura almacenada,
# basta con incrementar este valor para ignorar automáticamente cachés antiguas.
_MCCFR_CACHE_VERSION = 1


def _get_game_cache_name(model_type: type) -> str:
    """
    Obtiene un nombre corto y legible a partir de la clase del ForwardModel.

    Ejemplos:
    - LoveLetterForwardModel -> love_letter
    - BattleshipForwardModel -> battleship
    """
    name = model_type.__name__

    if name.endswith("ForwardModel"):
        name = name[:-len("ForwardModel")]

    name = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    name = re.sub(r"[^a-z0-9_-]+", "_", name).strip("_")

    return name or "game"


def _get_persistent_cache_path(model_key: tuple) -> Path:
    """
    Devuelve una ruta estable, única y legible para una configuración concreta de MCCFR.

    El nombre incluye:
    - juego / ForwardModel;
    - configuración estructural, como número de jugadores o tamaño del tablero;
    - número de iteraciones solicitado.

    Ejemplos:
        mccfr_love_letter_2_players_5000_iterations.pkl
        mccfr_battleship_2_players_grid_10_5000_iterations.pkl
    """
    model_type = model_key[0]
    configuration = model_key[1] if len(model_key) > 1 else ()
    iterations = model_key[2] if len(model_key) > 2 else None

    parts = [
        "mccfr",
        _get_game_cache_name(model_type)
    ]

    for key, value in configuration:
        if key == "num_players":
            parts.append(f"{value}_players")
        elif key == "grid_size":
            parts.append(f"grid_{value}")
        else:
            safe_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(key)).strip("_")
            safe_value = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value)).strip("_")
            parts.append(f"{safe_key}_{safe_value}")

    if iterations is not None:
        parts.append(f"{iterations}_iterations")

    return _MCCFR_CACHE_DIR / ("_".join(parts) + ".pkl")


def _get_legacy_persistent_cache_path(model_key: tuple) -> Path:
    """
    Devuelve la ruta que utilizaban las versiones anteriores basadas en SHA-256.

    Se mantiene únicamente para poder recuperar una caché antigua y migrarla
    automáticamente al nuevo nombre legible sin obligar a reentrenar.
    """
    model_type = model_key[0]
    remaining_key = model_key[1:]

    cache_identity = (
        model_type.__module__,
        model_type.__qualname__,
        remaining_key,
    )

    cache_hash = hashlib.sha256(
        repr(cache_identity).encode("utf-8")
    ).hexdigest()

    return _MCCFR_CACHE_DIR / f"{cache_hash}.pkl"


def _save_agent_to_disk(
    model_key: tuple,
    agent: MCCFRAgent[S, A, I],
    training_stats: Optional[MCCFRStats] = None
) -> None:
    """
    Guarda de forma persistente la memoria aprendida por MCCFR.

    Solo se persiste agent.nodes, no el ForwardModel completo. De esta manera,
    al cargar la caché se reutiliza el modelo actual de la ejecución y únicamente
    se restauran los Information Sets con sus regret_sum y strategy_sum.

    La escritura es atómica:
    primero se crea un archivo temporal y después se sustituye el archivo final.
    Así reducimos el riesgo de dejar una caché corrupta si el proceso se interrumpe
    justo mientras se estaba guardando.
    """
    cache_path = _get_persistent_cache_path(model_key)
    temp_path = cache_path.with_suffix(".tmp")

    cache_data = {
        "version": _MCCFR_CACHE_VERSION,
        "nodes": agent.nodes,
        "training_stats": training_stats,
    }

    try:
        _MCCFR_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        with temp_path.open("wb") as cache_file:
            pickle.dump(cache_data, cache_file, protocol=pickle.HIGHEST_PROTOCOL)

        temp_path.replace(cache_path)
        print(f"[MCCFR] Caché persistente guardada en: {cache_path}")

    except (OSError, pickle.PickleError, AttributeError, TypeError) as exc:
        # Un fallo al guardar la caché no debe impedir que MCCFR siga funcionando
        # con el agente que ya está correctamente entrenado en memoria.
        print(f"[MCCFR] No se pudo guardar la caché persistente: {exc}")

        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass


def _load_agent_from_disk(
    model_key: tuple,
    model: ImperfectForwardModel[S, A, I]
) -> tuple[Optional[MCCFRAgent[S, A, I]], Optional[MCCFRStats]]:
    """
    Intenta reconstruir un agente MCCFR desde la caché persistente.

    Si no existe archivo, está corrupto o pertenece a otra versión del formato,
    devuelve (None, None). El wrapper dinámico continuará entonces con el entrenamiento
    normal y sobrescribirá la caché con una copia válida.

    Si la caché es válida, devuelve tanto el agente como las estadísticas originales
    del entrenamiento que se guardaron junto a sus Information Sets.
    """
    cache_path = _get_persistent_cache_path(model_key)
    legacy_cache_path = _get_legacy_persistent_cache_path(model_key)

    if not cache_path.exists():
        if legacy_cache_path.exists():
            cache_path = legacy_cache_path
        else:
            return None, None

    try:
        with cache_path.open("rb") as cache_file:
            cache_data = pickle.load(cache_file)

        if not isinstance(cache_data, dict):
            raise ValueError("Formato de caché inválido.")

        if cache_data.get("version") != _MCCFR_CACHE_VERSION:
            print(
                "[MCCFR] La caché persistente pertenece a otra versión. "
                "Se volverá a entrenar."
            )
            return None, None

        nodes = cache_data.get("nodes")
        if not isinstance(nodes, dict):
            raise ValueError("La caché no contiene una tabla de nodos válida.")

        cached_training_stats = _restore_cached_training_stats(
            cache_data.get("training_stats")
        )

        agent = MCCFRAgent(model=model)
        agent.nodes = nodes

        print(
            f"\n[MCCFR] Caché persistente cargada para {type(model).__name__} "
            f"({len(agent.nodes)} Information Sets)."
        )

        # Si se ha cargado una caché antigua con nombre SHA-256, la migramos al
        # nombre legible actual para que las siguientes ejecuciones la encuentren
        # directamente sin perder el entrenamiento existente.
        readable_cache_path = _get_persistent_cache_path(model_key)
        if cache_path != readable_cache_path:
            try:
                readable_cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.replace(readable_cache_path)
                print(
                    f"[MCCFR] Caché migrada al nuevo nombre: "
                    f"{readable_cache_path.name}"
                )
            except OSError as exc:
                print(
                    f"[MCCFR] No se pudo renombrar la caché antigua: {exc}"
                )

        return agent, cached_training_stats

    except (OSError, EOFError, pickle.PickleError, AttributeError, ImportError,
            ModuleNotFoundError, TypeError, ValueError) as exc:
        print(
            f"[MCCFR] No se pudo cargar la caché persistente ({exc}). "
            "Se volverá a entrenar."
        )
        return None, None


# Caché global en memoria por tipo de modelo + configuración estructural del juego.
# Así no se reutiliza, por ejemplo, un agente entrenado para otro número de jugadores
# o para un tablero de Battleship de tamaño diferente.
_MCCFR_CACHE: dict[tuple, MCCFRAgent] = {}

def choose_ai_move_mccfr(
    info_state: I,
    model: ImperfectForwardModel[S, A, I],
    *args,
    **kwargs
) -> tuple[Optional[A], MCCFRStats]:
    """
    Wrapper dinámico compatible con entornos de selección de juego en runtime:
    Si la configuración del juego no tiene un agente precalculado en caché, ejecuta
    una fase de entrenamiento External Sampling MCCFR desde estados iniciales nuevos
    antes del primer movimiento.

    Una vez completado el entrenamiento inicial no se vuelve a entrenar durante la
    partida. Si aparece un InformationSet no visitado, la inferencia utiliza el
    fallback definido en choose_ai_move_mccfr().

    Devuelve siempre una tupla (action, stats) para desempaquetar limpiamente en Match.py.
    """
    global _MCCFR_CACHE

    # Extrae el número de iteraciones si fue proporcionado por kwargs o args posicionales
    iterations = 5000
    if "iterations" in kwargs:
        iterations = kwargs["iterations"]
    elif len(args) > 0 and isinstance(args[0], int):
        iterations = args[0]

    # La clave incluye clase del modelo, configuración estructural del juego y
    # presupuesto de entrenamiento. Así no se reutiliza un agente de 1000
    # iteraciones cuando se solicita, por ejemplo, uno de 5000.
    model_key = _get_cache_key(model, info_state) + (iterations,)

    deterministic = kwargs.get("deterministic", False)

    start_time = time.perf_counter()
    training_stats = MCCFRStats()

    # Inicialización bajo demanda:
    # 1. Reutiliza la caché RAM si ya está cargada en esta ejecución.
    # 2. Si no, intenta cargar la memoria persistente desde disco.
    # 3. Solo si tampoco existe en disco, entrena y guarda el resultado.
    if model_key not in _MCCFR_CACHE:
        cache_load_start = time.perf_counter()
        agent, cached_training_stats = _load_agent_from_disk(model_key, model)
        cache_load_elapsed = time.perf_counter() - cache_load_start

        if agent is not None:
            training_stats = cached_training_stats or MCCFRStats()
            training_stats.cache_loads = 1
            training_stats.cache_load_time = cache_load_elapsed

        if agent is None:
            print(
                f"\n[MCCFR] Entrenando agente para {type(model).__name__} "
                f"({iterations} iteraciones)..."
            )
            agent = MCCFRAgent(model=model)

            training_start = time.perf_counter()

            agent.train(
                initial_info_state=info_state,
                iterations=iterations,
                stats=training_stats
            )

            training_stats.training_elapsed_time = time.perf_counter() - training_start
            training_stats.information_sets = len(agent.nodes)

            # Guardamos inmediatamente el entrenamiento completado para que sobreviva
            # al cierre del programa y esté disponible en la siguiente ejecución.
            _save_agent_to_disk(
                model_key,
                agent,
                training_stats=training_stats
            )

            print("[MCCFR] ¡Entrenamiento completado con éxito!\n")

        _MCCFR_CACHE[model_key] = agent

    agent = _MCCFR_CACHE[model_key]

    # No se reentrena durante la partida.
    # Si el InformationSet actual no fue visitado durante el entrenamiento global,
    # choose_ai_move_mccfr() utilizará una acción aleatoria como fallback.
    # De esta manera el presupuesto indicado (por ejemplo, 5000 iteraciones)
    # permanece fijo durante todo el experimento.

    # Obtenemos la jugada y sus estadísticas
    action, inference_stats = choose_ai_move_mccfr(
        info_state=info_state,
        model=model,
        agent=agent,
        deterministic=deterministic
    )

    # Si en esta llamada se realizó entrenamiento, devolvemos sus métricas reales.
    # Si se reutilizó la caché, las métricas de entrenamiento permanecen a cero
    # porque no se ha vuelto a entrenar. information_sets sí refleja el tamaño
    # actual de la estrategia aprendida.
    if (
        training_stats.iterations_completed > 0
        or training_stats.cache_loads > 0
    ):
        stats = training_stats
    else:
        stats = inference_stats

    stats.information_sets = len(agent.nodes)

    # elapsed_time mantiene el mismo significado general que en los demás
    # algoritmos: tiempo total consumido por esta llamada pública.
    stats.elapsed_time = time.perf_counter() - start_time

    return action, stats