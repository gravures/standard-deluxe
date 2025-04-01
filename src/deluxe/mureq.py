# Copyright (c) 2025 - Gilles Coissac
# This file is part of standard-deluxe library.
#
# standard-deluxe is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
#
# standard-deluxe is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with standard-deluxe. If not, see <https://www.gnu.org/licenses/>
#
# This code was forked from the mureq library:
#   https://github.com/slingamn/mureq.git
#   licensed under the BSD Zero Clause License
#   Copyright (c) 2021 Shivaram Lingamneni
#
# This version of mureq has been modified as follow:
# - include type hints for all the functions and methods in the module.
# - docstrings have been reformatted to accomoddate the formers.
# - the module docstring has been written with the library readme's content.
# - a new case for a raised exception has been added where a possible
#   unbound variable seems to have been missed by original code.
#
# ruff: noqa: DOC201, DOC501, PTH118, PLC0415
"""Mureq is a replacement for python-requests.

>>> mureq.get('https://clients3.google.com/generate_204')
Response(status_code=204)
>>> response = _; response.status_code
204
>>> response.headers['date']
'Sun, 26 Dec 2021 01:56:04 GMT'
>>> response.body
b''
>>> params={'snap': 'certbot', 'interface': 'content'}
>>> response = mureq.get('http://snapd/v2/connections', params=params,
    unix_socket='/run/snapd.socket')
>>> response.status_code
200
>>> response.headers['Content-type']
'application/json'
>>> response.body
b'{"type":"sync","status-code":200,"status":"OK","result":{"established":[],
"plugs":[],"slots":[]}}'
>>> response.json()
{'type': 'sync', 'status-code': 200, 'status': 'OK', 'result': {'established':
[], 'plugs': [], 'slots': []}}

Why?
====

In short: performance (memory consumption), security (resilience to supply-chain
attacks), and simplicity.

Performance
-----------

python-requests is extremely memory-hungry, mainly due to large transitive
dependencies like chardet https://github.com/chardet/chardet that are not needed
by typical consumers. Here's a simple benchmark using Python 3.9.7, as packaged
by Ubuntu 21.10 for amd64:

.. prompt:: bash

    python3 -c "import os; os.system('grep VmRSS /proc/' str(os.getpid()) + '/status')"
    VmRSS:      7404 kB
    python3 -c "import os, mureq; os.system('grep VmRSS /proc/' + str(os.getpid()) + '/status')"
    VmRSS:     13304 kB
    python3 -c "import os, mureq; mureq.get('https://www.google.com');
                os.system('grep VmRSS /proc/' + str(os.getpid()) + '/status')"
    VmRSS:     15872 kB
    python3 -c "import os, requests; os.system('grep VmRSS /proc/' + str(os.getpid()) + '/status')"
    VmRSS:     21488 kB
    python3 -c "import os, requests; requests.get('https://www.google.com');
                os.system('grep VmRSS /proc/' + str(os.getpid()) + '/status')"
    VmRSS:     24352 kB

In terms of the time cost of HTTP requests, any differences between mureq and python-requests
should be negligible, except in the case of workloads that use the connection pooling functionality
of python-requests. Since mureq opens and closes a new connection for each request, migrating such
a workload will incur a performance penalty. Note, however, that the normal python-requests API
(requests.request, requests.get, etc.) also disables connection pooling, `instead closing
the socket immediately to prevent accidental resource leaks <https://github.com/psf/requests/blob/a1a6a549a0143d9b32717dbe3d75cd543ae5a4f6/requests/api.py#L57-L61>`.
In order to use connection pooling, you must explicitly create and manage a `requests.Session
<https://docs.python-requests.org/en/latest/user/advanced/#session-objects>` object.

It's unclear to me whether connection pooling even makes sense in the typical Python context
(single-threaded synchronous I/O, where there's no guarantee that the thread of control will
re-enter the connection pool). It is much easier to implement this correctly in Go
(see: https://pkg.go.dev/net/http#Client).

Security
--------

Together with its transitive dependencies, python-requests is tens of thousands of lines
of third-party code that cannot feasibly be audited. The most common way of distributing
python-requests and its dependencies is `pypi.org <https://pypi.org/>`, which has relatively weak
security properties: as of late 2021 it supports 'hash pinning, but not code signing
<https://flawed.net.nz/2021/02/02/PyPI-Security-State/>`.
Typical Python deployments with third-party dependencies are vulnerable to `supply-chain attacks
<https://en.wikipedia.org/wiki/Supply_chain_attack>` against pypi.org, i.e., compromises of user
credentials on pypi.org (or of pypi.org itself) that allow the introduction of malicious code into
their dependencies.

In contrast, mureq is approximately 350 lines of code that can be audited easily and included
directly in a project. Since mureq's functionality is limited in scope, you should be able
to "install" it and forget about it.

Simplicity
----------

python-requests was an essential addition to the ecosystem when it was created in 2011,
but that time is past, and now in many cases the additional complexity it introduces
is no longer justified:

    1. The standard library has caught up to python-requests in many respects.
    The most important change is PEP 476 https://www.python.org/dev/peps/pep-0476/,
    which began validating TLS certificates by default against the system trust
    store. This change has landed in every version of Python that still receives
    security updates.
    2. Large portions of python-requests are now taken up with compatibility shims
    that cover EOL versions of Python, or that preserve compatibility with
    deprecated versions of the library itself.
    3. python-requests and urllib3 have never actually handled the low-level HTTP
    mechanics specified in RFC 7230 https://datatracker.ietf.org/doc/html/rfc7230
    and its predecessors; this has always been deferred to the standard library
    (http.client https://docs.python.org/3/library/http.client.html in Python 3,
    httplib https://docs.python.org/2/library/httplib.html in Python 2). This is why
    it's so easy to reimplement the core functionality of python-requests in a small
    amount of code.

However, the API design of python-requests is excellent and in my opinion still considerably
superior to that of `urllib.request <https://docs.python.org/3/library/urllib.request.html>`
hence the case for a lightweight third-party library with a requests-like API.

How do I use mureq?
-------------------

The core API (mureq.get, mureq.post, mureq.request, etc.) is similar to python-requests, with
a few differences. For now, see the docstrings in mureq.py itself for documentation.
HTML documentation will be released later if there's a demand for it.

If you're switching from python-requests, there are a few things to keep in mind:

    1. mureq.get, mureq.post, and mureq.request mostly work like the analogous
    python-requests calls https://docs.python-requests.
    org/en/latest/user/quickstart/#make-a-request.
    2. The response type is mureq.HTTPResponse, which exposes fewer methods and
    properties than requests.Response. In particular, it does not have text (since
    mureq doesn't do any encoding detection). Instead, the response body is in the
    body member, which is always of type bytes. (For the sake of compatibility,
    the content property is provided as an alias for body.)
    3. The default way to send a POST body is with the body kwarg, which only
    accepts bytes.
    4. The json kwarg takes an arbitrary object, which is serialized to JSON,
    encoded as UTF-8, and sent as the request body with the usual Content-Type:
    application/json header.
    5. To send a form-encoded POST body, use the form kwarg. This accepts a
    dictionary of key-value pairs, or any object that can be serialized by urllib.
    parse.urlencode https://docs.python.org/3/library/urllib.parse.html#urllib.parse.
    urlencode. It will add the usual Content-Type: application/x-www-form-urlencoded
    header.
    6. To make a request without reading the entire body at once, use with mureq.
    yield_response(url, method, **kwargs). This yields a http.client.HTTPResponse
    https://docs.python.org/3/library/http.client.html#httpresponse-objects. Exiting
    the contextmanager automatically closes the socket.
    7. mureq does not follow HTTP redirections by default. To enable them, use the
    kwarg max_redirects, which takes an integer number of redirects to allow, e.g.
    max_redirects=2.
    8. mureq will throw a subclass of mureq.HTTPException (which is actually just
    `http.client.HTTPException <https://docs.python.org/3/library/http.client.html#http.client.HTTPException>`)
    for any runtime I/O error (including invalid
    HTTP responses, connection failures, timeouts, and exceeding the redirection
    limit). It may throw other exceptions (in particular ValueError) for programming
    errors, such as invalid or inconsistent arguments.
    9. mureq supports two ways of making HTTP requests over a Unix domain stream
    socket:
    • The unix_socket kwarg, which overrides the hostname in the URL, e.g.
    mureq.get('http://snapd/', unix_socket='/run/snapd.socket')
    • The http+unix URL scheme, which take the percent-encoded path as the hostname, e.g.
    http+unix://%2Frun%2Fsnapd.socket/ to connect to /run/snapd.socket.
"""

from __future__ import annotations

import abc
import contextlib
import io
import os.path
import socket
import ssl
import sys
import urllib.parse
from collections.abc import Generator, Mapping, MutableMapping, Sequence
from http.client import HTTPConnection, HTTPException, HTTPMessage, HTTPResponse, HTTPSConnection
from typing import Any, ClassVar, Literal, Protocol, TypeAlias, cast, runtime_checkable


__version__ = "0.2.0"

__all__ = [
    "HTTPException",
    "Response",
    "TooManyRedirects",
    "delete",
    "get",
    "head",
    "patch",
    "post",
    "put",
    "request",
    "yield_response",
]

DEFAULT_TIMEOUT = 15.0
DEFAULT_UA = f"Python {sys.version.split()[0]}"


@runtime_checkable
class Buffer(Protocol, abc.ABC):  # type: ignore[misc]  # pyright: ignore[reportGeneralTypeIssues]
    def __buffer__(self, flags: int, /) -> memoryview: ...


HeaderValue: TypeAlias = Buffer | str | int
HTTPHeaders: TypeAlias = MutableMapping[str, HeaderValue]
HTTPMethod: TypeAlias = Literal[
    "POST", "GET", "HEAD", "PUT", "DELETE", "CONNECT", "OPTIONS", "TRACE", "PATCH"
]
QueryType: TypeAlias = (
    Mapping[Any, Any]
    | Mapping[Any, Sequence[Any]]
    | Sequence[tuple[Any, Any]]
    | Sequence[tuple[Any, Sequence[Any]]]
)


def request(
    method: HTTPMethod, url: str, *, read_limit: int | None = None, **kwargs: Any
) -> Response:
    """Performs an HTTP request and reads the entire response body.

    This function performs an HTTP request using the specified method and URL.
    It handles reading the response and returning it as a `Response` object.

    Args:
        method (HTTPMethod): The HTTP method to use for the request (e.g., 'GET', 'POST').
        url (str): The URL to which the request is sent.
        read_limit (Optional[int]): The maximum number of bytes to read from the response body.
            If None, the entire response body will be read. Defaults to None.
        **kwargs (Any): Additional keyword arguments to be passed to the request.

    Returns:
        Response: An instance of the `Response` class containing the response data.

    Raises:
        HTTPException: If an HTTP error occurs during the request.
    """
    with yield_response(method, url, **kwargs) as response:
        try:
            body = response.read(read_limit)
        except HTTPException:
            raise
        except OSError as e:
            raise HTTPException(str(e)) from e
        return Response(
            response.url,
            response.status,
            _prepare_incoming_headers(response.headers),
            body,
        )


def get(url: str, **kwargs: Any) -> Response:
    """Get performs an HTTP GET request."""
    return request("GET", url=url, **kwargs)


def post(url: str, body: str | None = None, **kwargs: Any) -> Response:
    """Post performs an HTTP POST request."""
    return request("POST", url=url, body=body, **kwargs)


def head(url: str, **kwargs: Any) -> Response:
    """Head performs an HTTP HEAD request."""
    return request("HEAD", url=url, **kwargs)


def put(url: str, body: str | None = None, **kwargs: Any) -> Response:
    """Put performs an HTTP PUT request."""
    return request("PUT", url=url, body=body, **kwargs)


def patch(url: str, body: str | None = None, **kwargs: Any) -> Response:
    """Patch performs an HTTP PATCH request."""
    return request("PATCH", url=url, body=body, **kwargs)


def delete(url: str, **kwargs: Any) -> Response:
    """Delete performs an HTTP DELETE request."""
    return request("DELETE", url=url, **kwargs)


@contextlib.contextmanager
def yield_response(
    method: HTTPMethod,
    url: str,
    *,
    unix_socket: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    headers: HTTPHeaders | None = None,
    params: QueryType | None = None,
    body: bytes | None = None,
    form: QueryType | None = None,
    json: object | None = None,
    verify: bool = True,
    source_address: str | tuple[str, int] | None = None,
    max_redirects: int | None = None,
    ssl_context: ssl.SSLContext | None = None,
) -> Generator[HTTPResponse, Any, None]:
    """Exposes the actual http.client.HTTPResponse.

    This function is a low-level API that exposes the actual
    http.client.HTTPResponse via a context manager.

    Note that unlike mureq.Response, http.client.HTTPResponse does not
    automatically canonicalize multiple appearances of the same header by
    joining them together with a comma delimiter.

    To retrieve canonicalized headers from the response, use response.getheader().
    see: https://docs.python.org/3/library/http.client.html#http.client.HTTPResponse.getheader

    Args:
        method (HTTPMethod): The HTTP method to request (e.g., 'GET', 'POST').
        url (str): The URL to request.
        unix_socket (str | None): Path to Unix domain socket to query,
                                  or None for a normal TCP request.
        timeout (float): Timeout in seconds, or None for no timeout (default: 15 seconds).
        headers (HTTPHeaders | None): HTTP headers as a mapping or list of key-value pairs.
        params (QueryType | None): Parameters to be URL-encoded and added to the query string,
                                   as a mapping or list of key-value pairs.
        body (bytes | None): Payload body of the request.
        form (QueryType | None): Parameters to be form-encoded and sent as the payload body,
                                 as a mapping or list of key-value pairs.
        json (object | None): Object to be serialized as JSON and sent as the payload body.
        verify (bool): Whether to verify TLS certificates (default: True).
        source_address (str | tuple[str, int] | None): Source address to bind to for TCP.
        max_redirects (int | None): Maximum number of redirects to follow, or None (the default)
                                    for no redirection.
        ssl_context (ssl.SSLContext | None): TLS config to control certificate validation,
                                             or None for default behavior.

    Yields:
        HTTPResponse: The actual HTTP response object.

    Raises:
        HTTPException: If an HTTP error occurs during the request.
    """
    headers_ = _prepare_outgoing_headers(headers)
    enc_params = _prepare_params(params)
    body_ = _prepare_body(body, form, json, headers_)
    visited_urls: list[str] = []

    while max_redirects is None or len(visited_urls) <= max_redirects:
        url, conn, path = _prepare_request(
            url,
            enc_params=enc_params,
            timeout=timeout,
            unix_socket=unix_socket,
            verify=verify,
            source_address=source_address,
            ssl_context=ssl_context,
        )
        enc_params = ""  # don't reappend enc_params if we get redirected
        visited_urls.append(url)
        try:
            try:
                conn.request(method, path, headers=headers_, body=body_)
                response = conn.getresponse()
            except HTTPException:
                raise
            except OSError as e:
                # wrap any IOError that is not already an HTTPException
                # in HTTPException, exposing a uniform API for remote errors
                raise HTTPException(str(e)) from e
            redirect_url = _check_redirect(url, response.status, response.headers)
            if max_redirects is None or redirect_url is None:
                response.url = url  # https://bugs.python.org/issue42062
                yield response
                return
            else:
                url = redirect_url
                if response.status == 303:
                    # NOTE: see ->
                    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/303
                    method = "GET"
        finally:
            conn.close()

    raise TooManyRedirects(visited_urls)


class Response:
    """Response contains a completely consumed HTTP response.

    :ivar str url: the retrieved URL, indicating whether a redirection occurred
    :ivar int status_code: the HTTP status code
    :ivar http.client.HTTPMessage headers: the HTTP headers
    :ivar bytes body: the payload body of the response
    """

    __slots__: ClassVar[tuple[str, ...]] = ("body", "headers", "status_code", "url")

    def __init__(
        self,
        url: str,
        status_code: int,
        headers: HTTPMessage,
        body: bytes,
    ) -> None:
        self.url: str = url
        self.status_code: int = status_code
        self.headers: HTTPMessage = headers
        self.body: bytes = body

    def __repr__(self) -> str:
        return f"Response(status_code={self.status_code:d})"

    @property
    def ok(self) -> bool:
        """Returns whether the response had a successful status code.

        (anything other than a 40x or 50x).
        """
        return not (400 <= self.status_code < 600)

    @property
    def content(self) -> bytes:
        """Returns the response body (the `body` member).

        This is an alias for compatibility with requests.Response.
        """
        return self.body

    def raise_for_status(self) -> None:
        """Raise_for_status checks the response's success code.

        raising an exception for error codes.
        """
        if not self.ok:
            raise HTTPErrorStatus(self.status_code)

    def json(self):
        """Attempts to deserialize the response body as UTF-8 encoded JSON."""
        import json as jsonlib

        return jsonlib.loads(self.body)

    def _debugstr(self):
        buf = io.StringIO()
        print("HTTP", self.status_code, file=buf)
        for k, v in self.headers.items():
            print(f"{k}: {v}", file=buf)
        print(file=buf)
        try:
            print(self.body.decode("utf-8"), file=buf)
        except UnicodeDecodeError:
            print(f"<{len(self.body)} bytes binary data>", file=buf)
        return buf.getvalue()


class TooManyRedirects(HTTPException):
    """TooManyRedirects error.

    TooManyRedirects is raised when automatic following of redirects was
    enabled, but the server redirected too many times without completing.
    """


class HTTPErrorStatus(HTTPException):
    """HTTPErrorStatus error.

    HTTPErrorStatus is raised by Response.raise_for_status() to indicate an
    HTTP error code (a 40x or a 50x). Note that a well-formed response with an
    error code does not result in an exception unless raise_for_status() is
    called explicitly.
    """

    def __init__(self, status_code: int) -> None:
        self.status_code: int = status_code

    def __str__(self) -> str:
        return f"HTTP response returned error code {self.status_code:d}"


# end public API, begin internal implementation details

_JSON_CONTENTTYPE = "application/json"
_FORM_CONTENTTYPE = "application/x-www-form-urlencoded"


class UnixHTTPConnection(HTTPConnection):
    """UnixHTTPConnection.

    Subclass of HTTPConnection that connects to a Unix domain
    stream socket instead of a TCP address.
    """

    def __init__(self, path: str, timeout: float = DEFAULT_TIMEOUT) -> None:
        super().__init__("localhost", timeout=timeout)
        self._unix_path: str = path
        self.sock: socket.socket

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout)
            sock.connect(self._unix_path)
        except Exception:
            sock.close()
            raise
        self.sock = sock


def _check_redirect(url: str, status: int, response_headers: HTTPMessage) -> str | None:
    """Return the URL to redirect to, or None for no redirection."""
    if status not in {301, 302, 303, 307, 308}:
        return None
    location = response_headers.get("Location")
    if not location:
        return None
    parsed_location = urllib.parse.urlparse(location)
    if parsed_location.scheme:
        # absolute URL
        return location

    old_url = urllib.parse.urlparse(url)
    if location.startswith("/"):
        # absolute path on old hostname
        return urllib.parse.urlunparse((
            old_url.scheme,
            old_url.netloc,
            parsed_location.path,
            parsed_location.params,
            parsed_location.query,
            parsed_location.fragment,
        ))

    # relative path on old hostname
    old_dir, _old_file = os.path.split(old_url.path)
    new_path = os.path.join(old_dir, location)
    return urllib.parse.urlunparse((
        old_url.scheme,
        old_url.netloc,
        new_path,
        parsed_location.params,
        parsed_location.query,
        parsed_location.fragment,
    ))


def _prepare_outgoing_headers(headers: HTTPHeaders | HTTPMessage | None) -> HTTPHeaders:
    if headers is None:
        headers = HTTPMessage()
    elif not isinstance(headers, HTTPMessage):
        new_headers = HTTPMessage()
        iterator = headers.items() if hasattr(headers, "items") else iter(headers)
        for k, v in iterator:
            new_headers[k] = str(v)
        headers = new_headers

    # NOTE: seems to be necessary for type checkers that do not want
    #       to consider our HTTPHeedears type as acceptable parent type
    headers = cast("HTTPHeaders", dict(headers))

    _setdefault_header(headers, "User-Agent", DEFAULT_UA)
    return headers


# TODO: join multi-headers together so that get(), __getitem__(),
#       etc. behave intuitively, then stuff them back in an HTTPMessage.
def _prepare_incoming_headers(headers: HTTPMessage) -> HTTPMessage:
    headers_dict: dict[str, list[str]] = {}
    for k, v in headers.items():
        headers_dict.setdefault(k, []).append(str(v))
    result = HTTPMessage()
    # note that iterating over headers_dict preserves the original
    # insertion order in all versions since Python 3.6:
    for k, vlist in headers_dict.items():
        result[k] = ",".join(vlist)
    return result


def _setdefault_header(headers: HTTPHeaders, name: str, value: str) -> None:
    if name not in headers:
        headers[name] = value


def _prepare_body(
    body: bytes | None, form: QueryType | None, json: object | None, headers: HTTPHeaders
) -> bytes | str | None:
    if body is not None:
        # if not isinstance(body, bytes):
        #     raise TypeError("body must be bytes or None", type(body))
        return body

    if json is not None:
        _setdefault_header(headers, "Content-Type", _JSON_CONTENTTYPE)
        import json as jsonlib

        return jsonlib.dumps(json).encode("utf-8")

    if form is not None:
        _setdefault_header(headers, "Content-Type", _FORM_CONTENTTYPE)
        return urllib.parse.urlencode(form, doseq=True)

    return None


def _prepare_params(params: QueryType | None) -> str:
    return "" if params is None else urllib.parse.urlencode(params, doseq=True)


def _prepare_request(  # noqa: C901, PLR0912
    url: str,
    *,
    enc_params: str = "",
    timeout: float = DEFAULT_TIMEOUT,
    source_address: str | tuple[str, int] | None = None,
    unix_socket: str | None = None,
    verify: bool = True,
    ssl_context: ssl.SSLContext | None = None,
):
    """Parses the URL, returns the path and the right HTTPConnection subclass."""
    parsed_url = urllib.parse.urlparse(url)
    is_unix = unix_socket is not None
    scheme = parsed_url.scheme.lower()

    if scheme.endswith("+unix"):
        scheme = scheme[:-5]
        is_unix = True
        if scheme == "https":
            msg = "https and unix socket is not implemented"
            raise ValueError(msg)

    if scheme not in {"http", "https"}:
        msg = "unrecognized scheme"
        raise ValueError(msg, scheme)

    is_https = scheme == "https"
    host = parsed_url.hostname
    port = 443 if is_https else 80

    if parsed_url.port:
        port = parsed_url.port

    path = parsed_url.path
    if parsed_url.query:
        if enc_params:
            path = f"{path}?{parsed_url.query}&{enc_params}"
        else:
            path = f"{path}?{parsed_url.query}"
    elif enc_params:
        path = f"{path}?{enc_params}"
    else:
        pass  # just parsed_url.path in this case

    if isinstance(source_address, str):
        source_address = (source_address, 0)

    if is_unix:
        if unix_socket is None:
            unix_socket = urllib.parse.unquote(parsed_url.netloc)
        conn = UnixHTTPConnection(unix_socket, timeout=timeout)
    else:
        if host is None:
            # NOTE: original code seems not to have considered this case,
            #       so not sure what else to do apart raising an exception.
            msg = "hostname is undefined!"
            raise HTTPException(msg)

        if is_https:
            if ssl_context is None:
                ssl_context = ssl.create_default_context()
                if not verify:
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
            conn = HTTPSConnection(
                host,
                port,
                source_address=source_address,
                timeout=timeout,
                context=ssl_context,
            )
        else:
            conn = HTTPConnection(
                host,
                port,
                source_address=source_address,
                timeout=timeout,
            )

    munged_url = urllib.parse.urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        path,
        parsed_url.params,
        "",
        parsed_url.fragment,
    ))
    return munged_url, conn, path
