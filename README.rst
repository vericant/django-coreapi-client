#####################
Django CoreAPI client
#####################

A small requests-based RPC client for Django projects that talk to
DRF services via a runtime-fetched schema.

Since 2.0 the ``coreapi`` package is no longer used; the client fetches and
parses the schema itself and performs plain JSON HTTP calls with
``requests``. The public interface is unchanged from 1.x.

Since 2.1 both schema flavors are supported and auto-detected from the
schema response: corejson (DRF's legacy coreapi generator) and OpenAPI 3.x
(e.g. drf-spectacular). OpenAPI paths are mapped onto the same key chains
the coreapi generator produced, so call sites are identical either way.


#####
Usage
#####

Define settings:

.. code-block:: python

    COREAPI_CLIENT = {
        'example_server': {
            'SCHEMA_URL': 'https://example.com/api/schema/',
            'AUTH_USERNAME': 'client-example',
            'AUTH_PASSWORD': 'password-example',
        },
    }

Initialize client:

.. code-block:: python

   from django_coreapi_client import Client

   client = Client('example_server')


Access API endpoints according to the schema, e.g.

.. code-block:: python

   users = client.api.users.list()
   project = client.api.users.projects.read(id=7)
   new_project = client.api.users.projects.create(name='xxx', user_id=3)

Responses are plain dicts (or lists). Server errors (4xx/5xx) raise
``django_coreapi_client.exceptions.ErrorMessage``:

.. code-block:: python

   from django_coreapi_client.exceptions import ErrorMessage

   try:
       client.api.users.projects.read(id=404)
   except ErrorMessage as e:
       print(e.error.title)   # '404 Not Found'
       print(e.error.content) # decoded response body


#######
Testing
#######

.. code-block:: bash

   pip install -e .[testing]
   DJANGO_SETTINGS_MODULE=test_settings pytest
