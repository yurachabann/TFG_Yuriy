import random
from typing import Set, Tuple, List
from generic.imperfect.forward_model import ImperfectForwardModel
from .actions import ShootAction
from .game_state import BattleshipGameState, SHIP_SIZES
from .information_state import BattleshipInformationState


class BattleshipForwardModel(
    ImperfectForwardModel[
        BattleshipGameState, ShootAction, BattleshipInformationState
    ]
):

    def setup_game(self, state: BattleshipGameState) -> None:
        """Coloca los barcos aleatoriamente para ambos jugadores al iniciar el juego."""
        for p in range(1, state.num_players + 1):
            state.ships[p] = self._place_ships_randomly(state.grid_size)
        state.current_player = 1

    def create_initial_state(
        self,
        reference_information_state: BattleshipInformationState
    ) -> BattleshipGameState:
        """
        Crea una partida NUEVA e independiente de Battleship.

        El InformationState recibido se utiliza únicamente para conservar la
        configuración estructural del juego. No se reutilizan barcos, disparos
        ni ninguna otra información privada de la partida actual.
        """
        state = BattleshipGameState(
            grid_size=reference_information_state.grid_size
        )
        self.setup_game(state)
        return state

    def create_information_state(
        self, state: BattleshipGameState, player_id: int
    ) -> BattleshipInformationState:
        """Crea el estado de información observada desde el punto de vista del jugador."""
        enemy_id = 2 if player_id == 1 else 1

        enemy_positions = (
            set().union(*state.ships[enemy_id])
            if state.ships[enemy_id]
            else set()
        )
        my_hits = state.shots[player_id].intersection(enemy_positions)

        sunk_ships_coords = [
            ship.copy()
            for ship in state.ships[enemy_id]
            if ship.issubset(state.shots[player_id])
        ]

        return BattleshipInformationState(
            observer_id=player_id,
            grid_size=state.grid_size,
            my_ships=[s.copy() for s in state.ships[player_id]],
            my_shots=state.shots[player_id].copy(),
            enemy_shots=state.shots[enemy_id].copy(),
            current_player=state.current_player,
            my_hits=my_hits,
            sunk_ships=sunk_ships_coords,
        )

    def determinize(
        self, info_state: BattleshipInformationState
    ) -> BattleshipGameState:
        """Genera un estado hipotético coherente para las simulaciones MCTS/ISMCTS."""
        enemy_id = 2 if info_state.observer_id == 1 else 1
        det_state = BattleshipGameState(
            grid_size=info_state.grid_size,
            current_player=info_state.current_player,
        )

        det_state.ships[info_state.observer_id] = [
            s.copy() for s in info_state.my_ships
        ]
        det_state.shots[info_state.observer_id] = info_state.my_shots.copy()
        det_state.shots[enemy_id] = info_state.enemy_shots.copy()

        # Genera barcos hipotéticos para el enemigo respetando impactos, agua y no-adyacencia
        det_state.ships[enemy_id] = self._generate_valid_hypothetical_ships(
            info_state
        )

        return det_state

    def compute_available_actions(
        self, state: BattleshipGameState
    ) -> list[ShootAction]:
        """Calcula las acciones de disparo disponibles para el turno actual."""
        if state.is_terminal:
            return []

        p = state.current_player
        already_shot = state.shots[p]
        enemy_id = 2 if p == 1 else 1

        # 1. Filtrar los impactos de barcos que AÚN NO se han hundido completamente
        active_hits = set()
        for ship in state.ships[enemy_id]:
            if not ship.issubset(already_shot):  # Barco con partes vivas
                active_hits.update(ship.intersection(already_shot))

        # 2. Si hay tocados activos, restringimos disparos a las casillas contiguas
        if active_hits:
            adjacent_targets = set()
            for r, c in active_hits:
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < state.grid_size and 0 <= nc < state.grid_size:
                        if (nr, nc) not in already_shot:
                            adjacent_targets.add((nr, nc))

            if adjacent_targets:
                return [
                    ShootAction(player=p, row=r, col=c)
                    for (r, c) in adjacent_targets
                ]

        # 3. Devolver cualquier casilla libre si no hay tocados activos
        return [
            ShootAction(player=p, row=r, col=c)
            for r in range(state.grid_size)
            for c in range(state.grid_size)
            if (r, c) not in already_shot
        ]

    def advance(self, state: BattleshipGameState, action: ShootAction) -> None:
        """Aplica la acción de disparo al estado de la partida."""
        p = action.player
        enemy_id = 2 if p == 1 else 1
        target = (action.row, action.col)

        state.shots[p].add(target)

        hit = False
        sunk_ship = False
        sunk_ship_size = 0

        for ship in state.ships[enemy_id]:
            if target in ship:
                hit = True
                if ship.issubset(state.shots[p]):
                    sunk_ship = True
                    sunk_ship_size = len(ship)
                break

        if sunk_ship:
            state.last_action_summary = (
                f"Jugador {p} disparó a ({action.col}, {action.row}) -> "
                f"💥 ¡HUNDIDO! (Barco de tamaño {sunk_ship_size})"
            )
        elif hit:
            state.last_action_summary = (
                f"Jugador {p} disparó a ({action.col}, {action.row}) -> "
                f"🔥 ¡TOCADO!"
            )
        else:
            state.last_action_summary = (
                f"Jugador {p} disparó a ({action.col}, {action.row}) -> "
                f"🟦 AGUA"
            )

        all_enemy_positions = set().union(*state.ships[enemy_id])
        if all_enemy_positions.issubset(state.shots[p]):
            state.is_terminal = True
            state.winner = p
            return

        state.current_player = enemy_id

    def evaluate_terminal(self, state: BattleshipGameState, player_id: int) -> float:
        if state.winner is None:
            return 0.0
        return 1.0 if state.winner == player_id else -1.0

    # -------------------------------------------------------------
    # MÉTODOS AUXILIARES DE GENERACIÓN Y COLOCACIÓN DE BARCOS
    # -------------------------------------------------------------
    def _get_forbidden_zone(self, ship_coords: Set[Tuple[int, int]], grid_size: int) -> Set[Tuple[int, int]]:
        """Calcula el margen de 8 casillas (ortogonal + diagonal) alrededor del barco."""
        forbidden = set()
        for r, c in ship_coords:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < grid_size and 0 <= nc < grid_size:
                        forbidden.add((nr, nc))
        return forbidden

    def _place_ships_randomly(self, grid_size: int) -> list[Set[Tuple[int, int]]]:
        """Genera una distribución válida inicial sin solapamientos ni adyacencias."""
        while True:
            ships = []
            forbidden_zone = set()
            all_placed = True

            for size in SHIP_SIZES:
                placed = False
                for _ in range(100):
                    orientation = random.choice(["H", "V"])
                    r = random.randint(0, grid_size - 1)
                    c = random.randint(0, grid_size - 1)

                    coords = set()
                    for i in range(size):
                        nr = r + (i if orientation == "V" else 0)
                        nc = c + (i if orientation == "H" else 0)
                        if nr < grid_size and nc < grid_size:
                            coords.add((nr, nc))

                    if len(coords) == size and not coords.intersection(forbidden_zone):
                        ships.append(coords)
                        forbidden_zone.update(self._get_forbidden_zone(coords, grid_size))
                        placed = True
                        break

                if not placed:
                    all_placed = False
                    break

            if all_placed:
                return ships

    def _generate_valid_hypothetical_ships(
        self, info: BattleshipInformationState
    ) -> list[Set[Tuple[int, int]]]:
        """
        Genera una flota hipotética para la determinización de ISMCTS garantizando:
        1. Respetar los disparos al agua (no poner barcos ahí).
        2. Mantener exactamente las coordenadas de los barcos ya hundidos.
        3. Cubrir el 100% de los impactos activos ('active_hits') alineados en barcos válidos.
        4. Cumplir la regla de NO adyacencia (8 casillas alrededor de cada barco).
        """
        grid_size = info.grid_size
        my_shots = getattr(info, "my_shots", set())
        my_hits = getattr(info, "my_hits", set())
        sunk_ships = getattr(info, "sunk_ships", [])

        # Agua = disparos míos que no fueron aciertos
        water_shots = my_shots - my_hits

        # Barcos y casillas hundidas
        sunk_cells = set()
        forbidden_sunk = set()
        for ship in sunk_ships:
            sunk_cells.update(ship)
            forbidden_sunk.update(self._get_forbidden_zone(ship, grid_size))

        # Tocados aún activos (barcos no hundidos)
        active_hits = my_hits - sunk_cells

        # Calcular tamaños de barcos que aún quedan por colocar (enemigos vivos)
        remaining_sizes = list(SHIP_SIZES)
        for ship in sunk_ships:
            if len(ship) in remaining_sizes:
                remaining_sizes.remove(len(ship))

        # Las casillas prohibidas base son: agua + zona de exclusión de barcos hundidos
        base_forbidden = water_shots.union(forbidden_sunk)

        for _ in range(500):
            hypothetical_ships = [s.copy() for s in sunk_ships]
            forbidden_zone = base_forbidden.copy()
            uncovered_hits = active_hits.copy()
            
            # Ordenamos los barcos a colocar de mayor a menor para facilitar el encaje
            sizes_to_place = sorted(remaining_sizes, reverse=True)
            all_placed = True

            for size in sizes_to_place:
                placed = False
                
                # A) Si quedan aciertos sin cubrir, forzamos colocar el barco sobre alguno de ellos
                if uncovered_hits:
                    target_hit = random.choice(list(uncovered_hits))
                    for orientation in random.sample(["H", "V"], 2):
                        # Probar desplazamientos para que target_hit quede dentro del barco
                        for offset in random.sample(range(size), size):
                            r0 = target_hit[0] - (offset if orientation == "V" else 0)
                            c0 = target_hit[1] - (offset if orientation == "H" else 0)
                            
                            coords = set()
                            valid = True
                            for i in range(size):
                                nr = r0 + (i if orientation == "V" else 0)
                                nc = c0 + (i if orientation == "H" else 0)
                                if 0 <= nr < grid_size and 0 <= nc < grid_size:
                                    coords.add((nr, nc))
                                else:
                                    valid = False
                                    break
                            
                            # Debe ser válido y no tocar casillas prohibidas ni agua
                            if valid and len(coords) == size and not coords.intersection(forbidden_zone):
                                hypothetical_ships.append(coords)
                                forbidden_zone.update(self._get_forbidden_zone(coords, grid_size))
                                uncovered_hits -= coords
                                placed = True
                                break
                        if placed:
                            break

                # B) Si no hay tocados pendientes para este barco o no encajó arriba, buscar casilla aleatoria
                if not placed and not uncovered_hits:
                    for _ in range(80):
                        orientation = random.choice(["H", "V"])
                        r = random.randint(0, grid_size - 1)
                        c = random.randint(0, grid_size - 1)

                        coords = set()
                        for i in range(size):
                            nr = r + (i if orientation == "V" else 0)
                            nc = c + (i if orientation == "H" else 0)
                            if nr < grid_size and nc < grid_size:
                                coords.add((nr, nc))

                        if len(coords) == size and not coords.intersection(forbidden_zone):
                            hypothetical_ships.append(coords)
                            forbidden_zone.update(self._get_forbidden_zone(coords, grid_size))
                            placed = True
                            break

                if not placed:
                    all_placed = False
                    break

            # Si todos los barcos se colocaron y todos los active_hits quedaron cubiertos
            if all_placed and len(uncovered_hits) == 0:
                return hypothetical_ships

        # En caso extremo, usamos una búsqueda con backtracking para encontrar
        # una flota compatible en lugar de devolver una configuración inválida.
        fallback_ships = self._generate_valid_hypothetical_ships_backtracking(info)
        if fallback_ships is not None:
            return fallback_ships

        raise ValueError(
            "No se pudo generar una flota hipotética compatible con la información observada."
        )

    def _generate_valid_hypothetical_ships_backtracking(
        self, info: BattleshipInformationState
    ) -> list[Set[Tuple[int, int]]] | None:
        """
        Fallback exacto para la determinización.

        Busca mediante backtracking una colocación que:
        - conserve los barcos ya hundidos;
        - respete disparos al agua e impactos conocidos;
        - mantenga los tamaños de barcos restantes;
        - evite solapamientos y cualquier tipo de adyacencia entre barcos.
        """
        grid_size = info.grid_size
        my_shots = getattr(info, "my_shots", set())
        my_hits = getattr(info, "my_hits", set())
        sunk_ships = getattr(info, "sunk_ships", [])

        water_shots = my_shots - my_hits

        sunk_cells = set()
        forbidden_zone = set(water_shots)

        for ship in sunk_ships:
            sunk_cells.update(ship)
            forbidden_zone.update(self._get_forbidden_zone(ship, grid_size))

        active_hits = my_hits - sunk_cells

        remaining_sizes = list(SHIP_SIZES)
        for ship in sunk_ships:
            if len(ship) in remaining_sizes:
                remaining_sizes.remove(len(ship))

        def placements_for_size(
            size: int,
            current_forbidden: Set[Tuple[int, int]],
            required_hit: Tuple[int, int] | None = None
        ) -> list[Set[Tuple[int, int]]]:
            placements = []

            for orientation in ("H", "V"):
                for r in range(grid_size):
                    for c in range(grid_size):
                        coords = set()

                        for i in range(size):
                            nr = r + (i if orientation == "V" else 0)
                            nc = c + (i if orientation == "H" else 0)

                            if nr >= grid_size or nc >= grid_size:
                                coords = set()
                                break

                            coords.add((nr, nc))

                        if len(coords) != size:
                            continue

                        if required_hit is not None and required_hit not in coords:
                            continue

                        if coords.intersection(current_forbidden):
                            continue

                        placements.append(coords)

            return placements

        def backtrack(
            sizes_left: list[int],
            placed_ships: list[Set[Tuple[int, int]]],
            current_forbidden: Set[Tuple[int, int]],
            uncovered_hits: Set[Tuple[int, int]]
        ) -> list[Set[Tuple[int, int]]] | None:
            if not sizes_left:
                if uncovered_hits:
                    return None
                return placed_ships

            # Si todavía hay impactos sin explicar, intentamos cubrir uno de ellos
            # con cualquiera de los tamaños de barco que quedan disponibles.
            if uncovered_hits:
                target_hit = next(iter(uncovered_hits))
                tried_sizes = set()

                for index, size in enumerate(sizes_left):
                    if size in tried_sizes:
                        continue
                    tried_sizes.add(size)

                    candidates = placements_for_size(
                        size,
                        current_forbidden,
                        required_hit=target_hit
                    )

                    for coords in candidates:
                        next_sizes = sizes_left[:index] + sizes_left[index + 1:]
                        next_forbidden = current_forbidden.union(
                            self._get_forbidden_zone(coords, grid_size)
                        )
                        result = backtrack(
                            next_sizes,
                            placed_ships + [coords],
                            next_forbidden,
                            uncovered_hits - coords
                        )

                        if result is not None:
                            return result

                return None

            # Cuando todos los impactos conocidos ya están cubiertos,
            # colocamos los barcos restantes en cualquier posición válida.
            size = sizes_left[0]
            for coords in placements_for_size(size, current_forbidden):
                next_forbidden = current_forbidden.union(
                    self._get_forbidden_zone(coords, grid_size)
                )
                result = backtrack(
                    sizes_left[1:],
                    placed_ships + [coords],
                    next_forbidden,
                    uncovered_hits
                )

                if result is not None:
                    return result

            return None

        initial_ships = [s.copy() for s in sunk_ships]
        return backtrack(
            remaining_sizes,
            initial_ships,
            forbidden_zone,
            active_hits
        )