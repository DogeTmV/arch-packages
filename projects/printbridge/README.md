# printbridge

A small authenticated local print bridge. It accepts PDF, PNG and UTF-8
plaintext over loopback HTTP, spools each job as JSON, and hands it to the
local `lp` command. A dry-run mode records the exact command without printing.

## Inspiration

Inspired by **Google Cloud Print**, which was discontinued in 2020. This is an
**original reimplementation, no upstream code/assets** were used: it is an
independent spiritual successor with its own name, protocol subset, storage
format and implementation built only on the Python 3 standard library.

## Install

```sh
# Arch Linux (from this repository's package)
makepkg -si

# Or run directly
./printbridge --help
```

Python 3 is the only dependency. Printing itself requires a working `lp`
command and a configured printer; the bridge, spool queue and dry-run mode do
not.

## Usage

```sh
# Set local defaults (stored in ~/.local/share/printbridge/config.json)
printbridge config --token 'a-long-random-secret' --printer Office

# Run the server (binds to 127.0.0.1 by default)
printbridge serve --port 8123 --spool ~/spool
printbridge serve --port 0 --dry-run            # safe experiments, no lp calls

# Submit a file from another local process
printbridge send report.pdf --url http://127.0.0.1:8123/print \
    --token 'a-long-random-secret'

# Inspect and manage the JSON spool
printbridge queue --spool ~/spool
printbridge status --spool ~/spool
printbridge cancel JOB_ID --spool ~/spool
```

`POST /print` requires `Content-Type` of `application/pdf`, `image/png` or
`text/plain` (PDF/PNG payloads are checked against their magic bytes), a
`Content-Length` no larger than 5 MiB, and the token in either
`X-Auth-Token: TOKEN` or `Authorization: Bearer TOKEN`. Accepted requests get
`202` plus the job ID. `GET /health` is an unauthenticated liveness check.

The config file is `~/.local/share/printbridge/config.json`, and the default
spool is `~/.local/share/printbridge/spool/`. `PRINTBRIDGE_CONFIG` and
`PRINTBRIDGE_SPOOL` override those paths. If no token is configured, `serve`
generates a random one-time token and prints it to stderr. Every command
accepts `--help`; `--version` prints the version.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The suite starts an ephemeral server on port 0 in a thread with a temporary
spool and `--dry-run`, so `lp` is never invoked. It covers auth rejection,
content validation, the client round trip, queue/status/cancel and the
loopback default.

## License

MIT — see [LICENSE](LICENSE). Original reimplementation, no upstream
code/assets.
