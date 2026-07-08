"""
Minimal schema document model plus a corejson (``application/coreapi+json``)
parser. Only the parts of the format that DRF's coreapi schema generator
emits are supported: nested sections of links with ``url``, ``action`` and
``fields`` (``name`` / ``required`` / ``location``).
"""
from __future__ import unicode_literals, absolute_import

import json
from urllib.parse import urljoin

from .exceptions import LinkLookupError, ParseError


class Field(object):

    def __init__(self, name, required=False, location=''):
        self.name = name
        self.required = required
        self.location = location

    def __repr__(self):
        return 'Field(name={!r}, required={!r}, location={!r})'.format(
            self.name, self.required, self.location)


class Link(object):

    def __init__(self, url, action='get', fields=None):
        self.url = url
        self.action = action or 'get'
        self.fields = fields or []

    def __repr__(self):
        return 'Link(url={!r}, action={!r})'.format(self.url, self.action)


class Document(object):
    """Nested mapping of section names to sub-sections and ``Link`` objects."""

    def __init__(self, url='', title='', content=None):
        self.url = url
        self.title = title
        self.content = content or {}

    def __getitem__(self, key):
        return self.content[key]

    def __contains__(self, key):
        return key in self.content

    def lookup_link(self, keys):
        """Resolve a chain of keys (e.g. ``['api', 'things', 'list']``) to a Link."""
        node = self.content
        for index, key in enumerate(keys):
            try:
                node = node[key]
            except (KeyError, TypeError):
                raise LinkLookupError(
                    'Index {!r} did not reference a link. Key {!r} was not found.'
                    .format(list(keys), key))
        if not isinstance(node, Link):
            raise LinkLookupError(
                'Index {!r} did not reference a link.'.format(list(keys)))
        return node


def _unescape_key(key):
    # corejson escapes reserved-looking keys ('_type', '__type', ...) by
    # prepending an underscore.
    if key.startswith('_') and key.lstrip('_') in ('type', 'meta'):
        return key[1:]
    return key


def _parse_node(value, base_url):
    if isinstance(value, dict):
        if value.get('_type') == 'link':
            fields = [
                Field(
                    name=field.get('name'),
                    required=bool(field.get('required', False)),
                    location=field.get('location', ''),
                )
                for field in value.get('fields', [])
            ]
            return Link(
                url=urljoin(base_url, value.get('url', '')),
                action=value.get('action', 'get'),
                fields=fields,
            )
        return {
            _unescape_key(key): _parse_node(item, base_url)
            for key, item in value.items()
            if key not in ('_type', '_meta')
        }
    if isinstance(value, list):
        return [_parse_node(item, base_url) for item in value]
    return value


def parse_corejson(data, base_url=''):
    """Parse a decoded corejson document into a ``Document``."""
    if not isinstance(data, dict) or data.get('_type') != 'document':
        raise ParseError('Schema response is not a corejson document.')
    meta = data.get('_meta', {})
    url = meta.get('url') or base_url or ''
    content = {
        _unescape_key(key): _parse_node(value, url)
        for key, value in data.items()
        if key not in ('_type', '_meta')
    }
    return Document(url=url, title=meta.get('title', ''), content=content)


def loads_corejson(text, base_url=''):
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ParseError('Schema response is not valid JSON: {}'.format(exc))
    return parse_corejson(data, base_url=base_url)
