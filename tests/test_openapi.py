import json

import pytest

import django_coreapi_client
from django_coreapi_client.document import Link
from django_coreapi_client.exceptions import ErrorMessage, ParseError
from django_coreapi_client.openapi import parse_openapi

from .conftest import SCHEMA_URL

# Shaped like a drf-spectacular document for the endpoints Breeze2020 uses.
# No 'servers' entry (spectacular default): paths are host-absolute.
OPENAPI_SCHEMA = {
    'openapi': '3.0.3',
    'info': {'title': 'VICKI API', 'version': '0.0.0'},
    'paths': {
        '/interview/api/interviews-2-breeze/': {
            'get': {
                'operationId': 'interview_api_interviews_2_breeze_list',
                'parameters': [
                    {'name': 'page', 'in': 'query', 'required': False,
                     'schema': {'type': 'integer'}},
                ],
                'responses': {'200': {'description': ''}},
            },
        },
        '/interview/api/interviews/{id}/': {
            'get': {
                'operationId': 'interview_api_interviews_retrieve',
                'parameters': [
                    {'name': 'id', 'in': 'path', 'required': True,
                     'schema': {'type': 'integer'}},
                ],
                'responses': {'200': {'description': ''}},
            },
        },
        '/interview/api/interview-onlinemeetings-2-breeze/': {
            'get': {
                'operationId':
                    'interview_api_interview_onlinemeetings_2_breeze_list',
                'parameters': [
                    {'name': 'page', 'in': 'query', 'required': False,
                     'schema': {'type': 'integer'}},
                ],
                'responses': {'200': {'description': ''}},
            },
        },
        '/users/api/vericant-users/{id}/': {
            'get': {
                'operationId': 'users_api_vericant_users_retrieve',
                'parameters': [
                    {'name': 'id', 'in': 'path', 'required': True,
                     'schema': {'type': 'integer'}},
                ],
                'responses': {'200': {'description': ''}},
            },
        },
        '/harvest/api/breeze-webvideo-items/': {
            'post': {
                'operationId': 'harvest_api_breeze_webvideo_items_create',
                'requestBody': {
                    'content': {
                        'application/json': {
                            'schema':
                                {'$ref': '#/components/schemas/WebVideoItem'},
                        },
                    },
                },
                'responses': {'201': {'description': ''}},
            },
        },
        '/api/scheduled/sync/': {
            'post': {
                'operationId': 'api_scheduled_sync_create',
                'requestBody': {
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'array',
                                'items': {'type': 'object'},
                            },
                        },
                    },
                },
                'responses': {'200': {'description': ''}},
            },
        },
        '/api/things/{id}/': {
            'patch': {
                'operationId': 'api_things_partial_update',
                'parameters': [
                    {'name': 'id', 'in': 'path', 'required': True,
                     'schema': {'type': 'integer'}},
                ],
                'requestBody': {
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'object',
                                'properties': {'due_date': {'type': 'string'}},
                            },
                        },
                    },
                },
                'responses': {'200': {'description': ''}},
            },
            'delete': {
                'operationId': 'api_things_destroy',
                'parameters': [
                    {'name': 'id', 'in': 'path', 'required': True,
                     'schema': {'type': 'integer'}},
                ],
                'responses': {'204': {'description': ''}},
            },
        },
    },
    'components': {
        'schemas': {
            'WebVideoItem': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer', 'readOnly': True},
                    'harvest_id': {'type': 'integer'},
                    'web_video_type': {'type': 'string'},
                    'component': {'type': 'string'},
                    'filename': {'type': 'string'},
                },
                'required': ['harvest_id'],
            },
        },
    },
}


@pytest.fixture
def openapi_client(mocked_responses):
    mocked_responses.get(
        SCHEMA_URL,
        body=json.dumps(OPENAPI_SCHEMA),
        content_type='application/vnd.oai.openapi+json',
    )
    return django_coreapi_client.Client('example_server')


class TestParseOpenapi:

    def test_breeze_chain_shapes_resolve(self):
        document = parse_openapi(OPENAPI_SCHEMA, base_url=SCHEMA_URL)
        chains = [
            ['interview', 'api', 'interviews-2-breeze', 'list'],
            ['interview', 'api', 'interviews', 'read'],
            ['interview', 'api', 'interview-onlinemeetings-2-breeze', 'list'],
            ['users', 'api', 'vericant-users', 'read'],
            ['harvest', 'api', 'breeze-webvideo-items', 'create'],
        ]
        for chain in chains:
            assert isinstance(document.lookup_link(chain), Link)

    def test_paths_resolve_against_schema_host(self):
        document = parse_openapi(OPENAPI_SCHEMA, base_url=SCHEMA_URL)
        link = document.lookup_link(['interview', 'api', 'interviews', 'read'])
        assert link.url == 'https://example.com/interview/api/interviews/{id}/'

    def test_path_pk_coerced_to_id(self):
        # drf-spectacular keeps SCHEMA_COERCE_PATH_PK on by default; the
        # parser must surface 'id' path params for .read(id=...) calls.
        document = parse_openapi(OPENAPI_SCHEMA, base_url=SCHEMA_URL)
        link = document.lookup_link(['users', 'api', 'vericant-users', 'read'])
        fields = {field.name: field for field in link.fields}
        assert fields['id'].location == 'path'
        assert fields['id'].required is True

    def test_request_body_object_becomes_form_fields(self):
        document = parse_openapi(OPENAPI_SCHEMA, base_url=SCHEMA_URL)
        link = document.lookup_link(
            ['harvest', 'api', 'breeze-webvideo-items', 'create'])
        names = {field.name for field in link.fields}
        assert names == {'harvest_id', 'web_video_type', 'component',
                         'filename'}
        assert all(field.location == 'form' for field in link.fields)

    def test_request_body_array_becomes_body_field(self):
        document = parse_openapi(OPENAPI_SCHEMA, base_url=SCHEMA_URL)
        link = document.lookup_link(['api', 'scheduled', 'sync', 'create'])
        assert [(f.name, f.location) for f in link.fields] == \
            [('data', 'body')]

    def test_server_url_respected(self):
        data = dict(OPENAPI_SCHEMA)
        data['servers'] = [{'url': 'https://api.example.org'}]
        document = parse_openapi(data, base_url=SCHEMA_URL)
        link = document.lookup_link(['interview', 'api', 'interviews', 'read'])
        assert link.url == \
            'https://api.example.org/interview/api/interviews/{id}/'

    def test_non_openapi_document_raises(self):
        with pytest.raises(ParseError):
            parse_openapi({'_type': 'document'})


class TestOpenapiClientEndToEnd:

    def test_schema_autodetected_by_content_type(self, openapi_client):
        assert openapi_client.schema.title == 'VICKI API'

    def test_schema_autodetected_by_sniffing_payload(self, mocked_responses):
        mocked_responses.get(
            SCHEMA_URL,
            body=json.dumps(OPENAPI_SCHEMA),
            content_type='application/json',
        )
        client = django_coreapi_client.Client('example_server')
        assert client.schema.title == 'VICKI API'

    def test_list_with_page_param(self, openapi_client, mocked_responses):
        mocked_responses.get(
            'https://example.com/interview/api/interviews-2-breeze/',
            json={'results': [], 'next': None})
        response = openapi_client.interview.api['interviews-2-breeze'].list(
            page=3)
        assert response == {'results': [], 'next': None}
        request = mocked_responses.calls[-1].request
        assert request.url.endswith('/interviews-2-breeze/?page=3')

    def test_read_with_id(self, openapi_client, mocked_responses):
        mocked_responses.get(
            'https://example.com/interview/api/interviews/42/',
            json={'id': 42, 'status': 'CANCELED'})
        response = openapi_client.interview.api.interviews.read(id=42)
        assert response == {'id': 42, 'status': 'CANCELED'}

    def test_create_upload_payload(self, openapi_client, mocked_responses):
        mocked_responses.post(
            'https://example.com/harvest/api/breeze-webvideo-items/',
            json={'id': 1}, status=201)
        openapi_client.harvest.api['breeze-webvideo-items'].create(
            harvest_id=7, web_video_type='input', component='main',
            filename='b2://x.mp4')
        request = mocked_responses.calls[-1].request
        assert json.loads(request.body) == {
            'harvest_id': 7, 'web_video_type': 'input',
            'component': 'main', 'filename': 'b2://x.mp4'}

    def test_404_error_title(self, openapi_client, mocked_responses):
        mocked_responses.get(
            'https://example.com/interview/api/interviews/99/',
            status=404, json={'detail': 'Not found.'})
        with pytest.raises(ErrorMessage) as exc_info:
            openapi_client.interview.api.interviews.read(id=99)
        assert exc_info.value.error.title == '404 Not Found'

    def test_delete_returns_none(self, openapi_client, mocked_responses):
        mocked_responses.delete('https://example.com/api/things/5/',
                                status=204)
        assert openapi_client.api.things.delete(id=5) is None

    def test_partial_update_path_and_body(self, openapi_client,
                                          mocked_responses):
        mocked_responses.patch('https://example.com/api/things/5/',
                               json={'due_date': '2026-07-08'})
        openapi_client.api.things.partial_update(id=5,
                                                 due_date='2026-07-08')
        request = mocked_responses.calls[-1].request
        assert request.url == 'https://example.com/api/things/5/'
        assert json.loads(request.body) == {'due_date': '2026-07-08'}
