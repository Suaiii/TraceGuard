"""
TraceGuard Detection Module API
14x14 Grad-CAM heatmap — 张潇 -> 贺杰, 羿帅
"""
import torch
import torch.nn.functional as F
from torchvision import transforms
import numpy as np
from PIL import Image

from .models.mambaout_custom import MambaOutCustom

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]


class Detector:

    def __init__(self, checkpoint_path='./checkpoints/best.pth', device='cuda'):
        self.device = torch.device(device if torch.cuda.is_available() else 'cpu')

        self.model = MambaOutCustom(num_classes=2, pretrained=False)
        ckpt = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
        self.model.load_state_dict(
            ckpt['model_state_dict'] if 'model_state_dict' in ckpt else ckpt,
            strict=False
        )
        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])

        # ---- Grad-CAM hook @ stage2 (14x14, 384 channels) ----
        self.activation = None  # [B, 384, 14, 14]
        self.gradient = None    # [B, 384, 14, 14]

        def forward_hook(module, inp, out):
            # out: [B, 14, 14, 384] (BHWC) -> [B, 384, 14, 14] (BCHW)
            self.activation = out.permute(0, 3, 1, 2)

        def backward_hook(module, grad_in, grad_out):
            self.gradient = grad_out[0].permute(0, 3, 1, 2)

        self.model.backbone.stages[2].register_forward_hook(forward_hook)
        self.model.backbone.stages[2].register_full_backward_hook(backward_hook)

        print(f'[Detector] loaded: {checkpoint_path}')

    # ---- 标准检测 (羿帅用) ----
    def predict(self, image_or_path):
        img = self._load(image_or_path)
        t = self.transform(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(t)
            p = F.softmax(logits, dim=1)[0]
        return {
            'label': 'fake' if p[1] > p[0] else 'real',
            'real_prob': float(p[0]), 'fake_prob': float(p[1]),
            'risk_score': float(p[1]),
        }

    # ---- Grad-CAM 热力图 (贺杰用) ----
    def get_heatmap(self, image_or_path):
        """14x14 Grad-CAM，上采样到原图尺寸返回"""
        img = self._load(image_or_path)
        original = self._load(image_or_path, preprocess=False)
        t = self.transform(img).unsqueeze(0).to(self.device)
        t.requires_grad_(True)

        # 1. Forward
        logits = self.model(t)

        # 2. Backward: 对 fake 类的 logit 求梯度
        self.model.zero_grad()
        logits[0, 1].backward()

        # 3. 通道权重 = 梯度在空间上的平均值
        w = self.gradient.detach().mean(dim=[2, 3], keepdim=True)  # [1, 384, 1, 1]

        # 4. 加权激活 + ReLU = 热力图
        cam = (w * self.activation.detach()).sum(dim=1, keepdim=True)  # [1, 1, 14, 14]
        cam = F.relu(cam)

        # 5. 归一化
        cmin, cmax = cam.min(), cam.max()
        cam = (cam - cmin) / (cmax - cmin + 1e-8)

        # 6. 上采样到原图尺寸
        ow, oh = original.size
        cam_orig = F.interpolate(cam, size=(oh, ow), mode='bilinear',
                                 align_corners=False).squeeze().cpu().numpy()

        p = F.softmax(logits, dim=1)[0]
        return {
            'heatmap': cam_orig,            # [H, W] 热力图，0~1
            'label': 'fake' if p[1] > p[0] else 'real',
            'fake_prob': float(p[1]),
            'original_size': (ow, oh),
        }

    # ---- 空间特征提取 (贺杰定位模块用) ----
    def get_spatial_features(self, image_or_path):
        """返回多尺度空间特征供定位模块使用

        Returns:
            feat_s2: np.ndarray [384, 14, 14]  Stage2 精细空间特征
            feat_s3: np.ndarray [576, 7, 7]    Stage3 深层语义特征
            fake_prob: float
        """
        img = self._load(image_or_path)
        t = self.transform(img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits, feat_s3, feat_s2 = self.model(t, return_spatial=True)
            p = F.softmax(logits, dim=1)[0]
        return {
            'feat_s2': feat_s2.squeeze(0).cpu().numpy(),  # [384, 14, 14]
            'feat_s3': feat_s3.squeeze(0).cpu().numpy(),  # [576, 7, 7]
            'fake_prob': float(p[1]),
        }

    def _load(self, x, preprocess=True):
        if isinstance(x, str):
            img = Image.open(x).convert('RGB')
        elif isinstance(x, Image.Image):
            img = x.convert('RGB')
        else:
            raise TypeError('Need PIL.Image or file path')
        return img


if __name__ == '__main__':
    import sys
    detector = Detector(checkpoint_path='./checkpoints/best.pth')
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if path:
        r = detector.predict(path)
        print(f'result: {r["label"]}, fake_prob={r["fake_prob"]:.4f}')
        h = detector.get_heatmap(path)
        print(f'heatmap: {h["heatmap"].shape}, range=[{h["heatmap"].min():.3f},{h["heatmap"].max():.3f}]')
    else:
        print('usage: python inference_api.py <image>')
