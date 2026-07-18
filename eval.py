#!/usr/bin/env python3
"""Cross-Domain Evaluation — Accuracy only, per generator."""
import os, sys, argparse
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.metrics import accuracy_score
from tqdm import tqdm

from train import FlatImageDataset, get_val_transform, seed_everything
from models.mambaout_custom import MambaOutCustom


@torch.no_grad()
def evaluate_loader(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    for images, lbs in tqdm(loader, desc='Eval', ncols=100):
        logits = model(images.to(device), return_features=False)
        all_preds.append(logits.argmax(1).cpu().numpy())
        all_labels.append(lbs.numpy())
    return np.concatenate(all_preds), np.concatenate(all_labels)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=str, default='./checkpoints/best.pth')
    parser.add_argument('--source_root', type=str, default='./models/train')
    parser.add_argument('--genimage_root', type=str, default='./models/Genimage')
    parser.add_argument('--batch_size', type=int, default=64)
    parser.add_argument('--device', type=str, default='cuda')
    args = parser.parse_args()

    seed_everything(42)
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f'[Device] {device}')

    # ---- Load Model ----
    print(f'\n[Load] {args.checkpoint}')
    model = MambaOutCustom(num_classes=2, pretrained=False)
    ckpt = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    if 'model_state_dict' in ckpt:
        model.load_state_dict(ckpt['model_state_dict'])
        info = ckpt.get('accuracy', ckpt.get('best_val_acc', '?'))
        print(f'[Load] Epoch={ckpt.get("epoch", "?")}, ValAcc={info}')
    else:
        model.load_state_dict(ckpt, strict=False)
    model.to(device)
    model.eval()

    transform = get_val_transform()

    # ---- 1. Source Val ----
    print(f'\n{"="*50}')
    print('1. Source Domain Validation')
    print(f'{"="*50}')
    src_full = FlatImageDataset(args.source_root, transform=transform, labeled=True)
    labels_arr = np.array(src_full.labels)
    indices = np.arange(len(src_full))
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.15, random_state=42)
    _, val_idx = next(sss.split(indices, labels_arr))
    val_ds = Subset(src_full, val_idx)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    preds, lbls = evaluate_loader(model, val_loader, device)
    acc = accuracy_score(lbls, preds) * 100
    print(f'  Source Val Accuracy: {acc:.2f}%')

    # ---- 2. Cross-Generator ----
    print(f'\n{"="*50}')
    print('2. Cross-Generator Blind Detection')
    print(f'   (Source-Real vs GenImage-Fake, 1:1 balanced)')
    print(f'{"="*50}')

    # Real images from source val
    real_idx = [i for i in val_idx if labels_arr[i] == 0]
    real_paths = [src_full.samples[i] for i in real_idx]

    genimage_root = Path(args.genimage_root)
    generators = sorted([d.name for d in genimage_root.iterdir() if d.is_dir()])
    print(f'\n  Found {len(generators)} generators: {generators}')

    results = {}
    print(f'\n  {"Generator":<14} {"#Test":>7}  {"Acc%":>8}')
    print(f'  {"-"*33}')

    for gen in generators:
        gen_dir = genimage_root / gen
        fake_files = sorted(set(
            list(gen_dir.rglob('*.png')) +
            list(gen_dir.rglob('*.jpg')) +
            list(gen_dir.rglob('*.jpeg')) +
            list(gen_dir.rglob('*.PNG')) +
            list(gen_dir.rglob('*.JPG'))
        ))

        if len(fake_files) == 0:
            print(f'  {gen:<14} {"SKIP":>7}  (no images found)')
            continue

        n_test = min(len(real_paths), len(fake_files))
        np.random.seed(42)
        sampled_real = np.random.choice(real_paths, n_test, replace=False)
        sampled_fake = np.random.choice(fake_files, n_test, replace=False)

        from PIL import Image
        images_list, test_labels = [], []
        for p in sampled_real:
            images_list.append(transform(Image.open(p).convert('RGB')))
            test_labels.append(0)
        for p in sampled_fake:
            images_list.append(transform(Image.open(p).convert('RGB')))
            test_labels.append(1)

        x_batch = torch.stack(images_list)
        y_batch = np.array(test_labels)

        all_preds = []
        with torch.no_grad():
            for i in range(0, len(x_batch), args.batch_size):
                bx = x_batch[i:i+args.batch_size].to(device)
                logits = model(bx, return_features=False)
                all_preds.append(logits.argmax(1).cpu().numpy())

        preds = np.concatenate(all_preds)
        acc = accuracy_score(y_batch, preds) * 100
        results[gen] = acc
        print(f'  {gen:<14} {n_test:>7}  {acc:>7.2f}%')

    # ---- 3. Summary ----
    print(f'\n{"="*50}')
    print('3. Summary')
    print(f'{"="*50}')
    if results:
        avg = np.mean(list(results.values()))
        best = max(results, key=results.get)
        worst = min(results, key=results.get)
        print(f'  Average: {avg:.2f}%')
        print(f'  Best:    {best} ({results[best]:.2f}%)')
        print(f'  Worst:   {worst} ({results[worst]:.2f}%)')

        print(f'\n  Markdown Table:')
        print(f'  | Generator | Accuracy |')
        print(f'  |---|---:|')
        for gen in generators:
            if gen in results:
                print(f'  | {gen} | {results[gen]:.2f}% |')
        print(f'  | **Average** | **{avg:.2f}%** |')


if __name__ == '__main__':
    main()
