"""Profile size test engine -- ported from Panda88CO/udi-yolink (profile-size-test branch).

Plain functions plus a closure-based factory (make_engine); no classes, and no
udi_interface dependency, so it can be unit tested anywhere.  The Controller
supplies an `updater` callable (which should call polyglot.updateJsonProfile
and raise on failure) and a `log` callable.
"""
import json
import os
import threading
import time
import types

VERSION = "1.0.3"
MAX_KB = 2048

DEFAULT_PARAMS = {
    'mode': 'sweep',
    'sweep_start': 20,
    'sweep_end': 100,
    'sweep_step': 10,
    'small_kb': 15,
    'large_kb': 90,
    'profile_file': '',
    'include_st': True,
    'run_on_start': False,
}
VALID_MODES = ('sweep', 'test', 'file')
INT_KEYS = ('sweep_start', 'sweep_end', 'sweep_step', 'small_kb', 'large_kb')
BOOL_KEYS = ('include_st', 'run_on_start')
_TRUE = ('1', 'true', 'yes', 'on', 'y')
_FALSE = ('0', 'false', 'no', 'off', 'n')


def parse_params(raw):
    """Turn the customParams dict (all strings) into validated typed params.

    Returns (params, warnings).  Anything invalid falls back to its default.
    """
    params = dict(DEFAULT_PARAMS)
    warnings = []
    raw = raw or {}

    mode = str(raw.get('mode', '') or '').strip().lower()
    if mode:
        if mode in VALID_MODES:
            params['mode'] = mode
        else:
            warnings.append("mode '%s' is not one of sweep/test/file; using 'sweep'" % mode)

    for key in INT_KEYS:
        text = str(raw.get(key, '') or '').strip()
        if not text:
            continue
        try:
            val = int(text)
        except ValueError:
            warnings.append("%s '%s' is not a whole number; using %s" % (key, text, DEFAULT_PARAMS[key]))
            continue
        if val < 1 or val > MAX_KB:
            warnings.append("%s %d is outside 1..%d; using %s" % (key, val, MAX_KB, DEFAULT_PARAMS[key]))
            continue
        params[key] = val

    for key in BOOL_KEYS:
        text = str(raw.get(key, '') or '').strip().lower()
        if not text:
            continue
        if text in _TRUE:
            params[key] = True
        elif text in _FALSE:
            params[key] = False
        else:
            warnings.append("%s '%s' is not true/false; using %s" % (key, text, str(DEFAULT_PARAMS[key]).lower()))

    params['profile_file'] = str(raw.get('profile_file', '') or '').strip()

    if params['sweep_start'] > params['sweep_end']:
        warnings.append("sweep_start (%d) is greater than sweep_end (%d); using defaults for the sweep range"
                        % (params['sweep_start'], params['sweep_end']))
        for key in ('sweep_start', 'sweep_end', 'sweep_step'):
            params[key] = DEFAULT_PARAMS[key]

    if params['mode'] == 'file' and not params['profile_file']:
        warnings.append("mode is 'file' but profile_file is empty; using 'sweep'")
        params['mode'] = 'sweep'

    return params, warnings


SAMPLE_EDITORS = [
    {"id": "STATUS", "ranges": [{"uom": "25", "subset": "0,1", "names": {"0": "Not Connected", "1": "Connected"}}]},
    {"id": "SWSTATE", "ranges": [{"uom": "25", "subset": "0,1,99", "names": {"0": "Off", "1": "On", "99": "Unknown"}}]},
    {"id": "TEMP_C", "ranges": [{"uom": "4", "min": -40, "max": 100, "prec": 1}, {"uom": "25", "subset": "99", "names": {"99": "Unknown"}}]},
    {"id": "TEMP_F", "ranges": [{"uom": "17", "min": -40, "max": 212, "prec": 1}, {"uom": "25", "subset": "99", "names": {"99": "Unknown"}}]},
    {"id": "HUMIDITY", "ranges": [{"uom": "51", "min": 0, "max": 100, "prec": 1}]},
    {"id": "PERCENT", "ranges": [{"uom": "51", "min": 0, "max": 100, "prec": 0}]},
    {"id": "DELAYSEC", "ranges": [{"uom": "57", "min": 0, "max": 86400, "prec": 0}]},
    {"id": "DELAYMIN", "ranges": [{"uom": "44", "min": 0, "max": 1440, "prec": 0}]},
    {"id": "BATLVL", "ranges": [{"uom": "25", "subset": "0,1,2,3,4,99", "names": {"0": "Low", "1": "MedLow", "2": "Med", "3": "MedHigh", "4": "High", "99": "Unknown"}}]},
    {"id": "DOORSTATE", "ranges": [{"uom": "25", "subset": "0,1,99", "names": {"0": "Closed", "1": "Open", "99": "Unknown"}}]},
    {"id": "MOTIONSTATE", "ranges": [{"uom": "25", "subset": "0,1,99", "names": {"0": "No Motion", "1": "Motion", "99": "Unknown"}}]},
    {"id": "WATERSTATE", "ranges": [{"uom": "25", "subset": "0,1,99", "names": {"0": "Dry", "1": "Wet", "99": "Unknown"}}]},
    {"id": "FLOWRATE", "ranges": [{"uom": "69", "min": 0, "max": 10000, "prec": 1}, {"uom": "25", "subset": "99", "names": {"99": "Unknown"}}]},
    {"id": "POWERWATT", "ranges": [{"uom": "73", "min": -1, "max": 5000, "prec": 2}]},
    {"id": "ENERGYKWH", "ranges": [{"uom": "119", "min": -1, "max": 10000, "prec": 2}]},
    {"id": "CMDOPT", "ranges": [{"uom": "25", "subset": "0,1,2,3", "names": {"0": "DON/DOF", "1": "DON Only", "2": "DOF Only", "3": "None"}}]},
    {"id": "UNIXTIME", "ranges": [{"uom": "151", "min": 1700000000, "max": 9999999999, "prec": 0}]},
]


def make_editor(index):
    base = SAMPLE_EDITORS[index % len(SAMPLE_EDITORS)]
    ranges = []
    for r in base['ranges']:
        r_copy = dict(r)
        if 'names' in r_copy:
            r_copy['names'] = dict(r_copy['names'])
        ranges.append(r_copy)
    return {"id": "%s_%d" % (base['id'], index), "ranges": ranges}


def make_nodedef(index, editor_ids, include_st=True):
    node_id = "NODE_%03d" % index
    props = []
    if include_st:
        props.append({"id": "ST", "editor": "STATUS", "name": "Status for Node %d" % index})
    for p_idx in range(5):
        ed = editor_ids[(index * 5 + p_idx) % len(editor_ids)] if editor_ids else "STATUS"
        props.append({"id": "GV%d" % p_idx, "editor": ed, "name": "Driver %d for Node %d" % (p_idx, index)})

    accepts = []
    for c_idx in range(3):
        accepts.append({
            "id": "CMD_%d" % c_idx,
            "name": "Command %d" % c_idx,
            "parameters": [{
                "id": "PARAM1",
                "name": "Param %d" % c_idx,
                "editor": editor_ids[c_idx % len(editor_ids)] if editor_ids else "STATUS",
            }],
        })

    return {
        "id": node_id,
        "name": "Diagnostic Device Node %d" % index,
        "icon": "GenericCtl",
        "properties": props,
        "cmds": {"accepts": accepts, "sends": [{"id": "DON", "name": "DON"}, {"id": "DOF", "name": "DOF"}]},
        "links": {"ctl": [], "rsp": []},
    }


def generate_payload(target_kb, include_st=True):
    """Payload of at least target_kb KB (overshoots by at most one nodedef).

    Size is tracked incrementally (len of each added item + 2 for the
    ', ' separator) instead of re-serializing the whole payload every step.
    """
    target = int(target_kb) * 1024
    editors = [
        {"id": "STATUS", "ranges": [{"uom": "25", "subset": "0,1", "names": {"0": "Not Connected", "1": "Connected"}}]},
        {"id": "READY", "ranges": [{"uom": "25", "subset": "0,1", "names": {"0": "Initializing", "1": "Ready"}}]},
        {"id": "TIME", "ranges": [{"uom": "151", "min": 1700000000, "max": 9999999999, "prec": 0}]},
    ]
    nodedefs = [{
        "id": "SETUP",
        "name": "Diagnostic Profile Controller",
        "icon": "GenericCtl",
        "properties": [
            {"id": "ST", "editor": "STATUS", "name": "Node Server Status"},
            {"id": "GV1", "editor": "READY", "name": "Profile Status"},
            {"id": "TIME", "editor": "TIME", "name": "Last Update"},
        ],
        "cmds": {"accepts": [], "sends": [{"id": "DON", "name": "DON"}, {"id": "DOF", "name": "DOF"}]},
        "links": {"ctl": [], "rsp": []},
    }]
    payload = {"editors": editors, "nodedefs": nodedefs, "linkdefs": []}
    current = len(json.dumps(payload).encode('utf-8'))
    editor_ids = [e["id"] for e in editors]
    ed_count = 0
    nd_count = 1

    while current < target:
        ed = make_editor(ed_count)
        ed_count += 1
        editors.append(ed)
        editor_ids.append(ed["id"])
        current += len(json.dumps(ed).encode('utf-8')) + 2
        if current >= target:
            break
        nd = make_nodedef(nd_count, editor_ids, include_st)
        nd_count += 1
        nodedefs.append(nd)
        current += len(json.dumps(nd).encode('utf-8')) + 2

    return payload


def load_payload_from_file(path, base_dir='.'):
    full = path if os.path.isabs(path) else os.path.join(base_dir, path)
    if not os.path.exists(full):
        raise FileNotFoundError("Profile JSON file not found: %s" % full)
    with open(full, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict) or 'nodedefs' not in data or 'editors' not in data:
        raise ValueError("Invalid profile format in %s: must contain 'nodedefs' and 'editors'" % full)
    return data


def summarize(results):
    """Collapse result rows into the values the results node displays.

    code: 0 = no results, 1 = all passed, 2 = boundary found (mixed), 3 = all failed.
    """
    passed = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    if not results:
        code = 0
    elif passed and failed:
        code = 2
    elif passed:
        code = 1
    else:
        code = 3
    max_pass = max(passed, key=lambda r: r['bytes']) if passed else None
    min_fail = min(failed, key=lambda r: r['bytes']) if failed else None
    return {
        'code': code,
        'max_pass_kb': round(max_pass['size_kb'], 1) if max_pass else 0,
        'min_fail_kb': round(min_fail['size_kb'], 1) if min_fail else 0,
        'non_monotonic': bool(max_pass and min_fail and max_pass['bytes'] > min_fail['bytes']),
    }


def format_report(results):
    lines = []
    lines.append("=" * 80)
    lines.append("        DYNAMIC JSON PROFILE SIZE DIAGNOSTIC REPORT")
    lines.append("=" * 80)
    lines.append("Version   : v%s" % VERSION)
    lines.append("Timestamp : %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
    lines.append("-" * 80)
    lines.append("%-25s | %-12s | %-12s | %-8s | %-10s" % ('Test Description', 'Size', 'Nodes/Eds', 'Time', 'Status'))
    lines.append("-" * 80)
    for r in results:
        lines.append("%-25s | %-12s | %-12s | %-7.2fs | %-10s" % (
            r['name'], r['size_str'], r['counts'], r['elapsed'], 'PASS' if r['success'] else 'FAIL'))
        if not r['success'] and r.get('detail'):
            lines.append("  -- Detail: %s" % r['detail'])
    lines.append("-" * 80)

    s = summarize(results)
    passed = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    if s['code'] == 2:
        max_pass = max(passed, key=lambda r: r['bytes'])
        min_fail = min(failed, key=lambda r: r['bytes'])
        lines.append("CONCLUSION:")
        lines.append("  Smallest failure : %s bytes (%.1f KB)" % (format(min_fail['bytes'], ','), min_fail['size_kb']))
        lines.append("  Largest passing  : %s bytes (%.1f KB)" % (format(max_pass['bytes'], ','), max_pass['size_kb']))
        if s['non_monotonic']:
            lines.append("  [!] Non-monotonic: a larger payload passed than the smallest failure; the")
            lines.append("      failure may not be purely size-related (or the system was in a different state).")
        else:
            lines.append("  Failure boundary lies between %.1f KB and %.1f KB." % (max_pass['size_kb'], min_fail['size_kb']))
    elif s['code'] == 3:
        lines.append("CONCLUSION: all tested payload sizes failed.")
    elif s['code'] == 1:
        lines.append("CONCLUSION: all tested payload sizes passed.")
    else:
        lines.append("CONCLUSION: no results.")
    lines.append("=" * 80)
    return "\n".join(lines)


def make_engine(updater, log, on_done=None, base_dir='.'):
    """Build a test runner.  Returns a namespace with run(params),
    start_async(params), is_running() and state['last_results'].
    Only one run executes at a time; concurrent requests are logged and ignored.
    """
    lock = threading.Lock()
    state = {'last_results': []}

    def send(name, payload):
        n = len(json.dumps(payload).encode('utf-8'))
        nd = len(payload.get('nodedefs', []))
        ed = len(payload.get('editors', []))
        log("  -> %s: %s bytes, %d nodeDefs, %d editors" % (name, format(n, ','), nd, ed))
        start = time.time()
        try:
            res = updater(payload)
            if res is False:
                raise RuntimeError("updateJsonProfile returned False")
            if isinstance(res, dict) and (res.get('error') or res.get('success') is False):
                raise RuntimeError(res.get('message', 'Profile update rejected by Polyglot'))
            ok, msg = True, "accepted (%s bytes)" % format(n, ',')
        except Exception as e:
            ok, msg = False, "%s: %s" % (type(e).__name__, e)
        elapsed = time.time() - start
        return {
            'name': name, 'bytes': n, 'size_kb': n / 1024.0, 'size_str': "%.1f KB" % (n / 1024.0),
            'counts': "%dnd/%ded" % (nd, ed), 'elapsed': elapsed, 'success': ok, 'detail': msg,
        }

    def run_sweep(start_kb, end_kb, step_kb, include_st):
        log("\n[SWEEP] %d KB to %d KB, step %d KB (include_st=%s)" % (start_kb, end_kb, step_kb, include_st))
        results = []
        for size_kb in range(start_kb, end_kb + 1, step_kb):
            results.append(send("Sweep: %d KB" % size_kb, generate_payload(size_kb, include_st)))
        return results

    def run_two_tier(small_kb, large_kb, include_st):
        log("\n[TWO-TIER] small %d KB vs large %d KB (include_st=%s)" % (small_kb, large_kb, include_st))
        return [
            send("Test 1: Small Payload", generate_payload(small_kb, include_st)),
            send("Test 2: Large Payload", generate_payload(large_kb, include_st)),
        ]

    def run_file(path):
        log("\n[FILE] %s" % path)
        payload = load_payload_from_file(path, base_dir)
        payload.setdefault('linkdefs', [])
        return [send("File: %s" % os.path.basename(path), payload)]

    def run(params):
        if not lock.acquire(False):
            log("[INFO] A profile size test is already running; ignoring this request.")
            return None
        try:
            mode = params.get('mode', 'sweep')
            include_st = params.get('include_st', True)
            if mode == 'file':
                results = run_file(params['profile_file'])
            elif mode == 'test':
                results = run_two_tier(params['small_kb'], params['large_kb'], include_st)
            else:
                results = run_sweep(params['sweep_start'], params['sweep_end'], params['sweep_step'], include_st)
            state['last_results'] = results
            log("\n" + format_report(results) + "\n")
            if on_done:
                try:
                    on_done(summarize(results), results)
                except Exception as e:
                    log("[WARN] on_done callback failed: %s" % e)
            return results
        except Exception as e:
            log("[ERROR] Profile size test aborted: %s: %s" % (type(e).__name__, e))
            return None
        finally:
            lock.release()

    def start_async(params):
        t = threading.Thread(target=run, args=(dict(params),), daemon=True)
        t.start()
        return t

    def is_running():
        return lock.locked()

    return types.SimpleNamespace(run=run, start_async=start_async, is_running=is_running, state=state)
