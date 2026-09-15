import chess
import chess.engine

def fen_to_board(fen):
    fen = fen.strip()

    try:
        return chess.Board(fen)
    except ValueError:
        # Allows board-only FEN, for example:
        # rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR
        return chess.Board(fen + " w - - 0 1")

def detect_move_from_boards(current_board, new_board):
    changed = []

    for square in chess.SQUARES:
        old_piece = current_board.piece_at(square)
        new_piece = new_board.piece_at(square)

        if old_piece != new_piece:
            changed.append(square)

    if len(changed) == 0:
        return None

    # Normal move, capture, or promotion
    if len(changed) == 2:
        from_square = None
        to_square = None

        for square in changed:
            old_piece = current_board.piece_at(square)
            new_piece = new_board.piece_at(square)

            if old_piece is not None and new_piece is None:
                from_square = square
            else:
                to_square = square

        if from_square is not None and to_square is not None:
            return chess.Move(from_square, to_square)

    # Castling: 4 squares changed, return the king move
    if len(changed) == 4:
        king_from = None
        king_to = None

        for square in changed:
            old_piece = current_board.piece_at(square)
            new_piece = new_board.piece_at(square)

            if old_piece is not None and old_piece.piece_type == chess.KING:
                king_from = square

            if new_piece is not None and new_piece.piece_type == chess.KING:
                king_to = square

        if king_from is not None and king_to is not None:
            return chess.Move(king_from, king_to)

    # En passant: 3 squares changed
    if len(changed) == 3:
        from_square = None
        to_square = None

        for square in changed:
            old_piece = current_board.piece_at(square)
            new_piece = new_board.piece_at(square)

            if old_piece is not None and old_piece.piece_type == chess.PAWN and new_piece is None:
                from_square = square

            if new_piece is not None and new_piece.piece_type == chess.PAWN and old_piece is None:
                to_square = square

        if from_square is not None and to_square is not None:
            return chess.Move(from_square, to_square)

    return None

def print_board(board, perspective=chess.WHITE):
    

    if perspective == chess.BLACK:
        print("\n  h g f e d c b a")
        rank_range = range(8)
        file_range = range(7, -1, -1)
        UNICODE_PIECES = {
        'p': '♙', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔',
        'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚'
        }   
    else:
        print("\n  a b c d e f g h")
        rank_range = range(7, -1, -1)
        file_range = range(8)
        UNICODE_PIECES = {
        'p': '♙', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚',
        'P': '♟', 'n': '♘', 'b': '♗', 'r': '♖', 'q': '♕', 'k': '♔'
        }


    for rank in rank_range:
        print(rank + 1, end=" ")

        for file in file_range:
            square = chess.square(file, rank)
            piece = board.piece_at(square)

            if piece:
                print(UNICODE_PIECES[piece.symbol()], end=" ")
            else:
                print(".", end=" ")

        print(rank + 1)

    if perspective == chess.BLACK:
        print("  h g f e d c b a\n")
    else:
        print("  a b c d e f g h\n")

def get_configs(configs):
    configs = {}
    configs["board"] = None

    while configs["board"] is None:
        board = input("Do you want to start with the standard chess board? (yes/no): ").strip().lower()
        if board in ["yes", "y"]:
            configs["board"] = chess.Board()
            break
        elif board in ["no", "n"]:
            while True:
                board = input("Enter the FEN string for the starting position: ").strip()
                try:
                    configs["board"] = chess.Board(fen=board)
                    break
                except ValueError:
                    print("Invalid FEN string. Please try again.")
            
    
    side = ""
    while side not in ["white", "black"]:
        side = input("Choose your side (white/black): ").strip().lower()
    configs["side"] = side

    while True:
        elo = input("Choose Stockfish strength (Elo 1350-2850, default 1320): ").strip()
        if elo == "":
            configs["elo"] = 1320
            break
        try:            
            elo = int(elo)
            if 1350 <= elo <= 2850:
                configs["elo"] = elo
                break
            else:
                print("Please enter a valid Elo between 1350 and 2850.")
        except ValueError:
            print("Invalid input. Please enter a number for the Elo rating.")
    

    return configs



def main():

    configs = get_configs(configs={})
    side = configs["side"]
    elo = configs["elo"]
    board = configs["board"]

    board = chess.Board(board.fen())
    #engine = chess.engine.SimpleEngine.popen_uci("./stockfish/stockfish-ubuntu-x86-64-avx2")
    engine = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish") # TODO check for permenant path in linux

    engine.configure({
    "UCI_LimitStrength": True,
    "UCI_Elo": elo
    })

    if side == "black":
        board.turn = chess.WHITE
        perspective = chess.BLACK
        result = engine.play(board, chess.engine.Limit(time=0.1))
        board.push(result.move)
        print ("Stockfish plays white : ", result.move)
    if side == "white":
        board.turn = chess.WHITE
        perspective = chess.WHITE
        print("You are playing as white. Stockfish will play as black.")

    while not board.is_game_over():
        print_board(board, perspective)
        legal = list(board.legal_moves)
        moved = False
        while not moved:
            move = input("Enter your move (e.g., e2e4), or 'quit'")
            if move.lower() == "quit":
                print("Exiting the game.")
                engine.quit()
                return
            if move.lower() == "help":
                print("Legal moves:", legal)
            try:
                chess.Move.from_uci(move)
            except ValueError:
                print("Invalid move format. Please enter in UCI format (e.g., e2e4).")
                continue
            if chess.Move.from_uci(move) in legal:
                try:
                    board.push_san(move)
                    moved = True
                except ValueError:
                    print("Invalid move.")
                    moved = False
            else:
                print("Illegal move.")

        result = engine.play(board, chess.engine.Limit(time=0.1))
        if result.move is not None:
            board.push(result.move)
        else:
            print("Stockfish has no legal moves. Game over.")
            break

    print("Game over. Result:", board.result())

if __name__ == "__main__":
    main()

