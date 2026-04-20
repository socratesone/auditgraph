# Contract: Redaction detector categories

Defines the reporting-category contract for the redaction detector set after Spec 027. Specifies which credential formats map to which category name, what the category names mean to downstream consumers, and what MUST NOT change when future detectors are added.

Applies to: User Story 4 / FR-012 through FR-015 / Clarification Q6.

## Category set (post-Spec-027)

| Category name | Meaning | Rotation workflow |
|---|---|---|
| `credential` | Generic `key=value` credential keywords in document text | Depends on keyword; text-substring level |
| `jwt` | JSON Web Token (three base64 segments separated by dots) | Re-issue token, invalidate session |
| `bearer` | `Authorization: Bearer <token>` header literal | Re-issue token, update client config |
| `url_credential` | Basic auth credentials embedded in a URL (`https://user:pass@host/`) | Rotate credential, update URL references |
| `vendor_token` | Developer platform tokens (GitHub, Slack) | Per-user token rotation via platform UI |
| **`cloud_keys`** (NEW) | Cloud IAM credentials (AWS, GCP, Anthropic, OpenAI, Stripe) | Cloud console rotation, possibly cascading permission updates |
| `pem_private_key` | PEM-encoded private key block | Regenerate keypair, update all trusting parties |

## Why `cloud_keys` is separate from `vendor_token`

The two categories cover disjoint credential classes with materially different operational characteristics:

1. **Blast radius.** An AWS access key grants programmatic access to infrastructure, storage, and services — potentially terabytes of data and the ability to launch instances, read S3, query RDS. A GitHub `ghp_` token grants repository access — typically smaller scope, typically recoverable via re-clone. An OpenAI or Anthropic key grants API usage that maps to spend (a different concern: billing fraud rather than data exfiltration).

2. **Rotation workflow.** Cloud IAM rotation requires: navigate to IAM console, generate new credential, update SDK config, possibly update IAM policies attached to the principal, possibly invalidate old credential. Developer platform rotation requires: generate new token via platform UI, update one or two dotfiles, done. These are workflows a different team runs, with different tooling, on different time horizons.

3. **Compliance treatment.** Cloud IAM credentials are typically named explicitly in compliance frameworks (PCI, HIPAA, SOC2). Developer platform tokens are typically categorized under "development credentials" with different (usually weaker) requirements. Conflating them in reports forces the reader to look at every entry to determine severity; separating them gives the reader a directly-actionable category.

A user seeing `vendor_token: 8, cloud_keys: 2` in a redaction summary knows immediately that the two `cloud_keys` matches are the priority. A user seeing `vendor_token: 10` with the two categories merged has to inspect each entry before they can triage.

## Assignment table

### `credential` (extended by FR-013)

Matched by `credential_kv` detector (`utils/redaction.py`). Pattern shape: `(?i)\b(<keyword>)\s*[:=]\s*<value>`.

Keywords (existing + new):

| Keyword | Existing or New | Example |
|---|---|---|
| `password` | existing | `password=hunter2` |
| `secret` | existing | `secret: abc123` |
| `token` | existing | `token=xyz` |
| `api_key` | existing | `api_key=my-key` |
| `apikey` | existing | `apikey=my-key` |
| `client_secret` | existing | `client_secret: xyz` |
| `private_key` | existing | `private_key=...` |
| `aws_access_key_id` | NEW | `aws_access_key_id=AKIA...` |
| `aws_secret_access_key` | NEW | `aws_secret_access_key=abc...` |
| `auth_token` | NEW | `auth_token: xyz` |
| `access_token` | NEW | `access_token=xyz` |
| `refresh_token` | NEW | `refresh_token=xyz` |
| `session_token` | NEW | `session_token=xyz` |
| `passwd` | NEW | `passwd=hunter2` |
| `pwd` | NEW | `pwd=hunter2` |
| `bearer` | NEW | `bearer=xyz` |
| `auth` | NEW | `auth=xyz` |

**Note**: `aws_access_key_id=AKIA...` is intentionally caught by BOTH the `credential` detector (via the `aws_access_key_id` keyword) AND the `cloud_keys` detector (via the `AKIA[0-9A-Z]{16}` pattern). The redactor replaces the matched substring in both cases; double-coverage is desirable for defense in depth. Summary reports count each match once (the first detector that matches wins; plan phase picks which detector runs first).

### `cloud_keys` (NEW)

One new detector (or a family of detectors sharing the category; plan phase decides). Matches ALL of:

| Provider | Pattern | Reference |
|---|---|---|
| AWS | `AKIA[0-9A-Z]{16}` | Official AWS access key format |
| Google | `AIza[0-9A-Za-z_-]{35}` | Google API key format |
| Anthropic | `sk-ant-api\d{2}-[A-Za-z0-9_-]{40,}` | Anthropic API key format (as of 2026) |
| OpenAI | `sk-proj-[A-Za-z0-9_-]{40,}` or `sk-[A-Za-z0-9]{48}` | OpenAI API key formats (project-scoped + legacy) |
| Stripe (live) | `sk_live_[A-Za-z0-9]{24,}` | Stripe live secret key format |

The exact regex for each pattern is a plan-phase decision; this contract defines WHICH prefixes belong to this category, not the specific regex syntax.

Test format inventory specific examples (for FR-015 positive tests):

```
AKIAIOSFODNN7EXAMPLE           (AWS, 20 chars total)
AIzaSyD-EXAMPLE-ex4mpleKey-ABCDEFGHIJK1234   (Google, ~39 chars total)
sk-ant-api03-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXA_xyz   (Anthropic)
sk-proj-EXAMPLEexampleEXAMPLEexampleEXAMPLEexampleEXAMPLEexample   (OpenAI)
sk_live_EXAMPLEexampleEXAMPLEex   (Stripe, 24+ chars after prefix)
```

### `vendor_token` (extended by FR-012)

Stays narrow to GitHub and Slack developer platform tokens. The existing regex is extended to cover new GitHub prefixes but NOT cloud providers.

| Prefix | Existing or New | Provider | Example |
|---|---|---|---|
| `ghp_` | existing | GitHub classic PAT | `ghp_abc12345678901234567890123456789012345` |
| `xox[baprs]-` | existing | Slack tokens | `xoxp-1234567890-1234567890-abc...` |
| `github_pat_` | NEW | GitHub fine-grained PAT | `github_pat_11ABCDEFG0abc...` |
| `gho_` | NEW | GitHub OAuth user-to-server | `gho_abc...` |
| `ghu_` | NEW | GitHub user-to-server (GH App) | `ghu_abc...` |
| `ghs_` | NEW | GitHub server-to-server | `ghs_abc...` |
| `ghr_` | NEW | GitHub refresh token | `ghr_abc...` |
| `xoxe.xoxp-` | NEW | Slack new-format token (rotated tokens) | `xoxe.xoxp-1-...` |

Not in `vendor_token`: AWS, GCP, OpenAI, Anthropic, Stripe — those are `cloud_keys`.

## Reporting contract

The `RedactionSummary.by_category` dict uses category names as keys and integer match counts as values. Post-Spec-027, a representative summary looks like:

```json
{
  "by_category": {
    "credential": 3,
    "cloud_keys": 2,
    "vendor_token": 1,
    "jwt": 0,
    "bearer": 0,
    "url_credential": 0,
    "pem_private_key": 0
  },
  "total": 6
}
```

### Stable requirements

1. **Category names are stable across releases.** Once a category name is defined by a shipped spec, it MUST NOT be renamed in a later spec. New detectors use new category names.
2. **Two categories appear as independent dict entries.** Summary consumers that want to merge them can do so locally, but the redactor does not do the merge for them.
3. **Zero-count entries may be omitted or included at plan-phase discretion.** Both `{"credential": 3, "cloud_keys": 2}` and `{"credential": 3, "cloud_keys": 2, "jwt": 0, ...}` are valid representations. Downstream consumers MUST handle both.
4. **Order within the dict is deterministic.** When the dict is serialized (e.g., to JSON), keys are sorted alphabetically so identical inputs produce identical output.

## Testing contract (FR-015)

Every format added by this spec requires:

1. **At least one positive test** — a document containing one instance of the format is redacted, and the format's substring is absent from the redacted output.
2. **At least one negative test** — a visually-similar benign string is NOT redacted. Examples:
   - For AWS `AKIA`: a benign string like `"AKIA_like_this_but_lowercase"` or `"AKIAFOO"` (not 20 chars total) is not matched.
   - For Google `AIza`: a benign string like `"Mozilla/5.0 Aiza..."` (wrong case) is not matched.
   - For OpenAI `sk-proj-`: a benign string like `"my sk-proj-planning-file.md"` (shorter than the key length) is not matched.
3. **A summary assertion** — after redacting a document containing multiple formats across both `cloud_keys` and `vendor_token`, the `by_category` dict shows both entries with their expected counts, confirming the severity-signal split.

## Not allowed

- Merging `cloud_keys` and `vendor_token` into a single category even when they appear together in the same document. They are distinct reporting buckets regardless of document content.
- Renaming `vendor_token` to something broader (e.g., `developer_token`) in this spec. The existing name is stable; future renames need their own spec and backwards-compat plan.
- Adding a `cloud_keys` subcategory per provider (e.g., `cloud_keys.aws`, `cloud_keys.gcp`). Clarification Q6 explicitly rejected the per-vendor granularity. One category, one dict entry.
- Including the matched secret value in the summary. The redactor reports counts and categories; the sentinel never appears in reports.
