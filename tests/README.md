# CMMS test kit (dummy data only)

Runs the real `index.html` in a headless browser against a fake Supabase, so changes can be checked before they go live. No real company data and no real passwords are used.

| File | What it is |
|---|---|
| `harness.py` | Loads the app from this repo at `https://demo.local/gfb-cmms/`, swaps `supabase.js` for the fake, blocks other network. `login(page, email)`: `admin@demo.my` (approver) or `tech@demo.my` (editor). |
| `fake-supabase.js` | In-memory Supabase: auth, `docs` / `tombstones`, the save_doc RPC with the same optimistic-lock (`base`) check as live, storage signed URLs. |
| `mkdemo.py` | Builds `demo-data.js` (assets, work orders, parts, suppliers…). Rerun after changing it. |
| `regress.py` | 12 core flows (save, sync, conflict, purchasing, stock, settings, idle sync). Run after every change. |
| `lost_update.py`, `lowprio.py` | Concurrency and code-review regression checks. |
| `status_rules.py` | Asset status automation (repair job, incident, D/O, calibration) and DOSH decision. |
| `dsp_test.py`, `dsp_nophoto.py` | Disposal reports: raise, photo gate, complete, cancel, print, listing. |

Run from this folder (needs `pip install playwright` and `playwright install chromium`):

```
python3 mkdemo.py        # only when demo data changed
python3 regress.py
python3 status_rules.py
```

Notes
- Launch Chromium with `--lang=en-GB` so date fields show DD/MM/YYYY.
- `page.evaluate("...")` calls the result if the expression returns a function; end such snippets with `;0`.
- Screenshots go to `tests/out/` (ignored by git).
