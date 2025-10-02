#!/usr/bin/env python3
"""Demo script showing the improved movement system."""

from game.board import Board
from game.units.unit_types import Predator, Grazer, Scavenger
from game.plants.plant_types import BasicPlant
from game.board import Position
import time
import os


def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')


def display_board(board, iteration):
    """Display the board state."""
    clear_screen()
    print(f"=== Movement Demo - Iteration {iteration} ===")
    print("P=Predator, G=Grazer, S=Scavenger, *=Plant, .=Empty")
    print("Units use smart movement to avoid edges and pursue goals\n")
    
    # Top border
    print("┌" + "─" * (board.width * 2 + 1) + "┐")
    
    for y in range(board.height):
        print("│ ", end="")
        for x in range(board.width):
            obj = board.get_object(x, y)
            if obj is None:
                print(". ", end="")
            elif isinstance(obj, Predator):
                print("P ", end="")
            elif isinstance(obj, Grazer):
                print("G ", end="")
            elif isinstance(obj, Scavenger):
                print("S ", end="")
            elif hasattr(obj, 'growth_rate'):  # Plant
                print("* ", end="")
            else:
                print("? ", end="")
        print("│")
    
    # Bottom border
    print("└" + "─" * (board.width * 2 + 1) + "┘")


def run_demo():
    """Run the movement demonstration."""
    # Create a board
    board = Board(20, 15)
    
    # Create units at various edge/corner positions
    units = []
    
    # Predator in top-left corner
    predator = Predator(0, 0, board=board)
    board.place_object(predator, 0, 0)
    units.append(predator)
    
    # Grazer on right edge
    grazer1 = Grazer(19, 7, board=board)
    board.place_object(grazer1, 19, 7)
    units.append(grazer1)
    
    # Scavenger on bottom edge
    scavenger = Scavenger(10, 14, board=board)
    board.place_object(scavenger, 10, 14)
    units.append(scavenger)
    
    # Another grazer in bottom-right corner
    grazer2 = Grazer(19, 14, board=board)
    board.place_object(grazer2, 19, 14)
    units.append(grazer2)
    
    # Add some plants in the center area
    for i in range(5):
        x = 8 + (i % 3) * 2
        y = 6 + (i // 3) * 2
        plant = BasicPlant(Position(x, y))
        board.place_object(plant, x, y)
    
    # Run simulation
    print("\nStarting movement demo...")
    print("Watch how units escape from edges and corners!")
    print("\nPress Ctrl+C to stop")
    
    iteration = 0
    try:
        while True:
            # Display current state
            display_board(board, iteration)
            
            # Show unit states
            print("\nUnit States:")
            for i, unit in enumerate(units):
                if unit.alive:
                    unit_type = unit.__class__.__name__
                    print(f"{unit_type} at ({unit.x}, {unit.y}) - "
                          f"State: {unit.state}, Energy: {unit.energy:.0f}/{unit.max_energy}")
            
            # Update all units
            for unit in units[:]:  # Copy list in case units die
                if unit.alive:
                    unit.update(board)
                    
                    # Show movement decision for first few iterations
                    if iteration < 10:
                        moves, _ = unit.get_movement_options(board)
                        if moves and len(moves) > 0:
                            best_move = moves[0]
                            print(f"\n{unit.__class__.__name__} chose move to "
                                  f"({best_move[0]}, {best_move[1]}) with score {best_move[2]:.1f}")
            
            time.sleep(1)
            iteration += 1
            
    except KeyboardInterrupt:
        print("\n\nDemo stopped.")
        print("\nKey observations:")
        print("- Units successfully escape from corners and edges")
        print("- Movement scoring prevents getting stuck")
        print("- Units pursue their goals (plants, prey, corpses) intelligently")
        print("- Edge avoidance is balanced with goal pursuit")


if __name__ == "__main__":
    run_demo()