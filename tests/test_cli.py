"""
CLI 测试 (参数解析, 无模型)
"""

import pytest
import subprocess
import sys
import os


class TestCLI:

    @pytest.fixture
    def cli_module_path(self):
        """返回 cli.py 模块路径"""
        return os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'explanation', 'cli.py'
        )

    def test_help_output(self):
        """--help 不报错且打印帮助"""
        result = subprocess.run(
            [sys.executable, '-m', 'explanation.cli', '--help'],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        assert result.returncode == 0
        assert '--input' in result.stdout or '--input' in result.stderr

    def test_missing_input_fails(self):
        """无 --input 时报错"""
        result = subprocess.run(
            [sys.executable, '-m', 'explanation.cli'],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        assert result.returncode != 0  # 应非零退出

    def test_config_flag_exists(self):
        """--config 参数存在"""
        result = subprocess.run(
            [sys.executable, '-m', 'explanation.cli', '--help'],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        assert '--config' in result.stdout or '--config' in result.stderr

    def test_nonexistent_input_fails(self):
        """不存在的输入文件报错"""
        result = subprocess.run(
            [sys.executable, '-m', 'explanation.cli', '--input', '/nonexistent/file.jpg'],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        assert result.returncode != 0


class TestBatchCLI:

    def test_batch_help(self):
        """批量脚本 --help 正常"""
        result = subprocess.run(
            [sys.executable, '-m', 'explanation.batch', '--help'],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        assert result.returncode == 0

    def test_batch_config_flag(self):
        """批量脚本 --config 参数存在"""
        result = subprocess.run(
            [sys.executable, '-m', 'explanation.batch', '--help'],
            capture_output=True, text=True, timeout=15,
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )
        assert '--config' in result.stdout or '--config' in result.stderr
