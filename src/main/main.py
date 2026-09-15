from .config import AppConfig
from factories.hardware_factory import HardwareFactory
from factories.board_setup_factory import BoardSetupFactory
from factories.game_factory import GameFactory
from factories.init_board_detector_factory import InitDetectorFactory
from .session import ChessSession
from common.utils import repo_path


if __name__ == "__main__":
    # Load system settings
    config = AppConfig.load(repo_path("src/main/config.yaml"))

    # Instantiate hardware factory (creates shared camera/robot references)
    hw_factory = HardwareFactory(config)
    camera = hw_factory.get_camera()
    robot_hw = hw_factory.get_robot_hardware()

    #  Create domain-specific setup service (if configured)
    board_setup_service = None
    if config.game.run_board_setup:
        setup_factory = BoardSetupFactory(config, camera=camera, robot=robot_hw)
        board_setup_service = setup_factory.create_setup_service()

    #  Create board detector
    init_board_detector = None
    if config.game.run_initial_detection:
        init_detecotr_factory = InitDetectorFactory(config, camera=camera)
        init_board_detector = init_detecotr_factory.create_initial_board_detector()

    #  Create gameplay domain
    game_factory = GameFactory(config, camera=camera, robot=robot_hw)
    chess_game = game_factory.create_game()

    #  Assemble session and run execution pipeline
    session = ChessSession(
        config=config,
        hardware_resources=hw_factory.get_active_resources(),
        game=chess_game,
        board_setup_service=board_setup_service,
        initial_board_detector=init_board_detector
    )

    session.run()