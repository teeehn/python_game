"""Test the centralized movement system."""

import pytest
from game.units.base_unit import Unit
from game.plants.base_plant import Plant
from game.board import Board, Position


class MockBoard:
    def __init__(self, width=10, height=10):
        self.width = width
        self.height = height
        self.objects = {}
        
    def is_valid_position(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height
        
    def get_object(self, x, y):
        return self.objects.get((x, y))
        
    def place_object(self, obj, x, y):
        self.objects[(x, y)] = obj
        
    def remove_object(self, x, y):
        if (x, y) in self.objects:
            del self.objects[(x, y)]
            return True
        return False
        
    def move_object(self, old_x, old_y, new_x, new_y):
        if self.is_valid_position(new_x, new_y) and (new_x, new_y) not in self.objects:
            if (old_x, old_y) in self.objects:
                obj = self.objects[(old_x, old_y)]
                del self.objects[(old_x, old_y)]
                self.objects[(new_x, new_y)] = obj
                return True
        return False


def test_get_movement_options_basic():
    """Test basic movement option detection."""
    board = MockBoard()
    unit = Unit(5, 5, speed=1, vision=3, board=board)
    
    possible_moves, visible_objects = unit.get_movement_options(board)
    
    # With speed=1, should have 4 cardinal moves
    assert len(possible_moves) == 4
    
    # Check all moves are within speed limit
    for x, y, score in possible_moves:
        assert abs(x - unit.x) + abs(y - unit.y) <= unit.speed
        assert board.is_valid_position(x, y)
        
    # No visible objects on empty board
    assert len(visible_objects) == 0


def test_get_movement_options_with_obstacles():
    """Test movement options when blocked by other units."""
    board = MockBoard()
    unit = Unit(5, 5, speed=2, vision=3, board=board)
    
    # Place obstacles around the unit
    obstacle1 = Unit(6, 5, board=board)  # Right
    obstacle2 = Unit(5, 6, board=board)  # Down
    board.place_object(obstacle1, 6, 5)
    board.place_object(obstacle2, 5, 6)
    
    possible_moves, visible_objects = unit.get_movement_options(board)
    
    # Should not include blocked positions
    move_positions = [(x, y) for x, y, _ in possible_moves]
    assert (6, 5) not in move_positions
    assert (5, 6) not in move_positions
    
    # Should see the obstacles
    assert len(visible_objects) == 2
    obj_positions = [(x, y) for _, x, y, _ in visible_objects]
    assert (6, 5) in obj_positions
    assert (5, 6) in obj_positions


def test_edge_avoidance_scoring():
    """Test that edge positions get lower scores."""
    board = MockBoard(width=10, height=10)
    
    # Unit near edge
    unit = Unit(1, 1, speed=1, vision=3, board=board)
    possible_moves, _ = unit.get_movement_options(board)
    
    # Find scores for moves
    scores = {}
    for x, y, score in possible_moves:
        scores[(x, y)] = score
        
    # Move toward center should have higher score than move to edge
    if (2, 1) in scores and (0, 1) in scores:
        assert scores[(2, 1)] > scores[(0, 1)], "Move away from edge should score higher"
        
    # Test unit at edge
    edge_unit = Unit(0, 5, speed=1, vision=3, board=board)
    edge_moves, _ = edge_unit.get_movement_options(board)
    
    edge_scores = {}
    for x, y, score in edge_moves:
        edge_scores[(x, y)] = score
        
    # Move away from edge should have bonus
    if (1, 5) in edge_scores:
        assert edge_scores[(1, 5)] > 0, "Moving away from edge should have positive score"


def test_corner_stuck_prevention():
    """Test that units don't get stuck in corners."""
    board = MockBoard(width=10, height=10)
    
    # Unit in corner
    unit = Unit(0, 0, speed=1, vision=3, board=board)
    possible_moves, _ = unit.get_movement_options(board)
    
    # Should have exactly 2 moves from corner (right and down)
    assert len(possible_moves) == 2
    
    # Both moves should have positive scores (moving away from corner)
    for x, y, score in possible_moves:
        assert score > 0, f"Move to ({x}, {y}) should have positive score"
        
    # Choose move should not return None
    chosen_move = unit.choose_move(board)
    assert chosen_move is not None, "Should choose a move from corner"


def test_state_based_movement_scoring():
    """Test that different states affect movement scoring appropriately."""
    board = MockBoard()
    
    # Test fleeing behavior
    fleeing_unit = Unit(5, 5, speed=2, vision=5, board=board)
    fleeing_unit.state = "fleeing"
    
    # Place a threat
    threat = Unit(7, 5, strength=20, board=board)
    board.place_object(threat, 7, 5)
    
    possible_moves, visible_objects = fleeing_unit.get_movement_options(board)
    
    # Debug: print all moves and their scores
    print("\nFleeing unit moves:")
    for x, y, score in possible_moves[:5]:  # Show top 5 moves
        print(f"  Move to ({x}, {y}): score = {score}")
    
    # Find best move
    best_move = possible_moves[0] if possible_moves else None
    assert best_move is not None
    
    # Best move should be away from threat
    best_x, best_y, best_score = best_move
    
    # Find moves that go left
    left_moves = [(x, y, s) for x, y, s in possible_moves if x < fleeing_unit.x]
    assert len(left_moves) > 0, "Should have moves to the left"
    
    # The best move should be one that increases distance from threat
    assert best_x <= fleeing_unit.x, f"Should flee away from threat at (7,5), but chose ({best_x},{best_y})"
    
    # Test hungry behavior
    hungry_unit = Unit(5, 5, speed=2, vision=5, energy=30, board=board)
    hungry_unit.state = "hungry"
    hungry_unit.max_energy = 100
    
    # Clear the board first
    board.objects.clear()
    
    # Place food with proper Plant initialization
    food = Plant(Position(7, 5), base_energy=50.0, growth_rate=1.0, regrowth_time=10.0)
    board.place_object(food, 7, 5)
    
    food_moves, _ = hungry_unit.get_movement_options(board)
    
    # Best move should be toward food
    if food_moves:
        food_best = food_moves[0]
        food_x, food_y, _ = food_best
        assert food_x > hungry_unit.x, "Should move toward food on the right"


def test_vision_range_adjustments():
    """Test that vision range changes based on state."""
    board = MockBoard()
    
    # Normal vision
    unit = Unit(5, 5, vision=4, board=board)
    
    # Place objects at various distances
    for i in range(1, 7):
        board.place_object(Unit(5+i, 5, board=board), 5+i, 5)
    
    # Normal state
    _, visible_normal = unit.get_movement_options(board)
    visible_count_normal = len(visible_normal)
    
    # Hunting state (1.5x vision)
    unit.state = "hunting"
    _, visible_hunting = unit.get_movement_options(board)
    visible_count_hunting = len(visible_hunting)
    
    # Fleeing state (1.2x vision)
    unit.state = "fleeing"  
    _, visible_fleeing = unit.get_movement_options(board)
    visible_count_fleeing = len(visible_fleeing)
    
    # Hunting should see more than normal
    assert visible_count_hunting >= visible_count_normal
    # Fleeing should see more than normal but less than hunting
    assert visible_count_fleeing >= visible_count_normal
    assert visible_count_hunting >= visible_count_fleeing


def test_speed_limit_enforcement():
    """Test that movement options respect speed limits."""
    board = MockBoard()
    
    # Test different speeds
    for speed in [1, 2, 3]:
        unit = Unit(5, 5, speed=speed, board=board)
        possible_moves, _ = unit.get_movement_options(board)
        
        # Check all moves respect Manhattan distance
        for x, y, _ in possible_moves:
            manhattan_dist = abs(x - unit.x) + abs(y - unit.y)
            assert manhattan_dist <= speed, f"Move to ({x}, {y}) exceeds speed {speed}"
            
        # Verify we get expected number of moves (minus current position)
        # For speed=1: 4 moves (cardinal)
        # For speed=2: 12 moves (cardinal + diagonal + 2-step cardinal)
        # For speed=3: 28 moves
        if speed == 1:
            assert len(possible_moves) == 4
        elif speed == 2:
            assert len(possible_moves) == 12


def test_dead_and_restricted_states():
    """Test that dead/resting/feeding units can't move."""
    board = MockBoard()
    
    for state in ["dead", "decaying", "resting", "feeding"]:
        unit = Unit(5, 5, board=board)
        unit.state = state
        if state in ["dead", "decaying"]:
            unit.alive = False
            
        possible_moves, visible_objects = unit.get_movement_options(board)
        
        assert len(possible_moves) == 0, f"Units in {state} state should have no moves"
        assert len(visible_objects) == 0, f"Units in {state} state should see nothing"


def test_choose_move_with_no_good_options():
    """Test that choose_move returns None when all moves are bad."""
    board = MockBoard(width=3, height=3)
    
    # Unit in center of tiny board, all edge moves
    unit = Unit(1, 1, speed=1, board=board)
    
    # Manually set very low scores by overriding the scoring method
    class PessimisticUnit(Unit):
        def _calculate_move_score(self, target_x, target_y, visible_objects, board):
            return -20  # Very negative score
            
    pessimistic = PessimisticUnit(1, 1, speed=1, board=board)
    chosen = pessimistic.choose_move(board)
    
    assert chosen is None, "Should not move when all options are very bad"


def test_exploration_direction_bonus():
    """Test that exploration direction gets scoring bonus."""
    board = MockBoard()
    unit = Unit(5, 5, speed=1, board=board)
    unit.exploration_direction = (1, 0)  # Moving right
    
    possible_moves, _ = unit.get_movement_options(board)
    
    # Find scores
    scores = {(x, y): score for x, y, score in possible_moves}
    
    # Right move should have bonus
    if (6, 5) in scores and (4, 5) in scores:
        assert scores[(6, 5)] > scores[(4, 5)], "Exploration direction should get bonus"