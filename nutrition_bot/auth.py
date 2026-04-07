from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import unquote

from config import get_settings


def verify_telegram_init_data(init_data: str) -> dict | None:
    """
    Верифицирует initData от Telegram WebApp.
    Возвращает dict с данными юзера или None если подпись невалидна.
    """
    # Dev-режим: в разработке возвращаем тестового юзера
    if init_data == 'dev':
        return {'id': 123456, 'first_name': 'Dev', 'username': 'devuser'}

    try:
        parsed = dict(
            item.split('=', 1)
            for item in unquote(init_data).split('&')
            if '=' in item
        )
        received_hash = parsed.pop('hash', None)
        if not received_hash:
            return None

        data_check_string = '\n'.join(
            f'{k}={v}' for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b'WebAppData',
            get_settings().bot_token.encode(),
            hashlib.sha256,
        ).digest()

        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        user_data = json.loads(parsed.get('user', '{}'))
        return user_data
    except Exception:
        return None
