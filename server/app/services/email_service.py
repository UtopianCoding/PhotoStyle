"""
邮件验证码服务

提供邮箱验证码的生成、存储（Redis）、校验与邮件发送功能。
用于注册流程中的邮箱验证。
"""

import logging
import random
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import redis.asyncio as aioredis

from app.config import settings
from app.core.exceptions import RateLimitExceededException, ValidationException

logger = logging.getLogger(__name__)

# Redis key 前缀
_CODE_KEY_PREFIX = "email_code:"
_RATE_LIMIT_KEY_PREFIX = "email_rate:"

# 验证码有效期（秒）
_CODE_TTL = 300  # 5 分钟
# 发送频率限制（秒）
_RATE_LIMIT_TTL = 60  # 60 秒内只能发一次


class EmailService:
    """邮件验证码服务"""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """获取 Redis 异步客户端（懒初始化单例）"""
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis.url,
                decode_responses=True,
            )
        return self._redis

    async def close(self) -> None:
        """关闭 Redis 连接"""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    # -------------------- 验证码生成与存储 --------------------

    @staticmethod
    def _generate_code() -> str:
        """生成 6 位数字验证码"""
        return f"{random.randint(0, 999999):06d}"

    async def send_code(self, email: str, client_ip: str = "") -> None:
        """
        生成验证码、存入 Redis 并发送邮件。
        
        多维度防刷机制：
        - 同一邮箱 60 秒冷却期
        - 同一邮箱每日上限 10 次
        - 同一邮箱每小时上限 3 次
        - 同一 IP 每小时上限 10 次
        - 全局每小时上限 1000 次

        Args:
            email: 目标邮箱
            client_ip: 客户端 IP 地址（可选，用于 IP 级限流）

        Raises:
            RateLimitExceededException: 触发任一限流规则
            ValidationException: 邮件发送失败或邮箱格式错误
        """
        r = await self._get_redis()
        
        # 邮箱格式基础校验
        if not email or "@" not in email or len(email) > 254:
            raise ValidationException("邮箱格式不正确")

        # ===== 多维度限流检查 =====
        
        # 1. 60 秒冷却期（同一邮箱）
        rate_key = f"{_RATE_LIMIT_KEY_PREFIX}{email}"
        ttl = await r.ttl(rate_key)
        if ttl > 0:
            raise RateLimitExceededException(f"发送过于频繁，请 {ttl} 秒后重试")

        # 2. 每小时限流（同一邮箱，最多 3 次）
        hourly_email_key = f"email_hourly:{email}"
        hourly_email_count = await r.get(hourly_email_key)
        if hourly_email_count and int(hourly_email_count) >= 3:
            ttl = await r.ttl(hourly_email_key)
            minutes = ttl // 60 if ttl else 60
            raise RateLimitExceededException(f"该邮箱每小时最多发送 3 次，请 {minutes} 分钟后重试")

        # 3. 每日限流（同一邮箱，最多 10 次）
        daily_email_key = f"email_daily:{email}"
        daily_email_count = await r.get(daily_email_key)
        if daily_email_count and int(daily_email_count) >= 10:
            raise RateLimitExceededException("该邮箱今日发送次数已达上限（10 次），请明天再试")

        # 4. IP 限流（如果有 IP，每小时最多 10 次）
        if client_ip:
            hourly_ip_key = f"ip_hourly:{client_ip}"
            hourly_ip_count = await r.get(hourly_ip_key)
            if hourly_ip_count and int(hourly_ip_count) >= 10:
                ttl = await r.ttl(hourly_ip_key)
                minutes = ttl // 60 if ttl else 60
                raise RateLimitExceededException(f"当前 IP 每小时最多发送 10 次，请 {minutes} 分钟后重试")

        # 5. 全局限流（每小时最多 1000 次）
        global_hourly_key = "global_hourly"
        global_hourly_count = await r.get(global_hourly_key)
        if global_hourly_count and int(global_hourly_count) >= 1000:
            raise RateLimitExceededException("系统繁忙，请稍后再试")

        # ===== 生成验证码并存储 =====
        code = self._generate_code()
        code_key = f"{_CODE_KEY_PREFIX}{email}"

        # 存入 Redis，设置 5 分钟过期
        await r.set(code_key, code, ex=_CODE_TTL)

        # ===== 更新所有计数器 =====
        
        # 60 秒冷却期
        await r.set(rate_key, "1", ex=_RATE_LIMIT_TTL)
        
        # 每小时邮箱计数（3600 秒）
        if not hourly_email_count:
            await r.set(hourly_email_key, "1", ex=3600)
        else:
            await r.incr(hourly_email_key)
        
        # 每日邮箱计数（86400 秒）
        if not daily_email_count:
            await r.set(daily_email_key, "1", ex=86400)
        else:
            await r.incr(daily_email_key)
        
        # IP 每小时计数
        if client_ip:
            if not hourly_ip_count:
                await r.set(f"ip_hourly:{client_ip}", "1", ex=3600)
            else:
                await r.incr(f"ip_hourly:{client_ip}")
        
        # 全局每小时计数
        if not global_hourly_count:
            await r.set(global_hourly_key, "1", ex=3600)
        else:
            await r.incr(global_hourly_key)

        # ===== 发送邮件 =====
        try:
            await self._send_email(email, code)
            logger.info("[验证码] 已发送至 %s (IP: %s)", email, client_ip or "unknown")
        except Exception as e:
            # 邮件发送失败时，回滚冷却期（允许重试）
            await r.delete(rate_key)
            logger.error("[验证码] 发送至 %s 失败: %s", email, e)
            raise ValidationException(f"邮件发送失败: {str(e)}")

    async def verify_code(self, email: str, code: str) -> bool:
        """
        校验验证码是否正确。校验成功后删除验证码（一次性使用）。

        Args:
            email: 邮箱
            code: 用户输入的验证码

        Returns:
            True if valid

        Raises:
            ValidationException: 验证码错误或已过期
        """
        r = await self._get_redis()
        code_key = f"{_CODE_KEY_PREFIX}{email}"

        stored = await r.get(code_key)
        if stored is None:
            raise ValidationException("验证码已过期，请重新获取")
        if stored != code.strip():
            raise ValidationException("验证码错误")

        # 校验成功，删除验证码（一次性使用）
        await r.delete(code_key)
        logger.info("[验证码] %s 验证通过", email)
        return True

    # -------------------- 邮件发送 --------------------

    async def _send_email(self, to_email: str, code: str) -> None:
        """通过 SMTP 发送验证码邮件"""
        smtp_cfg = settings.smtp

        if not smtp_cfg.username or not smtp_cfg.password.get_secret_value():
            # 未配置 SMTP 时，仅打印日志（开发环境）
            logger.warning(
                "[验证码] SMTP 未配置，验证码仅记录日志: email=%s, code=%s",
                to_email, code,
            )
            return

        subject = f"【{smtp_cfg.from_name}】邮箱验证码"
        html_body = self._build_email_html(code)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{smtp_cfg.from_name} <{smtp_cfg.username}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            # 根据端口选择连接方式：465 使用 SSL，587 使用 STARTTLS
            logger.debug("[邮件] 正在连接 SMTP: %s:%d", smtp_cfg.host, smtp_cfg.port)
            
            # 创建 SSL 上下文（兼容 QQ 等国内邮箱服务器）
            ssl_context = ssl.create_default_context()
            
            if smtp_cfg.port == 465:
                # 直接 SSL 连接，显式传入 SSL 上下文
                server = smtplib.SMTP_SSL(
                    smtp_cfg.host, 
                    smtp_cfg.port, 
                    timeout=15,
                    context=ssl_context
                )
                logger.debug("[邮件] SSL 连接已建立")
            else:
                # STARTTLS 连接（端口 587 或 25）
                server = smtplib.SMTP(smtp_cfg.host, smtp_cfg.port, timeout=15)
                server.ehlo()  # 识别服务器功能
                logger.debug("[邮件] SMTP 连接已建立，EHLO 完成")
                
                if smtp_cfg.use_tls:
                    server.starttls(context=ssl_context)
                    server.ehlo()  # TLS 握手后重新识别
                    logger.debug("[邮件] STARTTLS 握手完成")

            logger.debug("[邮件] 正在登录: %s", smtp_cfg.username)
            server.login(smtp_cfg.username, smtp_cfg.password.get_secret_value())
            logger.debug("[邮件] 登录成功")
            
            server.sendmail(smtp_cfg.username, [to_email], msg.as_string())
            server.quit()
            logger.info("[邮件] 发送成功: to=%s", to_email)
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("[邮件] 认证失败（请检查用户名和授权码）: %s", exc)
            raise ValidationException(f"邮件发送失败: SMTP 认证失败，请检查授权码配置") from exc
        except smtplib.SMTPServerDisconnected as exc:
            logger.error("[邮件] 服务器断开连接: %s", exc)
            raise ValidationException(f"邮件发送失败: SMTP 服务器断开连接，请检查网络或端口配置") from exc
        except smtplib.SMTPException as exc:
            logger.error("[邮件] SMTP 错误: %s", exc)
            raise ValidationException(f"邮件发送失败: {exc}") from exc
        except Exception as exc:
            logger.error("[邮件] 发送失败: %s", exc)
            raise ValidationException(f"邮件发送失败: {exc}") from exc

    @staticmethod
    def _build_email_html(code: str) -> str:
        """构建验证码邮件 HTML 模板"""
        return f"""
        <div style="max-width:480px;margin:0 auto;padding:40px 24px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1c1c1a;">
          <div style="text-align:center;margin-bottom:32px;">
            <div style="display:inline-block;width:40px;height:40px;border-radius:4px;background:#c8442b;color:#fff;font-size:22px;line-height:40px;text-align:center;font-weight:700;">影</div>
          </div>
          <div style="background:#faf8f3;border:1px solid rgba(156,150,139,0.25);border-radius:12px;padding:32px;text-align:center;">
            <h2 style="font-size:18px;margin:0 0 8px;font-weight:700;">邮箱验证码</h2>
            <p style="font-size:14px;color:#9c968b;margin:0 0 24px;">你正在注册 PhotoStyle，验证码 5 分钟内有效</p>
            <div style="font-size:36px;font-weight:700;letter-spacing:0.2em;color:#c8442b;font-family:'Courier New',monospace;margin:0 0 24px;">{code}</div>
            <p style="font-size:12px;color:#b5afa3;margin:0;">如非本人操作，请忽略此邮件</p>
          </div>
          <p style="text-align:center;font-size:11px;color:#b5afa3;margin-top:24px;letter-spacing:0.05em;">PhotoStyle &middot; AI Photo Style Transfer</p>
        </div>
        """
