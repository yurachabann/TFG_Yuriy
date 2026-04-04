from dataclasses import dataclass


@dataclass
class AggregatedStats:
    games: int = 0

    p1_wins: int = 0
    p2_wins: int = 0
    draws: int = 0

    total_nodes_visited_p1: int = 0
    total_nodes_visited_p2: int = 0

    total_cutoffs_p1: int = 0
    total_cutoffs_p2: int = 0

    total_elapsed_time_p1: float = 0.0
    total_elapsed_time_p2: float = 0.0

    max_depth_reached_p1: int = 0
    max_depth_reached_p2: int = 0

    ai_turns_p1: int = 0
    ai_turns_p2: int = 0


def update_ai_stats(agg: AggregatedStats, player: int, stats):
    if stats is None:
        return

    if player == 1:
        agg.total_nodes_visited_p1 += stats.nodes_visited
        agg.total_cutoffs_p1 += stats.cutoffs
        agg.total_elapsed_time_p1 += stats.elapsed_time
        agg.max_depth_reached_p1 = max(agg.max_depth_reached_p1, stats.max_depth)
        agg.ai_turns_p1 += 1
    else:
        agg.total_nodes_visited_p2 += stats.nodes_visited
        agg.total_cutoffs_p2 += stats.cutoffs
        agg.total_elapsed_time_p2 += stats.elapsed_time
        agg.max_depth_reached_p2 = max(agg.max_depth_reached_p2, stats.max_depth)
        agg.ai_turns_p2 += 1


def run_human_vs_ai(game, ai_fn, ai_name: str, human_player: int = 1, show_board: bool = True):
    state = game["create_state"]()
    model = game["create_model"]()

    ai_player = 2 if human_player == 1 else 1
    agg = AggregatedStats(games=1)

    print(f"\n=== {game['name']} | Humano vs {ai_name} ===")

    if show_board:
        game["print_board"](state)

    while not state.is_terminal:
        if state.current_player == human_player:
            move = game["read_human_move"](state)
            game["apply_human_move"](state, move, human_player)
        else:
            action, stats = ai_fn(state, model, ai_player)
            update_ai_stats(agg, ai_player, stats)
            model.advance(state, action)

            if "print_ai_action" in game:
                game["print_ai_action"](action)

        if show_board:
            game["print_board"](state)

    if state.winner is None:
        agg.draws += 1
        print("Empate")
    elif state.winner == human_player:
        print("Gana el humano")
        if human_player == 1:
            agg.p1_wins += 1
        else:
            agg.p2_wins += 1
    else:
        print("Gana la IA")
        if ai_player == 1:
            agg.p1_wins += 1
        else:
            agg.p2_wins += 1

    return agg


def run_ai_vs_ai(game, ai1_fn, ai1_name: str, ai2_fn, ai2_name: str, games_count: int = 1, show_board: bool = True):
    agg = AggregatedStats(games=games_count)

    for game_index in range(games_count):
        state = game["create_state"]()
        model = game["create_model"]()

        print(f"\n=== Partida {game_index + 1}/{games_count}: {ai1_name} vs {ai2_name} ===")

        if show_board:
            game["print_board"](state)

        while not state.is_terminal:
            if state.current_player == 1:
                action, stats = ai1_fn(state, model, 1)
                update_ai_stats(agg, 1, stats)
                model.advance(state, action)

                if show_board and "print_ai_action" in game:
                    print(f"[Jugador 1 - {ai1_name}]")
                    game["print_ai_action"](action)
            else:
                action, stats = ai2_fn(state, model, 2)
                update_ai_stats(agg, 2, stats)
                model.advance(state, action)

                if show_board and "print_ai_action" in game:
                    print(f"[Jugador 2 - {ai2_name}]")
                    game["print_ai_action"](action)

            if show_board:
                game["print_board"](state)

        if state.winner is None:
            agg.draws += 1
            print("Empate")
        elif state.winner == 1:
            agg.p1_wins += 1
            print(f"Gana jugador 1 ({ai1_name})")
        else:
            agg.p2_wins += 1
            print(f"Gana jugador 2 ({ai2_name})")

    return agg


def print_aggregated_stats(agg: AggregatedStats, p1_name="Jugador 1", p2_name="Jugador 2"):
    print("\n=== RESULTADOS ===")
    print("Partidas:", agg.games)
    print(f"Victorias {p1_name}:", agg.p1_wins)
    print(f"Victorias {p2_name}:", agg.p2_wins)
    print("Empates:", agg.draws)

    print(f"\n--- Stats {p1_name} ---")
    print("Nodos visitados:", agg.total_nodes_visited_p1)
    print("Cutoffs:", agg.total_cutoffs_p1)
    print("Máxima profundidad:", agg.max_depth_reached_p1)
    print("Tiempo total:", agg.total_elapsed_time_p1)
    if agg.ai_turns_p1 > 0:
        print("Tiempo medio por turno:", agg.total_elapsed_time_p1 / agg.ai_turns_p1)

    print(f"\n--- Stats {p2_name} ---")
    print("Nodos visitados:", agg.total_nodes_visited_p2)
    print("Cutoffs:", agg.total_cutoffs_p2)
    print("Máxima profundidad:", agg.max_depth_reached_p2)
    print("Tiempo total:", agg.total_elapsed_time_p2)
    if agg.ai_turns_p2 > 0:
        print("Tiempo medio por turno:", agg.total_elapsed_time_p2 / agg.ai_turns_p2)