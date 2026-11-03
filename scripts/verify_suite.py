"""Audit a saved corpus, every native trace, and report links without rerunning timings."""
import argparse
import csv
import hashlib
import json
import pathlib
import re
import statistics
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.targets.extend(value for key, value in attrs if key == 'href')

def verify(folder, catalog_path):
    summary, catalog = read(folder/'summary.json'), read(catalog_path)
    assert summary['status'] == 'complete' and summary['failed'] == 0
    assert summary['passed'] == summary['uniqueInputs'] == len(catalog['cases'])
    assert sha(catalog_path) == summary['run']['catalogSha256']
    assert read(folder/'catalog.json') == catalog
    assert len({json.dumps([c['A'], c['B']]) for c in catalog['cases']}) == len(catalog['cases'])
    method = folder/'method'
    assert hashlib.sha256((method/'benchmark_suite.py').read_bytes() + (method/'compare.py').read_bytes()).hexdigest() == summary['run']['runnerSha256']
    rows = {row['id']: row for row in summary['cases']}
    assert len(rows) == len(catalog['cases'])
    records = 0
    for case in catalog['cases']:
        case_dir = folder/'cases'/case['id']
        a, b = case['A'], case['B']
        expected = [[sum(x*y for x, y in zip(row, col)) for col in zip(*b)] for row in a]
        assert sha(catalog_path.parent/case['inputFile']) == sha(case_dir/'input.json') == case['inputSha256']
        row, details = rows[case['id']], read(case_dir/'summary.json')
        assert row['status'] == 'passed' and row['C'] == details['C'] == expected
        assert details['A'] == a and details['B'] == b
        assert details['measuredRuns'] == summary['run']['runs']
        for index, edition in enumerate(['baseline', 'optimized']):
            stats = details['results'][index]
            assert row[edition] == stats
            assert stats['executableSha256'] == summary['run']['executableSha256'][edition]
            samples = []
            for iteration in range(summary['run']['runs'] + 1):
                raw = read(case_dir/f'{edition}-{iteration}.json')
                records += 1
                assert raw['edition'] == edition and raw['speed'] == 2 and raw['status'] == 'complete'
                assert raw['A'] == a and raw['B'] == b and raw['C'] == expected
                assert raw['algorithm'] == {'baseline':'baseline-v1', 'optimized':'transpose-v1.2'}[edition]
                assert raw['activeCardUses'] == raw['rescues'] == raw['fangzhu'] == len(raw['trace'])
                assert raw['drawnCards'] == sum(map(sum, expected))
                final = {p['id']: p for p in raw['finalPlayers']}
                outputs = 0
                for p in raw['initialPlayers']:
                    if p['general'] == 'caopi':
                        assert final[p['id']]['hp'] == 1
                    match = re.fullmatch(r'C\[(\d+),(\d+)\]', p['label'])
                    if match:
                        i, j = (int(v)-1 for v in match.groups())
                        assert p['hand'] == [] and final[p['id']]['handCount'] == expected[i][j]
                        outputs += 1
                assert outputs == len(a)*len(b[0])
                for step in raw['trace']:
                    assert step['caopiHp'] == 1 and len(step['rescueCardIds']) == 1
                    assert step['after'] - step['before'] == len(step['drawnCardIds'])
                if iteration:
                    samples.append(raw)
            assert stats['samplesMs'] == [s['engineMs'] for s in samples]
            assert stats['medianMs'] == statistics.median(s['engineMs'] for s in samples)
            assert stats['computeSamplesMs'] == [s['prepareMs']+s['runWallMs'] for s in samples]
            assert stats['medianComputeMs'] == statistics.median(stats['computeSamplesMs'])
    with (folder/'summary.csv').open(encoding='utf-8-sig', newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == len(rows) and {r['id'] for r in csv_rows} == set(rows)
    for row in csv_rows:
        assert row['status'] == 'passed' and json.loads(row['C']) == rows[row['id']]['C']
    reports = list(folder.rglob('report.html'))
    assert len(reports) == len(rows)+1
    for report in reports:
        parser = Links()
        parser.feed(report.read_text(encoding='utf-8'))
        for target in parser.targets:
            assert (report.parent/target).is_file(), (report, target)
    return dict(passed=True, cases=len(rows), nativeRecords=records, htmlReports=len(reports),
                shapes=sorted({tuple(c['shape']) for c in catalog['cases']}),
                full2x2=sum(c['shape']==[2,2,2] for c in catalog['cases']),
                summarySha256=sha(folder/'summary.json'), methodSha256=summary['run']['runnerSha256'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=pathlib.Path, default=ROOT/'evidence/versions/suite-v1')
    parser.add_argument('--catalog', type=pathlib.Path, default=ROOT/'examples/suites/sgemm-v1/catalog.json')
    args = parser.parse_args()
    result = verify(args.results, args.catalog)
    (args.results/'integrity.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
