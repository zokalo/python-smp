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
    yandex = 18
    pepper = 19


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


@enum.unique
class ProxyUsage(enum.IntEnum):
    unspecified = 0

    ig_login = 1
    ig_checkpoint = 2

    ig_check_email = 3
    ig_check_username = 4

    ig_userinfo_private_edit = 5
    ig_userinfo_private_get = 6
    ig_userinfo_get = 7

    ig_post = 8
    ig_post_delete = 9
    ig_post_archive = 10
    ig_post_info = 11
    ig_post_type = 12
    ig_post_comments = 13

    ig_comment = 14
    ig_comment_delete = 15

    ig_upload = 16

    ig_search_location = 17
    ig_search_users = 18

    ig_feed = 19
    ig_news = 20
    ig_direct_messages = 21

    ig_get_followers = 22
    ig_get_location_edges = 23
    ig_get_tag_edges = 24

    ig_search_tags = 25

    ig_post_edit = 26

    ig_approve_friendship = 27
    ig_get_followers_pending = 28

    ig_get_live_stream_key = 29
    ig_start_live_streaming= 30
    ig_end_live_streaming= 31
