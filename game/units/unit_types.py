"""
Unit Types module for the ecosystem simulation game.

This module implements various unit types that inherit from the base Unit class,
each with specialized behaviors and characteristics.
"""

import random # Ensure random is imported for Scavenger fallback
from game.units.base_unit import Unit
from game.plants.base_plant import Plant # For Scavenger._find_food
from typing import Optional, Tuple

class Predator(Unit):
    """
    A predator unit that actively hunts other units.
    
    Predators have high strength and speed, making them effective hunters.
    They primarily target other units for food rather than plants.
    """
    
    def __init__(self, x, y, hp=None, config=None, board=None):
        """
        Initialize a new predator unit.
        
        Args:
            x (int): Initial x-coordinate on the board.
            y (int): Initial y-coordinate on the board.
            hp (int, optional): Health points. Defaults to template value.
        """
        super().__init__(x, y, unit_type="predator", hp=hp, energy=80, strength=15, speed=2, vision=6, config=config, board=board)
        self.target = None
        if self.config:
            self.energy_cost_move_hunt = self.config.get("units", "energy_consumption.move_hunt")
            self.energy_cost_move_flee = self.config.get("units", "energy_consumption.move_flee")

        if not hasattr(self, 'energy_cost_move_hunt') or self.energy_cost_move_hunt is None:
            self.energy_cost_move_hunt = self.energy_cost_move
        if not hasattr(self, 'energy_cost_move_flee') or self.energy_cost_move_flee is None:
            self.energy_cost_move_flee = self.energy_cost_move + 1

    def update(self, board):
        """
        Update the predator's state based on its surroundings.
        Predators prioritize hunting over other activities.
        Args:
            board (Board): The game board.
        """
        super().update(board)
        if not self.alive or self.state == "resting":
            return

        if self.state == "wandering" and \
           not (self.energy <= self.max_energy * 0.2) and \
           not (self.hp < self.max_hp * 0.3):
            return

        if self.energy <= self.max_energy * 0.2:
            self.state = "hungry"
            self._find_closest_food(board)
        elif self.hp < self.max_hp * 0.3:
            self.state = "fleeing"
            self._flee_from_threats(board)
        else:
            self.state = "hunting"
            self._hunt_prey(board)

    def _calculate_move_score(self, dx, dy, new_x, new_y, analysis) -> float:
        """Override base scoring to prioritize hunting behavior."""
        # Start with base scoring
        score = super()._calculate_move_score(dx, dy, new_x, new_y, analysis)
        
        # Look for prey in visible objects
        for obj_info in analysis['visible_objects']:
            obj = obj_info['object']
            if isinstance(obj, (Grazer, Scavenger)) and obj.alive:
                obj_x, obj_y = obj_info['position']
                current_dist = abs(obj_x - self.x) + abs(obj_y - self.y)
                new_dist = abs(obj_x - new_x) + abs(obj_y - new_y)
                
                # Strong bonus for moves that get us closer to prey
                if new_dist < current_dist:
                    score += 40  # High priority for hunting
                    if self.state == "hunting":
                        score += 20  # Extra bonus when actively hunting
        
        # Look for threats (other predators)
        for obj_info in analysis['visible_objects']:
            obj = obj_info['object']
            if isinstance(obj, Predator) and obj != self and obj.alive:
                if obj.strength > self.strength:  # Stronger predator
                    obj_x, obj_y = obj_info['position']
                    current_dist = abs(obj_x - self.x) + abs(obj_y - self.y)
                    new_dist = abs(obj_x - new_x) + abs(obj_y - new_y)
                    
                    # Penalty for moves closer to stronger predators
                    if new_dist < current_dist:
                        score -= 30
                        if self.hp < self.max_hp * 0.5:
                            score -= 20  # Extra penalty when wounded
        
        return max(0, score)
    
    def _hunt_prey(self, board):
        """Hunt for prey within vision range using centralized movement."""
        analysis = self.get_movement_analysis(board)
        
        # Check if any prey is adjacent for attack
        for obj_info in analysis['visible_objects']:
            obj = obj_info['object']
            if isinstance(obj, (Grazer, Scavenger)) and obj.alive:
                if obj_info['distance'] == 1:  # Adjacent
                    energy_before_attack = self.energy
                    self.attack(obj)
                    if self.energy < energy_before_attack:
                        self.state = "combat"
                        self.gain_experience("combat")
                        if not obj.alive:
                            self.gain_experience("hunting")
                            self.eat(obj)
                    return
        
        # No adjacent prey, select best move
        best_move = self.select_best_move(analysis)
        if best_move:
            dx, dy = best_move['direction']
            if self.move(dx, dy, board):
                self.energy -= self.energy_cost_move_hunt - self.energy_cost_move  # Adjust for hunt cost
                self.gain_experience("hunting", 0.5)
        else:
            # No good moves, maybe explore
            explore_move = self._get_exploration_move()
            if explore_move:
                dx, dy = explore_move
                if self.move(dx, dy, board):
                    self.energy -= self.energy_cost_move_hunt - self.energy_cost_move

    def _find_closest_food(self, board):
        """Find and move toward the closest food source using centralized movement."""
        analysis = self.get_movement_analysis(board)
        
        # Check if any food is adjacent
        for obj_info in analysis['visible_objects']:
            if obj_info['type'] == 'corpse' and obj_info['distance'] == 1:
                obj = obj_info['object']
                if hasattr(obj, 'decay_stage') and obj.decay_stage < 3:
                    self.eat(obj)
                    return
        
        # Use movement analysis to find best move toward food
        best_move = self.select_best_move(analysis)
        if best_move:
            dx, dy = best_move['direction']
            self.move(dx, dy, board)
        else:
            # No good moves, explore
            explore_move = self._get_exploration_move()
            if explore_move:
                dx, dy = explore_move
                self.move(dx, dy, board)

    def _flee_from_threats(self, board):
        """Predator flees from stronger Predators using centralized movement."""
        # The scoring system already handles fleeing, just select best move
        analysis = self.get_movement_analysis(board)
        best_move = self.select_best_move(analysis)
        
        if best_move:
            dx, dy = best_move['direction']
            if self.move(dx, dy, board):
                self.energy -= self.energy_cost_move_flee - self.energy_cost_move
                self.gain_experience("fleeing")

class Scavenger(Unit):
    """
    A scavenger unit that specializes in finding and consuming dead units.
    Scavengers have enhanced vision and can detect dead units from farther away.
    They're not as strong as predators but are more efficient at extracting energy from corpses.
    """
    def __init__(self, x, y, hp=None, config=None, board=None):
        super().__init__(x, y, unit_type="scavenger", hp=hp, energy=110, strength=8, speed=1, vision=8, config=config, board=board)
        if self.config:
            self.energy_cost_move_scavenge = self.config.get("units", "energy_consumption.move_graze")
            self.energy_cost_move_flee = self.config.get("units", "energy_consumption.move_flee")

        if not hasattr(self, 'energy_cost_move_scavenge') or self.energy_cost_move_scavenge is None:
            self.energy_cost_move_scavenge = self.energy_cost_move
        if not hasattr(self, 'energy_cost_move_flee') or self.energy_cost_move_flee is None:
            self.energy_cost_move_flee = self.energy_cost_move + 1
            
    def _calculate_move_score(self, dx, dy, new_x, new_y, analysis) -> float:
        """Override base scoring to prioritize finding corpses and avoiding predators."""
        # Start with base scoring
        score = super()._calculate_move_score(dx, dy, new_x, new_y, analysis)
        
        # Look for corpses
        for obj_info in analysis['visible_objects']:
            if obj_info['type'] == 'corpse':
                obj = obj_info['object']
                if hasattr(obj, 'decay_stage') and obj.decay_stage < 4:
                    obj_x, obj_y = obj_info['position']
                    current_dist = abs(obj_x - self.x) + abs(obj_y - self.y)
                    new_dist = abs(obj_x - new_x) + abs(obj_y - new_y)
                    
                    # Bonus for moves closer to corpses
                    if new_dist < current_dist:
                        score += 35
                        if self.state == "scavenging":
                            score += 15
                        # Prioritize fresher corpses
                        if obj.decay_stage < 2:
                            score += 10
        
        # Avoid predators
        for obj_info in analysis['visible_objects']:
            obj = obj_info['object']
            if isinstance(obj, Predator) and obj.alive:
                obj_x, obj_y = obj_info['position']
                current_dist = abs(obj_x - self.x) + abs(obj_y - self.y)
                new_dist = abs(obj_x - new_x) + abs(obj_y - new_y)
                
                # Bonus for moves away from predators
                if new_dist > current_dist:
                    score += 30
                elif new_dist < current_dist:
                    score -= 40  # Penalty for moving toward predators
        
        # Also consider plants as backup food
        if self.energy < self.max_energy * 0.3:
            for obj_info in analysis['visible_objects']:
                if obj_info['type'] == 'plant':
                    obj_x, obj_y = obj_info['position']
                    current_dist = abs(obj_x - self.x) + abs(obj_y - self.y)
                    new_dist = abs(obj_x - new_x) + abs(obj_y - new_y)
                    
                    if new_dist < current_dist:
                        score += 10  # Small bonus for backup food
        
        return max(0, score)

    def update(self, board):
        super().update(board)
        if not self.alive or self.state == "resting": return

        if self.energy < self.max_energy * 0.3:
            self.state = "hungry"
            self._find_food(board)
        elif self.hp < self.max_hp * 0.3:
            self.state = "fleeing"
            self._flee_from_threats(board)
        else:
            self.state = "scavenging"
            self._search_for_corpses(board)

    def _search_for_corpses(self, board):
        """Search for dead units to consume using centralized movement."""
        analysis = self.get_movement_analysis(board)
        
        # Check if any corpse is adjacent
        for obj_info in analysis['visible_objects']:
            if obj_info['type'] == 'corpse' and obj_info['distance'] == 1:
                obj = obj_info['object']
                if hasattr(obj, 'decay_stage') and obj.decay_stage < 4:
                    self.eat(obj)
                    return
        
        # Use movement analysis to find best move
        best_move = self.select_best_move(analysis)
        if best_move:
            dx, dy = best_move['direction']
            if self.move(dx, dy, board):
                self.energy -= self.energy_cost_move_scavenge - self.energy_cost_move
                self.gain_experience("hunting", 0.2)

    def _find_food(self, board):
        """Find any food source when hungry using centralized movement."""
        analysis = self.get_movement_analysis(board)
        
        # Check if any food is adjacent
        for obj_info in analysis['visible_objects']:
            if obj_info['distance'] == 1:
                if obj_info['type'] == 'corpse':
                    obj = obj_info['object']
                    if hasattr(obj, 'decay_stage') and obj.decay_stage < 4:
                        self.eat(obj)
                        return
                elif obj_info['type'] == 'plant':
                    self.eat(obj_info['object'])
                    return
        
        # Use movement analysis to find best move toward food
        best_move = self.select_best_move(analysis)
        if best_move:
            dx, dy = best_move['direction']
            if self.move(dx, dy, board):
                self.energy -= self.energy_cost_move_scavenge - self.energy_cost_move

    def _flee_from_threats(self, board):
        """Scavenger flees from Predators using centralized movement."""
        # The scoring system already handles fleeing
        analysis = self.get_movement_analysis(board)
        best_move = self.select_best_move(analysis)
        
        if best_move:
            dx, dy = best_move['direction']
            if self.move(dx, dy, board):
                self.energy -= self.energy_cost_move_flee - self.energy_cost_move
                self.gain_experience("fleeing")

class Grazer(Unit):
    """
    A grazer unit that primarily consumes plants.
    Grazers are peaceful units with high energy capacity but low strength.
    They avoid combat and focus on finding and consuming plants.
    """
    def __init__(self, x, y, hp=None, config=None, board=None):
        super().__init__(x, y, unit_type="grazer", hp=hp, energy=130, strength=5, speed=1, vision=5, config=config, board=board)
        if self.config:
            self.energy_cost_move_graze = self.config.get("units", "energy_consumption.move_graze")
            self.energy_cost_move_flee = self.config.get("units", "energy_consumption.move_flee")

        if not hasattr(self, 'energy_cost_move_graze') or self.energy_cost_move_graze is None:
            self.energy_cost_move_graze = self.energy_cost_move
        if not hasattr(self, 'energy_cost_move_flee') or self.energy_cost_move_flee is None:
            self.energy_cost_move_flee = self.energy_cost_move + 1 # Default flee cost
            
    def _calculate_move_score(self, dx, dy, new_x, new_y, analysis) -> float:
        """Override base scoring to prioritize fleeing from predators and finding plants."""
        # Start with base scoring
        score = super()._calculate_move_score(dx, dy, new_x, new_y, analysis)
        
        # Strong fleeing behavior from predators
        for obj_info in analysis['visible_objects']:
            obj = obj_info['object']
            if isinstance(obj, Predator) and obj.alive:
                obj_x, obj_y = obj_info['position']
                current_dist = abs(obj_x - self.x) + abs(obj_y - self.y)
                new_dist = abs(obj_x - new_x) + abs(obj_y - new_y)
                
                # Strong bonus for moves that increase distance from predators
                if new_dist > current_dist:
                    score += 50  # High priority for fleeing
                    if self.state == "fleeing":
                        score += 30  # Extra bonus when actively fleeing
                elif new_dist < current_dist:
                    score -= 60  # Heavy penalty for moving toward predators
        
        # Look for plants to eat
        for obj_info in analysis['visible_objects']:
            if obj_info['type'] == 'plant':
                obj_x, obj_y = obj_info['position']
                current_dist = abs(obj_x - self.x) + abs(obj_y - self.y)
                new_dist = abs(obj_x - new_x) + abs(obj_y - new_y)
                
                # Bonus for moves closer to plants
                if new_dist < current_dist:
                    score += 25
                    if self.energy < self.max_energy * 0.5:
                        score += 15  # Extra bonus when hungry
        
        return max(0, score)
            
    def update(self, board):
        super().update(board)
        if not self.alive:
            return
        
        visible_units_data = self.look(board) # Use self.look()
        threats = [item[0] for item in visible_units_data if isinstance(item[0], Predator) and item[0].alive]
        
        if threats:
            self.state = "fleeing"
            self._flee_from_threats(board, threats) # Pass threats to avoid re-calculating
        elif self.energy < self.max_energy * 0.4: # Adjusted threshold for consistency
            self.state = "hungry"
            self._find_food(board)
        else:
            self.state = "grazing" # Default state if not fleeing or hungry
            self._graze(board)

    def _graze(self, board):
        """Wander to find and consume plants using centralized movement."""
        analysis = self.get_movement_analysis(board)
        
        # Check if any plant is adjacent
        for obj_info in analysis['visible_objects']:
            if obj_info['type'] == 'plant' and obj_info['distance'] == 1:
                plant = obj_info['object']
                if self.eat(plant):
                    self.gain_experience("feeding")
                    return
        
        # Use movement analysis to find best move
        best_move = self.select_best_move(analysis)
        if best_move:
            dx, dy = best_move['direction']
            if self.move(dx, dy, board):
                self.energy -= self.energy_cost_move_graze - self.energy_cost_move
                self.gain_experience("feeding", 0.2)

    def _find_food(self, board):
        """Find closest plant when hungry using centralized movement."""
        # Same as _graze but with urgency
        self._graze(board)

    def _flee_from_threats(self, board, threats):
        """Move away from predators using centralized movement."""
        # The scoring system already handles fleeing
        analysis = self.get_movement_analysis(board)
        best_move = self.select_best_move(analysis)
        
        if best_move:
            dx, dy = best_move['direction']
            if self.move(dx, dy, board):
                self.energy -= self.energy_cost_move_flee - self.energy_cost_move
                self.gain_experience("fleeing")

# Dictionary mapping unit type names to their classes
UNIT_TYPES = {
    "predator": Predator,
    "scavenger": Scavenger,
    "grazer": Grazer
}
