TraceGuard:面向社交媒体网络传播的 可解释 AIGC 图像取证平台
Windows 可执行程序

目录结构：
  TraceGuard.exe
  TraceGuard\

使用方法：
1. 安装 Python 3.10 或更高版本。
2. 在 TraceGuard 目录中执行：python -m pip install -r requirements.txt
3. 双击 TraceGuard.exe，或在命令行执行：TraceGuard.exe --device cuda --port 8000
4. 浏览器访问 http://127.0.0.1:8000/

启动器会自动查找 TraceGuard\.venv\Scripts\python.exe、TraceGuard\venv\Scripts\python.exe 或系统 PATH 中的 python.exe。
也可以通过 TRACEGUARD_PYTHON 环境变量指定 Python 解释器。

本程序是“可执行启动器 + 运行目录”形式，模型权重和 Python 依赖保留在 TraceGuard 目录中，便于替换和复核；不是把 PyTorch 与 545MB 权重强行封装进单一文件。
