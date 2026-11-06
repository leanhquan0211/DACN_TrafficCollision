"""So hai cache B2 trên cùng tracks; ghi cặp thêm/mất và score, không suy nhãn."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.storage_paths import output_path, require_output_path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', type=Path, required=True)
    p.add_argument('--after', type=Path, required=True)
    p.add_argument('--output', type=Path, default=output_path(ROOT,'data_audit','v010_b2_candidate_comparison',child='comparison.json'))
    a = p.parse_args()
    a.output = require_output_path(ROOT,a.output,'data_audit',allow_version_root=False)
    def read(path):
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    before, after = read(a.before), read(a.after)
    if not before or len(before) != len(after):
        raise ValueError('Caches need equal, nonempty frame coverage')
    counts = Counter()
    changes = []
    for old, new in zip(before, after):
        if old['frame'] != new['frame'] or old['video_id'] != new['video_id'] or old['tracks'] != new['tracks']:
            raise ValueError('Frame or tracks differ; cannot attribute difference to selector')
        x = {tuple(c['track_ids']): c for c in old['candidates']}
        y = {tuple(c['track_ids']): c for c in new['candidates']}
        added, removed = sorted(y.keys()-x.keys()), sorted(x.keys()-y.keys())
        counts.update(before=len(x), after=len(y), added=len(added), removed=len(removed),
                      before_high=sum(c['rule_score'] >= .75 for c in x.values()),
                      after_high=sum(c['rule_score'] >= .75 for c in y.values()),
                      before_capped=int(old['candidate_cap_reached']), after_capped=int(new['candidate_cap_reached']))
        if added or removed:
            changes.append({'frame': old['frame'], 'added_pairs': added, 'removed_pairs': removed})
    result = {'scope': 'development selector comparison; added pairs are unreviewed, not automatically FP',
              'video_id': before[0]['video_id'], 'frames': len(before), 'counts': dict(counts),
              'before_pairs_per_frame': counts['before']/len(before), 'after_pairs_per_frame': counts['after']/len(before),
              'before_sha256': hashlib.sha256(a.before.read_bytes()).hexdigest(),
              'after_sha256': hashlib.sha256(a.after.read_bytes()).hexdigest(), 'changes': changes}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: result[k] for k in ('video_id','frames','counts','before_pairs_per_frame','after_pairs_per_frame')}))


if __name__ == '__main__':
    main()
