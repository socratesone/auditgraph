---
title: "Incident token=S011_SECRET_SENTINEL title"
---

This note describes an incident report. The sentinel value used to verify
redaction is referenced only in the frontmatter above (in the form
`token=...` which the credential_kv detector recognizes). The body prose
intentionally does NOT mention the sentinel because the redactor's regex
detectors target credential-shaped strings (key=value pairs, JWT segments,
bearer tokens, vendor tokens, URL credentials, private keys), not free-text
English prose mentions of secrets.
