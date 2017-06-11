import enum


@enum.unique
class AccessType(enum.IntEnum):
    token = 1
    cookies = 2

    @classmethod
    def as_choices(cls):
        return [(attr.value, attr.name) for attr in cls]
