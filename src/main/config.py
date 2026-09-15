import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from common.utils import repo_path


@dataclass
class RobotConfig:
    is_mock: bool = False
    ip: str = "192.168.57.101"
    base_tcp_port: int = 63352
    speed: float = 0.1
    acceleration: float = 0.1


@dataclass
class EngineConfig:
    is_mock: bool = False
    path: str = "/usr/games/stockfish"
    depth: int = 15
    skill_level: int = 20


@dataclass
class VisionConfig:
    model_name: str = "binary"
    manual_orientation: bool = False
    manual_on_platform: bool = False



@dataclass
class GameSetupConfig:
    run_board_setup: bool = False
    run_initial_detection: bool = True
    white_player: str = "human"
    black_player: str = "robot"
    white_name: str = "Human Player"
    black_name: str = "Robot Player"
    initial_fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def get_color_for(self, player_type: str = "robot") -> Optional[str]:
        """
        Queries which color the specified player type is playing as.
        Returns 'white', 'black', or None if not found.
        """
        if self.white_player.lower() == player_type.lower():
            return "white"
        elif self.black_player.lower() == player_type.lower():
            return "black"
        return None


@dataclass
class AppConfig:
    #Use field() to avoid unwanted mutations
    game: GameSetupConfig = field(default_factory=GameSetupConfig)
    robot: RobotConfig = field(default_factory=RobotConfig)
    engine: EngineConfig = field(default_factory=EngineConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)

    @classmethod
    def load(cls, filepath: str = repo_path("src/main/config.yaml")) -> "AppConfig":
        """Loads config from YAML or JSON file."""
        if not os.path.exists(filepath):
            print(f"[Config] File '{filepath}' not found. Loading defaults.")
            return cls()
        

        data: Dict[str, Any] = {}
        if filepath.endswith(".yaml") or filepath.endswith(".yml"):
            try:
                import yaml
                with open(filepath, "r") as f:
                    data = yaml.safe_load(f) or {}
            except ImportError:
                raise ImportError("PyYAML is required to parse .yaml files. Install via 'pip install pyyaml' or use JSON.")
        elif filepath.endswith(".json"):
            with open(filepath, "r") as f:
                data = json.load(f)

        return cls(
            game=GameSetupConfig(**data.get("game", {})),
            robot=RobotConfig(**data.get("robot", {})),
            engine=EngineConfig(**data.get("engine", {})),
            vision=VisionConfig(**data.get("vision", {})),
        )