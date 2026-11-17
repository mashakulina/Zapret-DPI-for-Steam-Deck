"""Configure Decky's custom store through its local settings API (stdlib only)."""
import json
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID


UNOFFICIAL_STORE_URL = 'https://deckyloader.ru/store/plugins'
CUSTOM_STORE = 2
_API_URL = 'http://127.0.0.1:1337'
_MAX_RESPONSE = 32 * 1024


class DeckyStoreError(RuntimeError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class DeckySettingsClient:
    """Use the legacy HTTP API without replacing Decky's single WebSocket client."""

    def __init__(self, opener=None, timeout=4):
        self.opener = opener or build_opener(ProxyHandler({}), _NoRedirect())
        self.timeout = timeout
        self._token = None

    def _request(self, path, payload=None):
        headers = {}
        data = None
        if payload is not None:
            if self._token is None:
                raw_token = self._request('/auth/token')
                try:
                    token = raw_token.decode('ascii').strip()
                    UUID(token)
                except (ValueError, UnicodeError) as error:
                    raise DeckyStoreError('Decky Loader вернул неверный токен доступа.') from error
                self._token = token
            headers = {'Content-Type': 'application/json', 'X-Decky-Auth': self._token}
            data = json.dumps(payload).encode('utf-8')
        request = Request(_API_URL + path, data=data, headers=headers)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read(_MAX_RESPONSE + 1)
        except HTTPError as error:
            error.close()
            if error.code in (401, 403):
                message = 'Decky Loader отклонил доступ. Повторите подключение магазина.'
            elif error.code == 404:
                message = 'Эта версия Decky Loader не поддерживает используемый API настроек.'
            else:
                message = f'Decky Loader вернул HTTP {error.code}.'
            raise DeckyStoreError(message) from error
        except (URLError, OSError, HTTPException) as error:
            raise DeckyStoreError('Decky Loader недоступен. Установите и запустите его, затем повторите подключение.') from error
        if len(body) > _MAX_RESPONSE:
            raise DeckyStoreError('Decky Loader вернул слишком большой ответ.')
        return body

    def _method(self, method, payload):
        try:
            result = json.loads(self._request('/methods/' + method, payload))
        except (ValueError, UnicodeError) as error:
            raise DeckyStoreError('Не удалось прочитать ответ Decky Loader.') from error
        if not isinstance(result, dict) or result.get('success') is not True:
            raise DeckyStoreError('Decky Loader не подтвердил изменение или чтение настройки.')
        if 'result' not in result:
            raise DeckyStoreError('В ответе Decky Loader отсутствует результат операции.')
        return result['result']

    def get_setting(self, key, default):
        return self._method('get_setting', {'key': key, 'default': default})

    def set_setting(self, key, value):
        self._method('set_setting', {'key': key, 'value': value})


def configure_unofficial_store(client=None):
    """Select the requested store; restore only our changes if a write fails."""
    client = client or DeckySettingsClient()
    previous = {'store-url': client.get_setting('store-url', ''),
                'store': client.get_setting('store', 0)}
    if not isinstance(previous['store-url'], str) or type(previous['store']) is not int or previous['store'] not in (0, 1, 2):
        raise DeckyStoreError('Настройки магазина Decky имеют неподдерживаемый формат. Они не изменены.')
    desired = {'store-url': UNOFFICIAL_STORE_URL, 'store': CUSTOM_STORE}
    pending = [key for key in desired if previous[key] != desired[key]]
    if not pending:
        return False

    attempted = []
    try:
        # URL must be saved before selecting the custom store.
        for key in pending:
            if client.get_setting(key, previous[key]) != previous[key]:
                raise DeckyStoreError('Настройки магазина изменились в Decky. Повторите подключение.')
            attempted.append(key)
            client.set_setting(key, desired[key])
        if any(client.get_setting(key, previous[key]) != value for key, value in desired.items()):
            raise DeckyStoreError('Decky Loader не сохранил выбранный магазин.')
    except DeckyStoreError as error:
        failures = []
        for key in reversed(attempted):
            try:
                current = client.get_setting(key, previous[key])
                if current not in (desired[key], previous[key]):
                    raise DeckyStoreError('Настройка уже изменена другим действием.')
                if current != previous[key]:
                    client.set_setting(key, previous[key])
                    if client.get_setting(key, previous[key]) != previous[key]:
                        raise DeckyStoreError('Не удалось подтвердить восстановление.')
            except DeckyStoreError:
                failures.append(key)
        if failures:
            raise DeckyStoreError(f'{error}\nНе удалось восстановить настройки: {", ".join(failures)}. '
                                 'Проверьте магазин в настройках Decky Loader.') from error
        if attempted:
            raise DeckyStoreError(f'{error}\nПрежние настройки магазина восстановлены.') from error
        raise
    return True
