from juegos.four_in_line.four_in_line import play_human_vs_ai
from algoritmos.minmax_ab_depth_limit import choose_ai_move_alpha_beta_depth_limit


def choose_move_depth5(state, model, ai):
    return choose_ai_move_alpha_beta_depth_limit(state, model, ai, max_depth=5)


if __name__ == "__main__":
    play_human_vs_ai(choose_move_depth5, "Alpha-Beta Depth Limited")