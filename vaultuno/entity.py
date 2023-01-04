import pandas as pd
import pprint
import re
from enum import Enum

ISO8601YMD = re.compile(r'\d{4}-\d{2}-\d{2}T')
NY = 'America/New_York'


class Entity(object):
    def __init__(self, raw):
        self._raw = raw

    def __getattr__(self, key):
        if key in self._raw:
            val = self._raw[key]
            if isinstance(val, str) and key.endswith('Date') and ISO8601YMD.match(val):
                return pd.Timestamp(val)
            else:
                return val
        return super().__getattribute__(key)

    def __repr__(self):
        return '{name}({raw})'.format(
            name=self.__class__.__name__,
            raw=pprint.pformat(self._raw, indent=4))


class ProviderType(str, Enum):
    ALPACA_PROVIDER = '244000ff-74d7-4cc4-8149-3efc9197c71e'


class RebalancingFrequency(str, Enum):
    NEVER = "NEVER"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class RebalanceState(str, Enum):
    MATCHING = "MATCHING"
    SELLING = "SELLING"
    BUYING = "BUYING"
    CANCELING = "CANCELING"
    READY = "READY"


class Profile(Entity):
    """
    User profile
    """
    pass


class BrokerAccount(Entity):
    """
    Brokerage account
    """
    pass


class Portfolio(Entity):
    """
    Portfolio
    """
    pass


class Position(Entity):
    """
    Position
    """
    pass


class Performance(Entity):
    """
    Portfolio or account performance information
    """
    pass
