# Blob presence and future multi-server replication

Status: design contract for a future upstream Rust implementation, tracked by
[issue #1](https://github.com/brenorb/blossom-cli/issues/1). This wrapper forwards
arguments and process results; it does not implement HTTP preflight, retries,
replication or the proposed JSON output below.

## Reviewed baseline

The wrapper pins published `blossom-cli` and `blossom-rs` **0.6.0**, with crate VCS
revision `7fd99b563d3155e4675bc5580fba5852871802ea`. The CLI accepts one `--server`;
its `exists` command delegates to the client's existence query. The library's
query answers whether *any* configured server returned a successful HEAD response;
when none succeeds it returns false, including after HTTP or transport failures.
That aggregate boolean cannot describe each replication target's presence.

The issue's separate JavaScript reference was reviewed at
`8157c20e4bf59cf67f15f29b9bffa88bc8dc4d91`. Its `hasBlob()` treats every HTTP status
except 404 as present. `multiServerUpload()` uses that result to mark targets as
already holding the blob; a failed mirror on such a target skips normal upload.
A 500 preflight can therefore suppress the fallback without establishing a replica.
This observation concerns the referenced SDK, not a claim that the Rust client
uses the same status classification.

Sources:

- [Published CLI](https://crates.io/crates/blossom-cli/0.6.0) and
  [library](https://crates.io/crates/blossom-rs/0.6.0).
- [Rust existence query](https://github.com/MonumentalSystems/blossom-rs/blob/7fd99b563d3155e4675bc5580fba5852871802ea/src/client/mod.rs#L302-L325).
- [SDK presence query](https://github.com/hzrd149/blossom-client-sdk/blob/8157c20e4bf59cf67f15f29b9bffa88bc8dc4d91/src/actions/has.ts)
  and [replication flow](https://github.com/hzrd149/blossom-client-sdk/blob/8157c20e4bf59cf67f15f29b9bffa88bc8dc4d91/src/actions/multi-server.ts).

## Presence belongs to a target

Keep `(server, sha256)` results separate. Define three states for a HEAD probe:

| Observation | Presence | Next action |
| --- | --- | --- |
| Final 2xx response | `present` | Record confirmed presence; register ownership if the operation requires it. |
| 404 | `absent` | Attempt normal upload or mirror from a confirmed source. |
| 401 | `unknown` | Resolve authorization; at most one scoped authenticated re-probe when a signer is available. |
| 403 | `unknown` | Report denied authorization; retry only after authorization changes. |
| 429 | `unknown` | Bounded retry respecting Retry-After. |
| 5xx | `unknown` | Bounded retry, then continue to the appropriate fallback or report failure. |
| Timeout, DNS, TLS or other transport failure | `unknown` | Bounded retry; never infer presence or absence. |
| Other non-2xx, including an unhandled redirect | `unknown` | Preserve the status for diagnostics; do not infer presence. |

Only 2xx counts as presence. No non-2xx exception is assumed without a separately
reviewed protocol guarantee. Redirect handling must preserve the requested target
identity; do not forward signed authorization to a different origin.

A successful target cannot establish presence on a failed target. An `exists`
boolean obtained across multiple servers must not gate per-server upload.
Cancellation ends work and reports unfinished targets; it is not absence.

## Replication and fallback

For each requested target:

1. Probe and retain the state, HTTP status/error category and attempt count.
2. If authorization can be resolved with the configured signer, retry HEAD once
   for that target and blob. Scope credentials to that origin, operation and hash;
   lack of credentials leaves the result unknown.
3. For absent or unknown targets, attempt the permitted normal upload, or mirror
   from a source whose blob is confirmed. Never use an unknown target as a source.
4. If mirror/registration fails, keep normal upload eligible. In particular,
   `unknown + failed mirror` must not take a silent "already present" branch.
5. Confirm success only from a successful operation with the expected blob hash
   or a successful subsequent HEAD on the target. A timed-out upload might have
   completed: re-probe before repeating it, while retaining ownership uncertainty.
6. If permissions, retry limits, cancellation or the operation deadline prevent
   further work, emit an explicit failed/unfinished result for that target.

Confirmed content presence and successful ownership registration are distinct.
When registration is requested, a failed registration is an operation failure even
if HEAD confirmed content. Presence does not silently satisfy an ownership request.
An upload fallback that fails also leaves the target failed; eligibility is not a
guarantee that a replica was created.

## Proposed retry policy

Use at most **three attempts per network operation**, including its initial
attempt, and a **30-second deadline per target** covering its probe and fallbacks.
Each request has at most a 5-second timeout and cannot exceed the remaining deadline.
These are proposed initial defaults for upstream review, not current wrapper options.

For 429, 5xx and retryable transport failures, use full-jitter exponential backoff
with a 250-ms base and a 2-second cap. Respect a valid Retry-After delay (delta seconds
or HTTP date) as a minimum. If that delay exceeds the target's remaining budget,
stop and report rate limiting; do not shorten it and retry early. Missing or invalid
Retry-After uses backoff. Do not retry permanent certificate validation errors or
403 without a change in authorization.

The one authenticated HEAD re-probe also counts against these limits. Retries must
not become nested unbounded loops across HEAD, mirror, registration and upload.
Continue independent targets after a target failure; no automatic cross-origin
credentials, payment, or interactive authorization is assumed.

## Proposed result contract

A future upstream operation should expose one record per requested target in text
and JSON output. It should retain the hash, target, preflight state/status or error,
attempts by operation, action taken, final content presence, registration outcome
and final operation result. Never log secret keys or signed authorization headers.

Illustrative JSON for a failed target (not current CLI output):

```json
{
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "targets": [
    {
      "server": "https://replica.example.com",
      "preflight": { "state": "unknown", "http_status": 500, "attempts": 3 },
      "operations": [
        { "action": "mirror", "result": "failed", "attempts": 1 },
        { "action": "upload", "result": "failed", "attempts": 1 }
      ],
      "content_presence": "unknown",
      "registration": "unconfirmed",
      "result": "failed",
      "reason": "target_deadline_exceeded"
    }
  ],
  "result": "failed"
}
```

Text output must name failed targets and distinguish absent from unknown. Report
`partial` when at least one target succeeds and another fails; `failed` when none
succeeds. Exit zero only when every requested target meets the operation's success
criteria; any failed, unconfirmed or cancelled target requires a nonzero exit.
JSON and text must describe the same result. The wrapper must transparently forward
the upstream output and exit status once upstream provides this behavior.

## Required upstream regression matrix

These are acceptance tests for the future Rust implementation. They are not tests
of a protocol implementation in this Python wrapper.

| Fixture | Required assertion |
| --- | --- |
| HEAD 200/204 | Presence is confirmed only for the responding target. |
| HEAD 404 | Target is absent; upload/mirror remains eligible. |
| HEAD 401, then authenticated 200 | Initially unknown; one correctly scoped re-probe may confirm it. |
| HEAD 401 with no signer, or 403 | Unknown, explicit authorization failure; no false success. |
| HEAD 429 with valid, missing, invalid or excessive Retry-After | Unknown; limits/deadline honored, no early retry of a valid delay. |
| HEAD 500, then mirror failure | Unknown; normal upload is attempted when permitted and time remains. |
| HEAD timeout/DNS/transport failure | Unknown; retry bounded; no false proof of presence. |
| HEAD TLS certificate failure | Unknown; no validation bypass or repeated permanent-error loop. |
| HEAD 500, then successful fallback upload | Only the successful fallback confirms the replica. |
| Timed-out upload, then successful HEAD | Content confirmed without assuming successful registration. |
| Target A 200; target B 500 and failed fallback | Per-target state retained; aggregate result partial and exit nonzero. |
| All targets fail; cancellation; deadline exhaustion | Every requested target represented; operation unsuccessful and exit nonzero. |
| Present content, failed requested ownership registration | Registration failure remains visible; exit nonzero. |
| Text/JSON serialization | Same target outcomes, no secret material, no omitted failed targets. |

Use local mock servers and controlled clocks/RNG for deterministic retry tests.
Exercise the orchestration through failed mirror and upload fallback, not just a
status-classification helper. Run protocol tests against the upstream Rust client;
then add wrapper delegation tests against the resulting published CLI before
updating the wrapper's pin. Publishing an upstream implementation and verifying
this matrix remain separate work from recording this contract.
