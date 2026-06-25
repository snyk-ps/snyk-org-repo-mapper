# http-transport-retries Specification

## Purpose

Normative requirements for transient transport failures when the Bitbucket Server and Snyk REST clients use stdlib `urllib` with the project’s shared retry helper.

## Requirements

### Requirement: Bitbucket Server HTTP client SHALL retry RemoteDisconnected

The Bitbucket Server REST client that uses `urllib.request.urlopen` SHALL treat `http.client.RemoteDisconnected` as a retriable failure when wrapped by the project’s standard HTTP retry helper, using the same `max_attempts` and base backoff parameters as for `urllib.error.URLError` and `TimeoutError`. When all attempts fail, the caller SHALL receive a non–raw-library error consistent with other Bitbucket network failures (clear message, prior exception chained).

#### Scenario: Transient disconnect during paginated request

- **WHEN** `urlopen` raises `RemoteDisconnected` on a Bitbucket API request and a subsequent attempt returns a valid HTTP response
- **THEN** the client SHALL return parsed JSON (or bytes for raw file paths) without surfacing `RemoteDisconnected` to the caller

#### Scenario: Exhausted retries on Bitbucket

- **WHEN** `RemoteDisconnected` persists through all configured retry attempts
- **THEN** the client SHALL raise an error that indicates a Bitbucket network failure and SHALL NOT leave an unwrapped `RemoteDisconnected` as the sole user-facing exception type on that code path

### Requirement: Snyk REST HTTP client SHALL retry RemoteDisconnected

The Snyk REST client that uses `urllib.request.urlopen` SHALL treat `http.client.RemoteDisconnected` as a retriable failure under the same retry policy as `urllib.error.URLError` and `TimeoutError`.

#### Scenario: Transient disconnect during Snyk JSON request

- **WHEN** `urlopen` raises `RemoteDisconnected` and a later attempt succeeds
- **THEN** the client SHALL return the parsed JSON document to the caller
