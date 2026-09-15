
class ChessRobotBaseException(Exception):
    """Base exception class for all custom errors in this project."""
    pass


class RobotFailedException(ChessRobotBaseException):
    """Raised when the physical robot arm fails to execute an action."""
    def __init__(self, message: str = "Robot failed while performing a playing move"):
        super().__init__(message)

class EngineNoMove(ChessRobotBaseException):
    """Raised when the engine is out moves."""
    def __init__():
        super().__init__("Engine is out moves")


class YoloVisionException(ChessRobotBaseException):
    """Raised when the YOLO vision model fails to detect or parse the board."""
    pass