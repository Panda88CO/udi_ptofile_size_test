import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import profile_size_engine as eng  # noqa: E402


def _size(p):
    return len(json.dumps(p).encode('utf-8'))


def test_payload_reaches_target_without_big_overshoot():
    for kb in (15, 50, 90):
        p = eng.generate_payload(kb)
        n = _size(p)
        assert n >= kb * 1024
        assert n < kb * 1024 + 4096


def test_ids_unique():
    p = eng.generate_payload(40)
    ed_ids = [e['id'] for e in p['editors']]
    nd_ids = [n['id'] for n in p['nodedefs']]
    assert len(ed_ids) == len(set(ed_ids))
    assert len(nd_ids) == len(set(nd_ids))


def test_include_st_flag():
    with_st = eng.generate_payload(20, include_st=True)
    without = eng.generate_payload(20, include_st=False)
    for nd in with_st['nodedefs']:
        assert any(pr['id'] == 'ST' for pr in nd['properties'])
    for nd in without['nodedefs']:
        if nd['id'] != 'SETUP':
            assert not any(pr['id'] == 'ST' for pr in nd['properties'])


def test_parse_params_defaults_and_validation():
    params, warns = eng.parse_params({})
    assert params == eng.DEFAULT_PARAMS and warns == []
    params, warns = eng.parse_params({'mode': 'bogus', 'sweep_step': 'x', 'large_kb': '99999'})
    assert params['mode'] == 'sweep'
    assert params['sweep_step'] == 10 and params['large_kb'] == 90
    assert len(warns) == 3
    params, warns = eng.parse_params({'sweep_start': '200', 'sweep_end': '50'})
    assert (params['sweep_start'], params['sweep_end']) == (20, 100)
    assert warns
    params, warns = eng.parse_params({'mode': 'file'})
    assert params['mode'] == 'sweep' and warns
    params, _ = eng.parse_params({'run_on_start': 'TRUE', 'include_st': 'no'})
    assert params['run_on_start'] is True and params['include_st'] is False


def _threshold_updater(limit_bytes):
    def updater(payload):
        if _size(payload) > limit_bytes:
            raise RuntimeError('Update profile request failed')
    return updater


def test_sweep_finds_boundary():
    done = {}
    logs = []
    engine = eng.make_engine(_threshold_updater(64 * 1024), logs.append,
                             on_done=lambda s, r: done.update(s))
    params, _ = eng.parse_params({'sweep_start': '20', 'sweep_end': '100', 'sweep_step': '20'})
    results = engine.run(params)
    # sizes 20, 40, 60, 80, 100 KB against a 64 KB limit
    assert [r['success'] for r in results] == [True, True, True, False, False]
    assert done['code'] == 2
    assert 60 <= done['max_pass_kb'] < 64 <= done['min_fail_kb']
    assert not done['non_monotonic']
    assert any('CONCLUSION' in m for m in logs)


def test_all_pass_and_all_fail_codes():
    params, _ = eng.parse_params({'mode': 'test', 'small_kb': '10', 'large_kb': '20'})
    seen = {}
    eng.make_engine(lambda p: None, lambda m: None, on_done=lambda s, r: seen.update(s)).run(params)
    assert seen['code'] == 1

    def boom(p):
        raise RuntimeError('nope')
    eng.make_engine(boom, lambda m: None, on_done=lambda s, r: seen.update(s)).run(params)
    assert seen['code'] == 3 and seen['max_pass_kb'] == 0


def test_file_mode(tmp_path):
    f = tmp_path / 'p.json'
    f.write_text(json.dumps({'editors': [], 'nodedefs': []}))
    sent = []
    params, _ = eng.parse_params({'mode': 'file', 'profile_file': 'p.json'})
    engine = eng.make_engine(sent.append, lambda m: None, base_dir=str(tmp_path))
    results = engine.run(params)
    assert len(results) == 1 and results[0]['success']
    assert sent[0]['linkdefs'] == []


def test_missing_file_aborts_cleanly():
    logs = []
    params, _ = eng.parse_params({'mode': 'file', 'profile_file': 'nope.json'})
    engine = eng.make_engine(lambda p: None, logs.append, base_dir='/nonexistent')
    assert engine.run(params) is None
    assert any('ERROR' in m for m in logs)
    assert not engine.is_running()
