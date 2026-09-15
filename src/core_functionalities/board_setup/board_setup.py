from src.arm.behaviors.board_setting_robot import BoardSettingRobot
from src.perception.yolo.vision_inference.orientation_detector import OrientationDetector
from src.perception.yolo.vision_inference.platform_piece_classifier import PlatformPieceClassifier
from .placement_planner import PlacementPlanner
from common.exceptions import RobotFailedException
from common.enums_and_dicts import INT_TO_NAME, ColoredPieceType

class PieceIngestionPipeline:
    """Handles pre-game board arrangement and piece alignment."""
    def __init__(self, robot: BoardSettingRobot, orientation_detector: OrientationDetector, platform_classifier: PlatformPieceClassifier, placement_planner: PlacementPlanner):
        self.robot = robot
        self.orientation_detector = orientation_detector
        self.platform_classifier = platform_classifier
        self.placement_planner = placement_planner

    def get_num_of_pieces(self)->int:
        return self.placement_planner.get_total_count()

    def process_next_piece(self):
        # 1. Take picture & detect orientation
        pose = self.orientation_detector.detect_pickup_pose()
        head = pose.head
        base = pose.base
        orientation = pose.orientation

        print(f"pixel head = {head}")
        print(f"pixel base = {base}")
        print(f"camera head = {self.robot.robot_hardware.camera_vector_to_robot_vector(head)}")
        print(f"camera base = {self.robot.robot_hardware.camera_vector_to_robot_vector(base)}")
        # 2. Arm move piece to platform
        if not self.robot.move_piece_to_platform(
            self.robot.robot_hardware.camera_vector_to_robot_vector(head),
            self.robot.robot_hardware.camera_vector_to_robot_vector(base),
            orientation
        ):
            raise RobotFailedException("Robot failed while moving piece to platform")

        # 3. Detect piece class on platform
        piece_type: ColoredPieceType = self.platform_classifier.identify_piece()
        if piece_type is None:
            return

        # 4. Decide where to put on (board or grave yard)
        target_square = self.placement_planner.get_targer_for_piece(piece_type)

        # 5. Move piece from platform to board
        if not self.robot.move_from_platform_to_target(target_square, piece_type, orientation):
            raise RobotFailedException("Robot failed while moving piece from platform to target "+target_square)

        print(f"Placed {INT_TO_NAME[piece_type]} onto {target_square}")


class BoardSetupService:
    def __init__(self, pipeline: PieceIngestionPipeline):
        self.pipeline = pipeline

    def setup_board(self, target_fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"):
        """
        Runs the loop until all pieces are placed on the board.
        At the end returns the grave yard for the game.
        """
        print("[Setup] Starting piece ingestion loop...")
        
        for _ in range(self.pipeline.get_num_of_pieces()):
            self.pipeline.process_next_piece()

        print("[Setup] Board setup complete!")

        ###TODO: at end get graveyard