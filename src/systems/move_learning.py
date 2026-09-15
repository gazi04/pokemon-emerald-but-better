"""The post-level-up move-learning queue.

Extracted from BattleSystem. Unlike the ability/held-item hooks, this one owns
real state of its own — the queue of moves waiting to be learned and the one
move waiting on a forget-a-move choice — so it is a small collaborator object,
the same shape as Progression, rather than a module of free functions.

The pokemon and the DataLoader are passed per call rather than held, so the
queue cannot go stale against a switched-in pokemon.
"""

from src.core.data_loader import DataLoader
from src.model.battle.battle_pokemon import BattlePokemon


class MoveLearningQueue:
    """The view drives this like the other message-gated sub-flows: queue the
    names, then pump advance() until it returns None, handling a replacement
    prompt in between."""

    def __init__(self):
        self._queue: list[str] = []
        self.pending: str | None = None

    def queue_moves(self, move_names: list[str]) -> None:
        self._queue.extend(move_names)

    def has_pending(self) -> bool:
        return bool(self._queue) or self.pending is not None

    def advance(self, pokemon: BattlePokemon, data_loader: DataLoader) -> dict | None:
        """Advance the learn queue.
        Returns None when done, {"type": "learned", ...} when a free slot let the
        move be learned outright, or {"type": "needs_replace", ...} when the
        moveset is full and the player must pick a move to forget.
        """
        if not self._queue:
            return None

        name = self._queue.pop(0)
        if pokemon.knows_move(name):
            return self.advance(pokemon, data_loader)  # already knows it — skip

        move = data_loader.get_move(name)
        display = (move.name if move else name).capitalize()

        if pokemon.has_free_move_slot():
            pokemon.learn_move(name, move.pp if move else 0)
            return {
                "type": "learned",
                "messages": [f"{pokemon.name} learned {display}!"],
            }

        self.pending = name
        return {
            "type": "needs_replace",
            "move": display,
            "messages": [
                f"{pokemon.name} wants to learn {display}.",
                f"But {pokemon.name} already knows four moves.",
                f"Forget a move to make room for {display}?",
            ],
        }

    def replace(
        self, index: int, pokemon: BattlePokemon, data_loader: DataLoader
    ) -> list[str]:
        """Forget the move at `index` and learn the pending one."""
        if self.pending is None:
            raise RuntimeError(
                "replace_learned_move() called with no pending learn; "
                "caller must check has_pending_learn()/current_learning_move() first"
            )
        name = self.pending
        self.pending = None
        move = data_loader.get_move(name)
        display = (move.name if move else name).capitalize()
        forgotten = pokemon.replace_move(index, name, move.pp if move else 0)
        return [
            f"{pokemon.name} forgot {forgotten.capitalize()}...",
            f"...and learned {display}!",
        ]

    def skip(self, pokemon: BattlePokemon, data_loader: DataLoader) -> list[str]:
        """Decline to learn the pending move."""
        if self.pending is None:
            raise RuntimeError(
                "skip_learned_move() called with no pending learn; "
                "caller must check has_pending_learn()/current_learning_move() first"
            )
        name = self.pending
        self.pending = None
        move = data_loader.get_move(name)
        display = (move.name if move else name).capitalize()
        return [f"{pokemon.name} did not learn {display}."]
