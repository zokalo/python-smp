import datetime

import jwt


def create_jwt(app_id, app_secret, user_id=None, scopes=None, duration=None):
    if duration is None:
        duration = datetime.timedelta(minutes=5)

    return jwt.encode({
        'iss': app_id,
        'sub': user_id,
        'scp': scopes,
        'exp': datetime.datetime.utcnow() + duration,
    }, app_secret, algorithm='HS256')
