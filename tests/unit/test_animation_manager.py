"""Animation cycling: sequences reuse frames, and fps defaults to exactly one
cycle per unit of progress (one cycle per tile stepped)."""

from src.entities.components.animation_manager import Animation, AnimationManager
import pytest


class FakeTexture:
    """Stands in for arcade.Texture — flip is all the Animation needs."""

    def __init__(self, name):
        self.name = name

    def flip_left_right(self):
        return FakeTexture(f"{self.name}_flipped")

    def __repr__(self):
        return self.name


A, B, C = FakeTexture("a"), FakeTexture("b"), FakeTexture("c")


# --- Animation --------------------------------------------------------------


def test_defaults_to_one_cycle_per_unit_of_progress():
    anim = Animation([A, B, C])
    assert anim.fps == 3
    # progress 0..1 walks the whole cycle exactly once
    assert [anim.frame(p) for p in (0.0, 0.34, 0.67)] == [A, B, C]


def test_sequence_reuses_frames_without_reloading_them():
    # "step, idle, step, idle" from only three textures
    anim = Animation([A, B, C], sequence=[0, 2, 1, 2])
    assert [anim.frame(p) for p in (0.0, 0.25, 0.5, 0.75)] == [A, C, B, C]
    assert anim.fps == 4  # follows the sequence length, not the frame count


def test_cycle_wraps_past_one():
    anim = Animation([A, B])
    assert anim.frame(0.0) is anim.frame(1.0)


def test_explicit_fps_overrides_default():
    anim = Animation([A, B], fps=4)  # two cycles per tile
    assert [anim.frame(p) for p in (0.0, 0.25, 0.5, 0.75)] == [A, B, A, B]


def test_flipped_mirrors_frames_and_keeps_timing():
    anim = Animation([A, B], sequence=[0, 1, 0], fps=6)
    flipped = anim.flipped()

    assert [t.name for t in flipped.frames] == ["a_flipped", "b_flipped"]
    assert flipped.sequence == [0, 1, 0]
    assert flipped.fps == 6


# --- AnimationManager -------------------------------------------------------


def test_add_and_get_round_trip():
    manager = AnimationManager()
    manager.add("walk", "down", [A, B])  # type: ignore
    animation = manager.get("walk", "down")

    if animation is None:
        pytest.fail("The variable animation is None.")

    assert animation.frame(0.0) is A


def test_get_returns_none_for_unknown_animation():
    assert AnimationManager().get("fly", "up") is None


def test_animations_are_keyed_by_name_and_direction():
    manager = AnimationManager()
    manager.add("walk", "down", [A])  # type: ignore
    manager.add("walk", "up", [B])  # type: ignore
    manager.add("run", "down", [C])  # type: ignore

    animation1 = manager.get("walk", "down")
    animation2 = manager.get("walk", "up")
    animation3 = manager.get("run", "down")

    if animation1 is None or animation2 is None or animation3 is None:
        pytest.fail("The variable animations is None.")

    assert animation1.frame(0.0) is A
    assert animation2.frame(0.0) is B
    assert animation3.frame(0.0) is C
