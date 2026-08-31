from .actions import PokerAction, PokerActionType
from .cards import CARD_NAMES
from .forward_model import LeducPokerForwardModel
from .game_state import LeducPokerGameState


ACTION_NAMES = {
    PokerActionType.CHECK: "CHECK (pasar sin apostar)",
    PokerActionType.BET: "BET (apostar)",
    PokerActionType.CALL: "CALL (igualar)",
    PokerActionType.RAISE: "RAISE (subir)",
    PokerActionType.FOLD: "FOLD (retirarse)"
}


def print_board(state: LeducPokerGameState, debug_mode: bool = True):
    print("\n=================== LEDUC POKER ===================")

    if state.last_action_summary:
        print(f" ÚLTIMA JUGADA: {state.last_action_summary}")
        print("---------------------------------------------------")

    public = (
        CARD_NAMES[state.public_card]
        if state.public_card is not None
        else "todavía no revelada"
    )

    print(f" Ronda de apuestas: {state.betting_round}/2")
    print(f" Carta pública: {public}")
    print(f" Bote: {state.pot} fichas")
    print(f" Turno actual: Jugador {state.current_player}")
    print(
        " Contribuciones: "
        f"J1={state.contributions[1]} | J2={state.contributions[2]}"
    )
    print("---------------------------------------------------")

    for player in (1, 2):
        card = state.private_cards[player]

        if debug_mode and card is not None:
            card_text = CARD_NAMES[card]
        else:
            card_text = "OCULTA"

        print(f"Jugador {player}: carta privada -> {card_text}")

    if state.is_terminal:
        if state.winner is None:
            print(" Resultado: EMPATE")
        else:
            print(f" Ganador: Jugador {state.winner}")

    print("===================================================\n")


def print_action_summary(
    action: PokerAction,
    state_before: LeducPokerGameState
):
    print(
        f"\n >>> JUGADA REAL: Jugador {action.player} -> "
        f"{action.action_type.value} <<<"
    )


def print_action_result(
    state_before: LeducPokerGameState,
    action: PokerAction,
    state_after: LeducPokerGameState
):
    if state_after.last_action_summary:
        print(f"  └─ {state_after.last_action_summary}")
    print("---------------------------------------------------\n")


def print_ai_action(action: PokerAction):
    print(
        f" IA (Jugador {action.player}) elige: "
        f"{action.action_type.value}"
    )


def read_human_move(state: LeducPokerGameState) -> PokerActionType:
    """Permite al jugador humano elegir únicamente entre acciones legales."""
    player = state.current_player
    card = state.private_cards[player]

    print(f"\n TU TURNO (Jugador {player})")
    if card is not None:
        print(f"Tu carta privada: {CARD_NAMES[card]}")

    if state.public_card is not None:
        print(f"Carta pública: {CARD_NAMES[state.public_card]}")

    print(f"Bote actual: {state.pot} fichas")

    model = LeducPokerForwardModel()
    legal_actions = model.compute_available_actions(state)

    for index, action in enumerate(legal_actions):
        print(f"  [{index}] {ACTION_NAMES[action.action_type]}")

    while True:
        try:
            option = int(input("Selecciona acción: ").strip())
            if 0 <= option < len(legal_actions):
                return legal_actions[option].action_type
        except ValueError:
            pass

        print(" Opción no válida.")
