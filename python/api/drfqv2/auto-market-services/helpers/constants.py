# built ins
from enum import Enum, auto


class InstrumentState(Enum):
    ACTIVE = auto()
    EXPIRED = auto()


class RFQState(Enum):
    OPEN = auto()
    CLOSED = auto()


class OrderDirection(Enum):
    BUY = auto()
    SELL = auto()


class VenueInterface(Enum):
    WS = auto()
    REST = auto()


class OrderState(Enum):
    OPEN = auto()
    CLOSED = auto()
