import datetime

import jwt


def create_jwt(app_id, app_secret, subowner_id=None, duration=None):
    if duration is None:
        duration = datetime.timedelta(minutes=5)

    return jwt.encode({
        'iss': app_id,
        'sub': subowner_id,
        # 'scp': [],  # TODO: set scope
        'exp': datetime.datetime.utcnow() + duration,
    }, app_secret, algorithm='HS256')
