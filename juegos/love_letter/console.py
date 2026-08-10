from .game_state import LoveLetterGameState

CARD_NAMES = {
    1: "GUARD (Guardia)",
    2: "PRIEST (Sacerdote)",
    3: "BARON (Barón)",
    4: "HANDMAID (Doncella)",
    5: "PRINCE (Príncipe)",
    6: "KING (Rey)",
    7: "COUNTESS (Condesa)",
    8: "PRINCESS (Princesa)",
}

def print_board(state: LoveLetterGameState, debug_mode: bool = True):
    print("\n=================== ESTADO DEL TABLERO ===================")
    
    if getattr(state, "last_action_summary", None):
        print(f"📢 ÚLTIMA JUGADA: {state.last_action_summary}")
        print("----------------------------------------------------------")

    print(f"📦 Mazo restante: {len(state.deck)} cartas")
    print(f"🎯 Turno actual: Jugador {state.current_player}")
    print("----------------------------------------------------------")

    for p in range(1, state.num_players + 1):
        status = "💀 ELIMINADO" if state.eliminated[p] else "🟢 ACTIVO"
        descartes = [f"{c.name}({c.value})" for c in state.played_cards[p]]
        
        # --- MODO DEPURACIÓN / ESPECTADOR ---
        if debug_mode and p != 1 and not state.eliminated[p]:
            # Muestra las cartas reales en la mano de la IA entre corchetes
            cards_str = ", ".join(c.name for c in state.hands[p])
            print(f"  Jugador {p} [{status}]: {len(state.hands[p])} carta(s) -> 👁️ [IA TIENE: {cards_str}] | Descartes: {descartes}")
        else:
            print(f"  Jugador {p} [{status}]: {len(state.hands[p])} carta(s) en mano | Descartes: {descartes}")
            
    print("==========================================================")




def print_action_summary(action, state_before: LoveLetterGameState):
    """Muestra la intención y objetivo de la jugada elegida."""
    p = action.player
    card = action.card
    target = action.target
    guess = action.guess

    print(f"\n🎬 >>> JUGADA REAL: El Jugador {p} ha utilizado {card.name} ({card.value}) <<<")

    if card.value == 1:
        guess_val = guess.value if hasattr(guess, 'value') else guess
        guess_name = CARD_NAMES.get(guess_val, str(guess_val))
        print(f"  └─ 🎯 Objetivo: Jugador {target} | 🔮 Adivinanza: {guess_name}")

    elif card.value == 2:
        if target:
            print(f"  └─ 👁️ Mira en secreto la mano del Jugador {target}")
            # Si el humano es quien juega el Priest, muestra en pantalla la carta vista
            if p == 1 and not state_before.eliminated[target] and len(state_before.hands[target]) > 0:
                target_card = state_before.hands[target][0]
                print(f"  └─ 🕵️ [INFORMACIÓN REVELADA]: El Jugador {target} tiene {target_card.name} ({target_card.value})")
        else:
            print(f"  └─ 👁️ Descartado sin efecto (Todos los objetivos están protegidos)")

    elif card.value == 3:
        if target:
            print(f"  └─ ⚔️ Duelo de Barón contra Jugador {target}")
        else:
            print(f"  └─ ⚔️ Descartado sin efecto (Todos los objetivos están protegidos)")

    elif card.value == 4:
        print(f"  └─ 🛡️ Se protege con la Doncella hasta su próximo turno")

    elif card.value == 5:
        print(f"  └─ 👑 Obliga al Jugador {target} a descartar su mano y robar otra carta")

    elif card.value == 6:
        if target:
            print(f"  └─ 🔄 Intercambia su mano con el Jugador {target}")
        else:
            print(f"  └─ 🔄 Descartado sin efecto (Todos los objetivos están protegidos)")

    elif card.value == 7:
        print(f"  └─ 🎭 Condesa descartada sin efecto adicional")

    elif card.value == 8:
        print(f"  └─ 💥 ¡HA JUGADO LA PRINCESA! Queda ELIMINADO automáticamente")

    print("----------------------------------------------------------")


def print_action_result(state_before, action, state_after):
    """Muestra las consecuencias de la jugada tras actualizar el estado del juego."""
    card = action.card
    target = action.target
    p = action.player

    if card.value == 1 and target is not None:
        if state_after.eliminated[target]:
            print(f"  └─ 💥 ¡ACIERTO! El Jugador {target} tenía esa carta y ha sido ELIMINADO.")
        else:
            print(f"  └─ ❌ FALLO: El Jugador {target} NO tenía esa carta.")

    elif card.value == 3 and target is not None:
        if state_after.eliminated[target]:
            print(f"  └─ 💥 ¡Jugador {p} gana el duelo! Jugador {target} queda ELIMINADO.")
        elif state_after.eliminated[p]:
            print(f"  └─ 💀 ¡Jugador {target} gana el duelo! Jugador {p} queda ELIMINADO.")
        else:
            print(f"  └─ 🤝 Empate en el duelo. Nadie cae.")

    elif card.value == 5 and target is not None:
        if len(state_before.played_cards[target]) < len(state_after.played_cards[target]):
            discarded = state_after.played_cards[target][-1]
            print(f"  └─ 📦 Carta descartada por Jugador {target}: {discarded.name} ({discarded.value})")
            if discarded.value == 8:
                print(f"  └─ 💥 ¡Descartó la PRINCESA! El Jugador {target} queda ELIMINADO.")

    print("----------------------------------------------------------\n")


def read_human_move(state: LoveLetterGameState):
    """Gestión interactiva de la entrada del jugador humano."""
    player = state.current_player
    hand = state.hands[player]

    print(f"\n👉 TU TURNO (Jugador {player})")
    print("Tus cartas disponibles:")
    for i, c in enumerate(hand):
        print(f"  [{i}] {c.name} (Valor: {c.value})")

    # Selección de carta
    card_idx = -1
    while card_idx not in range(len(hand)):
        try:
            card_idx = int(input(f"\nSelecciona carta a jugar (0 - {len(hand)-1}): "))
        except ValueError:
            pass

    selected_card = hand[card_idx]
    print(f"➔ Has elegido jugar: {selected_card.name} ({selected_card.value})")

    target = None
    guess = None

    # Cartas con objetivo
    if selected_card.value in [1, 2, 3, 5, 6]:
        valid_targets = [
            p for p in range(1, state.num_players + 1)
            if not state.eliminated[p] and (
                (selected_card.value == 5 and p == player) or 
                (p != player and not state.protected[p])
            )
        ]

        if not valid_targets:
            print("\n⚠️ No hay objetivos válidos disponibles (todos están protegidos o eliminados). La carta se descartará sin efecto.")
            target = None
        else:
            print(f"\nJugadores seleccionables: {valid_targets}")
            while target not in valid_targets:
                try:
                    target = int(input(f"Introduce jugador objetivo: "))
                    if target not in valid_targets:
                        print(f"⚠️ Jugador {target} no es válido o está protegido.")
                except ValueError:
                    pass

    # Adivinanza para el Guardia
    if selected_card.value == 1 and target is not None:
        print("\nCartas que puedes adivinar:")
        for v in range(2, 9):
            print(f"  [{v}] {CARD_NAMES[v]}")

        while guess not in range(2, 9):
            try:
                guess = int(input("Adivina el valor de la carta rival (2-8): "))
            except ValueError:
                pass

    return selected_card, target, guess