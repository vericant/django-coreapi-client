2.1.0 (2026-07-08)
------------------

- Add an OpenAPI 3.x document parser alongside the corejson one. The
  schema flavor is auto-detected from the response content type (with a
  payload sniff fallback), so servers exposing drf-spectacular OpenAPI
  documents (e.g. Vicki) and servers still exposing corejson (CAP,
  Schools) work with the same client version.
- OpenAPI paths map onto the same key chains DRF's legacy coreapi
  generator produced (path segments + method-derived action names such
  as ``list``/``read``/``create``/``partial_update``), so existing call
  sites keep working unchanged.


2.0.0 (2026-07-08)
------------------

- Replace the ``coreapi`` dependency with a requests-based implementation.
  The public interface is unchanged: ``Client(name)``, attribute/key
  chaining, ``.read/.list/.create/.partial_update``, plain dict responses.
- The schema (corejson) is still fetched from ``SCHEMA_URL`` at runtime and
  parsed by a small internal parser; parameter routing follows the link
  field locations (``path``/``query``/``form``/``body``) exactly as
  coreapi did.
- New ``django_coreapi_client.exceptions.ErrorMessage`` raised on 4xx/5xx
  responses, with a coreapi-compatible surface (``str(e)`` message and
  ``e.error.title`` such as ``'404 Not Found'``). Callers should swap
  ``coreapi.exceptions.ErrorMessage`` imports to it.
- Empty response bodies (e.g. 204 No Content) return ``None``.
- Dropped Python 2 support; requires Python >= 3.10 and Django >= 4.2.
- Added a pytest-based test suite.


1.1.0 (2017-08-20)
------------------

- Loosening Django version.


1.0.1 (2017-08-11)
------------------

- Performance improvement.


1.0.0 (2017-08-11)
------------------

- Releasing v1.0.0 to PyPi.


0.2.1 (2017-08-11)
------------------

- README.


0.2.0 (2017-08-11)
------------------

- Syntactic sugar.


0.1.0 (2017-08-10)
------------------

- Django CoreAPI client v0.1.0 released.
