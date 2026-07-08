"""
Requests-based replacement for ``coreapi.Client``: fetches the schema
document and performs actions against its links, preserving coreapi's
parameter routing and error behavior.
"""
from __future__ import unicode_literals, absolute_import

import requests
import uritemplate

from .document import Document, loads_corejson
from .exceptions import Error, ErrorMessage, ParameterError, ParseError

SCHEMA_ACCEPT = 'application/coreapi+json, application/vnd.oai.openapi+json'

_BODY_UNSET = object()


def _decode_response(response):
    if not response.content:
        return None
    content_type = response.headers.get('Content-Type', '')
    if 'json' in content_type:
        try:
            return response.json()
        except ValueError:
            pass
    return response.text


class HTTPClient(object):
    """
    Drop-in stand-in for the old ``coreapi.Client``: exposes ``get(url)`` to
    fetch+parse a schema and ``action(document, keys, params=...)``.
    """

    def __init__(self, auth=None):
        self.auth = auth
        self.session = requests.Session()

    def get(self, url):
        response = self.session.get(
            url, auth=self.auth, headers={'Accept': SCHEMA_ACCEPT})
        if response.status_code >= 400:
            raise ErrorMessage(Error(
                title='{} {}'.format(response.status_code, response.reason),
                content=_decode_response(response),
            ))
        return self.parse_schema(response, base_url=url)

    def parse_schema(self, response, base_url=''):
        return loads_corejson(response.text, base_url=base_url)

    def action(self, document, keys, params=None):
        if not isinstance(document, Document):
            raise ParseError(
                'action() requires a schema Document, got {!r}'.format(document))
        if isinstance(keys, str):
            keys = keys.split()
        link = document.lookup_link(keys)
        return self.transition(link, params or {})

    def transition(self, link, params):
        path_params, query_params, body = self._route_params(link, params)

        url = uritemplate.expand(link.url, path_params)
        method = link.action.upper()

        request_kwargs = {'auth': self.auth}
        if query_params:
            request_kwargs['params'] = query_params
        if body is not _BODY_UNSET:
            request_kwargs['json'] = body

        response = self.session.request(method, url, **request_kwargs)

        if response.status_code >= 400:
            raise ErrorMessage(Error(
                title='{} {}'.format(response.status_code, response.reason),
                content=_decode_response(response),
            ))
        return _decode_response(response)

    @staticmethod
    def _route_params(link, params):
        fields = {field.name: field for field in link.fields}

        unknown = [key for key in params if key not in fields]
        if unknown:
            raise ParameterError(
                'Unknown parameter(s) {} for link {!r}. Valid parameters: {}'
                .format(sorted(unknown), link.url, sorted(fields)))
        missing = [
            field.name for field in link.fields
            if field.required and field.name not in params
        ]
        if missing:
            raise ParameterError(
                'Missing required parameter(s) {} for link {!r}.'
                .format(sorted(missing), link.url))

        # coreapi's default when a field has no explicit location.
        default_location = 'query' if link.action in ('get', 'delete') else 'form'

        path_params = {}
        query_params = {}
        form_params = {}
        body = _BODY_UNSET
        for name, value in params.items():
            location = fields[name].location or default_location
            if location == 'path':
                path_params[name] = value
            elif location == 'query':
                query_params[name] = value
            elif location == 'body':
                # The single body field's value becomes the entire request
                # body (DRF emits this for many=True serializers).
                body = value
            else:  # 'form'
                form_params[name] = value

        if form_params:
            body = form_params
        return path_params, query_params, body
