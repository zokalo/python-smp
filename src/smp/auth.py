import datetime


undefined_user = type('undefined_user', (), {})()


def create_jwt(app_id, app_secret, user_id=None, scopes=None, duration=None):
    import jwt

    if duration is None:
        duration = datetime.timedelta(minutes=5)

    payload = {
        'iss': app_id,
        'scp': scopes,
        'exp': datetime.datetime.utcnow() + duration,
    }

    if user_id is not undefined_user:
        payload['sub'] = user_id

    return jwt.encode(payload, app_secret, algorithm='HS256')
