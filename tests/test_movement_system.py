"""
Test suite for the centralized movement system with vision and edge detection.
"""

import pytest
from game.units.base_unit import Unit
from game.units.unit_types import Predator, Grazer, Scavenger
from game.board import Board, MovementType, Position
from game.plants.plant_types import BasicPlant
from game.config import Config

@pytest.fixture
def board():
    """Create a standard board for testing."""
    return Board(10, 10, MovementType.CARDINAL)

@pytest.fixture
def small_board():
    """Create a small board for edge testing."""
    return Board(3, 3, MovementType.CARDINAL)

@pytest.fixture
def config():
    """Create a config object for testing."""
    return Config('tests/test_config.json')

class TestMovementAnalysis:
    """Test the get_movement_analysis method that provides vision and movement options."""
    
    def test_basic_movement_analysis(self, board):
        """Test basic movement analysis returns valid moves and visible objects."""
        unit = Unit(5, 5, hp=100, energy=100, vision=3, board=board)
        board.place_object(unit, 5, 5)
        
        analysis = unit.get_movement_analysis(board)
        
        assert 'possible_moves' in analysis
        assert 'visible_objects' in analysis
        assert 'board_edges' in analysis
        
        # Should have 4 possible moves (cardinal directions)
        assert len(analysis['possible_moves']) == 4
        
        # Each move should have position and score
        for move in analysis['possible_moves']:
            assert 'position' in move
            assert 'score' in move
            assert 'direction' in move
            assert move['score'] >= 0
    
    def test_edge_detection(self, small_board):
        """Test that units detect board edges correctly."""
        # Unit at top-left corner
        unit = Unit(0, 0, hp=100, energy=100, vision=2, board=small_board)
        small_board.place_object(unit, 0, 0)
        
        analysis = unit.get_movement_analysis(small_board)
        
        # Should only have 2 possible moves from corner
        assert len(analysis['possible_moves']) == 2
        
        # Check edge detection
        edges = analysis['board_edges']
        assert edges['north'] == 0  # At north edge
        assert edges['west'] == 0   # At west edge
        assert edges['south'] == 2  # 2 squares from south edge
        assert edges['east'] == 2   # 2 squares from east edge
    
    def test_blocked_movement(self, board):
        """Test movement analysis with blocked positions."""
        unit1 = Unit(5, 5, hp=100, energy=100, vision=3, board=board)
        unit2 = Unit(5, 6, hp=100, energy=100, board=board)  # Block south
        unit3 = Unit(6, 5, hp=100, energy=100, board=board)  # Block east
        
        board.place_object(unit1, 5, 5)
        board.place_object(unit2, 5, 6)
        board.place_object(unit3, 6, 5)
        
        analysis = unit1.get_movement_analysis(board)
        
        # Should only have 2 unblocked moves
        assert len(analysis['possible_moves']) == 2
        
        # Verify the blocked directions are not in possible moves
        move_positions = {(m['position'][0], m['position'][1]) for m in analysis['possible_moves']}
        assert (5, 6) not in move_positions  # South blocked
        assert (6, 5) not in move_positions  # East blocked
    
    def test_vision_range(self, board):
        """Test that vision correctly identifies objects within range."""
        unit = Unit(5, 5, hp=100, energy=100, vision=3, board=board)
        board.place_object(unit, 5, 5)
        
        # Place objects at various distances
        near_unit = Unit(6, 5, hp=100, energy=100, board=board)  # Distance 1
        mid_unit = Unit(7, 5, hp=100, energy=100, board=board)   # Distance 2
        far_unit = Unit(8, 5, hp=100, energy=100, board=board)   # Distance 3
        out_unit = Unit(9, 5, hp=100, energy=100, board=board)   # Distance 4 (out of range)
        
        board.place_object(near_unit, 6, 5)
        board.place_object(mid_unit, 7, 5)
        board.place_object(far_unit, 8, 5)
        board.place_object(out_unit, 9, 5)
        
        analysis = unit.get_movement_analysis(board)
        visible_objects = analysis['visible_objects']
        
        # Should see 3 units (not the out of range one)
        assert len(visible_objects) == 3
        
        # Check each visible object has required info
        for obj_info in visible_objects:
            assert 'object' in obj_info
            assert 'position' in obj_info
            assert 'distance' in obj_info
            assert 'type' in obj_info
        
        # Verify distances
        distances = {obj['distance'] for obj in visible_objects}
        assert distances == {1, 2, 3}
    
    def test_plant_detection(self, board):
        """Test that plants are correctly identified in vision."""
        unit = Unit(5, 5, hp=100, energy=100, vision=2, board=board)
        board.place_object(unit, 5, 5)
        
        # Place a plant nearby
        plant = BasicPlant(Position(6, 5))
        board.place_object(plant, 6, 5)
        
        analysis = unit.get_movement_analysis(board)
        visible_objects = analysis['visible_objects']
        
        assert len(visible_objects) == 1
        assert visible_objects[0]['type'] == 'plant'
        assert visible_objects[0]['object'] == plant


class TestMovementScoring:
    """Test the movement scoring system."""
    
    def test_default_scoring(self, board):
        """Test default movement scoring favors exploration."""
        unit = Unit(5, 5, hp=100, energy=100, vision=3, board=board)
        board.place_object(unit, 5, 5)
        
        # Set exploration direction
        unit.exploration_direction = (1, 0)  # Moving east
        
        analysis = unit.get_movement_analysis(board)
        moves = analysis['possible_moves']
        
        # Find the eastward move
        east_move = next(m for m in moves if m['direction'] == (1, 0))
        
        # Exploration direction should have higher score
        other_scores = [m['score'] for m in moves if m['direction'] != (1, 0)]
        assert all(east_move['score'] >= score for score in other_scores)
    
    def test_edge_avoidance_scoring(self, board):
        """Test that moves toward edges get lower scores."""
        # Use a larger board and position near edge for clearer test
        unit = Unit(1, 5, hp=100, energy=100, vision=2, board=board)
        board.place_object(unit, 1, 5)
        
        analysis = unit.get_movement_analysis(board)
        moves = {(m['direction'][0], m['direction'][1]): m['score'] for m in analysis['possible_moves']}
        
        # From (1, 5), west leads to edge (0, 5), east leads away
        # All edge-directed moves should have lower scores
        assert moves[(-1, 0)] < moves[(1, 0)]  # West (to edge) vs East (away)
        
        # Test corner case
        unit2 = Unit(0, 0, hp=100, energy=100, vision=2, board=board)
        board.place_object(unit2, 0, 0)
        
        analysis2 = unit2.get_movement_analysis(board)
        moves2 = {(m['direction'][0], m['direction'][1]): m['score'] for m in analysis2['possible_moves']}
        
        # From corner, moves away from edges should score higher
        # Both south and east lead away from edges
        assert all(score > 0 for score in moves2.values())


class TestSelectBestMove:
    """Test the select_best_move method."""
    
    def test_selects_highest_score(self, board):
        """Test that the method selects the move with highest score."""
        unit = Unit(5, 5, hp=100, energy=100, vision=3, board=board)
        board.place_object(unit, 5, 5)
        
        analysis = unit.get_movement_analysis(board)
        best_move = unit.select_best_move(analysis)
        
        # Should select the move with highest score
        max_score = max(m['score'] for m in analysis['possible_moves'])
        assert best_move['score'] == max_score
    
    def test_no_moves_available(self, small_board):
        """Test behavior when no moves are available."""
        unit = Unit(1, 1, hp=100, energy=100, vision=2, board=small_board)
        small_board.place_object(unit, 1, 1)
        
        # Block all moves
        blockers = [
            Unit(0, 1, hp=100, energy=100, board=small_board),
            Unit(2, 1, hp=100, energy=100, board=small_board),
            Unit(1, 0, hp=100, energy=100, board=small_board),
            Unit(1, 2, hp=100, energy=100, board=small_board),
        ]
        for i, blocker in enumerate(blockers):
            pos = [(0, 1), (2, 1), (1, 0), (1, 2)][i]
            small_board.place_object(blocker, pos[0], pos[1])
        
        analysis = unit.get_movement_analysis(small_board)
        best_move = unit.select_best_move(analysis)
        
        assert best_move is None


class TestUnitTypeScoring:
    """Test that different unit types can override scoring."""
    
    def test_predator_scoring(self, board, config):
        """Test that predators score moves toward prey higher."""
        predator = Predator(5, 5, config=config, board=board)
        prey = Grazer(7, 5, config=config, board=board)
        
        board.place_object(predator, 5, 5)
        board.place_object(prey, 7, 5)
        
        analysis = predator.get_movement_analysis(board)
        moves = {(m['direction'][0], m['direction'][1]): m for m in analysis['possible_moves']}
        
        # Move toward prey (east) should have highest score
        east_move = moves[(1, 0)]
        other_moves = [m for d, m in moves.items() if d != (1, 0)]
        
        assert all(east_move['score'] > m['score'] for m in other_moves)
    
    def test_grazer_flee_scoring(self, board, config):
        """Test that grazers score moves away from predators higher."""
        grazer = Grazer(5, 5, config=config, board=board)
        predator = Predator(3, 5, config=config, board=board)
        
        board.place_object(grazer, 5, 5)
        board.place_object(predator, 3, 5)
        
        analysis = grazer.get_movement_analysis(board)
        moves = {(m['direction'][0], m['direction'][1]): m for m in analysis['possible_moves']}
        
        # Move away from predator (east) should have highest score
        east_move = moves[(1, 0)]
        west_move = moves[(-1, 0)]
        
        assert east_move['score'] > west_move['score']


class TestEdgeCasePrevention:
    """Test that the new system prevents units from getting stuck at edges."""
    
    def test_corner_navigation(self, small_board):
        """Test that units can navigate out of corners."""
        unit = Unit(0, 0, hp=100, energy=100, vision=2, speed=1, board=small_board)
        small_board.place_object(unit, 0, 0)
        
        # Unit should be able to find valid moves
        analysis = unit.get_movement_analysis(small_board)
        assert len(analysis['possible_moves']) > 0
        
        # Best move should lead away from corner
        best_move = unit.select_best_move(analysis)
        assert best_move is not None
        
        # Execute the move
        success = unit.move(best_move['direction'][0], best_move['direction'][1], small_board)
        assert success
        
        # Unit should no longer be in corner
        assert not (unit.x == 0 and unit.y == 0)
    
    def test_edge_walking(self, board):
        """Test that units can walk along edges without getting stuck."""
        unit = Unit(0, 5, hp=100, energy=100, vision=3, speed=1, board=board)
        board.place_object(unit, 0, 5)
        
        # Simulate several moves along the edge
        for _ in range(5):
            analysis = unit.get_movement_analysis(board)
            best_move = unit.select_best_move(analysis)
            
            if best_move:
                old_x, old_y = unit.x, unit.y
                unit.move(best_move['direction'][0], best_move['direction'][1], board)
                
                # Should have moved
                assert (unit.x, unit.y) != (old_x, old_y)
                
                # Should still be on board
                assert 0 <= unit.x < board.width
                assert 0 <= unit.y < board.height
    
    def test_exploration_direction_update(self, board):
        """Test that exploration direction updates when hitting edges."""
        unit = Unit(9, 5, hp=100, energy=100, vision=3, speed=1, board=board)
        board.place_object(unit, 9, 5)
        
        # Set eastward exploration (toward edge)
        unit.exploration_direction = (1, 0)
        
        # Get movement options
        analysis = unit.get_movement_analysis(board)
        best_move = unit.select_best_move(analysis)
        
        # Should not try to move east (off board)
        assert best_move['direction'] != (1, 0)
        
        # After moving, exploration direction should update
        old_direction = unit.exploration_direction
        unit.move(best_move['direction'][0], best_move['direction'][1], board)
        
        # If we hit an edge, direction should change
        if unit.x == 9:  # Still at east edge
            assert unit.exploration_direction != old_direction