"""Fresh residual-F03 review; writes only review3-output; run specified Python -B.
Reuses previous-independent_review.py ONLY with FIX/OUT path assignments changed.
No supplied test_semantics execution. No graph/client/builder execution or import.
"""
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
FIX = OUT.parent / 'review3-fixed'
PYTHON = '/Users/wangyuelin/.hermes/profiles/academic/runtime/venv/bin/python'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def load(path):
    return json.loads(path.read_text())

def freeze():
    raw = (FIX / 'manifest.json').read_bytes()
    manifest = json.loads(raw)
    files = {name: {'expected': expected, 'actual': sha((FIX / name).read_bytes())} for name, expected in manifest.items()}
    return {'manifest_sha256': sha(raw), 'files': files, 'ok': all(v['expected'] == v['actual'] for v in files.values())}

start = freeze()
save('manifest-execution-start.json', start)
assert start['ok']
initial = load(OUT / 'manifest-start.json')
assert initial['ok'] and initial['manifest_sha256'] == start['manifest_sha256']
previous = load(FIX / 'previous-findings.json')
assert [x['id'] for x in previous['findings']] == ['F03']
delta = load(FIX / 'delta.json')
assert set(delta) == {'tools/semantics.py', 'tools/compile_model.py', 'test_semantics.py'}

# Reverse each supplied unified diff in memory; verify both pre/post hashes,
# not merely the after-hash in the current manifest.
delta_results = {}
for name, spec in delta.items():
    current = (FIX / name).read_text()
    lines = current.splitlines(keepends=True)
    diff = spec['diff'].splitlines(keepends=True)
    h = 0
    restored = []
    pos = 0
    while h < len(diff):
        if not diff[h].startswith('@@ '):
            h += 1
            continue
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', diff[h])
        assert match
        target = int(match[3]) - 1
        restored.extend(lines[pos:target])
        pos = target
        h += 1
        while h < len(diff) and not diff[h].startswith('@@ '):
            line = diff[h]
            if line.startswith(' '):
                assert lines[pos] == line[1:]
                restored.append(line[1:]); pos += 1
            elif line.startswith('+'):
                assert lines[pos] == line[1:]
                pos += 1
            elif line.startswith('-'):
                restored.append(line[1:])
            else:
                raise AssertionError('Unexpected diff line')
            h += 1
    restored.extend(lines[pos:])
    before = ''.join(restored).encode()
    after = (FIX / name).read_bytes()
    delta_results[name] = {'beforeSHA256': sha(before), 'afterSHA256': sha(after), 'beforeMatches': sha(before) == spec['beforeSHA256'], 'afterMatches': sha(after) == spec['afterSHA256']}
assert all(x['beforeMatches'] and x['afterMatches'] for x in delta_results.values())
save('delta-verification.json', delta_results)

# Explicitly reuse the previous independent script, with only two assignments changed.
original = (FIX / 'previous-independent_review.py').read_text()
assert original.count("FIX = ROOT / 'review2-fixed'") == 1
assert original.count("OUT = ROOT / 'review2-output'") == 1
reused = original.replace("FIX = ROOT / 'review2-fixed'", "FIX = ROOT / 'review3-fixed'").replace("OUT = ROOT / 'review2-output'", "OUT = ROOT / 'review3-output'")
(OUT / 'reused_previous_independent_review.py').write_text(reused)
command = [PYTHON, '-B', str(OUT / 'reused_previous_independent_review.py')]
run = subprocess.run(command, capture_output=True, text=True)
(OUT / 'reused-stdout.txt').write_text(run.stdout)
(OUT / 'reused-stderr.txt').write_text(run.stderr)
save('reused-execution.json', {'command': command, 'exitCode': run.returncode, 'sourceSHA256': sha(original.encode()), 'executedSHA256': sha(reused.encode()), 'onlyFIXandOUTChanged': reused.replace("FIX = ROOT / 'review3-fixed'", "FIX = ROOT / 'review2-fixed'").replace("OUT = ROOT / 'review3-output'", "OUT = ROOT / 'review2-output'") == original, 'attribution': '复用上一轮独立脚本；非本轮新编独立证明；未运行随附test_semantics.py'})
assert run.returncode == 0
reuse = load(OUT / 'verification.json')
save('reused-verification.json', reuse)
assert reuse['mutations']['count'] == 84
assert reuse['mutations']['rejected'] == 84 and not reuse['failedChecks']
geom = load(OUT / 'geometry-recomputation.json')
assert len(geom['comparisons']) == 58 and all(x['equal'] for x in geom['comparisons'])

sys.path.insert(0, str(FIX / 'tools'))
from compile_model import compile_model, validate_model
from analyze import analyze
import semantics

m, p = compile_model(FIX / 'candidate/model.json')
a = analyze(p)

def rel(model, uid):
    return next(r for r in model['relationships'] if r['id'] == uid)

def raw(graph):
    return next(n for n in graph['nodes'] if n['id'] == 'SOURCE')['properties']['rawModelJson']

fresh = []
validate_original = semantics.validate
ids = ['BOUND-S04-C01', 'R059']
for uid in ids:
    other = ids[1] if uid == ids[0] else ids[0]
    for field in ['sourceUid', 'sourceVersion', 'locator']:
        wrong = {'sourceUid': 'V01:EV09', 'sourceVersion': '1.1', 'locator': rel(m, other)['properties']['locator']}[field]
        assert wrong != rel(m, uid)['properties'][field]
        for mutation in ['missing', 'misplaced']:
            bad_model = copy.deepcopy(m)
            prop = rel(bad_model, uid)['properties']
            if mutation == 'missing':
                prop.pop(field)
            else:
                prop[field] = wrong
            path = OUT / ('counterexample-' + uid + '-' + field + '-' + mutation + '.json')
            path.write_text(json.dumps(bad_model, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
            for route in ['canonical.validate_model', 'canonical.compile_model', 'actualLPG.full_analyze']:
                seen = []
                q = copy.deepcopy(p)
                qp = rel(q, uid)['properties']
                if mutation == 'missing':
                    qp.pop(field)
                else:
                    qp[field] = wrong
                def recording_validate(model):
                    actual = rel(model, uid)['properties']
                    seen.append({'present': field in actual, 'value': actual.get(field), 'assertions': {k: actual[k] for k in ['assertionSourceUid', 'assertionSourceVersion', 'assertionLocator']}})
                    return validate_original(model)
                record = {'relation': uid, 'field': field, 'mutation': mutation, 'route': route, 'wrongValue': wrong if mutation == 'misplaced' else None, 'fixture': path.name, 'fixtureSHA256': sha(path.read_bytes())}
                if route == 'actualLPG.full_analyze':
                    semantics.validate = recording_validate
                try:
                    if route == 'canonical.validate_model':
                        validate_model(copy.deepcopy(bad_model))
                    elif route == 'canonical.compile_model':
                        compile_model(path)
                    else:
                        analyze(q)  # default extensions=True: full production analysis entry point
                    record['rejected'] = False
                except Exception as exc:
                    record.update(rejected=isinstance(exc, ValueError), exceptionType=type(exc).__name__, message=str(exc))
                finally:
                    semantics.validate = validate_original
                if route == 'actualLPG.full_analyze':
                    record['rawModelJsonUnchanged'] = raw(q) == raw(p)
                    record['actualRehydratedValuesSeenByValidator'] = seen
                    assert len(seen) == 1
                    assert seen[0]['present'] == (mutation != 'missing')
                    assert mutation == 'missing' or seen[0]['value'] == wrong
                    assert seen[0]['assertions'] == {k: rel(m, uid)['properties'][k] for k in ['assertionSourceUid', 'assertionSourceVersion', 'assertionLocator']}
                    assert record['rawModelJsonUnchanged']
                fresh.append(record)
save('fresh-f03-results.json', fresh)
assert len(fresh) == 36 and all(x['rejected'] for x in fresh)

# Additional fresh positives: frozen identity, actual-LPG order invariance,
# canonical disk serialization and unchanged historical source records.
roundtrip = OUT / 'model-roundtrip.json'
roundtrip.write_bytes((FIX / 'candidate/model.json').read_bytes())
mm, pp = compile_model(roundtrip)
rev = copy.deepcopy(p)
rev['nodes'].reverse(); rev['relationships'].reverse()
base = load(FIX / 'baseline/model-2.1.json')
bn = {n['id']: n for n in base['nodes']}
mn = {n['id']: n for n in m['nodes']}
br = {r['id']: r for r in base['relationships']}
mr = {r['id']: r for r in m['relationships']}
new_ids = sorted(mr.keys() - br.keys())
expected = {'BOUND-S04-C01': ('S04','C01'), 'BOUND-S04-C02': ('S04','C02'), 'BOUND-S04-C03': ('S04','C03'), 'BOUND-S04-C04': ('S04','C04'), 'BOUND-S06-W10': ('S06','W10')}
historical_expected = {k: copy.deepcopy(v) for k,v in br.items() if v['type'] == 'HAS_SOURCE' and v['target'] == 'EV09'}
assert historical_expected
for record in historical_expected.values():
    assert record['properties']['assertionSourceVersion'] == 'V01-unified-2.1'
    record['properties']['assertionSourceVersion'] = 'V01-unified-2.2'
positives = {
    'normal_compile_payload_equals_frozen': p == load(FIX / 'candidate/payload.json'),
    'full_analysis_equals_frozen': a == load(FIX / 'candidate/analysis.json'),
    'model_json_roundtrip': m == json.loads(json.dumps(m, allow_nan=False)) and mm == m and pp == p,
    'payload_json_roundtrip': p == json.loads(json.dumps(p, allow_nan=False)),
    'full_analysis_json_roundtrip': a == json.loads(json.dumps(a, allow_nan=False)),
    'actual_lpg_reversed_full_analysis_equal': analyze(rev) == a,
    'EV09_entire_record_preserved_and_version_1_1': mn['EV09'] == bn['EV09'] and mn['EV09']['properties']['sourceVersion'] == '1.1',
    'historical_EV09_source_relations_preserved_except_current_assertion_version': all(mr[k] == v for k,v in historical_expected.items()),
    'all_old_evidenceRole_preserved': all(mr[k]['properties'].get('evidenceRole') == v['properties'].get('evidenceRole') for k,v in br.items()),
    'only_five_new_edges_exact_endpoints_and_type': new_ids == sorted(expected) and all((mr[k]['source'], mr[k]['target']) == expected[k] and mr[k]['type'] == 'BOUNDARY_PARTICIPANT' for k in expected),
    'no_added_nodes': mn.keys() == bn.keys(),
    'no_forbidden_module_imports': not any(k in sys.modules for k in ['run_graph','mcp_client','build_review']),
}
save('fresh-positive-results.json', positives)
assert all(positives.values())
end = freeze()
save('manifest-end.json', end)
assert end == start
assert not any(FIX.rglob('__pycache__'))
limits = [
    '仅复审残余F03及三文件delta回归；F01/F02/F04先前关闭，本轮不重新宣告其关闭。',
    '仅主动读取review3-fixed及本轮review3-output产物；首个当前目录manifest.json读取因不存在而失败，实际冻结清单为review3-fixed/manifest.json。未读取父目录其他内容、Paper、数据库、配置/凭据、会话、技能、记忆或日志。',
    '未联网、未启动子agent、未调用Neo4j/Obsidian；指定解释器加-B，禁止字节码写入。Python运行库及正常依赖只读导入。',
    'run_graph/build_review仅被复用脚本静态读取，未执行/导入；mcp_client及其connected未导入/调用；build_fix与随附test_semantics未执行。',
    '84项变异及58项几何比较为复用上一轮独立脚本实跑，不能称为本轮新编独立证明；本轮新编F03反例为36次入口执行。',
    '未执行数据库事务、实库读回、GUI或发布；本地完整analyze拒绝不等于实库guard已执行。',
    'delta前镜像仅由所给diff反向重建并核对beforeSHA256；没有访问上一轮目录。模型/payload/analysis的跨轮字节未变由用户提供，本轮验证当前冻结哈希和重新计算相等，非声称持有上一轮原件。',
    '本轮脚本首次执行在过严的历史整边字节判据处退出1：SRC-B02仅assertionSourceVersion由2.1升级2.2，历史sourceVersion仍1.1。修正输出脚本为仅允许这一精确断言版本差异后重跑；冻结源未改。',
    '仅限定合成模型及应用规则，不证明完整建筑语义、真实建筑有效性或完整OWL。',
]
findings = {'blocking': False, 'findings': [], 'closed': ['F03'], 'checked': [
    '冻结清单38条始末SHA256全部匹配，manifest自身及全表始末相等。',
    '三文件delta后SHA匹配，反向重建前SHA亦匹配。semantics:117-118共享检查来源别名与精确关系定位；compile_model:170使用get确保缺失字段明确拒绝。',
    '新编反例：BOUND-S04-C01与R059各自缺失/错置sourceUid/sourceVersion/locator；canonical validate、canonical compile及实际LPG完整analyze共36次全部ValueError拒绝。',
    '12次实际LPG反例均保留rawModelJson，包装器确认semantics.validate收到实际缺失/错误值且assertion来源未变；定位错置使用另一受测关系的有效JSON Pointer。',
    '复用上一轮独立脚本仅改FIX/OUT：84项变异全部拒绝、58项独立几何比较全部相等，复用脚本全部检查通过。',
    '正常编译payload和完整analysis与冻结相等，model/payload/完整analysis JSON往返相等，实际LPG反序完整分析相等。',
    'EV09整个历史节点及1.1、历史HAS_SOURCE来源保留（仅当前assertionSourceVersion按既定2.1到2.2升级）、285条旧边evidenceRole保留；仅五新增边及其端点/类型不变，无新节点。'
], 'limits': limits}
save('findings.json', findings)
summary = '''# F03残余项独立复审

结论：F03关闭，blocking=false。本轮仅报告F03与delta回归；不重开或重复宣告F01/F02/F04。

- 冻结manifest：38条始末均匹配，manifest自身SHA未变。
- delta：仅三文件；afterSHA及反向diff重建beforeSHA全部匹配。
- 本轮新编反例：两条边 × 三字段 × 缺失/错置 × 三入口 = 36次，全部ValueError拒绝。canonical validate与compile独立调用；实际LPG调用默认完整analyze。
- 实际LPG的12次变异未改rawModelJson；记录包装器确认校验器看到实际变异，assertion来源仍正确。
- 复用上一轮独立脚本：仅FIX/OUT赋值改路径；84项变异全部拒绝，58项几何比较全部相等。明确属于复用，不是本轮新编证明；未运行随附测试。
- 正常payload、完整analysis与冻结相等；JSON往返与LPG反序相等；EV09历史1.1、历史来源、旧边evidenceRole及五新增边范围保留。SRC-B02仅允许当前assertionSourceVersion按既定2.1到2.2升级，不改历史sourceVersion。

修复根据：tools/semantics.py:116-118先验证assertion精确定位，再验证非HAS_SOURCE来源别名与BOUNDARY_PARTICIPANT locator；历史HAS_SOURCE保持独立来源规则。未统一改写历史来源。

证据：fresh-f03-results.json、fresh-positive-results.json、reused-verification.json、mutation-probes.json、geometry-recomputation.json、delta-verification.json、manifest-execution-start.json、manifest-end.json。脚本为f03_review.py及reused_previous_independent_review.py；真实stdout/stderr和退出码见reused-*。

边界：未执行数据库、GUI、发布或正式审核构建；不宣称这些已完成。当前目录manifest.json不存在，首次读取失败后使用冻结包内manifest.json。跨轮未变以用户给定为前提；本轮只核当前冻结和重算结果。其余限制见findings.json。

执行纠正：新编脚本首次退出1，原因是历史整边判据误把当前断言版本升级也当作禁止；核对SRC-B02后只允许assertionSourceVersion从2.1到2.2这一精确差异并重跑，未修改冻结文件。
'''
(OUT / 'summary.md').write_text(summary)
artifacts = {x.name: sha(x.read_bytes()) for x in sorted(OUT.iterdir()) if x.is_file() and x.name != 'verification.json'}
verification = {
    'blocking': False, 'interpreter': sys.executable, 'dontWriteBytecode': sys.dont_write_bytecode,
    'command': [PYTHON, '-B', str(OUT / 'f03_review.py')],
    'completed': True, 'manifest': {'count': len(start['files']), 'sha256': start['manifest_sha256'], 'startEndEqual': end == start},
    'priorAttempt': {'exitCode': 1, 'stage': 'fresh positive historical whole-edge check', 'cause': 'Overstrict review-script assertion: SRC-B02 current assertionSourceVersion was upgraded from 2.1 to 2.2, while historical sourceVersion remains 1.1', 'correction': 'Allow only exact assertionSourceVersion upgrade in output review script; frozen sources unchanged'},
    'delta': delta_results, 'fresh': {'executions': len(fresh), 'rejected': sum(x['rejected'] for x in fresh), 'actualLPGExecutions': sum(x['route'] == 'actualLPG.full_analyze' for x in fresh)},
    'reusedPreviousIndependentScript': {'exitCode': run.returncode, 'mutations': reuse['mutations'], 'geometryComparisons': len(geom['comparisons']), 'failedChecks': reuse['failedChecks'], 'onlyFIXandOUTChanged': True},
    'positiveChecks': positives, 'providedTestsExecuted': False, 'databaseGUIOrPublicationExecuted': False,
    'artifactSHA256': artifacts, 'limits': limits,
}
save('verification.json', verification)
print(json.dumps({'blocking': False, 'closed': ['F03'], 'freshRejected': len(fresh), 'reusedRejected': reuse['mutations']['rejected'], 'geometryComparisons': len(geom['comparisons']), 'freezeFiles': len(start['files']), 'allPositiveChecks': all(positives.values()), 'output': str(OUT)}, ensure_ascii=False))
