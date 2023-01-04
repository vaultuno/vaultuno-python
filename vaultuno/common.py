import os


class URL(str):
    def __new__(cls, *value):
        if value:
            v0 = value[0]
            if not (isinstance(v0, str) or isinstance(v0, URL)):
                raise TypeError(f'Unexpected type for URL: "{type(v0)}"')
            if not (v0.startswith('http://') or v0.startswith('https://') or
                    v0.startswith('ws://') or v0.startswith('wss://')):
                raise ValueError(f'Passed string value "{v0}" is not an'
                                 f' "http*://" or "ws*://" URL')
        return str.__new__(cls, *value)


def get_base_url() -> URL:
    return URL(os.environ.get(
        'VU_API_BASE_URL', 'http://localhost:8080').rstrip('/'))


def get_api_version(api_version: str) -> str:
    api_version = api_version or os.environ.get('VU_API_VERSION')
    if api_version is None:
        api_version = 'v1'
    return api_version
