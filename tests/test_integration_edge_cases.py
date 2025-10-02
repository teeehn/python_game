"""Integration tests focusing on edge cases and boundary conditions."""

import pytest
import random
from game.board import Board, MovementType, Position
from game.units.base_unit import Unit # Keep for other tests if they use base Unit
from game.units.unit_types import Grazer # Import Grazer
from game.game_loop import GameLoop
from game.plants.base_plant import Plant

@pytest.fixture
def small_board():
    """Create a minimal 3x3 board for testing boundary conditions."""
    return Board(3, 3, MovementType.CARDINAL)

@pytest.fixture
def crowded_board(small_board):
    """Create a nearly-full board to test space constraints."""
    units = [
        Unit(0, 0, hp=120, energy=80, strength=15, speed=2, vision=6),   # Predator
        Unit(1, 1, hp=120, energy=150, strength=5, speed=1, vision=4),   # Grazer
        Unit(2, 2, hp=80, energy=100, strength=8, speed=3, vision=8)     # Scavenger
    ]
    for unit in units:
        small_board.place_object(unit, unit.x, unit.y)
    return small_board, units

@pytest.mark.integration
def test_board_boundary_movement(small_board):
    """Test unit behavior at board boundaries."""
    unit = Unit(0, 0, hp=120, energy=80, strength=15, speed=2, vision=6)  # Predator
    small_board.place_object(unit, 0, 0)
    
    # Try invalid positions
    invalid_positions = [(-1, 0), (0, -1), (3, 0), (0, 3)]
    for x, y in invalid_positions:
        assert not small_board.is_valid_position(x, y)
    
    # Process turn and verify unit stays in bounds
    game_loop = GameLoop(small_board)
    game_loop.add_unit(unit)
    game_loop.process_turn()
    
    pos = small_board.get_object_position(unit)
    assert small_board.is_valid_position(pos.x, pos.y)

@pytest.mark.integration
def test_unit_collision_handling(small_board):
    """Test behavior when units try to occupy the same space."""
    unit1 = Unit(0, 0, hp=120, energy=80, strength=15, speed=2, vision=6)  # Predator
    unit2 = Unit(0, 1, hp=120, energy=150, strength=5, speed=1, vision=4)  # Grazer
    
    small_board.place_object(unit1, 0, 0)
    small_board.place_object(unit2, 0, 1)
    
    # Attempt invalid placement
    assert not small_board.place_object(unit1, 0, 1)
    
    # Verify positions unchanged
    pos1 = small_board.get_object_position(unit1)
    pos2 = small_board.get_object_position(unit2)
    assert (pos1.x, pos1.y) == (0, 0)
    assert (pos2.x, pos2.y) == (0, 1)

@pytest.mark.integration
def test_unit_death_decay(small_board):
    """Test handling of unit death and decay process."""
    unit = Unit(1, 1, hp=120, energy=150, strength=5, speed=1, vision=4)  # Grazer
    small_board.place_object(unit, 1, 1)
    game_loop = GameLoop(small_board)
    game_loop.add_unit(unit)
    
    # Kill unit and verify decay
    unit.hp = 0
    game_loop.process_turn()
    
    assert not unit.alive
    assert unit.decay_stage > 0
    assert small_board.get_object(1, 1) == unit
    
    # Run decay process
    for _ in range(10):
        game_loop.process_turn()
        if small_board.get_object(1, 1) is None:
            break
    
    assert small_board.get_object(1, 1) is None

@pytest.mark.integration
def test_resource_competition(small_board):
    """Test multiple units competing for limited resources."""
    # Setup competing units
    units = [
                Grazer(0, 0, config=None, board=small_board),
                Grazer(2, 2, config=None, board=small_board)
    ]
    for unit in units: # Set energy lower so they will eat
        unit.energy = unit.max_energy // 2

    # Note: Default Grazer energy is 130. The original test used Unit with energy 150.
    # This might affect exact energy levels but the core logic (gaining some energy) should hold.
    plant = Plant(Position(1, 1), base_energy=50, growth_rate=0.1, regrowth_time=5)
    
    # Place objects
    for unit in units:
        small_board.place_object(unit, unit.x, unit.y)
    small_board.place_object(plant, 1, 1)
    
    game_loop = GameLoop(small_board)
    for unit in units:
        game_loop.add_unit(unit)
    
    # Record initial state
    initial_energies = {unit: unit.energy for unit in units}
    
    # Run competition
    for _ in range(5):
        game_loop.process_turn()
    
    # Check results
    energy_gained = [unit.energy > initial_energies[unit] for unit in units]
    assert any(energy_gained)
    assert not all(energy_gained)
