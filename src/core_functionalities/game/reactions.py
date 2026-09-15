import time
from abc import ABC, abstractmethod


class ReactionWaiter(ABC):
    """Abstract base class for human reaction handlers."""
    
    @abstractmethod
    def wait(self) -> None:
        """Waits for human action or input."""
        pass


class TimeReaction(ReactionWaiter):
    """Waits for a specified amount of seconds."""
    
    def __init__(self, seconds: float = 3.0):
        self.seconds = seconds

    def wait(self) -> None:
        print(f"Waiting for {self.seconds} second(s)...")
        time.sleep(self.seconds)


class ConsoleEnterReaction(ReactionWaiter):
    """Waits for a human user to press Enter in the terminal."""
    
    def __init__(self, prompt: str = "Press Enter when you have made your move..."):
        self.prompt = prompt

    def wait(self) -> None:
        input(self.prompt)


class WebClientReaction(ReactionWaiter):
    """
    Stub implementation for waiting on a human action via a Web Client
    (e.g., via WebSockets, HTTP REST polling, or UI event listeners).
    """
    
    def __init__(self, client_id: str = "default_client", poll_interval: float = 1.0, timeout: float = 60.0):
        self.client_id = client_id
        self.poll_interval = poll_interval
        self.timeout = timeout
        self._is_connected = False

    def _connect(self) -> bool:
        """Stub: Establishes connection/session with the web client."""
        self._is_connected = True
        return True

    def _poll_client_action() -> bool:
        """Stub: Polls backend server or database for client confirmation."""
        # TODO: Replace with real HTTP/Database check
        return False

    def _listen_websocket_event() -> bool:
        """Stub: Listens to incoming WebSocket event from client."""
        # TODO: Replace with real WebSocket event listener
        return False

    def wait(self) -> None:
        """
        Stub implementation for waiting on the web client reaction.
        """
        print(f"[WebClientReaction Stub] Listening for web client action (Client ID: {self.client_id})...")
        
        # Stub logic flow
        self._connect()
        
        # Simulated loop stub
        # In actual usage: Loop while polling or wait on a threading Event/Queue
        print("[WebClientReaction Stub] Web signal received.")