"""
LLM API 客户端 — 通过 OpenAI 兼容 SDK 调用，全部配置由 default.yaml 控制
"""

import logging

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    DeepSeek LLM API 客户端。

    使用 OpenAI 兼容接口，base_url 指向 DeepSeek API。

    Usage:
        client = DeepSeekClient(api_key="sk-xxx", model="deepseek-v4-pro")
        reply = client.chat([
            {"role": "system", "content": "你是取证分析专家"},
            {"role": "user", "content": "请分析以下数据..."},
        ])
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    @property
    def is_configured(self) -> bool:
        """检查 API Key 与必要参数是否已配置"""
        return bool(self.api_key and self.model and self.base_url)

    def _ensure_client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is not None:
            return
        if not self.is_configured:
            raise RuntimeError(
                "LLM client not configured. "
                "Check llm section in configs/default.yaml"
            )
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        except ImportError:
            raise ImportError(
                "openai package is required for LLM integration. "
                "Install with: pip install openai>=1.0"
            )

    def chat(
        self,
        messages: list[dict],
        temperature: float = None,
        max_tokens: int = None,
    ) -> str:
        """
        发送 chat completion 请求，返回回复文本。

        Args:
            messages: OpenAI 格式消息列表
            temperature: 覆盖默认温度
            max_tokens: 覆盖默认最大 token 数

        Returns:
            str — 模型回复文本
        """
        self._ensure_client()
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.error(f"DeepSeek API call failed: {exc}")
            raise
