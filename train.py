#!/usr/bin/env python3
"""
MambaOut + MK-MMD Domain-Adaptive AIGC Forgery Detection
Optimized: Diff LR, Beta Schedule, Warmup, Label Smoothing, Val Split
"""

import os, sys, math, random, argparse, warnings
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision import transforms
from sklearn.model_selection import StratifiedShuffleSplit
from tqdm import tqdm

from models.mambaout_custom import MambaOutCustom
from models.mkmmd import MKMMD_Loss, MultiLayerMMD, entropy_loss

warnings.filterwarnings('ignore')


# ==============================================================================
# Seed
# ==============================================================================
def seed_everything(seed=42):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print(f"[Seed] {seed}")


# ==============================================================================
# Data Transforms
# ==============================================================================
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

def get_train_transform():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.RandomCrop(224),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.05),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

def get_val_transform():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


# ==============================================================================
# Dataset
# ==============================================================================
class FlatImageDataset(Dataset):
    """Flat directory dataset with filename-based labels.

    Filename patterns: ..._0_real.png -> label=0 (real)
                       ..._1_fake.png -> label=1 (fake)
    Also supports labeled=False for unlabeled target domain.
    """
    IMG_EXT = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

    def __init__(self, root, transform=None, labeled=True):
        self.root = Path(root)
        self.transform = transform
        self.labeled = labeled

        self.samples = []
        for ext in self.IMG_EXT:
            self.samples.extend(self.root.rglob(f'*{ext}'))
            self.samples.extend(self.root.rglob(f'*{ext.upper()}'))
        self.samples = sorted(set(self.samples))

        if len(self.samples) == 0:
            raise RuntimeError(f'[Dataset] No images found in {root}!')

        if labeled:
            self.labels = []
            valid = []
            for p in self.samples:
                lbl = self._parse_label(p.stem)
                if lbl is not None:
                    self.labels.append(lbl)
                    valid.append(p)
            self.samples = valid
            self.num_classes = 2
            n_real = sum(1 for l in self.labels if l == 0)
            n_fake = sum(1 for l in self.labels if l == 1)
            print(f'[Dataset] Labeled: {len(self.samples)} (real={n_real}, fake={n_fake})')
        else:
            print(f'[Dataset] Unlabeled: {len(self.samples)}')

    @staticmethod
    def _parse_label(stem):
        s = stem.lower()
        if s.endswith('_real') or '_0_real' in s: return 0
        if s.endswith('_fake') or '_1_fake' in s: return 1
        if '_real' in s: return 0
        if '_fake' in s: return 1
        return None

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        from PIL import Image
        img = Image.open(self.samples[idx]).convert('RGB')
        if self.transform: img = self.transform(img)
        if self.labeled: return img, self.labels[idx]
        return img


# ==============================================================================
# Val Split
# ==============================================================================
def split_train_val(dataset, val_ratio=0.15, seed=42):
    labels = np.array(dataset.labels)
    indices = np.arange(len(dataset))
    sss = StratifiedShuffleSplit(n_splits=1, test_size=val_ratio, random_state=seed)
    train_idx, val_idx = next(sss.split(indices, labels))

    t_real = sum(1 for i in train_idx if labels[i] == 0)
    t_fake = sum(1 for i in train_idx if labels[i] == 1)
    v_real = sum(1 for i in val_idx if labels[i] == 0)
    v_fake = sum(1 for i in val_idx if labels[i] == 1)
    print(f'[Split] Train: {len(train_idx)} (real={t_real}, fake={t_fake})')
    print(f'[Split] Val:   {len(val_idx)} (real={v_real}, fake={v_fake})')
    return train_idx, val_idx


# ==============================================================================
# Trainer
# ==============================================================================
class Trainer:
    def __init__(self, model, mkmmd_loss, device,
                 source_loader, target_loader, val_loader=None,
                 lr_backbone=1e-5, lr_head=1e-3, weight_decay=1e-4,
                 beta_max=1.0, beta_warmup_epochs=10,
                 label_smoothing=0.1, warmup_epochs=5,
                 entropy_weight=0.1,    # 熵最小化权重
                 num_epochs=60, save_dir='./checkpoints'):

        self.model = model.to(device)
        self.mkmmd_loss = mkmmd_loss
        self.device = device
        self.source_loader = source_loader
        self.target_loader = target_loader
        self.val_loader = val_loader
        self.beta_max = beta_max
        self.beta_warmup_epochs = beta_warmup_epochs
        self.num_epochs = num_epochs
        self.warmup_epochs = warmup_epochs
        self.entropy_weight = entropy_weight
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.cls_criterion = nn.CrossEntropyLoss(label_smoothing=label_smoothing)

        # Differential LR
        bb_params, hd_params = [], []
        for name, param in model.named_parameters():
            if not param.requires_grad: continue
            if name.startswith('backbone.'): bb_params.append(param)
            else: hd_params.append(param)

        self.optimizer = optim.AdamW([
            {'params': bb_params, 'lr': lr_backbone},
            {'params': hd_params, 'lr': lr_head},
        ], weight_decay=weight_decay)

        self.base_lrs = [lr_backbone, lr_head]
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=num_epochs - warmup_epochs,
            eta_min=min(lr_backbone, lr_head) * 0.01)

        n_bb = sum(p.numel() for p in bb_params)
        n_hd = sum(p.numel() for p in hd_params)
        print(f'[Optim] Diff LR: backbone({n_bb/1e6:.1f}M)={lr_backbone}, head({n_hd/1e6:.2f}M)={lr_head}')

        self.best_val_acc = 0.0
        self.best_epoch = 0
        self.log = []
        self.global_step = 0

    def _get_beta(self, epoch):
        if epoch <= self.beta_warmup_epochs:
            return self.beta_max * (epoch / self.beta_warmup_epochs)
        return self.beta_max

    def _warmup_lr(self, epoch):
        if epoch <= self.warmup_epochs:
            scale = epoch / self.warmup_epochs
            for i, base_lr in enumerate(self.base_lrs):
                self.optimizer.param_groups[i]['lr'] = base_lr * scale

    def train_epoch(self, epoch):
        self.model.train()
        beta = self._get_beta(epoch)

        total_cls, total_mmd, total_ent, total_loss = 0.0, 0.0, 0.0, 0.0
        correct, total_s = 0, 0

        n_batches = min(len(self.source_loader), len(self.target_loader))
        pbar = tqdm(zip(self.source_loader, self.target_loader),
                    total=n_batches, desc=f'Epoch {epoch}/{self.num_epochs}',
                    ncols=140, unit='b')

        for (src_x, src_y), tgt_x in pbar:
            src_x, src_y = src_x.to(self.device), src_y.to(self.device)
            tgt_x = tgt_x.to(self.device)
            bs = src_x.size(0)

            # 多层特征: (logits, feat_s2, feat_s3, feat_bn)
            src_logits, src_s2, src_s3, src_bn = self.model(src_x, return_multilayer=True)
            tgt_logits, tgt_s2, tgt_s3, tgt_bn = self.model(tgt_x, return_multilayer=True)

            # 分类损失 + 熵最小化
            loss_cls = self.cls_criterion(src_logits, src_y)
            loss_ent = entropy_loss(tgt_logits)

            # 多层 MMD
            loss_mmd, mmd_details = self.mkmmd_loss(
                src_s2, tgt_s2, src_s3, tgt_s3, src_bn, tgt_bn
            )

            loss = loss_cls + beta * loss_mmd + self.entropy_weight * loss_ent

            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
            self.optimizer.step()
            self.global_step += 1

            total_cls += loss_cls.item()
            total_mmd += loss_mmd.item()
            total_ent += loss_ent.item()
            total_loss += loss.item()
            pred = src_logits.argmax(1)
            correct += (pred == src_y).sum().item()
            total_s += bs

            pbar.set_postfix({
                'CLS': f'{loss_cls.item():.3f}',
                'MMD': f'{loss_mmd.item():.3f}',
                'Ent': f'{loss_ent.item():.3f}',
                'Acc': f'{correct/total_s*100:.1f}%',
                'B': f'{beta:.2f}',
            })

        n_batches = max(n_batches, 1)
        return (total_loss / n_batches, correct / total_s * 100,
                total_mmd / n_batches, total_ent / n_batches)

    @torch.no_grad()
    def validate(self):
        self.model.eval()
        correct, total = 0, 0
        for images, labels in self.val_loader:
            images, labels = images.to(self.device), labels.to(self.device)
            logits = self.model(images, return_features=False)
            correct += (logits.argmax(1) == labels).sum().item()
            total += labels.size(0)
        return correct / total * 100

    def run(self):
        n_src = len(self.source_loader.dataset)
        n_tgt = len(self.target_loader.dataset)
        print(f'\n{"="*60}')
        print(f'Train: {self.num_epochs} epochs, beta->{self.beta_max}')
        print(f'Diff LR: backbone={self.base_lrs[0]}, head={self.base_lrs[1]}')
        print(f'Source: {n_src} | Target: {n_tgt}', end='')
        if self.val_loader:
            print(f' | Val: {len(self.val_loader.dataset)}')
        else:
            print()
        print(f'{"="*60}\n')

        for epoch in range(1, self.num_epochs + 1):
            self._warmup_lr(epoch)
            train_loss, train_acc, train_mmd, train_ent = self.train_epoch(epoch)

            if epoch > self.warmup_epochs:
                self.scheduler.step()

            val_acc = 0.0
            if self.val_loader:
                val_acc = self.validate()
                marker = ' <<< BEST' if val_acc > self.best_val_acc else ''
                print(f'  -> Val Acc: {val_acc:.2f}%{marker}')
                if val_acc > self.best_val_acc:
                    self.best_val_acc = val_acc
                    self.best_epoch = epoch
                    self.save_checkpoint('best.pth', epoch, val_acc)

            self.log.append({
                'epoch': epoch, 'train_loss': train_loss,
                'train_acc': train_acc, 'val_acc': val_acc,
            })

        self.save_checkpoint('last.pth', self.num_epochs, self.log[-1]['val_acc'])
        print(f'\nDone! Best Val: {self.best_val_acc:.2f}% at epoch {self.best_epoch}')
        return self.log

    def save_checkpoint(self, filename, epoch, acc):
        path = self.save_dir / filename
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'best_val_acc': self.best_val_acc,
            'accuracy': acc,
        }, path)
        print(f'  [Save] {path}')


# ==============================================================================
# Main
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description='MambaOut + MK-MMD Training')

    # Data
    parser.add_argument('--source_root', type=str, default='./models/train')
    parser.add_argument('--target_root', type=str, default='./models/Genimage')
    parser.add_argument('--target_generator', type=str, default=None,
                        help='Specific target subdir (default: all)')
    parser.add_argument('--val_ratio', type=float, default=0.15)
    parser.add_argument('--num_workers', type=int, default=4)

    # Model
    parser.add_argument('--bottleneck_dim', type=int, default=256)
    parser.add_argument('--pretrained', action='store_true', default=True)
    parser.add_argument('--pretrained_path', type=str, default='./mambaout_small.pth')

    # Hyperparams
    parser.add_argument('--lr_backbone', type=float, default=1e-5)
    parser.add_argument('--lr_head', type=float, default=1e-3)
    parser.add_argument('--weight_decay', type=float, default=1e-4)
    parser.add_argument('--beta_max', type=float, default=1.0)
    parser.add_argument('--beta_warmup', type=int, default=10)
    parser.add_argument('--label_smoothing', type=float, default=0.1)
    parser.add_argument('--warmup_epochs', type=int, default=5)
    parser.add_argument("--entropy_weight", type=float, default=0.1,
                        help="entropy minimization weight")

    # Training
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--epochs', type=int, default=60)
    parser.add_argument('--batch_size', type=int, default=48)

    # Output
    parser.add_argument('--save_dir', type=str, default='./checkpoints')
    parser.add_argument('--device', type=str, default='cuda')

    args = parser.parse_args()
    seed_everything(args.seed)
    device = torch.device(args.device if torch.cuda.is_available() else 'cpu')
    print(f'[Device] {device}')

    # ---- Data ----
    source_ds = FlatImageDataset(args.source_root, get_train_transform(), labeled=True)

    tgt_root = Path(args.target_root)
    if args.target_generator:
        tgt_root = tgt_root / args.target_generator
    target_ds = FlatImageDataset(str(tgt_root), get_train_transform(), labeled=False)

    train_idx, val_idx = split_train_val(source_ds, val_ratio=args.val_ratio, seed=args.seed)

    val_ds_full = FlatImageDataset(args.source_root, get_val_transform(), labeled=True)
    val_ds = Subset(val_ds_full, val_idx)
    train_ds = Subset(source_ds, train_idx)

    nw = args.num_workers
    source_loader = DataLoader(train_ds, batch_size=args.batch_size,
                               shuffle=True, num_workers=nw, pin_memory=True, drop_last=True)
    target_loader = DataLoader(target_ds, batch_size=args.batch_size,
                               shuffle=True, num_workers=nw, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size * 2,
                            shuffle=False, num_workers=nw, pin_memory=True)

    # ---- Model ----
    model = MambaOutCustom(
        num_classes=2, bottleneck_dim=args.bottleneck_dim,
        pretrained=args.pretrained, pretrained_path=args.pretrained_path,
        drop_path_rate=0.1,
    )

    # ---- Train ----
    mkmmd_loss = MultiLayerMMD(kernel_num=5, kernel_mul=2.0)
    trainer = Trainer(
        model=model, mkmmd_loss=mkmmd_loss, device=device,
        source_loader=source_loader, target_loader=target_loader,
        val_loader=val_loader,
        lr_backbone=args.lr_backbone, lr_head=args.lr_head,
        weight_decay=args.weight_decay,
        beta_max=args.beta_max, beta_warmup_epochs=args.beta_warmup,
            entropy_weight=args.entropy_weight,
        label_smoothing=args.label_smoothing,
        warmup_epochs=args.warmup_epochs,
        num_epochs=args.epochs, save_dir=args.save_dir,
    )
    trainer.run()


if __name__ == '__main__':
    main()
