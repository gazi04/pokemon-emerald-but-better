from enum import StrEnum


class BattleState(StrEnum):
    # intro → currently_turn (user picks action)
    # currently_turn → post_turn / waiting (turn resolves)
    # currently_turn → caught (successful catch)
    # post_turn / waiting → currently_turn (next turn begins)
    # waiting → switching (player switches)
    # switching → currently_turn (enemy gets turn after switch)
    # trainer_switch → trainer_sending (exp awarded after enemy faint)
    # trainer_sending → waiting (next trainer pokemon sent out)
    # trainer_sending → end (trainer has no more pokemon)
    # player_fainted → waiting (force switch to live pokemon)
    # player_fainted → lost (no usable pokemon left)
    # end / caught / lost → battle exits
    INTRO = "intro"
    CURRENTLY_TURN = "currently turn"
    POST_TURN = "post turn"
    WAITING = "waiting"
    SWITCHING = "switching"
    TRAINER_SWITCH = "trainer switch"
    TRAINER_SENDING = "trainer sending"
    PLAYER_FAINTED = "player fainted"
    CAUGHT = "caught"
    LOST = "lost"
    LEARNING_MOVE = "learning move"
    END = "end"
