"""Test that units don't get stuck at board edges with the new movement system."""

import pytest
from game.units.unit_types import Predator, Scavenger, Grazer
from game.board import Board


def test_units_escape_corners():
    """Test that units can escape from corners."""
    board = Board(10, 10)
    
    # Test each unit type in each corner
    corners = [(0, 0), (9, 0), (0, 9), (9, 9)]
    unit_types = [Predator, Scavenger, Grazer]
    
    for UnitClass in unit_types:
        for corner_x, corner_y in corners:
            # Create unit in corner
            unit = UnitClass(corner_x, corner_y, board=board)
            unit.energy = unit.max_energy * 0.5  # Ensure it can move
            board.place_object(unit, corner_x, corner_y)
            
            # Update several times
            moved = False
            for _ in range(5):
                unit.update(board)
                if (unit.x, unit.y) != (corner_x, corner_y):
                    moved = True
                    break
                    
            # Clean up
            board.remove_object(unit.x, unit.y)
            
            assert moved, f"{UnitClass.__name__} stuck at corner ({corner_x}, {corner_y})"


def test_units_escape_edges():
    """Test that units can move away from edges."""
    board = Board(10, 10)
    
    # Test positions along each edge (not corners)
    edge_positions = [
        (5, 0),  # Top edge
        (5, 9),  # Bottom edge  
        (0, 5),  # Left edge
        (9, 5),  # Right edge
    ]
    
    unit_types = [Predator, Scavenger, Grazer]
    
    for UnitClass in unit_types:
        for edge_x, edge_y in edge_positions:
            # Create unit at edge
            unit = UnitClass(edge_x, edge_y, board=board)
            unit.energy = unit.max_energy * 0.5  # Ensure it can move
            board.place_object(unit, edge_x, edge_y)
            
            # Check that it prefers to move away from edge
            chosen_move = unit.choose_move(board)
            
            if chosen_move:
                new_x, new_y = chosen_move
                
                # Calculate edge distances
                old_edge_dist = min(edge_x, 9 - edge_x, edge_y, 9 - edge_y)
                new_edge_dist = min(new_x, 9 - new_x, new_y, 9 - new_y)
                
                # Should prefer moving away from edge
                assert new_edge_dist >= old_edge_dist, \
                    f"{UnitClass.__name__} at ({edge_x}, {edge_y}) chose to move closer to edge"
                    
            # Clean up
            board.remove_object(unit.x, unit.y)


def test_continuous_movement_along_edges():
    """Test that units don't get stuck moving back and forth along edges."""
    board = Board(20, 20)
    
    # Place a grazer near the edge
    grazer = Grazer(1, 10, board=board)
    grazer.energy = grazer.max_energy * 0.6
    board.place_object(grazer, 1, 10)
    
    # Track positions to detect stuck patterns
    positions = []
    
    # Run for several updates
    for i in range(20):
        grazer.update(board)
        positions.append((grazer.x, grazer.y))
        
        # Check if we're stuck in a pattern (visiting same positions repeatedly)
        if i >= 10:
            recent_positions = positions[-10:]
            unique_positions = len(set(recent_positions))
            
            # Should have visited at least 3 different positions in last 10 moves
            # (allowing for some back-and-forth but not complete stuck pattern)
            assert unique_positions >= 3, \
                f"Grazer stuck in pattern, only visited {unique_positions} unique positions in last 10 moves"
    
    # Also check that the unit has moved away from the edge at some point
    max_edge_dist = max(min(x, 19 - x, y, 19 - y) for x, y in positions)
    assert max_edge_dist > 1, "Unit never moved away from board edge"


def test_fleeing_from_edge():
    """Test that fleeing units can escape from edges when threatened."""
    board = Board(10, 10)
    
    # Place a grazer at edge
    grazer = Grazer(0, 5, board=board)
    grazer.energy = grazer.max_energy * 0.5
    board.place_object(grazer, 0, 5)
    
    # Place a predator nearby to trigger fleeing
    predator = Predator(2, 5, board=board)
    board.place_object(predator, 2, 5)
    
    # Grazer should flee
    initial_pos = (grazer.x, grazer.y)
    grazer.update(board)
    
    # Should have moved (even from edge when fleeing)
    assert (grazer.x, grazer.y) != initial_pos, "Grazer didn't flee from edge position"
    
    # Should prefer moving away from predator if possible
    if grazer.y != 5:  # If moved vertically
        # Good, moved perpendicular to threat
        pass
    else:
        # If moved horizontally, should have moved away from edge if possible
        assert grazer.x > 0, "Grazer moved into corner instead of along edge"


def test_score_comparison_edge_vs_center():
    """Test that move scoring prefers center over edge positions."""
    board = Board(10, 10)
    
    # Create a unit
    unit = Predator(5, 5, board=board)
    
    # Get movement options
    _, visible_objects = unit.get_movement_options(board)
    
    # Compare scores for moves toward edge vs center
    edge_move_score = unit._calculate_move_score(5, 0, visible_objects, board)  # Toward top edge
    center_move_score = unit._calculate_move_score(5, 5, visible_objects, board)  # Stay at center
    away_from_edge_score = unit._calculate_move_score(5, 6, visible_objects, board)  # Away from edges
    
    # Staying in center or moving away from edges should score better than moving to edge
    assert center_move_score > edge_move_score, "Center position should score better than edge"
    assert away_from_edge_score >= edge_move_score, "Moving away from edge should score at least as good as moving to edge"