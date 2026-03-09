from juegos.tictactoe.tictactoe import play_human_vs_ai
from algoritmos.minmax import choose_ai_move


if __name__ == "__main__":
    play_human_vs_ai(choose_ai_move, "Minimax")