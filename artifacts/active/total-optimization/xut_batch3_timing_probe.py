#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

import xut_live_browser as xut  # noqa: E402
import undetected_chromedriver as uc  # noqa: E402
from claimcoin_autoclaim.iconcaptcha_solver import solve_iconcaptcha_data_url  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('url')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--timeout', type=int, default=300)
    args = ap.parse_args()

    marks = []
    t0 = time.monotonic()

    def mark(name: str, **data):
        marks.append({'name': name, 't': round(time.monotonic() - t0, 3), **data})

    def phase(name: str):
        class P:
            def __enter__(self):
                self.s = time.monotonic(); mark(name + ':start'); return self
            def __exit__(self, exc_type, exc, tb):
                mark(name + ':end', elapsed=round(time.monotonic() - self.s, 3), exc=str(exc) if exc else None)
        return P()

    opts = uc.ChromeOptions()
    opts.binary_location = xut.CHROME_PATH
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--window-size=1400,1000')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--lang=en-US')
    headless = os.getenv('SHORTLINK_BYPASS_XUT_HEADLESS', '0').strip().lower() in {'1', 'true', 'yes'}
    if headless:
        opts.add_argument('--headless=new')
    opts.page_load_strategy = 'eager'

    result = {'status': 0, 'input_url': args.url, 'env_dwell': xut.XUT_GAMESCRATE_DWELL_SECONDS, 'marks': marks, 'facts': {}, 'blockers': []}
    original_solver = xut.solve_canvas_via_local_api

    def profiled_solver(canvas_data_url: str) -> dict:
        s = time.monotonic()
        data = original_solver(canvas_data_url)
        elapsed = round(time.monotonic() - s, 3)
        ok = all(k in data for k in ('click_x', 'click_y'))
        entry = {'elapsed': elapsed, 'provider': data.get('provider'), 'has_click': ok, 'keys': sorted(data.keys())}
        if not ok:
            fs = time.monotonic()
            fallback = solve_iconcaptcha_data_url(canvas_data_url, similarity_threshold=20.0).to_dict()
            entry['fallback_elapsed'] = round(time.monotonic() - fs, 3)
            entry['fallback_keys'] = sorted(fallback.keys())
            entry['fallback_provider'] = 'local-python-direct'
            data = fallback
            data['provider'] = 'local-python-direct-after-bad-api'
        result.setdefault('facts', {}).setdefault('solver_calls', []).append(entry)
        return data

    xut.solve_canvas_via_local_api = profiled_solver
    driver = None
    try:
        with phase('chrome_launch'):
            driver = uc.Chrome(options=opts, use_subprocess=True, headless=headless, version_main=xut.detect_chrome_major())
            driver.set_page_load_timeout(60)
        with phase('initial_get'):
            driver.get(args.url)
            result['facts']['after_initial_get'] = xut.snap(driver, 'after-initial-get')

        with phase('step1_iconcaptcha_to_step2'):
            ok, attempt, history = xut.solve_step1_until_step2(driver)
        result['facts']['step1_ok'] = ok
        result['facts']['step1_attempt'] = attempt
        result['facts']['step1_history'] = history
        result['facts']['after_step1'] = xut.snap(driver, 'after-step1')
        if not ok:
            result['blockers'].append('Step 1 IconCaptcha did not reach Step 2')
            return 0

        with phase('steps2_to_gamescrate'):
            xut.continue_through_steps(driver)
        result['facts']['after_steps2_4'] = xut.snap(driver, 'after-steps2-4')

        with phase('gamescrate_entry_wait'):
            xut.wait_for(lambda: 'gamescrate.app' in driver.current_url or 'Step 5/6' in driver.title or 'Open Final Page' in xut.body_text(driver), timeout=90, interval=1)
        result['facts']['gamescrate_entry'] = xut.snap(driver, 'gamescrate-entry')

        with phase('open_final_visible_wait'):
            xut.wait_for(lambda: 'Open Final Page' in xut.body_text(driver), timeout=120, interval=1)
        result['facts']['open_final_visible'] = xut.snap(driver, 'open-final-visible')

        with phase('gamescrate_dwell'):
            time.sleep(max(0.0, xut.XUT_GAMESCRATE_DWELL_SECONDS))
        result['facts']['open_final_after_dwell'] = xut.snap(driver, 'open-final-after-dwell')

        with phase('open_final_click_plus_post_wait'):
            result['facts']['open_final_clicked'] = xut.click_button_contains(driver, 'open final page')
            time.sleep(3)
        result['facts']['post_open_final'] = xut.snap(driver, 'post-open-final')

        final_url = None
        loop_start = time.monotonic()
        mark('step6_final_wait:start')
        polls = 0
        for _ in range(80):
            polls += 1
            final_url = xut.final_url_from_current_state(driver)
            if final_url:
                break
            time.sleep(1)
        mark('step6_final_wait:end', elapsed=round(time.monotonic() - loop_start, 3), polls=polls, final_url=final_url)
        result['facts']['step6_clickables'] = xut.get_visible_exact_clickables(driver)
        result['facts']['final_state'] = xut.snap(driver, 'final-state')
        result['bypass_url'] = final_url
        result['status'] = 1 if xut.is_final_url(final_url) else 0
        result['message'] = 'XUT_FINAL_OK' if result['status'] else 'XUT_FINAL_NOT_FOUND'
        return 0
    except Exception as e:
        result['message'] = f'EXCEPTION: {e}'
        result['blockers'].append('timing probe exception')
        try:
            if driver:
                result['facts']['exception_state'] = xut.snap(driver, 'exception-state')
        except Exception as se:
            result['facts']['exception_snap_error'] = str(se)
        return 0
    finally:
        result['wall_seconds'] = round(time.monotonic() - t0, 3)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': result.get('status'), 'message': result.get('message'), 'bypass_url': result.get('bypass_url'), 'wall_seconds': result.get('wall_seconds'), 'out': str(args.out)}, ensure_ascii=False))
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == '__main__':
    raise SystemExit(main())
