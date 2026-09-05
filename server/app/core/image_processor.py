"""
图片处理器

封装图片压缩、缩略图生成、信息提取与 EXIF 方向处理等通用能力，
基于 Pillow 实现，供 ImageService 调用。
"""

import io
from typing import Tuple

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.exceptions import ValidationException
from app.schemas.image import ImageInfo


class ImageProcessor:
    """图片处理工具类（无状态，可直接实例化或作为类方法使用）"""

    # 允许处理的图片格式
    SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "GIF"}

    # 各格式对应的 MIME 类型
    FORMAT_TO_MIME = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
        "WEBP": "image/webp",
        "BMP": "image/bmp",
        "GIF": "image/gif",
    }

    @staticmethod
    def _open(image_bytes: bytes) -> Image.Image:
        """从字节流打开图片，失败抛出校验异常"""
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except (UnidentifiedImageError, OSError) as exc:
            raise ValidationException(f"无法识别的图片文件: {exc}") from exc
        return img

    @staticmethod
    def handle_exif(image: Image.Image) -> Image.Image:
        """
        根据 EXIF 方向标签自动旋转图片，避免上传后方向错乱。

        常见于手机拍摄的照片，其方向信息记录在 EXIF Orientation 字段中。
        """
        try:
            # ImageOps.exif_transpose 会读取 EXIF 并就地旋转
            return ImageOps.exif_transpose(image)
        except Exception:
            # 无 EXIF 或解析失败时原样返回
            return image

    @classmethod
    def compress_image(cls, image_bytes: bytes, max_size: int = 5 * 1024 * 1024) -> bytes:
        """
        压缩图片至目标大小以内。

        策略：
        1. 先统一处理 EXIF 方向；
        2. 若原图为 PNG 等无损格式且体积过大，转换为 JPEG 进一步压缩；
        3. 逐步降低 JPEG 质量，直到文件大小 <= max_size 或达到下限。

        Args:
            image_bytes: 原始图片字节流
            max_size: 目标最大字节数，默认 5MB

        Returns:
            压缩后的图片字节流
        """
        img = cls._open(image_bytes)
        img = cls.handle_exif(img)

        # 统一转换为 RGB（去除 alpha 通道），便于 JPEG 编码
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # 原始大小已满足要求，直接返回
        if len(image_bytes) <= max_size:
            return image_bytes

        # 逐步降低质量压缩
        quality = 90
        step = 10
        output = io.BytesIO()
        while quality >= 30:
            output.seek(0)
            output.truncate()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            if output.tell() <= max_size:
                return output.getvalue()
            quality -= step

        # 质量已到下限仍超标，则按比例缩小尺寸
        scale = 0.8
        while scale > 0.1:
            new_size = (max(1, int(img.width * scale)), max(1, int(img.height * scale)))
            resized = img.resize(new_size, Image.LANCZOS)
            output.seek(0)
            output.truncate()
            resized.save(output, format="JPEG", quality=50, optimize=True)
            if output.tell() <= max_size:
                return output.getvalue()
            scale -= 0.1

        # 最终兜底
        return output.getvalue()

    @classmethod
    def generate_thumbnail(cls, image_bytes: bytes, size: Tuple[int, int] = (512, 512)) -> bytes:
        """
        生成缩略图。

        使用等比例缩放并填充至目标尺寸（保持比例不变形），输出 JPEG。

        Args:
            image_bytes: 原始图片字节流
            size: 目标缩略图尺寸 (width, height)，默认 512x512

        Returns:
            缩略图字节流
        """
        img = cls._open(image_bytes)
        img = cls.handle_exif(img)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # 等比例缩放，最长边不超过 size 中较大者
        max_edge = max(size)
        if max(img.width, img.height) > max_edge:
            img.thumbnail(size, Image.LANCZOS)

        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()

    @classmethod
    def get_image_info(cls, image_bytes: bytes) -> ImageInfo:
        """
        提取图片信息：MIME 类型、宽高、文件大小。

        Args:
            image_bytes: 原始图片字节流

        Returns:
            ImageInfo 模式对象
        """
        img = cls._open(image_bytes)
        img = cls.handle_exif(img)

        fmt = (img.format or "JPEG").upper()
        mime = cls.FORMAT_TO_MIME.get(fmt, "image/jpeg")

        return ImageInfo(
            image_id="",  # 由上层服务填充
            original_url="",  # 由上层服务填充
            thumbnail_url=None,
            mime_type=mime,
            width=img.width,
            height=img.height,
            size=len(image_bytes),
            compressed=False,
            compressed_ratio=None,
            created_at=None,
        )
