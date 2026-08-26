"""
模型配置存储与内存缓存

提供 Provider 配置的持久化（数据库）与内存缓存层：
- 启动时从 DB 加载到内存，Provider 同步方法可直接读取
- 管理后台保存时写 DB 并刷新缓存，立即生效无需重启
- 首次启动（DB 为空）时从 .env 配置播种
"""

import json
import logging
from typing import Any

from app.database import async_session_maker

logger = logging.getLogger(__name__)

# 所有支持的 Provider ID 列表
ALL_PROVIDER_IDS = ["qianwen", "dalle", "minimax", "volcengine", "doubao"]


class ModelConfigStore:
    """Provider 配置内存缓存 + DB 持久化"""

    def __init__(self) -> None:
        self._configs: dict[str, dict[str, Any]] = {}
        self._default_provider: str = "qianwen"
        self._enabled_providers: list[str] = ["qianwen"]
        self._loaded: bool = False

    @property
    def loaded(self) -> bool:
        return self._loaded

    # -------------------- 读取 --------------------

    def get_default_provider(self) -> str:
        """获取默认 Provider ID"""
        return self._default_provider

    def get_enabled_providers(self) -> list[str]:
        """获取当前启用的 Provider ID 列表"""
        return list(self._enabled_providers)

    def get_config(self, provider_id: str) -> dict[str, Any] | None:
        """获取指定 Provider 的配置字典"""
        return self._configs.get(provider_id)

    def get_all_configs(self) -> dict[str, dict[str, Any]]:
        """获取所有 Provider 配置"""
        return dict(self._configs)

    def get_api_key(self, provider_id: str) -> str:
        """获取 Provider 的 API Key（兼容各 Provider 的 key 字段名）"""
        config = self._configs.get(provider_id)
        if not config:
            return ""
        # doubao 使用 access_key + secret_key，其他使用 api_key
        if provider_id == "doubao":
            return config.get("access_key", "")
        return config.get("api_key", "")

    # -------------------- 背景音乐配置 --------------------

    def get_bgm_music_url(self) -> str:
        """获取背景音乐 URL（空字符串表示使用内置 mp3）"""
        config = self._configs.get("_bgm") or {}
        return config.get("music_url", "").strip()

    async def save_bgm_music_url(self, music_url: str) -> None:
        """保存背景音乐 URL 到 DB 并更新内存"""
        from app.repositories.provider_config_repo import ProviderConfigRepository

        async with async_session_maker() as session:
            repo = ProviderConfigRepository(session)
            await repo.upsert(
                "_bgm",
                json.dumps({"music_url": music_url.strip()}, ensure_ascii=False),
            )
            await session.commit()

        self._configs["_bgm"] = {"music_url": music_url.strip()}
        logger.info("背景音乐 URL 已保存: %s", music_url.strip() or "(使用内置 mp3)")

    # -------------------- 写入 --------------------

    def set_config(self, provider_id: str, config: dict[str, Any]) -> None:
        """设置 Provider 配置（仅更新内存）"""
        self._configs[provider_id] = config

    def set_default_provider(self, provider_id: str) -> None:
        """设置默认 Provider ID（仅更新内存）"""
        self._default_provider = provider_id

    def set_enabled_providers(self, providers: list[str]) -> None:
        """设置启用的 Provider 列表（仅更新内存）"""
        self._enabled_providers = [p for p in providers if p in ALL_PROVIDER_IDS]

    # -------------------- DB 操作 --------------------

    async def refresh_from_db(self) -> None:
        """从 DB 重新加载所有配置到内存"""
        from app.repositories.provider_config_repo import ProviderConfigRepository

        async with async_session_maker() as session:
            repo = ProviderConfigRepository(session)
            rows = await repo.get_all_configs()

            configs: dict[str, dict[str, Any]] = {}
            for row in rows:
                try:
                    configs[row.provider_id] = json.loads(row.config_json)
                except (json.JSONDecodeError, TypeError):
                    configs[row.provider_id] = {}

            self._configs = configs

            # 读取默认 Provider
            default_row = await repo.get_by_provider_id("_default")
            if default_row:
                try:
                    data = json.loads(default_row.config_json)
                    self._default_provider = data.get("provider", "qianwen")
                except (json.JSONDecodeError, TypeError):
                    self._default_provider = "qianwen"
            elif configs:
                # 没有显式默认值记录，取第一个有 api_key 的 provider
                self._default_provider = "qianwen"

            # 读取启用 Provider 列表
            ep_row = await repo.get_by_provider_id("_enabled_providers")
            if ep_row:
                try:
                    data = json.loads(ep_row.config_json)
                    providers = data.get("providers", [])
                    self._enabled_providers = [p for p in providers if p in ALL_PROVIDER_IDS]
                except (json.JSONDecodeError, TypeError):
                    self._enabled_providers = ["qianwen"]
            else:
                self._enabled_providers = [self._default_provider]

        self._loaded = True
        logger.info(
            "模型配置已从 DB 加载: providers=%s, default=%s, enabled=%s",
            list(self._configs.keys()),
            self._default_provider,
            self._enabled_providers,
        )

    async def save_provider_config(
        self, provider_id: str, config: dict[str, Any]
    ) -> None:
        """保存 Provider 配置到 DB 并更新内存"""
        from app.repositories.provider_config_repo import ProviderConfigRepository

        async with async_session_maker() as session:
            repo = ProviderConfigRepository(session)
            await repo.upsert(provider_id, json.dumps(config, ensure_ascii=False))
            await session.commit()

        self._configs[provider_id] = config
        logger.info("Provider [%s] 配置已保存到 DB", provider_id)

    async def save_default_provider(self, provider_id: str) -> None:
        """保存默认 Provider 到 DB 并更新内存"""
        from app.repositories.provider_config_repo import ProviderConfigRepository

        async with async_session_maker() as session:
            repo = ProviderConfigRepository(session)
            await repo.upsert(
                "_default",
                json.dumps({"provider": provider_id}),
            )
            await session.commit()

        self._default_provider = provider_id
        logger.info("默认 Provider 已更新为 [%s]", provider_id)

    async def save_enabled_providers(self, providers: list[str]) -> None:
        """保存启用的 Provider 列表到 DB 并更新内存"""
        from app.repositories.provider_config_repo import ProviderConfigRepository

        valid = [p for p in providers if p in ALL_PROVIDER_IDS]
        if not valid:
            valid = ["qianwen"]

        async with async_session_maker() as session:
            repo = ProviderConfigRepository(session)
            await repo.upsert(
                "_enabled_providers",
                json.dumps({"providers": valid}),
            )
            await session.commit()

        self._enabled_providers = valid
        logger.info("启用 Provider 列表已更新: %s", valid)

    async def seed_from_env_if_empty(self) -> None:
        """首次启动时从 .env 配置播种到 DB"""
        from app.config import settings
        from app.repositories.provider_config_repo import ProviderConfigRepository

        async with async_session_maker() as session:
            repo = ProviderConfigRepository(session)
            rows = await repo.get_all_configs()

            if rows:
                # DB 已有数据，直接加载
                await session.close()
                await self.refresh_from_db()
                return

            await session.close()

        # DB 为空，从 .env 播种
        logger.info("provider_configs 表为空，从 .env 配置播种...")

        seeds: dict[str, dict[str, Any]] = {
            "qianwen": {
                "api_key": settings.dashscope.api_key.get_secret_value(),
                "base_url": settings.dashscope.base_url,
                "model_vision": settings.dashscope.model_vision,
                "model_image": settings.dashscope.model_image,
                "workspace_id": settings.dashscope.workspace_id,
                "region": settings.dashscope.region,
                # 运行时可调：超时（秒，默认 300）与提示词自动扩展（默认开启）
                "timeout": 300,
                "prompt_extend": True,
            },
            "dalle": {
                "api_key": settings.dalle.api_key.get_secret_value(),
                "base_url": settings.dalle.base_url,
                "model_image": settings.dalle.model_image,
                # GPT Image 2 特有参数默认值
                "size": "auto",
                "resolution": "1K",
                "quality": "medium",
            },
            "minimax": {
                "api_key": settings.minimax.api_key.get_secret_value(),
                "base_url": settings.minimax.base_url,
                "model_image": settings.minimax.model_image,
                "watermark": settings.minimax.watermark,
            },
            "volcengine": {
                "api_key": settings.volcengine.api_key.get_secret_value(),
                "base_url": settings.volcengine.base_url,
                "model_image": settings.volcengine.model_image,
                "watermark": settings.volcengine.watermark,
            },
            "doubao": {
                "access_key": settings.doubao.access_key.get_secret_value(),
                "secret_key": settings.doubao.secret_key.get_secret_value(),
            },
        }

        for pid, cfg in seeds.items():
            await self.save_provider_config(pid, cfg)

        await self.save_default_provider(settings.model.default_provider)
        await self.save_enabled_providers([settings.model.default_provider])
        await self.refresh_from_db()


# 全局单例
model_config_store = ModelConfigStore()
