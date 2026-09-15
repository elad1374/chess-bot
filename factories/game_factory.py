from src.main.config import AppConfig
from src.core_functionalities.game.game import Game
from src.core_functionalities.game.player import Player, HumanPlayer, RobotPlayer
from src.perception.yolo.processing.human_interpreter import HumanMoveController
from src.perception.yolo.vision_inference.board_pieces_detector import BoardPiecesDetector, ADVANCED
from src.perception.yolo.processing.fen_translator import BinaryToFenTranslator  # or factory for translators
from src.arm.behaviors.playing_robot import *
from src.perception.ZED.cameralib import Camera
from src.arm.chessbot import RobotHardware
from src.core_functionalities.chess_backbone.engine import ChessEngine
from src.arm.state.storage_manager import StorageManager
from src.arm.state.perception_state import PerceptionState

class GameFactory:
    """Dependency Injector responsible for constructing all sub-systems."""

    def __init__(self, config: AppConfig, camera: Camera, robot: RobotHardware):
        self.config = config
        self.camera = camera  
        self.robot = robot 

    def create_robot_hardware(self) -> PlayingRobot:
        """Builds real or mock robot hardware driver."""
        if self.config.robot.is_mock:
            print("[Factory] Injecting MockPlayingRobot")
            return PlayingMock()
        else:
            print(f"[Factory] Injecting Real PlayingRobot")
            human_color = self.config.game.get_color_for("human")
            robot_color = self.config.game.get_color_for("robot")
            return PlayingArm(self.robot, human_color, robot_color)

    def create_engine(self):
        return ChessEngine()

    def _build_human_interpreter(self) -> HumanMoveController:
        """Assembles Vision + Translator pipeline."""
        print(f"[Factory] Assembling Vision Pipeline with model '{self.config.vision.model_name}'")
        
        yolo_model = BoardPiecesDetector(model_name=self.config.vision.model_name, camera=self.camera)
        flip = self.config.game.white_player.lower() == "human"
        translator = BinaryToFenTranslator(flip=flip)
        advanced_model = BoardPiecesDetector(model_name=ADVANCED, camera=self.camera, optimize=True)
        
        return HumanMoveController(yolo_model=yolo_model, translator=translator, advanced_model=advanced_model)

    def _build_player(self, player_type: str, name: str) -> Player:
        """Constructs a Human or Robot player based on config type."""
        if player_type.lower() == "human":
            interpreter = self._build_human_interpreter()
            return HumanPlayer(name=name, interpreter=interpreter)
            
        elif player_type.lower() in ("robot", "ai"):
            playing_robot = self.create_robot_hardware()
            engine = self.create_engine()
            return RobotPlayer(name=name, engine=engine, robot=playing_robot)
            
        else:
            raise ValueError(f"Unknown player type: '{player_type}' in configuration.")

    def create_game(self) -> Game:
        """Factory entrypoint to build the full Game orchestrator."""
        white_player = self._build_player(
            player_type=self.config.game.white_player, 
            name=self.config.game.white_name
        )
        black_player = self._build_player(
            player_type=self.config.game.black_player, 
            name=self.config.game.black_name
        )
        perception_state = PerceptionState()
        storage = StorageManager()
        storage.calibrate_storage_from_fen(self.config.game.initial_fen)
        print(self.config.game.initial_fen)
        return Game(
            white_player=white_player,
            black_player=black_player,
            fen=self.config.game.initial_fen
        )