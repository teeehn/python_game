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
    
    def _calculate_move_score(self, target_x, target_y, visible_objects, board):
        """
        Override scoring for predator-specific behavior.
        Prioritizes moving toward prey and away from stronger predators.
        """
        # Start with base class scoring
        score = super()._calculate_move_score(target_x, target_y, visible_objects, board)
        
        # Additional scoring for predators
        if self.state == "hunting":
            # Look for prey
            for obj, obj_x, obj_y, _ in visible_objects:
                if hasattr(obj, 'alive') and obj.alive:
                    if isinstance(obj, (Grazer, Scavenger)):
                        # Score moves that get closer to prey
                        current_dist = abs(self.x - obj_x) + abs(self.y - obj_y)
                        new_dist = abs(target_x - obj_x) + abs(target_y - obj_y)
                        
                        if new_dist < current_dist:
                            score += 15  # Strong bonus for approaching prey
                            # Extra bonus for getting within attack range
                            if new_dist == 1:
                                score += 10
                        elif new_dist > current_dist:
                            score -= 5  # Penalty for moving away from prey
                            
                    elif isinstance(obj, Predator) and obj.strength > self.strength:
                        # Avoid stronger predators
                        current_dist = abs(self.x - obj_x) + abs(self.y - obj_y)
                        new_dist = abs(target_x - obj_x) + abs(target_y - obj_y)
                        
                        if new_dist < current_dist and new_dist < 3:
                            score -= 10  # Avoid getting too close to stronger predators
                            
        elif self.state == "hungry":
            # When hungry, look for any food including dead units
            for obj, obj_x, obj_y, _ in visible_objects:
                if (hasattr(obj, 'alive') and not obj.alive and 
                    hasattr(obj, 'decay_energy') and obj.decay_energy > 0):
                    # Score moves toward dead units
                    current_dist = abs(self.x - obj_x) + abs(self.y - obj_y)
                    new_dist = abs(target_x - obj_x) + abs(target_y - obj_y)
                    
                    if new_dist < current_dist:
                        score += 12
                    elif new_dist > current_dist:
                        score -= 3
        
        return score

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

    def _hunt_prey(self, board):
        """Hunt for prey within vision range."""
        # Get movement options and visible objects
        _, visible_objects = self.get_movement_options(board)
        
        # Find potential prey
        potential_prey = []
        for obj, x, y, dist in visible_objects:
            if hasattr(obj, 'alive') and obj.alive and isinstance(obj, (Grazer, Scavenger)):
                potential_prey.append((obj, x, y, dist))
        
        if potential_prey:
            # Find closest prey
            target_obj, target_x, target_y, _ = min(potential_prey, key=lambda p: p[3])
            
            # If adjacent, attack
            if abs(target_x - self.x) <= 1 and abs(target_y - self.y) <= 1:
                energy_before_attack = self.energy
                self.attack(target_obj)
                if self.energy < energy_before_attack:
                    self.state = "combat"
                    self.gain_experience("combat")
                    if not target_obj.alive:
                        self.gain_experience("hunting")
                        self.eat(target_obj)
            else:
                # Use centralized movement system
                chosen_move = self.choose_move(board)
                if chosen_move:
                    dx = chosen_move[0] - self.x
                    dy = chosen_move[1] - self.y
                    if self.move(dx, dy, board):
                        self.gain_experience("hunting", 0.5)
        else:
            # No prey visible, explore
            chosen_move = self.choose_move(board)
            if chosen_move:
                dx = chosen_move[0] - self.x
                dy = chosen_move[1] - self.y
                self.move(dx, dy, board)

    def _find_closest_food(self, board):
        """Find and move toward the closest food source (typically dead units for Predator)."""
        # Get movement options and visible objects
        _, visible_objects = self.get_movement_options(board)
        
        # Find food sources
        food_sources = []
        for obj, x, y, dist in visible_objects:
            if (hasattr(obj, 'alive') and not obj.alive and 
                hasattr(obj, 'decay_stage') and obj.decay_stage < 3):
                food_sources.append((obj, x, y, dist))

        if food_sources:
            # Find closest food
            target_obj, target_x, target_y, _ = min(food_sources, key=lambda f: f[3])
            
            # If adjacent, eat
            if abs(target_x - self.x) <= 1 and abs(target_y - self.y) <= 1:
                self.eat(target_obj)
            else:
                # Use centralized movement system
                chosen_move = self.choose_move(board)
                if chosen_move:
                    dx = chosen_move[0] - self.x
                    dy = chosen_move[1] - self.y
                    self.move(dx, dy, board)
        else:
            # No food visible, explore using centralized system
            chosen_move = self.choose_move(board)
            if chosen_move:
                dx = chosen_move[0] - self.x
                dy = chosen_move[1] - self.y
                self.move(dx, dy, board)

    def _flee_from_threats(self, board):
        """Predator flees from other (presumably stronger) Predators."""
        # The base class fleeing behavior handles this well
        # Just use the centralized movement system which already scores fleeing moves
        chosen_move = self.choose_move(board)
        if chosen_move:
            dx = chosen_move[0] - self.x
            dy = chosen_move[1] - self.y
            if self.move(dx, dy, board):
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
    
    def _calculate_move_score(self, target_x, target_y, visible_objects, board):
        """
        Override scoring for scavenger-specific behavior.
        Prioritizes moving toward corpses and away from predators.
        """
        # Start with base class scoring
        score = super()._calculate_move_score(target_x, target_y, visible_objects, board)
        
        # Additional scoring for scavengers
        if self.state == "scavenging":
            # Look for corpses
            for obj, obj_x, obj_y, _ in visible_objects:
                if (hasattr(obj, 'alive') and not obj.alive and 
                    hasattr(obj, 'decay_energy') and obj.decay_energy > 0):
                    # Score moves that get closer to corpses
                    current_dist = abs(self.x - obj_x) + abs(self.y - obj_y)
                    new_dist = abs(target_x - obj_x) + abs(target_y - obj_y)
                    
                    # Higher priority for fresher corpses
                    freshness_bonus = 0
                    if hasattr(obj, 'decay_stage'):
                        freshness_bonus = max(0, 4 - obj.decay_stage)
                    
                    if new_dist < current_dist:
                        score += 10 + freshness_bonus
                        # Extra bonus for getting within eating range
                        if new_dist == 1:
                            score += 5
                    elif new_dist > current_dist:
                        score -= 3
                        
        # Always avoid predators
        for obj, obj_x, obj_y, _ in visible_objects:
            if isinstance(obj, Predator) and obj.alive:
                current_dist = abs(self.x - obj_x) + abs(self.y - obj_y)
                new_dist = abs(target_x - obj_x) + abs(target_y - obj_y)
                
                if new_dist < current_dist and new_dist < 4:
                    score -= 15  # Strong penalty for approaching predators
                elif new_dist > current_dist:
                    score += 5   # Bonus for increasing distance from predators
        
        return score

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
        """Search for dead units to consume."""
        # Get movement options and visible objects
        _, visible_objects = self.get_movement_options(board)
        
        # Find corpses
        corpses = []
        for obj, x, y, dist in visible_objects:
            if (hasattr(obj, 'alive') and not obj.alive and 
                hasattr(obj, 'decay_stage') and obj.decay_stage < 4):
                corpses.append((obj, x, y, dist))
        
        if corpses:
            # Find closest corpse
            target_obj, target_x, target_y, _ = min(corpses, key=lambda c: c[3])
            
            # If adjacent, eat
            if abs(target_x - self.x) <= 1 and abs(target_y - self.y) <= 1:
                self.eat(target_obj)
            else:
                # Use centralized movement system
                chosen_move = self.choose_move(board)
                if chosen_move:
                    dx = chosen_move[0] - self.x
                    dy = chosen_move[1] - self.y
                    if self.move(dx, dy, board):
                        self.gain_experience("hunting", 0.2)
        else:
            # No corpses visible, explore
            chosen_move = self.choose_move(board)
            if chosen_move:
                dx = chosen_move[0] - self.x
                dy = chosen_move[1] - self.y
                self.move(dx, dy, board)

    def _find_food(self, board):
        """Find any food source when hungry."""
        # Get movement options and visible objects
        _, visible_objects = self.get_movement_options(board)
        
        # Find food sources
        food_sources = []
        for obj, x, y, dist in visible_objects:
            if ((hasattr(obj, 'alive') and not obj.alive and hasattr(obj, 'decay_stage')) or 
                isinstance(obj, Plant)):
                food_sources.append((obj, x, y, dist))
        
        if food_sources:
            # Find closest food
            target_obj, target_x, target_y, _ = min(food_sources, key=lambda f: f[3])
            
            # If adjacent, eat
            if abs(target_x - self.x) <= 1 and abs(target_y - self.y) <= 1:
                self.eat(target_obj)
            else:
                # Use centralized movement system
                chosen_move = self.choose_move(board)
                if chosen_move:
                    dx = chosen_move[0] - self.x
                    dy = chosen_move[1] - self.y
                    self.move(dx, dy, board)
        else:
            # No food visible, explore
            chosen_move = self.choose_move(board)
            if chosen_move:
                dx = chosen_move[0] - self.x
                dy = chosen_move[1] - self.y
                self.move(dx, dy, board)

    def _flee_from_threats(self, board):
        """Scavenger flees from Predators."""
        # Use centralized movement system which handles fleeing
        chosen_move = self.choose_move(board)
        if chosen_move:
            dx = chosen_move[0] - self.x
            dy = chosen_move[1] - self.y
            if self.move(dx, dy, board):
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
    
    def _calculate_move_score(self, target_x, target_y, visible_objects, board):
        """
        Override scoring for grazer-specific behavior.
        Prioritizes moving toward plants and strongly avoids predators.
        """
        # Start with base class scoring
        score = super()._calculate_move_score(target_x, target_y, visible_objects, board)
        
        # Additional scoring for grazers
        if self.state == "grazing" or self.state == "hungry":
            # Look for plants
            for obj, obj_x, obj_y, _ in visible_objects:
                if isinstance(obj, Plant):
                    # Score moves that get closer to plants
                    current_dist = abs(self.x - obj_x) + abs(self.y - obj_y)
                    new_dist = abs(target_x - obj_x) + abs(target_y - obj_y)
                    
                    if new_dist < current_dist:
                        score += 8
                        # Extra bonus for getting within eating range
                        if new_dist == 1:
                            score += 5
                    elif new_dist > current_dist:
                        score -= 2
        
        # Strong avoidance of predators
        for obj, obj_x, obj_y, _ in visible_objects:
            if isinstance(obj, Predator) and obj.alive:
                current_dist = abs(self.x - obj_x) + abs(self.y - obj_y)
                new_dist = abs(target_x - obj_x) + abs(target_y - obj_y)
                
                # Very strong penalty for getting close to predators
                if new_dist < current_dist:
                    score -= 20
                elif new_dist > current_dist:
                    score += 10
                    
                # Extra penalty if already too close
                if current_dist < 3:
                    if new_dist <= current_dist:
                        score -= 15
        
        return score
            
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
        """Wander to find and consume plants."""
        # Get movement options and visible objects
        _, visible_objects = self.get_movement_options(board)
        
        # Find plants
        plants = []
        for obj, x, y, dist in visible_objects:
            if isinstance(obj, Plant):
                plants.append((obj, x, y, dist))

        if plants:
            # Find closest plant
            target_obj, target_x, target_y, _ = min(plants, key=lambda p: p[3])
            
            # If adjacent, eat
            if abs(target_x - self.x) <= 1 and abs(target_y - self.y) <= 1:
                if self.eat(target_obj):
                    self.gain_experience("feeding")
            else:
                # Use centralized movement system
                chosen_move = self.choose_move(board)
                if chosen_move:
                    dx = chosen_move[0] - self.x
                    dy = chosen_move[1] - self.y
                    if self.move(dx, dy, board):
                        self.gain_experience("feeding", 0.2)
        else:
            # No plants visible, explore
            chosen_move = self.choose_move(board)
            if chosen_move:
                dx = chosen_move[0] - self.x
                dy = chosen_move[1] - self.y
                self.move(dx, dy, board)

    def _find_food(self, board):
        """Find closest plant when hungry."""
        # Get movement options and visible objects
        _, visible_objects = self.get_movement_options(board)
        
        # Find plants
        plants = []
        for obj, x, y, dist in visible_objects:
            if isinstance(obj, Plant):
                plants.append((obj, x, y, dist))
        
        if plants:
            # Find closest plant
            target_obj, target_x, target_y, _ = min(plants, key=lambda p: p[3])
            
            # If adjacent, eat
            if abs(target_x - self.x) <= 1 and abs(target_y - self.y) <= 1:
                if self.eat(target_obj):
                    self.gain_experience("feeding")
            else:
                # Use centralized movement system
                chosen_move = self.choose_move(board)
                if chosen_move:
                    dx = chosen_move[0] - self.x
                    dy = chosen_move[1] - self.y
                    self.move(dx, dy, board)
        else:
            # No plants visible, explore
            chosen_move = self.choose_move(board)
            if chosen_move:
                dx = chosen_move[0] - self.x
                dy = chosen_move[1] - self.y
                self.move(dx, dy, board)

    def _flee_from_threats(self, board, threats): # Accept threats to avoid re-calculating
        """Move away from predators."""
        # Use centralized movement system which handles fleeing
        chosen_move = self.choose_move(board)
        if chosen_move:
            dx = chosen_move[0] - self.x
            dy = chosen_move[1] - self.y
            if self.move(dx, dy, board):
                self.gain_experience("fleeing")

# Dictionary mapping unit type names to their classes
UNIT_TYPES = {
    "predator": Predator,
    "scavenger": Scavenger,
    "grazer": Grazer
}
