from juegos.tictactoe.tictactoe import play_human_vs_ai
from algoritmos.minmax_ab import choose_ai_move_alpha_beta


if __name__ == "__main__":
    play_human_vs_ai(choose_ai_move_alpha_beta, "Alpha-Beta")