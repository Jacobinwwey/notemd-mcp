# Markdown integrity and MCP execution reliability

## Baseline and architectural decision

Source: Obsidian NotEMD 1.9.12, commit `0f493b8d3cd60553e5a517660ca1a729ce4acdfc`. The target owns a Python/FastAPI processing backend and a Node stdio bridge. Diagram endpoints return Mermaid text; there is no Drawnix layout, SVG/PDF renderer or diagnostics modal to migrate directly.

Useful source contracts are conservative normalization, asynchronous cancellation/retry behavior and durable diagnostic visibility. Some old source helpers still strip punctuation or unescape money, so translating those implementations wholesale would reproduce the failures.

## Implemented components and root causes

| Owner | Previous failure | Resulting behavior |
| --- | --- | --- |
| `markdown_processing.py` | Global quote removal; arrow-based fence closure; deletion of inner code fences; escaped dollars changed | One ownership scanner, complete outer-envelope removal only, preserved labels/future families/code/currency/EOL, narrow malformed-tag normalization |
| `notemd_core.py` retry | `time.sleep` blocked the event loop; permanent configuration failures retried; cancellation inconsistent | Async backoff; only transient HTTP/transport failures retry; pre-cancellation and native task cancellation propagate |
| Batch file writes | Direct overwrite and newline normalization | Strict UTF-8 read, exact text comparison, same-directory staging/fsync/fresh-read/replace, skipped symlink files, explicit read-only errors and no-op preservation |
| `process-output.js`, `cli.js` | Child logs mixed into protocol stdout; protocol error codes flattened | Human logs to stderr, protocol-only stdout, retained MethodNotFound, sanitized bridge errors, import-safe CLI |
| Backend startup | All-interface bind; health could belong to another service | Loopback bridge and per-child instance handshake; explicit direct-HTTP host/port environment variables |
| Packaging/tests | Python wheel omitted modules; wrong console entry; test script mocked production and deleted a fixed directory | Explicit py_modules and real entry point; new modules in npm allowlist; production tests with disposable fixtures |

Final review reproduced a label-repair preservation bug in the sibling skills project and added the corresponding indented-code protection here. It also found Google keys in HTTP request URLs, Windows read-only staging residue, and a symlink-entry startup regression. Keys now use the supported request header, read-only input is rejected before staging, and CLI launch detection compares the real entry path.

## Compatibility

HTTP route names, MCP tool names/aliases and existing response fields remain stable. The public `cancelled` boolean means pre-cancellation, not a live cancellation token. Python task cancellation works; SDK request cancellation is not connected through the HTTP bridge yet.

Python >=3.10 and Node >=22.19 are the supported baseline. The CLI bridge still uses port 8000. Direct HTTP execution can set `NOTEMD_HOST` and `NOTEMD_PORT`; external exposure requires deployment authentication. Stdout consumers must treat stdout as protocol, with diagnostics collected from stderr.

Syntax cleanup does not implement a Mermaid parser. Unsupported syntax is preserved, not declared renderable. No PDF export or UI folding is claimed. Newline/BOM preservation applies to owned repair operations, not to every model-generated text response.

## Deferred migration candidates

1. Connect MCP request cancellation through HTTP to backend task lifetime, including child shutdown on stdin EOF.
2. Move rename/delete backlinks to complete transactional operations with vault containment and explicit partial-failure results. These historical paths are outside this syntax-repair update.
3. Introduce rendered artifacts only through a named capability boundary with validated MIME/output, renderer version and lineage; browser CSS/PDF internals do not belong in the text backend.
4. Extract provider transports from the broad core module if a later provider expansion justifies the boundary. Avoid creating pass-through service layers now.

Staged replacement catches source changes before commit but is not a filesystem-wide compare-and-swap lock against unrelated writers. Unbounded provider responses, end-to-end authorization and all legacy file mutations were not audited as solved.

## Validation and delivery

- `npm test`: 4 tests passed for compatible tool routing, protocol errors, child log isolation, sensitive-response omission and npm-style symlink entry.
- `npm run test:python`: 13 tests passed for production processing, Markdown protection, transient retry, nonblocking cancellation, write failures/read-only cleanup, Google credential transport and configuration log redaction.
- Newly added edge-case regressions failed before fixes and passed afterward.
- Python wheel built and installed outside the checkout; all four modules and the console entry resolved from the installed artifact.
- npm package contents include both new runtime modules. Source-distribution manifest includes requirements.
- CI verifies Linux/Python 3.10 and Windows/Python 3.13 with Node 22.19, tests and both packaging surfaces.
- No live provider, translation API, LM Studio or GUI operation was used. Documentation translations were authored directly by the coordinating assistant.

Implementation and local acceptance are complete. Version remains 0.6.1: these are source changes after that registry release, not overwritten or newly published npm/PyPI packages.
