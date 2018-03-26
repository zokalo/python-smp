import enum


@enum.unique
class AccountCredentialPermission(enum.IntFlag):
    pages = 1
    posts = 2
    audio = 4
    video = 8
    photos = 16
