import enum


@enum.unique
class CredentialExchangeType(enum.IntEnum):
    raw = 1         # both app frontend and app backend can read data
    protected = 2   # app backend can limit frontend to read data
    internal = 3    # only SMP can read data

    @classmethod
    def as_choices(cls):
        return [(attr.value, attr.name) for attr in cls]
