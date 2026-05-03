import arcade
import arcade.gui

class BagView(arcade.View):
    def __init__(self):
        super().__init__()
        
        self.manager = arcade.gui.UIManager()
        self.manager._pixelated = True
        
        tilemap = arcade.load_tilemap("assets/ui/bagUiDesign.tmx")
        uiLayer = tilemap.get_tilemap_layer("ui")
        
        for obj in uiLayer.tiled_objects:
            w = obj.size.width
            h = obj.size.height

            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            
            if obj.name == "background":
                self.manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/bagUi.png"),
                        width=w,
                        height=h,
                        x=x,
                        y=y
                    )
                )
            elif "Arrow" in obj.name:
                self.manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture(f"assets/ui/sprites/{obj.name}.png"),
                        width=w,
                        height=h,
                        x=x,
                        y=y
                    )
                )
            elif obj.name == "section":
                self.sectionText = arcade.gui.UILabel(
                    "ITEMS",
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=25,
                    align="center"
                )
                self.manager.add(self.sectionText)
            elif obj.name == "text":
                self.dialog = arcade.gui.UILabel(
                    "Return to the field.",
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=30
                )
                self.manager.add(self.dialog)
        
        self.inventory = [
            {"name": "POTION", "qty": 15},
            {"name": "ANTIDOTE", "qty": 4},
            {"name": "PARALYZE HEAL", "qty": 2},
            {"name": "AWAKENING", "qty": 1},
            {"name": "BURN HEAL", "qty": 3},
            {"name": "ICE HEAL", "qty": 1},
            {"name": "SUPER POTION", "qty": 10},
            {"name": "FULL HEAL", "qty": 5},
            {"name": "REVIVE", "qty": 2},
            {"name": "TEST", "qty": 0},
            {"name": "TEST", "qty": 0},
            {"name": "TEST", "qty": 0},
            {"name": "TEST", "qty": 0},
            {"name": "TEST", "qty": 0},
        ]
        
        self.max_visible_items = 12
        self.current_selection = 0  
        self.top_visible_index = 0  
        
        self.item_labels = []
        
        self.start_x = 420 
        self.start_y = 500
        self.spacing = 40 
        
        for i in range(self.max_visible_items):
            label = arcade.gui.UILabel(
                text="",
                x=self.start_x,
                y=self.start_y - (i * self.spacing),
                width=250,
                height=self.spacing,
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=20
            )
            self.item_labels.append(label)
            self.manager.add(label)
            
        self.cursor_label = arcade.Text(
            text="▶", 
            x=self.start_x - 30,
            y=self.start_y,
            width=30, 
            height=self.spacing,
            color=arcade.color.RED,
            font_name="Pokemon Emerald",
            font_size=20
        )

        self.update_item_list()

    def update_item_list(self):
        for i in range(self.max_visible_items):
            inventory_index = self.top_visible_index + i
            
            if inventory_index < len(self.inventory):
                item = self.inventory[inventory_index]
                if item["qty"] > 0:
                    display_text = f"{item['name']:<14} x{item['qty']}"
                else:
                    display_text = item['name']
                    
                self.item_labels[i].text = display_text
            else:
                self.item_labels[i].text = "" 

        cursor_ui_index = self.current_selection - self.top_visible_index
        self.cursor_label.y = self.start_y - (cursor_ui_index * self.spacing) + (self.spacing / 3)
        

    def on_key_press(self, key, modifiers):
        if key == arcade.key.UP:
            if self.current_selection > 0:
                self.current_selection -= 1
                
                if self.current_selection < self.top_visible_index:
                    self.top_visible_index -= 1
                    
                self.update_item_list()
        elif key == arcade.key.DOWN:
            if self.current_selection < len(self.inventory) - 1:
                self.current_selection += 1
                
                if self.current_selection >= self.top_visible_index + self.max_visible_items:
                    self.top_visible_index += 1
                    
                self.update_item_list()
                
    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.manager.draw()
        self.cursor_label.draw()
        
if __name__ == "__main__":
    window = arcade.Window(width=800, height=600)
    start_view = BagView()
    window.show_view(start_view)
    arcade.run()