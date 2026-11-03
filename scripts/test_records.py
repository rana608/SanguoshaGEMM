"""Input rejection and deterministic replay through the shipped native executable."""
import argparse, json, os, pathlib, subprocess

root = pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--edition',choices=['baseline','optimized'],default='baseline');parser.add_argument('--output-dir',type=pathlib.Path);args=parser.parse_args()
selected={'baseline':'baseline-v1','optimized':'transpose-v1.2'}[args.edition]
exe = root / ('dist/SanguoshaGEMM-'+args.edition.title()) / ('SanguoshaGEMM-'+args.edition.title()+'.exe')
out = (args.output_dir or root / 'evidence/versions' / args.edition / 'records').resolve()
out.mkdir(parents=True,exist_ok=True)
env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
summary = []

def run(name, payload, code):
    inp, result = out / (name + '.input.json'), out / (name + '.json')
    inp.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding='utf-8')
    result.unlink(missing_ok=True)
    p = subprocess.run([str(exe), '--gemm-case', str(inp.relative_to(root)), str(result.relative_to(root))],
                       cwd=root, env=env, capture_output=True, timeout=30)
    assert p.returncode == code, (name, p.returncode, p.stderr)
    data = json.loads(result.read_text(encoding='utf-8'))
    if code == 2:
        assert data['status'] == 'invalid-input' and data['error'], data
        assert 'C' not in data, data
    summary.append(dict(name=name, exitCode=p.returncode, status=data['status']))
    return data

invalid = {
    'malformed': '{', 'not-object': [], 'empty-object': {},
    'empty': {'A': [], 'B': [[1]]},
    'too-tall': {'A': [[1],[1],[1]], 'B': [[1]]},
    'too-wide': {'A': [[1,1,1]], 'B': [[1],[1],[1]]},
    'ragged': {'A': [[1,2],[1]], 'B': [[1],[1]]},
    'mismatch': {'A': [[1,2]], 'B': [[1]]},
    'negative': {'A': [[-1]], 'B': [[1]]},
    'decimal': {'A': [[1.5]], 'B': [[1]]},
    'too-large': {'A': [[101]], 'B': [[1]]},
    'boolean': {'A': [[True]], 'B': [[1]]},
    'string': {'A': [['1']], 'B': [[1]]},
    'null': {'A': [[None]], 'B': [[1]]},
    'algorithm': {'A': [[1]], 'B': [[1]], 'algorithm': 'future'},
    'speed-range': {'A': [[1]], 'B': [[1]], 'speed': 3},
    'speed-decimal': {'A': [[1]], 'B': [[1]], 'speed': 1.5},
    'speed-string': {'A': [[1]], 'B': [[1]], 'speed': 'fast'},
    'fault': {'A': [[1]], 'B': [[1]], 'fault': 'unknown'},
}
for name, payload in invalid.items():
    run(name, payload, 2)

stable = ['A','B','algorithm','transposed','tasks','completed','status','C',
          'initialPlayers','initialDrawPile','initialWeaponId','finalPlayers','trace',
          'activeCardUses','rescues','damagePoints','fangzhu','drawnCards','consumedCards','judgements']
for algorithm in [selected]:
    first = run('original-' + algorithm, dict(A=[[9,8],[7,6]], B=[[1,0],[0,1]], algorithm=algorithm, speed=2), 0)
    replay = run('replay-' + algorithm, first, 0)
    assert {k:first[k] for k in stable} == {k:replay[k] for k in stable}, algorithm
    assert first['peakWorkingSetBytes'] >= first['workingSetBytes'] > 0
    assert first['processCpuMs'] > 0
    assert all(len(t['drawnCardIds']) == t['after'] - t['before'] and len(t['rescueCardIds']) == 1 for t in first['trace'])

(out / 'summary.json').write_text(json.dumps(dict(passed=len(summary), cases=summary, replayComparedFields=stable), indent=2), encoding='utf-8')
print('PASS', len(summary), '(including exact state/action replay)')
