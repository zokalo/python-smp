from typing import List, Union

import datetime


_undefined_group_cls = type('undefined_group', (), {})
_undefined_user_cls = type('undefined_user', (), {})


def create_jwt(*,
               app_id: int,
               app_secret: bytes,
               group_id: Union[None, _undefined_group_cls, int] = None,
               user_id: Union[None, _undefined_user_cls, int] = None,
               scopes: Union[None, List[str], str] = None,
               duration: Union[None, datetime.timedelta] = None) -> bytes:
    import jwt

    if duration is None:
        duration = datetime.timedelta(minutes=5)

    payload = {
        'iss': app_id,
        'scp': scopes,
        'exp': datetime.datetime.utcnow() + duration,
    }

    if user_id is not create_jwt.undefined_user:
        payload['sub'] = user_id
    if group_id is not create_jwt.undefined_group:
        payload['grp'] = group_id

    return jwt.encode(payload, app_secret, algorithm='HS256')


create_jwt.undefined_group = _undefined_group_cls()
create_jwt.undefined_user = _undefined_user_cls()
