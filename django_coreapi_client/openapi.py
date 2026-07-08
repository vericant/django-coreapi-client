"""
OpenAPI 3.x document parser producing the same ``Document``/``Link`` model
as the corejson parser, with key chains matching what DRF's legacy coreapi
schema generator produced for router-registered ViewSets:

- URL path segments (minus ``{param}`` segments) become nested section keys.
- The final action key derives from the HTTP method: GET is ``read`` when
  the path contains a path parameter, otherwise ``list``; POST is
  ``create``; PATCH is ``partial_update``; PUT is ``update``; DELETE is
  ``delete``.

So ``GET /interview/api/interviews-2-breeze/{id}/`` resolves via
``client.interview.api['interviews-2-breeze'].read(id=...)``, unchanged
from the coreapi days.
"""
from __future__ import unicode_literals, absolute_import

import json
from urllib.parse import urljoin

from .document import Document, Field, Link
from .exceptions import ParseError


def _method_to_action(method, path):
    if method == 'get':
        return 'read' if '{' in path else 'list'
    return {
        'post': 'create',
        'patch': 'partial_update',
        'put': 'update',
        'delete': 'delete',
    }.get(method)


def _resolve_ref(node, root):
    while isinstance(node, dict) and '$ref' in node:
        target = root
        for part in node['$ref'].lstrip('#/').split('/'):
            target = target.get(part, {})
        node = target
    return node if isinstance(node, dict) else {}


def _request_body_fields(operation, root):
    request_body = _resolve_ref(operation.get('requestBody', {}), root)
    content = request_body.get('content', {})
    media = None
    for content_type, media_object in content.items():
        if 'json' in content_type:
            media = media_object
            break
    if media is None:
        return []
    schema = _resolve_ref(media.get('schema', {}), root)

    if schema.get('type') == 'array':
        # DRF's coreapi generator exposed many=True request bodies as a
        # single 'data' field whose value is the entire request body.
        return [Field('data', required=False, location='body')]

    fields = []
    for name, prop in schema.get('properties', {}).items():
        prop = _resolve_ref(prop, root)
        if prop.get('readOnly'):
            continue
        # Required left False on purpose: the server validates form
        # fields; enforcing client-side would misfire on schemas whose
        # 'required' list includes fields callers legitimately omit.
        fields.append(Field(name, required=False, location='form'))
    return fields


def _parameter_fields(operation, path_item, root):
    fields = []
    seen = set()
    parameters = list(path_item.get('parameters', []))
    parameters += operation.get('parameters', [])
    for parameter in parameters:
        parameter = _resolve_ref(parameter, root)
        name = parameter.get('name')
        location = parameter.get('in')
        if location not in ('path', 'query') or name in seen:
            continue
        seen.add(name)
        fields.append(Field(
            name,
            required=bool(parameter.get('required')) or location == 'path',
            location=location,
        ))
    return fields


def _url_maker(data, base_url):
    servers = data.get('servers') or []
    server_url = servers[0].get('url', '') if servers else ''

    if server_url:
        # OpenAPI semantics: paths are appended to the server URL.
        root = urljoin(base_url or '', server_url)
        return lambda path: root.rstrip('/') + path
    # No servers entry (drf-spectacular default): paths are absolute on
    # the host serving the schema.
    return lambda path: urljoin(base_url, path) if base_url else path


def _insert_link(content, path, action, link):
    segments = [
        segment for segment in path.strip('/').split('/')
        if segment and not (segment.startswith('{') and segment.endswith('}'))
    ]
    node = content
    for segment in segments:
        node = node.setdefault(segment, {})
        if isinstance(node, Link):
            raise ParseError(
                'Conflicting path layouts in OpenAPI document at {!r}.'
                .format(path))
    node[action] = link


def parse_openapi(data, base_url=''):
    """Parse a decoded OpenAPI 3.x document into a ``Document``."""
    if not isinstance(data, dict) or 'openapi' not in data:
        raise ParseError('Schema response is not an OpenAPI document.')

    make_url = _url_maker(data, base_url)
    content = {}

    for path, path_item in (data.get('paths') or {}).items():
        for method, operation in path_item.items():
            action = _method_to_action(method, path)
            if action is None:
                continue
            fields = (_parameter_fields(operation, path_item, data)
                      + _request_body_fields(operation, data))
            link = Link(url=make_url(path), action=method, fields=fields)
            _insert_link(content, path, action, link)

    return Document(
        url=base_url,
        title=data.get('info', {}).get('title', ''),
        content=content,
    )


def loads_openapi(text, base_url=''):
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ParseError('Schema response is not valid JSON: {}'.format(exc))
    return parse_openapi(data, base_url=base_url)
