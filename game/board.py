"""
Board module that implements the 2D game board for the ecosystem simulation.

This module provides the core functionality for the game board where units move around,
interact with each other, and interact with plants and obstacles.
"""

from enum import Enum
import random
from typing import List, Tuple, Optional, Set, Dict
from dataclasses import dataclass

class MovementType(Enum):
    """Defines allowed movement directions on the board."""
    CARDINAL = 4  # North, South, East, West
    DIAGONAL = 8  # Cardinal + Diagonals

@dataclass(frozen=True)  # Makes the class immutable and hashable
class Position:
    """Represents a position on the board."""
    x: int
    y: int

    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def __hash__(self):
        return hash((self.x, self.y))
class Board:
    """
    Represents the 2D game board where all game elements are placed and interact.
    
    The board is implemented as a 2D grid (matrix) that can contain units, plants,
    and obstacles. It manages movement, collision detection, and visibility.
    """
    
    def __init__(self, width: int, height: int, movement_type: MovementType = MovementType.CARDINAL):
        """
        Initialize a new game board with the specified dimensions.
        
        Args:
            width (int): The width of the board.
            height (int): The height of the board.
            movement_type (MovementType): Type of movement allowed (4 or 8 directions).
        """
        self.width = width
        self.height = height
        self.grid = [[None for _ in range(width)] for _ in range(height)]
        self.movement_type = movement_type
        self._object_positions: Dict[object, Position] = {}  # Track object positions
        self.random = random.Random()  # Create a dedicated random number generator
        
        # Define movement vectors based on movement type
        self.movement_vectors = [
            (0, 1),   # North
            (0, -1),  # South
            (1, 0),   # East
            (-1, 0),  # West
        ]
        if movement_type == MovementType.DIAGONAL:
            self.movement_vectors.extend([
                (1, 1),    # Northeast
                (-1, 1),   # Northwest
                (1, -1),   # Southeast
                (-1, -1),  # Southwest
            ])
    def is_valid_position(self, x, y):
        """
        Check if the given coordinates are within the board boundaries.
        
        Args:
            x (int): The x-coordinate to check.
            y (int): The y-coordinate to check.
            
        Returns:
            bool: True if the position is valid, False otherwise.
        """
        return 0 <= x < self.width and 0 <= y < self.height
    

    def get_object(self, x: int, y: int) -> Optional[object]:
        """
        Get the object at the specified position.
        
        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            
        Returns:
            Optional[object]: The object at the position, or None if empty.
        """
        if not self.is_valid_position(x, y):
            return None
        return self.grid[y][x]

    def place_object(self, obj: object, x: int, y: int) -> bool:
        """
        Place an object on the board at the specified position.
        
        Args:
            obj: The object to place (unit, plant, or obstacle).
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            
        Returns:
            bool: True if the object was placed successfully, False otherwise.
        """
        if not self.is_valid_position(x, y) or self.grid[y][x] is not None:
            return False
        
        self.grid[y][x] = obj
        self._object_positions[obj] = Position(x, y)
        return True
    
    def get_units_in_range(self, x: int, y: int, range_: int) -> List[object]:
        """
        Get all units within a specified range of a position.
        
        Args:
            x (int): Center x-coordinate
            y (int): Center y-coordinate
            range_ (int): Vision range to check
            
        Returns:
            List[object]: List of units found within range
        """
        units = []
        for dy in range(-range_, range_ + 1):
            for dx in range(-range_, range_ + 1):
                check_x, check_y = x + dx, y + dy
                if self.is_valid_position(check_x, check_y):
                    obj = self.get_object(check_x, check_y)
                    if obj is not None and hasattr(obj, 'alive'):  # Check if object is a unit
                        units.append(obj)
        return units

    def remove_object(self, x: int, y: int) -> Optional[object]:
        """
        Remove an object from the specified position.
        
        Args:
            x (int): The x-coordinate.
            y (int): The y-coordinate.
            
        Returns:
            The object that was removed, or None if there was no object.
        """
        if not self.is_valid_position(x, y):
            return None
        
        obj = self.grid[y][x]
        if obj is not None:
            self.grid[y][x] = None
            del self._object_positions[obj]
        return obj

    def get_object_position(self, obj: object) -> Optional[Position]:
        """
        Get the current position of an object on the board.
        
        Args:
            obj: The object to locate.
            
        Returns:
            Position: The object's position, or None if not found.
        """
        return self._object_positions.get(obj)

    def calculate_field_of_view(self, x: int, y: int, vision_range: int) -> Set[Position]:
        """
        Calculate visible positions from a given point within vision range.
        Uses ray casting for line of sight calculations.
        
        Args:
            x (int): The x-coordinate of the viewing position.
            y (int): The y-coordinate of the viewing position.
            vision_range (int): Maximum distance that can be seen.
            
        Returns:
            Set[Position]: Set of visible positions.
        """
        if not self.is_valid_position(x, y):
            return set()

        visible = set()
        center = Position(x, y)
        
        # Check all positions within the vision range square
        for dy in range(-vision_range, vision_range + 1):
            for dx in range(-vision_range, vision_range + 1):
                target_x, target_y = x + dx, y + dy
                
                # Skip if position is out of bounds or beyond vision range
                if not self.is_valid_position(target_x, target_y):
                    continue
                    
                target = Position(target_x, target_y)
                if center.distance_to(target) > vision_range:
                    continue
                
                # Check if line of sight is clear
                if self._has_line_of_sight(center, target):
                    visible.add(target)
        
        return visible

    def _has_line_of_sight(self, start: Position, end: Position) -> bool:
        """
        Check if there is a clear line of sight between two positions.
        Uses Bresenham's line algorithm for ray casting.
        
        Args:
            start (Position): Starting position.
            end (Position): Target position.
            
        Returns:
            bool: True if there is clear line of sight.
        """
        x0, y0 = start.x, start.y
        x1, y1 = end.x, end.y
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        n = 1 + dx + dy
        x_inc = 1 if x1 > x0 else -1
        y_inc = 1 if y1 > y0 else -1
        error = dx - dy
        dx *= 2
        dy *= 2

        while n > 0:
            # Check intermediate positions for obstacles
            if x != x0 or y != y0:  # Don't check start position
                if x == x1 and y == y1:  # Allow seeing the end position
                    return True
                obj = self.grid[y][x]
                if obj is not None and hasattr(obj, 'blocks_vision') and obj.blocks_vision:
                    return False
            
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx
            n -= 1
            
        return True
    
    def move_object(self, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
        """
        Move an object from one position to another.
        
        Args:
            from_x (int): The source x-coordinate.
            from_y (int): The source y-coordinate.
            to_x (int): The destination x-coordinate.
            to_y (int): The destination y-coordinate.
            
        Returns:
            bool: True if the move was successful, False otherwise.
        """
        if not self.is_valid_position(from_x, from_y) or not self.is_valid_position(to_x, to_y):
            return False
        
        obj = self.grid[from_y][from_x]
        if obj is None or self.grid[to_y][to_x] is not None:
            return False
            
        # Movement validation is now handled by the unit's movement system
        # The board just checks if the destination is valid and empty
        
        self.grid[to_y][to_x] = obj
        self.grid[from_y][from_x] = None
        self._object_positions[obj] = Position(to_x, to_y)
        
        # Update the object's own coordinates if it has them
        if hasattr(obj, 'x') and hasattr(obj, 'y'):
            obj.x = to_x
            obj.y = to_y
        
        return True

    def get_available_moves(self, x: int, y: int) -> List[Position]:
        """
        Get all valid moves from a given position based on movement type.
        
        Args:
            x (int): The x-coordinate of the starting position.
            y (int): The y-coordinate of the starting position.
            
        Returns:
            List[Position]: List of valid positions that can be moved to.
        """
        if not self.is_valid_position(x, y) or self.grid[y][x] is None:
            return []
            
        valid_moves = []
        for dx, dy in self.movement_vectors:
            new_x, new_y = x + dx, y + dy
            if self.is_valid_position(new_x, new_y) and self.grid[new_y][new_x] is None:
                valid_moves.append(Position(new_x, new_y))
        return valid_moves

    def move_unit(self, unit: object, dx: int, dy: int) -> bool:
        """
        Move a unit by a relative offset from its current position.
        
        Args:
            unit: The unit to move
            dx (int): The x-direction offset (-1, 0, or 1)
            dy (int): The y-direction offset (-1, 0, or 1)
            
        Returns:
            bool: True if the move was successful, False otherwise.
        """
        current_pos = self.get_object_position(unit)
        print(f"Moving unit from position: {current_pos}")
        if current_pos is None:
            print("Unit not found on board")
            return False
            
        target_x = current_pos.x + dx
        target_y = current_pos.y + dy
        print(f"Attempting to move to: ({target_x}, {target_y})")
        
        success = self.move_object(current_pos.x, current_pos.y, target_x, target_y)
        if success:
            print(f"Move successful, new position: {self.get_object_position(unit)}")
        else:
            print("Move failed")
        return success

    def get_plants_in_range(self, x: int, y: int, range_: int) -> List[object]:
        """
        Get all plants within a specified range of a position.
        
        Args:
            x (int): Center x-coordinate
            y (int): Center y-coordinate
            range_ (int): Range to check
            
        Returns:
            List[object]: List of plants found within range
        """
        plants = []
        for dy in range(-range_, range_ + 1):
            for dx in range(-range_, range_ + 1):
                check_x, check_y = x + dx, y + dy
                if self.is_valid_position(check_x, check_y):
                    obj = self.get_object(check_x, check_y)
                    if obj is not None and hasattr(obj, 'growth_rate'):  # Check if object is a plant
                        plants.append(obj)
        return plants

    def place_random_plants(self, num_plants: int, plant_factory) -> List[Position]:
        """
        Place a specified number of plants randomly on empty board positions.
        
        Args:
            num_plants (int): Number of plants to place.
            plant_factory: Function that creates a new plant instance.
            
        Returns:
            List[Position]: Positions where plants were placed.
        """
        empty_positions = [
            Position(x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.grid[y][x] is None
        ]
        
        if len(empty_positions) < num_plants:
            num_plants = len(empty_positions)
            
        selected_positions = random.sample(empty_positions, num_plants)
        placed_positions = []
        
        for pos in selected_positions:
            plant = plant_factory()
            if self.place_object(plant, pos.x, pos.y):
                placed_positions.append(pos)
                
        return placed_positions
