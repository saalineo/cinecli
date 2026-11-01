# cinecli architecture

`cinecli` is deliberately split into small layers so that a failing torrent
index, player, or optional integration does not compromise the rest of the CLI.

```text
simple CLI -> search orchestrator -> provider adapters -> normalized results
          -> selection -> torrent client -> local loopback stream/player
```

## User-facing contract

The normal interface is `cinecli <title>`, `cinecli -s <title>`, and
`cinecli -d <title>`. `cinecli --doctor` is the single troubleshooting entry
point. Configuration is optional; safe defaults must work without it.

## Reliability invariants

- Provider failures are isolated and reported as unavailable, never treated as
  proof that a title does not exist.
- Search work has a bounded collection budget and validates all user limits.
- Configuration never silently overrides an explicitly disabled provider.
- Streaming uses an isolated, disposable cache by default; downloads use the
  chosen durable output directory.
- Downloads fail on a stalled swarm instead of claiming a completed file.
- Network privacy diagnostics state their limits. Proxy protocols are explicit:
  HTTP for index traffic and SOCKS5 for libtorrent traffic.

## Extension points

Providers implement `search(query, net, mode, lang, quality)` and return the
normalized result schema used by `search.searcher`. New providers should include
recorded fixture tests, bounded requests, clear errors, and no side effects on
configuration. Playback and download share `TorrentClient`; user interaction
does not depend on provider-specific fields.
