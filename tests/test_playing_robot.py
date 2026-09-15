
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


from src.arm.behaviors.playing_robot import PlayingArm
from src.arm.chessbot import RobotHardware
from src.core_functionalities.game.actions import ChessAction
from src.core_functionalities.game.action_interpreter import ActionFactory
from common.enums_and_dicts import PieceType
import random



if __name__ == "__main__":
    
    test = "put_type_in_storage"


    if test == "castle":
        # test castling move execution on robot
        with RobotHardware() as robot:
            fen = "8/8/8/8/8/8/8/4K2R w - - 0 1"
            cur_move = "e1g1" #castle
            action_factory = ActionFactory()
            playing_arm = PlayingArm(robot, "black", "white")
            action: ChessAction = action_factory.interpret_action(cur_move, fen)
            if not action.execute_on_robot(playing_arm): 
                print("failed to execute action on robot")
            print(action.update_fen(fen))

    if test == "upgrade":
        # test pawn promotion move execution on robot
        with RobotHardware() as robot:
            fen = "2B5/3p4/8/8/8/8/8/8 b - - 0 1"
            cur_move = "d7c8q" #upgrade
            action_factory = ActionFactory()
            playing_arm = PlayingArm(robot, "white", "black")
            action: ChessAction = action_factory.interpret_action(cur_move, fen)
            if not action.execute_on_robot(playing_arm): 
                print("failed to execute action on robot")
            print(action.update_fen(fen))

    if test == "capture_4_pawns":
        print("\n--- Testing Storage: 4 Black Pawns ---")
        with RobotHardware() as robot:
            # Setup: White Rook on a1. Black Pawns on a2, a3, a4, a5
            fen = "8/8/8/p7/p7/p7/p7/R7 w - - 0 1"
            
            # The White Rook will move up the file, eating one pawn at a time
            moves = ["a1a2", "a2a3", "a3a4", "a4a5"]
            
            action_factory = ActionFactory()
            playing_arm = PlayingArm(robot, "black", "white")
            
            for move in moves:
                print(f"\n[!] Executing move: {move}")
                action: ChessAction = action_factory.interpret_action(move, fen)
                
                if not action.execute_on_robot(playing_arm): 
                    print("Failed to execute action on robot")
                    break
                    
                # Update the FEN for the next loop so the Rook knows where it is
                fen = action.update_fen(fen)
                
            print("\nFinal FEN:", fen)
            playing_arm.storage.print_state()


    if test == "capture_2_knights":
        print("\n--- Testing Storage: 2 Black Knights ---")
        with RobotHardware() as robot:
            # Setup: White Rook on h1. Black Knights on h2, h3
            fen = "8/8/8/8/8/7n/7n/7R w - - 0 1"
            
            # The White Rook will move up, eating both knights
            moves = ["h1h2", "h2h3"]
            
            action_factory = ActionFactory()
            playing_arm = PlayingArm(robot, "black", "white")
            
            for move in moves:
                print(f"\n[!] Executing move: {move}")
                action: ChessAction = action_factory.interpret_action(move, fen)
                
                if not action.execute_on_robot(playing_arm): 
                    print("Failed to execute action on robot")
                    break
                    
                fen = action.update_fen(fen)
                
            print("\nFinal FEN:", fen)
            playing_arm.storage.print_state()
    
    if test == "place_2_knights":
        print("\n--- Testing Storage: Retrieve 2 Black Knights ---")
        with RobotHardware() as robot:
            
            # Setup: Missing 2 Black Knights from the standard starting layout (b8 and g8)
            fen = "r1bqkb1r/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            
            playing_arm = PlayingArm(robot, "white", "black")
            
            # Use the method you moved inside StorageManager!
            playing_arm.storage.calibrate_storage_from_fen(fen)
            
            # --- Inline logic without calling an external function ---
            try:
                piece_type = PieceType.KNIGHT
                color = "black"
                target_square_1 = "b8"
                target_square_2 = "g8"
                
                # --- Knight 1 ---
                slot_1 = playing_arm.storage.get_slot_for_robot_promotion(piece_type, color)
                print(f"\n[!] Bringing Knight 1 from {slot_1} -> {target_square_1}")
                playing_arm._execute_movement(piece_type, start_pos=slot_1, end_pos=target_square_1, move_to_start=False)

                # --- Knight 2 ---
                slot_2 = playing_arm.storage.get_slot_for_robot_promotion(piece_type, color)
                print(f"[!] Bringing Knight 2 from {slot_2} -> {target_square_2}")
                playing_arm._execute_movement(piece_type, start_pos=slot_2, end_pos=target_square_2, move_to_start=True)

            except Exception as e:
                print(f"Failed to retrieve knights: {e}")

            print("\nFinal Storage State (Knights should be 0):")
            playing_arm.storage.print_state()
    
    if test == "place_4_pawns":
        print("\n--- Testing Storage: Retrieve 4 Black Pawns ---")
        with RobotHardware() as robot:
            
            # Setup: Missing 4 Black Pawns from the starting layout (a7, b7, c7, d7 empty)
            fen = "rnbqkbnr/1111pppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" # (or standard FEN with missing pawns)
            
            playing_arm = PlayingArm(robot, "white", "black")
            
            # Calibrate storage based on the FEN
            playing_arm.storage.calibrate_storage_from_fen(fen)
            
            # --- Inline logic for retrieving 4 pawns ---
            try:
                piece_type = PieceType.PAWN
                color = "black"
                target_squares = ["a7", "b7", "c7", "d7"]
                
                for i, target_square in enumerate(target_squares, start=1):
                    slot = playing_arm.storage.get_slot_for_robot_promotion(piece_type, color)
                    print(f"\n[!] Bringing Pawn {i} from {slot} -> {target_square}")
                    
                    # For the last pawn, we can return to start or keep it simple
                    move_to_start = (i == len(target_squares))
                    playing_arm._execute_movement(piece_type, start_pos=slot, end_pos=target_square, move_to_start=move_to_start)

            except Exception as e:
                print(f"Failed to retrieve pawns: {e}")

            print("\nFinal Storage State (Pawns should be 0):")
            playing_arm.storage.print_state()



    elif test == "random_storage_workflow":
        print("\n" + "="*40)
        print("STARTING INITIAL FEN STORAGE WORKFLOW (5 CAPTURES -> 3 RETRIEVALS)")
        print("="*40)
        
        with RobotHardware() as robot:
            playing_arm = PlayingArm(robot, "white", "black")
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
            action_factory = ActionFactory()        
            stored_items = []
            
            initial_piece_targets = [
                ("b8", PieceType.KNIGHT, "black"),
                ("g8", PieceType.KNIGHT, "black"),
                ("a7", PieceType.PAWN, "black"),
                ("b1", PieceType.KNIGHT, "white"),
                ("c1", PieceType.BISHOP, "white")
            ]

            for i, (sq, p_type, col) in enumerate(initial_piece_targets, start=1):
                print(f"\n[Step {i}] Capturing {col} {p_type.name} from {sq}")
                
                try:
                    slot = playing_arm.storage.get_slot_for_robot_capture(p_type, col)
                    print(f" -> Moving {sq} to storage slot: {slot}")
                    
                    playing_arm._execute_movement(piece=p_type, start_pos=sq, end_pos=slot, move_to_start=False)
                    
                    stored_items.append((p_type, col))
                    
                except Exception as e:
                    print(f"[!] Capture failed: {e}")

                playing_arm.storage.print_state()

            


            retrieval_targets = ["d3", "e4", "f3"] # Safe open squares on the board
            
            for i in range(1, 4):
                if not stored_items:
                    print("No more items in storage to retrieve!")
                    break
                
                p_type, col = stored_items.pop(0)
                target_square = retrieval_targets[i - 1]
                
                print(f"\n[Step {i}] Retrieving {col} {p_type.name} from storage -> {target_square}")
                
                try:
                    slot = playing_arm.storage.get_slot_for_robot_promotion(p_type, col)
                    print(f" -> Taking from storage slot: {slot}")
                    
                    playing_arm._execute_movement(
                        piece=p_type, 
                        start_pos=slot, 
                        end_pos=target_square, 
                        move_to_start=(i == 3)
                    )
                    
                except Exception as e:
                    print(f"[!] Retrieval failed: {e}")

                playing_arm.storage.print_state()

    elif test == "put_type_in_storage":
        with RobotHardware(flip=True) as robot:

            h_color = "white"
            r_color = "black"

            playing_arm = PlayingArm(robot, h_color, r_color)

            # remove in capture line (# move) before testing
            # change h_color and r_color for white/black at human side

            playing_arm.capture(from_square='a1', to_square='a1', remove_square='a1', moving_piece=PieceType.ROOK, captured_piece=PieceType.ROOK)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='h1', moving_piece=PieceType.ROOK, captured_piece=PieceType.ROOK)

            playing_arm.capture(from_square='a1', to_square='a1', remove_square='b1', moving_piece=PieceType.ROOK, captured_piece=PieceType.KNIGHT)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='g1', moving_piece=PieceType.ROOK, captured_piece=PieceType.KNIGHT)
        
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='c1', moving_piece=PieceType.ROOK, captured_piece=PieceType.BISHOP)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='f1', moving_piece=PieceType.ROOK, captured_piece=PieceType.BISHOP)
        
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='e1', moving_piece=PieceType.ROOK, captured_piece=PieceType.KING)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='d1', moving_piece=PieceType.ROOK, captured_piece=PieceType.QUEEN)

            playing_arm.capture(from_square='a1', to_square='a1', remove_square='a2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='b2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='c2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='d2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='e2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='f2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='g2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)
            playing_arm.capture(from_square='a1', to_square='a1', remove_square='h2', moving_piece=PieceType.ROOK, captured_piece=PieceType.PAWN)

            robot.move_to(robot.start_position)
        

