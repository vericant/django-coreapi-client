import pytest

from django_coreapi_client.document import Link, parse_corejson
from django_coreapi_client.exceptions import LinkLookupError, ParseError

from .conftest import COREJSON_SCHEMA, SCHEMA_URL


class TestParseCorejson:

    def test_relative_link_urls_resolve_against_document_url(self):
        document = parse_corejson(COREJSON_SCHEMA)
        link = document.lookup_link(['api', 'things', 'list'])
        assert link.url == 'https://example.com/api/things/'

    def test_document_meta(self):
        document = parse_corejson(COREJSON_SCHEMA)
        assert document.url == SCHEMA_URL
        assert document.title == 'Example API'

    def test_absolute_link_urls_kept(self):
        data = {
            '_type': 'document',
            '_meta': {'url': SCHEMA_URL},
            'ping': {'_type': 'link', 'url': 'https://other.example.com/ping/'},
        }
        document = parse_corejson(data)
        assert document.lookup_link(['ping']).url == \
            'https://other.example.com/ping/'

    def test_link_defaults(self):
        data = {
            '_type': 'document',
            'ping': {'_type': 'link', 'url': '/ping/'},
        }
        link = parse_corejson(data, base_url=SCHEMA_URL).lookup_link(['ping'])
        assert link.action == 'get'
        assert link.fields == []

    def test_field_parsing(self):
        document = parse_corejson(COREJSON_SCHEMA)
        link = document.lookup_link(['api', 'things', 'create'])
        fields = {field.name: field for field in link.fields}
        assert fields['name'].required is True
        assert fields['name'].location == 'form'
        assert fields['extra'].required is False

    def test_lookup_missing_key_raises(self):
        document = parse_corejson(COREJSON_SCHEMA)
        with pytest.raises(LinkLookupError):
            document.lookup_link(['api', 'nope', 'list'])

    def test_lookup_non_link_raises(self):
        document = parse_corejson(COREJSON_SCHEMA)
        with pytest.raises(LinkLookupError):
            document.lookup_link(['api', 'things'])

    def test_non_document_raises(self):
        with pytest.raises(ParseError):
            parse_corejson({'_type': 'link'})

    def test_parsed_link_type(self):
        document = parse_corejson(COREJSON_SCHEMA)
        assert isinstance(document['api']['things']['read'], Link)
