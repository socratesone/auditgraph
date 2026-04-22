# Code and Links Demo

We use `PostgreSQL` and `Redis`. Note that `postgresql` is the same as
`PostgreSQL` (case-folded). The `postgresql-client` CLI is different.

```bash
apt install postgresql redis-cli
```

```
raw content with no info string
```

## Links

See [the setup guide](setup.md) for details.

Also [intro][intro-ref].

Visit <https://example.com/docs>.

Or plain https://example.com/bare.

And a broken link: [ghost](does-not-exist.md).

Fragment only: [anchor](#intro).

Combined: [install](setup.md#install).

Query: [with-query](setup.md?tab=install).

Directory: [dir](subdir/).

Image: ![alt text](diagram.png)

[intro-ref]: intro.md "Intro Ref"
