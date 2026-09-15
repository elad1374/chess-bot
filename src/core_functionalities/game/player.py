from chess import Board, Move
from abc import ABC, abstractmethod
from .reactions import ReactionWaiter, ConsoleEnterReaction
from src.perception.yolo.processing.human_interpreter import HumanMoveController
from .actions import ChessAction
from .action_interpreter import ActionFactory
from src.arm.behaviors.playing_robot import PlayingRobot 
from common.exceptions import RobotFailedException
from src.core_functionalities.chess_backbone.engine import ChessEngine


class Player(ABC):
    def __init__(self, name: str = "Player"):
        self.name : str = name

    def make_move(self, board: Board):
        """
        Calculates or waits for a move given the current board.
        execute_move mutates the board object.
        """
        self.prepare_move(board)
        return self.execute_move(board)

    @abstractmethod
    def prepare_move(self, board: Board):
        pass

    @abstractmethod
    def execute_move(self, board: Board):
        pass



class HumanPlayer(Player):
    def __init__(self, name: str = "Human", reaction_waiter: ReactionWaiter = None, interpreter: HumanMoveController = None):
        super().__init__(name)
        # Default to pressing Enter if no reaction waiter is specified
        self.reaction_waiter : ReactionWaiter = reaction_waiter or ConsoleEnterReaction()
        self.interpreter: HumanMoveController = interpreter

    def prepare_move(self, board: Board):
        self.reaction_waiter.wait() # waits for human reaction

    def execute_move(self, board: Board):
        fen = self.interpreter.update_fen(board) #also updates board 
        print(f"[HumanPlayer] Move executed. New FEN: {fen}")
  
        



class RobotPlayer(Player):
    def __init__(self, name: str = "Robot", engine: ChessEngine=None, robot: PlayingRobot=None):
        super().__init__(name)
        self.engine = engine
        self.robot = robot
        self.cur_move = None
        self.action_factory = ActionFactory()
    
    def prepare_move(self, board: Board):
        self.cur_move = self.engine.choose_move(board)
        print(f"[RobotPlayer] Move prepared: {self.cur_move}")

    def execute_move(self, board: Board):
        action: ChessAction = self.action_factory.interpret_action(self.cur_move, board)
        if not action.execute_on_robot(self.robot): # TODO: should be future
            raise RobotFailedException("Robot failed while prforming a playing move")
        move = Move.from_uci(self.cur_move)
        board.push(move)

    