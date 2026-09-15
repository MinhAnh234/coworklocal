Source HEAD: db80289 (preserved)
Branch: perf/fsg-performance

Baseline: app import 1517ms; config 934ms; MainWindow 1742ms (offscreen, local machine).

Packets completed:
- P0: measured constructor with cProfile; dominant cost was provider model discovery (~0.7s network worker) and eager Workspace composition.
- P2: cache history listing by directory mtime/query and coalesce sidebar refresh bursts.
- P3: batch streaming Markdown/layout renders at 40ms; final content remains intact.
- P4: bounded attachment discovery avoids sorting a full recursive tree when a cap is set.
- P5: instrument monitoring log refresh; existing 30-day bounded window retained.
- P6: defer provider model discovery to the first Qt event-loop turn.

After: config 452ms; MainWindow 599ms in the same offscreen smoke benchmark (discovery no longer blocks construction).
Streaming render count is now bounded by batch cadence rather than token count.
Representative history benchmark: 1,000 files 383.6ms cold / 0.8ms cached on this machine.

Relevant commits: c5cb258 (perf: defer discovery and reduce UI refresh work).
Remaining bottleneck: eager Workspace/Co4E/Folder widget construction and import-time PySide6 overhead.

Closure pass (starting HEAD 58b5220): Workspace now keeps Co4E, Folder, and GraphRAG as tab placeholders and creates each once on first selection. MainWindow benchmark: 357.6ms; first opens Co4E 143.1ms, Folder 148.0ms, GraphRAG 270.6ms; repeat opens 0.0–2.4ms. Focused lazy navigation/project tests: 15 passed. Pytest temp failures were ACL/path setup issues, not production assertions; a pre-created writable repository-local temp base allowed the focused gates to pass.
Remaining startup cost is base PySide6/application import and eager Cowork shell; further lazy work is not justified without broader architectural risk.
Performance initiative status: closed for this pass.
