"""
Exceptions with a surface compatible with ``coreapi.exceptions``, so callers
can migrate by swapping the import only.
"""
from __future__ import unicode_literals, absolute_import


class CoreAPIClientError(Exception):
    """Base class for all django-coreapi-client errors."""


class Error(object):
    """
    Error payload attached to an ``ErrorMessage``.

    Mirrors the parts of ``coreapi.document.Error`` that callers rely on:
    ``title`` (e.g. ``'404 Not Found'``) and the decoded response ``content``.
    """

    def __init__(self, title='', content=None):
        self.title = title
        self.content = content if content is not None else {}

    def get(self, key, default=None):
        if isinstance(self.content, dict):
            return self.content.get(key, default)
        return default

    def __eq__(self, other):
        return (
            isinstance(other, Error)
            and self.title == other.title
            and self.content == other.content
        )

    def __repr__(self):
        return 'Error(title={!r}, content={!r})'.format(self.title, self.content)

    def __str__(self):
        if self.content:
            return '<Error: {}> {}'.format(self.title, self.content)
        return '<Error: {}>'.format(self.title)


class ErrorMessage(CoreAPIClientError):
    """
    Raised when the server responds with a 4xx/5xx status.

    ``exception.error.title`` carries the HTTP status line (e.g.
    ``'404 Not Found'``), matching the old ``coreapi.exceptions.ErrorMessage``.
    """

    def __init__(self, error):
        if not isinstance(error, Error):
            error = Error(title=str(error))
        self.error = error
        super(ErrorMessage, self).__init__(str(error))


class ParameterError(CoreAPIClientError):
    """Raised for unknown or missing required action parameters."""


class LinkLookupError(CoreAPIClientError):
    """Raised when a key chain does not resolve to a link in the schema."""


class ParseError(CoreAPIClientError):
    """Raised when a schema document or response cannot be decoded."""
