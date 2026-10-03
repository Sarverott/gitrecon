# Collecting and labeling activity

1. **Collect** into the [[raw-buffer]]:

    ```sh
    gitrecon events org:github --watch     # keep listening (Ctrl+C to stop)
    gitrecon archive 2026-10-01-0 2026-10-01-5
    gitrecon stars sarverott --save
    ```

2. **Look** at what came in: `gitrecon status`, then `gitrecon map` for node kinds,
   relations and hubs; `gitrecon map --node user:octocat` for one entity's neighbours.

3. **Conclude**: `gitrecon label`. Each [[label]] names its target, confidence and the
   events behind it (`--json` for the evidence ids, `--urls` for the pages of the labeled
   entities, `--name star-burst` for one kind).

Everything downstream of the buffer is rebuilt on every run, so new [[rule]]s and
tuned [[threshold]]s apply to the whole history at once.

From Python: `examples/activity-labels/notebook.ipynb`.

## Volume

GH Archive hours are hundreds of MB each nowadays. They are streamed to disk in their
original gzip form; the [[activity-graph]] and the [[labeler]] still read everything into
memory, so analyse days rather than months at a time until DuckDB-backed analysis lands.
