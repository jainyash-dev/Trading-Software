# Web application architecture

Owner decision D57. The product UI is a browser application. There is no Tauri or Electron shell. No desktop project was left in the tree: the earlier session installed a temporary Rust toolchain outside the repository and did not write a `src-tauri` directory.

## Processes

- `python3 platform/run_api.py` starts one FastAPI process on `127.0.0.1`. Port 0 is the default. A second start prints `already running` and exits. It reads `instance.port` only.
- The React app is Vite. `npm run dev` in `platform/web` proxies `/api` to `http://127.0.0.1:8765`. Set `GTF_BIND_PORT=8765` when you want that default. `GTF_PUBLIC_ORIGINS=http://127.0.0.1:5173` allows the dev origin if the proxy is not used.
- `npm run build` writes `platform/web/dist`. The API serves that directory from the same origin when it exists.

## Packages

The directory is `platform/` and it has no `__init__.py`, so Python's standard-library `platform` module still imports. Application code imports `gtf_platform`. Web dependencies stay in `platform/web/package.json`. They are not root Python dependencies.

## What the UI does not do

Zone detection, freshness, MTF eligibility, G0-G8 evaluation, trade-plan maths, and risk maths stay in `nse/`. The screens render supplied fields. Unknown status text is `Unknown status: <code>` and is not Pass.
