# UI Layer (`src/ui/`) — Report & Guide

## 1. What the UI layer is

`src/ui/` holds the **view-painting** half of the game. Each `arcade.View` in `src/states/` owns one
UI object (`self.ui`) and delegates drawing to it: the view handles input + navigation + lifecycle,
the UI object lays out widgets and draws them from data it's handed. The rule (from CLAUDE.md): **UI
managers render from model state; they do not own logic.** A UI class never mutates save data, never
runs combat — it receives values and shows them.

Layouts are authored in **Tiled `.tmx` files** (`assets/ui/*.tmx`), not hard-coded. Each UI reads a
`.tmx` to get the rectangles/positions of its boxes, then places arcade widgets at those bounds.

---

## 2. The pieces

### One UI class per screen (8)
| Class | File | LOC | Paired view |
|---|---|---|---|
| `DialogUI` | `dialog_ui.py` | 50 | `DialogView` |
| `MenuUi` | `menu_ui.py` | 65 | `MenuView` |
| `BagUI` | `bag_ui.py` | 137 | `BagView` |
| `ShopUI` | `shop_ui.py` | 205 | `ShopView` |
| `PokedexUi` | `pokedex_ui.py` | 185 | `PokedexView` |
| `PokemonMenuUi` | `pokemon_menu_ui.py` | 336 | `PokemonMenuView` |
| `PokemonInformationUI` | `pokemon_information_ui.py` | 395 | `PokemonInfoView` |
| `BattleUiManager` | `battle_ui_manager.py` | 342 | `BattleView` |

### Reusable components (`src/ui/components/`)
- **`TypewriterMessageBox`** (112) — animates text char-by-char into an `arcade.gui.UILabel`. Used by
  **both** `DialogUI` and `BattleUiManager`. Owns a message queue + persistent/one-shot callbacks.
- **`BattleMenuPanel`** (209) — the FIGHT/BAG/POKéMON/RUN + move buttons panel, used by
  `BattleUiManager`.

### Shared helper
- **`layout_parser.py`** (`parse_battle_layout`) — reads a `.tmx` and returns a flat
  `{object_name: {x, y, w, h}}` bounds dict (geometry only, no widgets). Currently used by the
  battle UI.

---

## 3. How it's written — two recurring shapes

### (a) A simple UI (`DialogUI`, the model to copy)
```python
class DialogUI:
    def __init__(self):
        self._manager = arcade.gui.UIManager()
        tilemap = arcade.load_tilemap(DIALOG_UI)          # .tmx path from constants
        ui_layer = tilemap.get_tilemap_layer("ui")
        self._textbound = {}
        for obj in ui_layer.tiled_objects:                # read box/text rectangles
            ...
            if obj.name == "box":
                self._manager.add(arcade.gui.UIImage(texture=..., x=x, y=y, ...))
            else:
                self._textbound["dialog"] = {"x": x, "y": y, "w": w, "h": h}
        self.message_box = TypewriterMessageBox(self._textbound, self._manager)

    def queue_messages(self, m):   self.message_box.queue_message(m)
    def is_text_finished(self):    return not self.message_box.is_processing
    def update(self, dt):          self.message_box.update(dt)
    def draw(self):                self._manager.draw()
```
Pattern: own an `arcade.gui.UIManager`, parse a `.tmx` for bounds, place widgets/components, expose
`draw()` + `update()` + small setters the view calls. Every UI follows this skeleton.

### (b) The one orchestrator (`BattleUiManager`)
The battle screen is the heaviest, so its UI is a **manager** coordinating sub-pieces:
```python
class BattleUiManager:
    def __init__(self, after_text_callback):
        self.bounds = parse_battle_layout(BATTLE_UI)      # shared layout_parser
        self.manager = arcade.gui.UIManager(); self.manager.enable()
        self._build_static_graphics()
        self.message_box = TypewriterMessageBox(self.bounds, self.manager)
        self.message_box.set_callback(after_text_callback)
        self.menu_panel  = BattleMenuPanel(self.bounds, self.manager)
        ...                                               # HP/exp bar rects, slide animation state
```
It exposes `switch_mode`, `queue_messages`, `set_player_info`/`set_enemy_info`,
`draw_hp_bar`/`draw_exp_bar`, `set_transition`, `update`, `draw` — the view calls these; the manager
never decides battle flow.

### The TypewriterMessageBox component
Char-by-char reveal driven by `update(dt)` against `TEXT_DELAY`. Public surface the rest of the game
uses: `queue_message`, `set_callback` (persistent, fires after every drain), `set_on_complete`
(one-shot), `reset_prompt`, `clear`, `is_processing`. This is the box the **MessageService** routes
text into — see `message_service_report.md`.

---

## 4. How it connects

```
   GameView (base)                     src/ui/
   ──────────────                      ───────
   on_draw   ──► self.ui.draw()        each *Ui owns an arcade.gui.UIManager
   on_update ──► self.ui.update(dt)    + widgets placed at .tmx bounds
        ▲                                   │
        │ view sets self.ui in __init__     │ reads
        │ (BattleView, DialogView, ...)     ▼
   states/*View ──────────────────────► assets/ui/*.tmx   (paths in src/constants.py)

   MessageService ──► active TypewriterMessageBox.queue_message(...)
```

- **View ↔ UI:** every view does `self.ui = SomeUI(...)` in `__init__`; the `GameView` base's default
  `on_draw`/`on_update` call `self.ui.draw()` / `self.ui.update(dt)` (views with extra render override
  and keep their own). See `game_director_report.md` for how views are built.
- **UI ↔ assets:** layouts live in `assets/ui/*.tmx`; the paths are named constants in
  `src/constants.py` (`BATTLE_UI`, `DIALOG_UI`, `BAG_UI`, …). Change a layout in Tiled, no code edit.
- **UI ↔ data:** content-heavy UIs (`PokedexUi`, `PokemonInformationUI`, `PokemonMenuUi`) take the
  injected `DataLoader` to read species data for display (see `data_loader_report.md`). They read,
  never write.
- **UI ↔ text:** `MessageService` (owned by `GameDirector`) pushes lines into whichever
  `TypewriterMessageBox` the active view registered.

---

## 5. How to use it

### Drive an existing UI from a view
```python
class DialogView(GameView):
    def __init__(self, ...):
        self.ui = DialogUI()
        self.ui.queue_messages(lines)
    # base GameView already calls self.ui.draw()/update(dt)
```

### Build a new screen's UI
1. Author the layout in Tiled → `assets/ui/my_screen.tmx`; add its path to `src/constants.py`.
2. Write `MyUi` following the `DialogUI` skeleton: own a `UIManager`, parse the `.tmx` for bounds,
   place widgets, expose `draw()`/`update(dt)` + setters.
3. Reuse components — `TypewriterMessageBox` for text, `parse_battle_layout`-style bounds reading.
4. In the view: `self.ui = MyUi(...)`; the base handles draw/update.

### Show animated text anywhere
Use a `TypewriterMessageBox` (or just publish a `TextMessageEvent` and let `MessageService` route it
to the active box — no UI reference needed).

---

## 6. Gotchas & rough edges

- **Class-name suffix is inconsistent.** Some are `...UI` (`BagUI`, `ShopUI`, `PokemonInformationUI`),
  others `...Ui` (`PokemonMenuUi`, `PokedexUi`, `MenuUi`, `BattleUiManager`). Cosmetic, flagged in the
  readability plan's "standardize to `*Ui`" companion — not yet unified. (The `PodedexUi`→`PokedexUi`
  typo was already fixed.)
- **Two layout-parsing paths.** `BattleUiManager` uses the shared `layout_parser.parse_battle_layout`;
  the other UIs each inline their own `.tmx` read in `__init__` (e.g. `DialogUI`). The shared parser
  isn't reused everywhere — duplication worth consolidating later.
- **`BattleUiManager` is an SRP offender (342 LOC).** It builds static graphics, computes HP/exp-bar
  geometry, runs the slide animation, *and* orchestrates sub-components. The SRP audit proposes pulling
  bar geometry/animation into a `BarRenderer` (refactor #12 Stage 3) — **deferred (YAGNI)**.
- **Hard-coded magic numbers.** Y-flips like `600 - obj.coordinates.y` (`dialog_ui.py:21`) and `/ 32`
  tile divisions assume the window/tile size; they're not pulled from config.
- **No logic in UI — keep it that way.** If you find yourself deciding *what happens* inside a `*Ui`,
  it belongs in the view or a system; the UI should only decide *how it looks*.

---

## 7. One-paragraph summary

`src/ui/` is the presentation layer: one UI class per screen (plus the heavier `BattleUiManager`
orchestrator), each owning an `arcade.gui.UIManager`, reading its layout from a Tiled `.tmx`
(paths in `constants.py`), and exposing `draw()`/`update()` for its paired view to call. Shared
components — `TypewriterMessageBox` (animated text, the target of `MessageService`) and
`BattleMenuPanel` — are reused across screens. UIs read injected `DataLoader` species data to display
but never mutate state. Rough edges: inconsistent `UI`/`Ui` naming, two layout-parsing paths, and the
oversized `BattleUiManager` (a `BarRenderer` split is planned but deferred).
