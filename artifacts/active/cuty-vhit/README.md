# Cuty VHit / HTTP-fast evidence

Large third-party JS bundles were intentionally not committed. The durable evidence here is the CDP lifecycle/fetch snapshots plus the replay probes:

- `cuty_lifecycle_probe_latest.json`: browser state/performance/localStorage snapshots showing `fp.vhit.io` and `vhit.io/api/request` during the final page.
- `cuty_fetch_probe_latest.json`: monkey-patched fetch log showing the VHit request shapes.
- `../cuty_http_vhit_replay_probe.py`: HTTP replay probe that verified the final URL.
