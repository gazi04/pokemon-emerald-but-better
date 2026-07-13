import random
import copy
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.save.player import PlayerPokemonMove
from src.model.static.pokemon import PokemonMove
from src.core.combat_calculator import calculate_damage
from src.core.data_loader import DataLoader
from src.enums.stat import Stat
from src.enums.effect_type import EffectType
from src.enums.status_effect import StatusEffect

class EnemyAI:
    def __init__(self, smartness: float, data_loader: DataLoader):
        self.smartness = max(0.0, min(1.0, smartness))
        self.typechart = data_loader.types
        self.data_loader = data_loader
        self.max_depth = 2

    def evaluate_hp(self, enemy_pokemon: BattlePokemon, player_pokemon: BattlePokemon) -> float:
        if enemy_pokemon.current_hp <= 0: return -1000  
        if player_pokemon.current_hp <= 0: return 1000 
        
        ai_hp_pct = enemy_pokemon.current_hp / enemy_pokemon.max_hp
        player_hp_pct = player_pokemon.current_hp / player_pokemon.max_hp
        
        return (ai_hp_pct - player_hp_pct) * 100
    
    def simulate_damage(self, attacker: BattlePokemon, defender: BattlePokemon, move: PokemonMove) -> int:
        if not move.power:
            return 0
        
        if defender.immunity_to(move):
            return 0
        
        multiplier, _ = attacker.ability_attack_multiplier(move)
        
        result = calculate_damage(
            attacker.level, attacker.stats, attacker.types, attacker.modifiers, 
            attacker.status_effect, move, defender.stats, defender.types, 
            defender.modifiers, 0, self.typechart
        )
        damage = result.damage
        if result.is_critical:
            damage //= 2  
            
        accuracy = move.accuracy if move.accuracy else 100
        
        return round((damage * multiplier) / (accuracy / 100))
    
    def simulate_effects_move(self, move: PokemonMove, user: BattlePokemon, target: BattlePokemon) -> int:
        if not move.effects or target.immunity_to(move):
            return 0

        status_weights = {"sleep": 50, "freeze": 50, "paralyzed": 35, "burn": 35, "poison": 20, "confusion": 50, "flinch": 40}
        score = 0
        
        for effect in move.effects:
            chance = effect.chance if effect.chance else 100
            factor = chance / 100
            
            if effect.type == EffectType.STAT:
                stat_key = effect.stat 
                if effect.target == 'self':
                    if (effect.change > 0 and user.modifiers.get(stat_key, 0) >= 6) or (effect.change < 0 and user.modifiers.get(stat_key, 0) <= -6):
                        continue
                    score += (effect.change * 15) * factor
                    user.modifiers[stat_key] = max(-6, min(6, user.modifiers.get(stat_key, 0) + effect.change))
                else:
                    if (effect.change > 0 and target.modifiers.get(stat_key, 0) >= 6) or (effect.change < 0 and target.modifiers.get(stat_key, 0) <= -6):
                        continue
                    score += (effect.change * 15) * factor * -1
                    target.modifiers[stat_key] = max(-6, min(6, target.modifiers.get(stat_key, 0) + effect.change))
                    
            elif effect.type == EffectType.STATUS_CONDITION:
                status_condition = effect.condition
                if effect.target != 'self' and target.status_effect == StatusEffect.NONE:
                    if status_condition == StatusEffect.BURN and "fire" in target.types: continue
                    if status_condition == StatusEffect.POISON and ("poison" in target.types or "steel" in target.types): continue
                    if status_condition == StatusEffect.PARALYSIS and ("ground" in target.types or "electric" in target.types): continue

                    score += status_weights.get(status_condition, 0) * factor
                    target.status_effect = status_condition
        return score
    
    def _player_moves_first(self, player_speed: int, player_priority: int, enemy_speed: int, enemy_priority: int) -> bool:
        return player_priority > enemy_priority or (
            player_priority == enemy_priority and player_speed >= enemy_speed
        )
    
    def simulate_turn(self, enemy_pokemon: BattlePokemon, enemy_move:PokemonMove, player_pokemon: BattlePokemon, player_move:PokemonMove) -> int:
        points = 0
        
        is_player_first = self._player_moves_first(
            player_pokemon.get_stat(Stat.SPEED), player_move.priority, 
            enemy_pokemon.get_stat(Stat.SPEED), enemy_move.priority
        )

        if is_player_first:
            enemy_pokemon.current_hp -= self.simulate_damage(player_pokemon, enemy_pokemon, player_move)
            points -= self.simulate_effects_move(player_move, player_pokemon, enemy_pokemon)
                    
            if enemy_pokemon.current_hp > 0:
                player_pokemon.current_hp -= self.simulate_damage(enemy_pokemon, player_pokemon, enemy_move)
                points += self.simulate_effects_move(enemy_move, enemy_pokemon, player_pokemon)
        else:
            player_pokemon.current_hp -= self.simulate_damage(enemy_pokemon, player_pokemon, enemy_move)
            points += self.simulate_effects_move(enemy_move, enemy_pokemon, player_pokemon)
                    
            if player_pokemon.current_hp > 0:
                enemy_pokemon.current_hp -= self.simulate_damage(player_pokemon, enemy_pokemon, player_move)
                points -= self.simulate_effects_move(player_move, player_pokemon, enemy_pokemon)
                
        return points
    
    def _evaluate_ai_move(self, enemy: BattlePokemon, player: BattlePokemon, ai_move, depth: int) -> float:
        """Returns the absolute worst-case score the player can force upon this AI move choice."""
        if ai_move.pp == 0: 
            return -float('inf')
        
        ai_move_data = self.data_loader.get_move(ai_move.name)
        player_moves = [m for m in player.moves if m.pp > 0]
        
        if not player_moves:
            return self.evaluate_hp(enemy, player)

        outcomes = []
        for p_move in player_moves:
            pokemon_move_data = self.data_loader.get_move(p_move.name)
            
            enemy_pokemon_copy, player_pokemon_copy = copy.deepcopy(enemy), copy.deepcopy(player)
            turn_score = self.simulate_turn(enemy_pokemon_copy, ai_move_data, player_pokemon_copy, pokemon_move_data)
            
            if depth <= 1 or enemy_pokemon_copy.current_hp <= 0 or player_pokemon_copy.current_hp <= 0:
                outcomes.append(turn_score + self.evaluate_hp(enemy_pokemon_copy, player_pokemon_copy))
            else:
                future_score = max(self._evaluate_ai_move(enemy_pokemon_copy, player_pokemon_copy, next_move, depth - 1) 
                                   for next_move in enemy_pokemon_copy.moves)
                outcomes.append(turn_score + future_score)

        return min(outcomes)

    def select_move(self, enemy_pokemon: BattlePokemon, player_pokemon: BattlePokemon) -> int:
        move_scores = {
            index: self._evaluate_ai_move(enemy_pokemon, player_pokemon, move, self.max_depth)
            for index, move in enumerate(enemy_pokemon.moves)
        }
        
        best_move_indices = sorted(move_scores.keys(), key=lambda idx: move_scores[idx], reverse=True)
        
        if random.random() < self.smartness:
            return best_move_indices[0]
        
        return random.choice(range(len(enemy_pokemon.moves)))