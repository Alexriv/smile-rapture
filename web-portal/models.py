from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
import bcrypt
import time


class ExperimentStatus(Enum):
    NOT_READY = 0
    READY = 1
    RUNNING = 2
    STOPPED = 3
    COMPLETED = 4
    RESULTS_READY = 5


@dataclass
class ResultEntry:
    data: str
    ts: float = field(default_factory=time.time)


@dataclass
class User:
    name_id: str
    email: str
    password: str
    experiment_ids: list[UUID.hex] = field(default_factory=list)
    admin: bool = False


@dataclass
class Experiment:
    experiment_name: str = "experiment"
    status: ExperimentStatus = ExperimentStatus.NOT_READY
    registry_tag: str = ""
    port_map: list[int] = field(default_factory=list)
    results: list[ResultEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    created_by: str = "none"
