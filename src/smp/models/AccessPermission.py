import enum


@enum.unique
class AccessPermission(enum.IntEnum):
    pages = 1
    posts = 2
    audio = 3
    video = 4
    photos = 5

    @classmethod
    def as_choices(cls):
        return [(attr.value, attr.name) for attr in cls]
