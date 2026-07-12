【文件清单】
  inference_api.py          — 检测器类，提供三个对外接口
  best.pth                  — 训练好的模型权重 (~520MB)
  models/__init__.py         — 模型包入口
  models/mambaout_custom.py  — MambaOut-Small 骨干网络定义
  models/mkmmd.py            — MK-MMD 损失函数定义

【环境要求】
  pip install torch torchvision pillow numpy

【快速测试】
  python inference_api.py 图片路径.jpg

【接口一：std_predict】只拿检测结果（给羿帅前端用）
  from inference_api import Detector
  detector = Detector(checkpoint_path='./best.pth')
  result = detector.predict('图片.jpg')
  # 返回: {'label': 'fake', 'real_prob': 0.03, 'fake_prob': 0.97, 'risk_score': 0.97}

【接口二：predict_with_features】检测结果 + 中间特征（你自己分析用）
  result, feat_256, feat_2304 = detector.predict_with_features('图片.jpg')
  # feat_256:  numpy array [256]  瓶颈层特征（256维）
  # feat_2304: numpy array [2304] 空间特征 = 576通道 × 2×2空间

【接口三：get_heatmap_data】热力图专用（你写heatmap代码的核心）
  data = detector.get_heatmap_data('图片.jpg')
  # 返回 dict:
  {
      'label':                   'real' 或 'fake',
      'fake_prob':               0.97,
      'feat_256':                numpy [256],   瓶颈层特征
      'feat_2304':               numpy [2304],  576×2×2 空间密集特征
      'classifier_weight_fake':  numpy [256],   fake类在分类头中的权重
      'classifier_bias_fake':    0.xx,          偏置
      'original_size':           (W, H),        原图尺寸
  }

【热力图生成思路 — feat_2304 的reshape方式】
  feat_2304 的组织：
    [ch0_x0y0, ch0_x0y1, ch0_x1y0, ch0_x1y1,
     ch1_x0y0, ch1_x0y1, ch1_x1y0, ch1_x1y1, ...]
  即先通道再空间 → reshape为 (576, 2, 2)

  第 i 个通道的空间贡献 ≈ classifier_weight_fake[i] × feat_256[i]
  → 576个通道加权求和 → 2×2 热力分数矩阵
  → 双线性插值上采样到 224×224 或原图尺寸
  → colormap 叠加原图

【注意事项】
  - 输入图片格式支持 JPG/PNG/BMP
  - 推理设备默认 cuda，若无 GPU 改为 device='cpu'
  - classifier_weight_fake 形状为 [256]，代表 fake 类对应 256 维瓶颈特征的权重
  - 瓶颈层输出经 ReLU，feat_256 各维度均非负
