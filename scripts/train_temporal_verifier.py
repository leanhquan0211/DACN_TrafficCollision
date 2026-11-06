"""Trainer chung T0/GRU từ release feature đã xác minh; không train detector.

--check chỉ kiểm schema và leakage. --train bị khóa khi config/release chưa
cho phép; test/holdout bị từ chối. Output là checkpoint, scaler và val logits.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.temporal_training import make_examples, validate_records
from src.temporal_verifiers import FEATURE_NAMES, make_model
from src.storage_paths import output_path, require_output_path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True, help='JSON: {records: [...]}')
    p.add_argument('--release', type=Path, required=True, help='Verified release metadata with data SHA')
    p.add_argument('--config', type=Path, default=ROOT/'configs/temporal_supervised_v1.json')
    p.add_argument('--kind', choices=['mlp', 'gru'], required=True)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Validate release without training (default)')
    mode.add_argument('--train', action='store_true')
    p.add_argument('--output-dir', type=Path, help='New canonical version directory (default v001_supervised_pilot)')
    a = p.parse_args()
    cfg = json.loads(a.config.read_text(encoding='utf-8'))
    release = json.loads(a.release.read_text(encoding='utf-8'))
    if release.get('data_sha256') != sha(a.data) or release.get('feature_names') != list(FEATURE_NAMES):
        raise ValueError('Release data hash or feature schema mismatch')
    records = json.loads(a.data.read_text(encoding='utf-8'))['records']
    counts = validate_records(records, int(cfg['window_frames']))
    print(json.dumps({'check': 'passed', 'counts': counts, 'can_train': release.get('can_train') is True,
                      'training_enabled': cfg.get('training_enabled') is True}))
    if not a.train:
        return
    if release.get('can_train') is not True or cfg.get('training_enabled') is not True:
        raise ValueError('Training blocked: release/config have not passed readiness')
    baseline = 'T0' if a.kind == 'mlp' else 'B3'
    a.output_dir = require_output_path(ROOT, a.output_dir or output_path(ROOT, 'baseline', 'v001_supervised_pilot', baseline=baseline), 'baseline', baseline=baseline)
    if not release.get('readiness_evidence'):
        raise ValueError('Readiness evidence is required')
    evidence = (ROOT/release['readiness_evidence']).resolve()
    if not evidence.is_relative_to(ROOT) or not evidence.is_file() or sha(evidence) != release.get('readiness_evidence_sha256'):
        raise ValueError('Readiness evidence is missing or its hash differs')
    if int(cfg['early_stopping_start_epoch']) <= 20 or int(cfg['patience']) < 1:
        raise ValueError('Early stopping cannot start before epoch 21')
    a.output_dir.mkdir(parents=True, exist_ok=False)
    # Gắn run ID vào thư mục version để resolver và Explore tìm được kết quả mới.
    (a.output_dir/'artifact_identity.json').write_text(json.dumps({
        'run_id': a.output_dir.name, 'baseline': baseline, 'name': a.output_dir.name
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    import torch
    from torch.utils.data import DataLoader, TensorDataset
    seed = int(cfg['seed'])
    random.seed(seed)
    torch.manual_seed(seed)
    scaler, examples = make_examples(records)
    def make_split(split):
        chosen = [r for r in examples if r['split'] == split]
        return chosen, TensorDataset(torch.tensor([r['window'] for r in chosen], dtype=torch.float32),
                                     torch.tensor([[r['label']] for r in chosen], dtype=torch.float32))
    train_rows, train_data = make_split('train')
    val_rows, val_data = make_split('val')
    train_loader = DataLoader(train_data, batch_size=int(cfg['batch_size']), shuffle=True,
                              generator=torch.Generator().manual_seed(seed))
    val_loader = DataLoader(val_data, batch_size=int(cfg['batch_size']), shuffle=False)
    model = make_model(a.kind, hidden_size=int(cfg['hidden_size']))
    optimizer = torch.optim.Adam(model.parameters(), lr=float(cfg['learning_rate']))
    loss_fn = torch.nn.BCEWithLogitsLoss()
    best, best_epoch, best_state, stale = float('inf'), 0, None, 0
    history = []
    for epoch in range(1, int(cfg['epochs'])+1):
        model.train()
        for x, y in train_loader:
            optimizer.zero_grad()
            logits = model(x[:, -1, :] if a.kind == 'mlp' else x)
            loss_fn(logits, y).backward()
            optimizer.step()
        model.eval()
        losses, values = [], []
        with torch.no_grad():
            for x, y in val_loader:
                logits = model(x[:, -1, :] if a.kind == 'mlp' else x)
                losses.extend(torch.nn.functional.binary_cross_entropy_with_logits(logits, y, reduction='none').view(-1).tolist())
                values.extend(logits.view(-1).tolist())
        val_loss = sum(losses)/len(losses)
        history.append({'epoch': epoch, 'val_bce': val_loss})
        if val_loss < best:
            best, best_epoch, stale = val_loss, epoch, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        elif epoch >= int(cfg['early_stopping_start_epoch']):
            stale += 1
        if epoch >= int(cfg['early_stopping_start_epoch']) and stale >= int(cfg['patience']):
            break
    model.load_state_dict(best_state)
    model.eval()
    predictions = []
    with torch.no_grad():
        for r in val_rows:
            x = torch.tensor([r['window']], dtype=torch.float32)
            logit = float(model(x[:, -1, :] if a.kind == 'mlp' else x).item())
            predictions.append({k: r[k] for k in ('video_id', 'group_id', 'frame', 'label')} | {'logit': logit})
    torch.save(best_state, a.output_dir/'best.pt')
    (a.output_dir/'scaler.json').write_text(json.dumps(scaler.state(), indent=2), encoding='utf-8')
    report = {'kind': a.kind, 'config': cfg, 'release': release, 'data_sha256': sha(a.data),
              'torch_version': torch.__version__, 'best_epoch': best_epoch, 'history': history,
              'validation_logits': predictions, 'scope': 'validation feature logits only; not event metrics'}
    (a.output_dir/'experiment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Training complete: {a.output_dir}; best epoch {best_epoch}')


if __name__ == '__main__':
    main()
