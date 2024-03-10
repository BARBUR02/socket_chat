from dataclasses import dataclass, asdict
from datetime import datetime
import json
import sys
from typing import Any, Literal
from colorama import Fore, Style
import threading

MCAST_GRP = "224.1.1.1"
MCAST_PORT = 5007
HOST = "127.0.0.1"
PORT = 9008
UDP_INDICATOR = "[UDP]: "
MULTICAST_INDICATOR = "[MULTICAST]: "


class ThreadSafeIncrementer:
    def __init__(self):
        self.value = 0
        self.lock = threading.Lock()

    def increment(self) -> int:
        with self.lock:
            self.value += 1
            return self.value


@dataclass
class User:
    id: int
    username: str | None

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other: "User") -> bool:
        if not isinstance(other, User):
            return False
        return self.id == other.id and self.username == other.username


@dataclass
class UserPayload:
    user_id: int
    username: str
    message: str
    send_time: datetime
    udp: bool = False

    @staticmethod
    def parse(payload_str: str) -> "UserPayload":
        data = json.loads(payload_str)
        data["send_time"] = datetime.fromisoformat(data["send_time"])
        return UserPayload(**data)

    def serialize(self) -> str:
        serialized_data = asdict(self)
        serialized_data["send_time"] = self.send_time.isoformat()
        serialized_data = json.dumps(serialized_data)
        return serialized_data


_USER_COLOR_MAPPINGS = {
    -1: Fore.LIGHTWHITE_EX,
    0: Fore.BLUE,
    1: Fore.CYAN,
    2: Fore.GREEN,
    3: Fore.MAGENTA,
    4: Fore.YELLOW,
    5: Fore.WHITE,
    "INFO": Fore.LIGHTMAGENTA_EX,
    "ERROR": Fore.RED,
}

NUMBER_OF_USER_COLORS = len(
    [key for key in _USER_COLOR_MAPPINGS.keys() if (type(key) == int and key != -1)]
)

DISPLAY_MODE = Literal["INFO", "ERROR"]


def _get_color(user_id: int) -> Any:
    return _USER_COLOR_MAPPINGS[user_id % NUMBER_OF_USER_COLORS]


def format_user_login(user_id: int, nickname: str) -> str:
    return (
        _USER_COLOR_MAPPINGS[user_id % NUMBER_OF_USER_COLORS]
        + nickname
        + Style.RESET_ALL
        + " has joined the chat."
    )


def display_message(user_payload: UserPayload) -> None:
    send_time = user_payload.send_time.strftime("%H:%M:%S")
    color = _get_color(user_payload.user_id)
    print(
        f"{Style.BRIGHT}[{send_time}] {color}{user_payload.username+':':<20}{Style.RESET_ALL} \t{user_payload.message}"
    )


def log_to_server(message, display_mode: DISPLAY_MODE = "INFO") -> None:
    print(_USER_COLOR_MAPPINGS[display_mode] + message + Style.RESET_ALL)


def move_input_down(user_payload: UserPayload, external=False) -> None:
    if not external:
        print("\033[1A\033[K", end="")
    else:
        print("\r\033[K", end="")
    display_message(user_payload)
