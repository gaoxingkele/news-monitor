"""Push channel registry — type → class mapping and factory."""
from __future__ import annotations

from typing import Type

from news_monitor.push.base import PushChannel
from news_monitor.push.feishu import FeishuChannel
from news_monitor.push.dingtalk import DingTalkChannel
from news_monitor.push.wecom import WeComChannel

_REGISTRY: dict[str, Type[PushChannel]] = {
    "feishu": FeishuChannel,
    "dingtalk": DingTalkChannel,
    "wecom": WeComChannel,
}


def create_channel(channel_type: str, config: dict) -> PushChannel:
    """Instantiate a push channel by type name."""
    cls = _REGISTRY.get(channel_type)
    if cls is None:
        raise ValueError(
            f"Unknown push channel: {channel_type!r}. Available: {list(_REGISTRY)}"
        )
    return cls(config=config)


def list_channels() -> list[str]:
    return list(_REGISTRY.keys())
