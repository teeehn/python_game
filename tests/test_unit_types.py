import pytest
from game.units.unit_types import Predator, Scavenger, Grazer
from game.board import Board

@pytest.fixture
def board():
    from game.board import MovementType
    return Board(width=10, height=10, movement_type=MovementType.DIAGONAL)

@pytest.fixture
def predator(board):
    pred = Predator(x=5, y=5, board=board)
    return pred

@pytest.fixture
def scavenger(board):
    scav = Scavenger(x=3, y=3, board=board)
    return scav

@pytest.fixture
def grazer(board):
    graz = Grazer(x=7, y=7, board=board)
    return graz

def test_unit_initialization():
    """Test that units are initialized with correct base stats."""
    predator = Predator(x=0, y=0)
    assert predator.hp == 120
    assert predator.energy == 80
    assert predator.strength == 15
    assert predator.speed == 2
    assert predator.vision == 6

    scavenger = Scavenger(x=0, y=0)
    assert scavenger.hp == 100
    assert scavenger.energy == 110
    assert scavenger.strength == 8
    assert scavenger.speed == 1
    assert scavenger.vision == 8

    grazer = Grazer(x=0, y=0)
    assert grazer.hp == 90
    assert grazer.energy == 130
    assert grazer.strength == 5
    assert grazer.speed == 1
    assert grazer.vision == 5

def test_experience_system():
    """Test that units gain experience and level up properly."""
    predator = Predator(x=0, y=0)
    
    # Test initial state
    assert predator.level == 1
    assert predator.experience == 0
    assert len(predator.traits) == 0
    
    # Test experience gain
    predator.gain_experience("combat", 10)
    assert predator.level == 2
    assert "battle_hardened" in predator.traits
    assert predator.strength > 15  # Should have increased due to combat specialization

def test_unit_behaviors(board, predator, scavenger, grazer):
    """Test that units exhibit their specialized behaviors."""
    # Place units on board
    board.place_object(predator, predator.x, predator.y)
    board.place_object(scavenger, scavenger.x, scavenger.y)
    board.place_object(grazer, grazer.x, grazer.y)
    
    # Test predator hunting behavior
    initial_energy = predator.energy
    predator.update(board)
    assert predator.energy < initial_energy  # Should have spent energy moving/hunting
    
    # Test grazer fleeing from predator
    grazer_pos = (grazer.x, grazer.y)
    grazer.update(board)
    assert (grazer.x, grazer.y) != grazer_pos  # Should have moved away from predator
    
    # Test scavenger behavior with dead unit
    # Place dead unit further away to ensure scavenger needs to move
    dead_unit = Grazer(x=1, y=1)
    dead_unit.alive = False
    board.place_object(dead_unit, dead_unit.x, dead_unit.y)
    scavenger_pos = (scavenger.x, scavenger.y)
    scavenger.update(board)
    assert (scavenger.x, scavenger.y) != scavenger_pos  # Should move toward dead unit

def test_unit_evolution():
    """Test that units evolve and specialize based on their actions."""
    grazer = Grazer(x=0, y=0)
    
    # Simulate successful feeding actions
    for _ in range(15):
        grazer.gain_experience("feeding")
    
    assert grazer.level > 1
    assert "efficient_digestion" in grazer.traits
    assert grazer.max_energy > 130  # Should have increased due to feeding specialization

def test_hungry_grazer_explores_when_no_plant_in_sight(mock_config):
    """Test that a hungry grazer explores if no plants are within its vision."""
    from game.board import Board, MovementType
    from game.plants.plant_types import BasicPlant # Using BasicPlant as an example
    from game.board import Position # Required for Plant instantiation

    # Setup
    # Use a larger board to ensure plant can be placed outside vision
    board = Board(width=30, height=30, movement_type=MovementType.DIAGONAL, config=mock_config)

    # Grazer setup
    grazer_initial_x, grazer_initial_y = 5, 5
    grazer = Grazer(x=grazer_initial_x, y=grazer_initial_y, config=mock_config)
    grazer.energy = grazer.max_energy * 0.1  # Make grazer hungry
    # Default vision for Grazer is 5.
    board.place_object(grazer, grazer_initial_x, grazer_initial_y)

    # Plant setup - place it well outside Grazer's vision (e.g., vision is 5, place >5 units away)
    # Grazer at (5,5), Plant at (15,15) is distance sqrt((15-5)^2 + (15-5)^2) = sqrt(100+100) = sqrt(200) approx 14
    plant = BasicPlant(position=Position(x=15, y=15))
    board.place_object(plant, 15, 15)

    initial_pos = (grazer.x, grazer.y)

    # Execution - run update a few times to allow for exploration moves
    for _ in range(10): # Number of ticks for exploration
        if not grazer.alive: # Stop if grazer dies for some reason
            break
        grazer.update(board)
        # Small check: if it found the plant and ate, its energy would go up significantly
        # For this test, we mainly care it moved, not that it found this specific plant far away.
        if grazer.energy > grazer.max_energy * 0.5: # Energy increased substantially
            break


    # Assertion
    final_pos = (grazer.x, grazer.y)
    assert final_pos != initial_pos, "Grazer should have moved from its initial position due to exploration."

    # Optional: Check if energy was consumed (if it moved)
    # This depends on whether it successfully moved in any tick.
    # If it couldn't move (e.g. blocked), energy might not decrease.
    # The primary assertion is movement.
    if final_pos != initial_pos:
         assert grazer.energy < grazer.max_energy * 0.1, "Grazer's energy should decrease after moving."

def test_hungry_scavenger_explores_when_no_food_in_sight(mock_config):
    """Test that a hungry Scavenger explores if no food is within its vision."""
    from game.board import Board, MovementType
    from game.plants.plant_types import BasicPlant # For placing a distant food item
    from game.board import Position # Required for Plant instantiation

    # Setup
    board_size = 30 # Ensure enough space for Scavenger to be far from food
    board = Board(width=board_size, height=board_size, movement_type=MovementType.DIAGONAL, config=mock_config)

    # Scavenger setup
    scavenger_initial_x, scavenger_initial_y = 5, 5
    # Scavenger default vision is 8
    scavenger = Scavenger(x=scavenger_initial_x, y=scavenger_initial_y, config=mock_config)
    scavenger.energy = scavenger.max_energy * 0.1  # Make scavenger hungry
    board.place_object(scavenger, scavenger_initial_x, scavenger_initial_y)

    # Food setup - place a plant far away, outside Scavenger's vision (8)
    # Scavenger at (5,5), Plant at (20,20). Dist = sqrt((20-5)^2 + (20-5)^2) = sqrt(225+225) = sqrt(450) ~ 21.2
    # This is well outside vision of 8.
    far_food_x, far_food_y = 20, 20
    plant = BasicPlant(position=Position(x=far_food_x, y=far_food_y))
    board.place_object(plant, far_food_x, far_food_y)

    initial_pos = (scavenger.x, scavenger.y)

    # Execution - run update a few times to allow for exploration moves
    for _ in range(10): # Number of ticks for exploration
        if not scavenger.alive: # Stop if scavenger dies
            break
        scavenger.update(board)
        # If scavenger somehow finds the distant plant and eats, its energy would go up.
        # We mainly care that it moved due to not seeing any food initially.
        if scavenger.energy > scavenger.max_energy * 0.5: # Energy increased substantially
            break

    # Assertion
    final_pos = (scavenger.x, scavenger.y)
    assert final_pos != initial_pos, "Scavenger should have moved from its initial position due to exploration."

    # Optional: Check if energy was consumed (if it moved successfully)
    if final_pos != initial_pos:
        # Scavenger's energy should be less than its starting low energy if it moved.
        # Allow for a very small tolerance if needed, but direct comparison should work.
        assert scavenger.energy < scavenger.max_energy * 0.1, "Scavenger's energy should decrease after moving."

def test_hungry_predator_explores_when_no_food_in_sight(mock_config):
    """Test that a hungry Predator explores if no dead units are within its vision."""
    from game.board import Board, MovementType
    from game.units.unit_types import Grazer # To create a mock dead unit
    # Position might not be strictly needed if Grazer takes x,y directly and board.place_object handles it.
    # from game.board import Position

    # Setup
    board_size = 30
    board = Board(width=board_size, height=board_size, movement_type=MovementType.DIAGONAL)

    # Predator setup
    predator_initial_x, predator_initial_y = 5, 5
    # Predator default vision is 6
    predator = Predator(x=predator_initial_x, y=predator_initial_y, config=mock_config, board=board)
    predator.energy = predator.max_energy * 0.25  # Make predator hungry but not resting
    board.place_object(predator, predator_initial_x, predator_initial_y)

    # Distant food setup: A dead Grazer
    # Predator at (5,5) with vision 6. Dead unit at (20,20).
    # Dist = sqrt((20-5)^2 + (20-5)^2) = sqrt(225+225) = sqrt(450) ~ 21.2. Well outside vision.
    far_food_x, far_food_y = 20, 20
    dead_grazer = Grazer(x=far_food_x, y=far_food_y, config=mock_config, board=board) # Create Grazer far away
    dead_grazer.alive = False
    dead_grazer.hp = 0
    dead_grazer.decay_stage = 1 # Predator looks for decay_stage < 3
    # Ensure it has some energy content for consumption if predator were to reach it (not expected in this test)
    if not hasattr(dead_grazer, 'decay_energy'):
        dead_grazer.decay_energy = 50
    board.place_object(dead_grazer, far_food_x, far_food_y)

    initial_pos = (predator.x, predator.y)

    # Execution - run update a few times to allow for exploration moves
    # Predator becomes hungry -> _find_closest_food -> no food -> explores
    for _ in range(10): # Number of ticks for exploration
        if not predator.alive:
            break
        predator.update(board)
        # If predator somehow finds the distant food and eats, its energy would go up.
        # We mainly care that it moved due to not seeing any food initially.
        if predator.energy > predator.max_energy * 0.5:
            break

    # Assertion
    final_pos = (predator.x, predator.y)
    assert final_pos != initial_pos, "Predator should have moved from its initial position due to exploration."

    if final_pos != initial_pos:
        # Predator's energy should be less than its starting energy if it moved (minus resting gains).
        assert predator.energy < predator.max_energy * 0.25, "Predator's energy should decrease after moving."
