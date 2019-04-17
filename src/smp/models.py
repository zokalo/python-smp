from __future__ import print_function, division, absolute_import, unicode_literals

import enum


@enum.unique
class Medium(enum.IntEnum):
    facebook = 1
    instagram = 2
    twitter = 3
    google = 4
    linkedin = 5
    pinterest = 6
    tumblr = 7
    pushbullet = 8
    telegram = 9
    viber = 10
    snapchat = 11
    periscope = 12
    whatsapp = 13
    slack = 14
    vk = 15
    ok = 16
    bitly = 17


@enum.unique
class PageType(enum.IntEnum):
    user = 1
    public = 2
    group = 3
    event = 4
    bot = 5


@enum.unique
class ProxyAccident(enum.IntEnum):
    unspecified = 0
    connection_error = 1
    write_timeout = 14
    ip_blocked = 11
    ig_checkpoint_required = 2
    ig_checkpoint_challenge_recursion = 3
    ig_password_reset = 4
    ig_response_delay = 5
    ig_caption_removed = 6
    ig_locked = 7
    ig_banned = 8
    ig_post_removed = 9
    ig_comment_removed = 10
    ig_sentry_block = 12
    ig_repeating_logout = 13
