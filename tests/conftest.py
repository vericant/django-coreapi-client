import json

import pytest
import responses

SCHEMA_URL = 'https://example.com/api/schema/'

# Shaped like a DRF coreapi schema: nested sections, links with
# path/query/form/body field locations, and a hyphenated endpoint name.
COREJSON_SCHEMA = {
    '_type': 'document',
    '_meta': {'url': SCHEMA_URL, 'title': 'Example API'},
    'api': {
        'things': {
            'list': {
                '_type': 'link',
                'url': '/api/things/',
                'action': 'get',
                'fields': [{'name': 'page', 'location': 'query'}],
            },
            'create': {
                '_type': 'link',
                'url': '/api/things/',
                'action': 'post',
                'fields': [
                    {'name': 'name', 'required': True, 'location': 'form'},
                    {'name': 'extra', 'location': 'form'},
                ],
            },
            'read': {
                '_type': 'link',
                'url': '/api/things/{id}/',
                'action': 'get',
                'fields': [{'name': 'id', 'required': True, 'location': 'path'}],
            },
            'patch': {
                'partial_update': {
                    '_type': 'link',
                    'url': '/api/things/{vicki_ref}/patch/',
                    'action': 'patch',
                    'fields': [
                        {'name': 'vicki_ref', 'required': True, 'location': 'path'},
                        {'name': 'due_date', 'location': 'form'},
                    ],
                },
            },
            'delete': {
                '_type': 'link',
                'url': '/api/things/{id}/',
                'action': 'delete',
                'fields': [{'name': 'id', 'required': True, 'location': 'path'}],
            },
        },
        'scheduled': {
            'sync': {
                'create': {
                    '_type': 'link',
                    'url': '/api/scheduled/sync/',
                    'action': 'post',
                    'fields': [{'name': 'data', 'location': 'body'}],
                },
            },
        },
        'things-2-breeze': {
            'list': {
                '_type': 'link',
                'url': '/api/things-2-breeze/',
                'action': 'get',
                'fields': [{'name': 'page', 'location': 'query'}],
            },
        },
    },
}


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        yield rsps


@pytest.fixture
def schema_response(mocked_responses):
    mocked_responses.get(
        SCHEMA_URL,
        body=json.dumps(COREJSON_SCHEMA),
        content_type='application/coreapi+json',
    )
    return mocked_responses


@pytest.fixture
def client(schema_response):
    import django_coreapi_client
    return django_coreapi_client.Client('example_server')
