import random
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.save.player import PlayerPokemonMove
from src.model.static.pokemon import PokemonMove
from src.core.combat_calculator import calculate_damage
from src.core.data_loader import DataLoader
from src.enums.stat import Stat

class EnemyAI:
    def __init__(self, smartness: float, data_loader: DataLoader):
        self.smartness = max(0.0, min(1.0, smartness))
        self.typechart = data_loader.types
        self.data_loader = data_loader

    def evaluate_hp(self, enemy_pokemon_hp: int, enemy_pokemon_max_hp: int, player_pokemon_hp: int, player_pokemon_hp_max: int) -> float:
        if enemy_pokemon_hp <= 0: return -1000  
        if player_pokemon_hp <= 0: return 1000 
        
        ai_hp_pct = enemy_pokemon_hp / enemy_pokemon_max_hp
        player_hp_pct = player_pokemon_hp / player_pokemon_hp_max
        
        return (ai_hp_pct - player_hp_pct) * 100
    
    def simulate_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move: PokemonMove) -> int:
        if not move.power:
            return 0
        
        result = calculate_damage(
            attacker.level, attacker.stats, attacker.types, attacker.modifiers, 
            attacker.status_effect, move, defender.stats, defender.types, 
            defender.modifiers, 0, self.typechart
        )
        damage = result.damage
        if result.is_critical:
            damage //= 2  
        
        return damage
    
    def minimax(self, enemy_pokemon: BattlePokemon, player_pokemon: BattlePokemon) -> dict[str, float]:
        move_scores = {}

        for ai_move in enemy_pokemon.moves:
            if ai_move.pp == 0:
                move_scores[ai_move.name] = -float('inf')
                continue

            worst_case_score = float('inf')
            ai_move_data = self.data_loader.get_move(ai_move.name)
            
            for player_move in player_pokemon.moves:
                if player_move.pp == 0:
                    continue

                player_move_data = self.data_loader.get_move(player_move.name)
                
                enemy_hp = enemy_pokemon.current_hp
                player_hp = player_pokemon.current_hp
                
                is_player_first = self._player_moves_first(
                    player_pokemon.get_stat(Stat.SPEED), player_move_data.priority, 
                    enemy_pokemon.get_stat(Stat.SPEED), ai_move_data.priority
                )

                if is_player_first:
                    player_damage = self.simulate_damage(player_pokemon, enemy_pokemon, player_move_data)
                    enemy_hp -= player_damage
                    
                    if enemy_hp > 0:
                        ai_dmg = self.simulate_damage(enemy_pokemon, player_pokemon, ai_move_data)
                        player_hp -= ai_dmg
                else:
                    ai_dmg = self.simulate_damage(enemy_pokemon, player_pokemon, ai_move_data)
                    player_hp -= ai_dmg
                    
                    if player_hp > 0:
                        player_damage = self.simulate_damage(player_pokemon, enemy_pokemon, player_move_data)
                        enemy_hp -= player_damage

                outcome_score = self.evaluate_hp(enemy_hp, enemy_pokemon.max_hp, player_hp, player_pokemon.max_hp)

                if outcome_score < worst_case_score:
                    worst_case_score = outcome_score

            move_scores[ai_move.name] = worst_case_score

        return move_scores
    
    def _player_moves_first(self, player_speed: int, player_priority: int, enemy_speed: int, enemy_priority: int) -> bool:
        return player_priority > enemy_priority or (
            player_priority == enemy_priority and player_speed >= enemy_speed
        )

    def select_move(self, enemy_pokemon: BattlePokemon, player_pokemon: BattlePokemon) -> int:
        move_scores = self.minimax(enemy_pokemon, player_pokemon)
    
        best_moves = sorted(move_scores.keys(), key=lambda m: move_scores[m], reverse=True)

        if random.random() < self.smartness:
            for index, move in enumerate(enemy_pokemon.moves):
                if move.name == best_moves[0]:
                    return index
        
        return random.choice(range(len(enemy_pokemon.moves)))