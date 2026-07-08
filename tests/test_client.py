import base64
import json

import pytest

import django_coreapi_client
from django_coreapi_client.exceptions import ErrorMessage, ParameterError

from .conftest import SCHEMA_URL


def _basic_auth_header(username, password):
    token = base64.b64encode(
        '{}:{}'.format(username, password).encode()).decode()
    return 'Basic {}'.format(token)


class TestSchemaFetch:

    def test_schema_fetched_with_basic_auth_and_accept_header(self, client,
                                                              schema_response):
        request = schema_response.calls[0].request
        assert request.url == SCHEMA_URL
        assert request.headers['Authorization'] == _basic_auth_header(
            'client-example', 'password-example')
        assert 'application/coreapi+json' in request.headers['Accept']

    def test_schema_fetched_once_per_client(self, client, schema_response):
        # Chaining must reuse the already-fetched schema.
        client.api.things.list
        client.api['things-2-breeze']
        schema_calls = [c for c in schema_response.calls
                        if c.request.url == SCHEMA_URL]
        assert len(schema_calls) == 1

    def test_schema_error_raises_error_message(self, mocked_responses):
        mocked_responses.get(SCHEMA_URL, status=403, json={'detail': 'nope'})
        with pytest.raises(ErrorMessage) as exc_info:
            django_coreapi_client.Client('example_server')
        assert exc_info.value.error.title == '403 Forbidden'


class TestChaining:

    def test_attribute_and_item_access_mixed(self, client, schema_response):
        schema_response.get('https://example.com/api/things-2-breeze/',
                            json={'results': [], 'next': None})
        response = client.api['things-2-breeze'].list()
        assert response == {'results': [], 'next': None}

    def test_action_with_explicit_keys(self, client, schema_response):
        schema_response.get('https://example.com/api/things/',
                            json={'results': []})
        response = client.action(['api', 'things', 'list'])
        assert response == {'results': []}


class TestParamRouting:

    def test_query_param(self, client, schema_response):
        schema_response.get('https://example.com/api/things/',
                            json={'results': [1], 'next': None})
        client.api.things.list(page=2)
        request = schema_response.calls[-1].request
        assert request.url == 'https://example.com/api/things/?page=2'

    def test_path_param(self, client, schema_response):
        schema_response.get('https://example.com/api/things/7/',
                            json={'id': 7})
        response = client.api.things.read(id=7)
        assert response == {'id': 7}

    def test_form_params_become_json_body(self, client, schema_response):
        schema_response.post('https://example.com/api/things/',
                             json={'id': 1, 'name': 'x'}, status=201)
        client.api.things.create(name='x', extra='y')
        request = schema_response.calls[-1].request
        assert json.loads(request.body) == {'name': 'x', 'extra': 'y'}
        assert request.headers['Content-Type'] == 'application/json'

    def test_body_param_becomes_entire_body(self, client, schema_response):
        schema_response.post('https://example.com/api/scheduled/sync/',
                             json={'ok': True})
        payload = [{'id': 1}, {'id': 2}]
        client.api.scheduled.sync.create(data=payload)
        request = schema_response.calls[-1].request
        assert json.loads(request.body) == payload

    def test_path_plus_form_partial_update(self, client, schema_response):
        schema_response.patch('https://example.com/api/things/12/patch/',
                              json={'due_date': '2026-07-08'})
        client.api.things.patch.partial_update(vicki_ref=12,
                                               due_date='2026-07-08')
        request = schema_response.calls[-1].request
        assert request.url == 'https://example.com/api/things/12/patch/'
        assert json.loads(request.body) == {'due_date': '2026-07-08'}

    def test_unknown_param_raises(self, client):
        with pytest.raises(ParameterError):
            client.api.things.list(bogus=1)

    def test_missing_required_param_raises(self, client):
        with pytest.raises(ParameterError):
            client.api.things.read()

    def test_request_uses_basic_auth(self, client, schema_response):
        schema_response.get('https://example.com/api/things/',
                            json={'results': []})
        client.api.things.list()
        request = schema_response.calls[-1].request
        assert request.headers['Authorization'] == _basic_auth_header(
            'client-example', 'password-example')


class TestResponses:

    def test_pagination_shape_passthrough(self, client, schema_response):
        body = {'count': 3, 'next': 'https://example.com/api/things/?page=2',
                'previous': None, 'results': [{'id': 1}, {'id': 2}]}
        schema_response.get('https://example.com/api/things/', json=body)
        response = client.api.things.list()
        assert response == body
        assert response['next'] == 'https://example.com/api/things/?page=2'

    def test_empty_body_returns_none(self, client, schema_response):
        schema_response.delete('https://example.com/api/things/3/',
                               status=204)
        assert client.api.things.delete(id=3) is None

    def test_404_raises_error_message_with_title(self, client,
                                                 schema_response):
        schema_response.get('https://example.com/api/things/99/', status=404,
                            json={'detail': 'Not found.'})
        with pytest.raises(ErrorMessage) as exc_info:
            client.api.things.read(id=99)
        error = exc_info.value.error
        assert error.title == '404 Not Found'
        assert error.content == {'detail': 'Not found.'}
        assert '404 Not Found' in str(exc_info.value)

    def test_500_raises_error_message(self, client, schema_response):
        schema_response.post('https://example.com/api/things/', status=500,
                             body='server exploded',
                             content_type='text/plain')
        with pytest.raises(ErrorMessage) as exc_info:
            client.api.things.create(name='x')
        assert exc_info.value.error.title == '500 Internal Server Error'


class TestClientSignature:

    def test_signature_keeps_mock_pattern_working(self, client):
        # Vicki chains produce new Client instances carrying the same
        # transport and schema.
        chained = client.api.things
        assert isinstance(chained, django_coreapi_client.Client)
        assert chained.client is client.client
        assert chained.schema is client.schema
        assert chained._keys == ['api', 'things']

    def test_explicit_schema_and_client_skip_fetch(self, client):
        clone = django_coreapi_client.Client(
            'example_server', keys=['api'], auth=client._auth,
            client=client.client, schema=client.schema)
        assert clone.schema is client.schema
