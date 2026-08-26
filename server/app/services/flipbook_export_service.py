"""
3D 翻页画册导出服务

将画册导出为独立的 HTML 静态网页（HTML + CSS + JS，3D 翻页效果）。
用户下载后可在本地浏览器直接打开浏览，图片通过原始 URL 引用。

实现要点：
- 内联 page-flip 库（优先读取本地 node_modules，缺失时回退 CDN）
- 内联相册样式（含 AI 生成的主题色）
- 服务端渲染所有页面（含自动补页 + 封底）
- 键盘 / 按钮 / 触摸翻页
"""

import html
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.flipbook import FlipbookPage, FlipbookProject

logger = logging.getLogger(__name__)

# 项目根目录（server/app/services/xxx.py → 项目根）
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
# page-flip 库浏览器版文件路径
_PAGE_FLIP_LIB_PATH = (
    _PROJECT_ROOT
    / "web"
    / "node_modules"
    / "page-flip"
    / "dist"
    / "js"
    / "page-flip.browser.js"
)
# CDN 回退地址
_PAGE_FLIP_CDN = "https://unpkg.com/page-flip@2.0.7/dist/js/page-flip.browser.js"
# 封面背景照片（web/src/fm 下的雪山图，导出时 base64 内联）
_COVER_ART_PATH = (
    _PROJECT_ROOT
    / "web"
    / "src"
    / "fm"
    / "pexels-kaomhg-26926197.jpg"
)
_cover_art_cache: str | None = None


def _load_cover_art() -> str:
    """读取封面照片并转为 base64（模块级缓存，避免重复 IO）"""
    global _cover_art_cache
    if _cover_art_cache is None:
        import base64 as _b64

        data = _COVER_ART_PATH.read_bytes()
        _cover_art_cache = _b64.b64encode(data).decode("ascii")
    return _cover_art_cache


# 背景音乐文件（web/src/bj 下的 mp3，导出时 base64 内联）
_MUSIC_PATH = (
    _PROJECT_ROOT
    / "web"
    / "src"
    / "bj"
    / "M500000KLNC112AvSq.mp3"
)
_music_b64_cache: str | None = None


def _load_music_b64() -> str:
    """读取背景音乐并转为 base64（模块级缓存，避免重复 IO；文件缺失返回空串）"""
    global _music_b64_cache
    if _music_b64_cache is None:
        if not _MUSIC_PATH.exists():
            _music_b64_cache = ""
        else:
            import base64 as _b64

            data = _MUSIC_PATH.read_bytes()
            _music_b64_cache = _b64.b64encode(data).decode("ascii")
    return _music_b64_cache

# 默认画册布局（页面未记录图片尺寸时使用）
_DEFAULT_WIDTH = 500
_DEFAULT_HEIGHT = 680
_DEFAULT_PADDING = 24

# 内联样式（与前端 photo-flipbook.css 保持一致，主题色用占位符替换）
_FLIPBOOK_CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; min-width: 320px; min-height: 100%; }
body {
  background:
    radial-gradient(circle at 50% 42%, rgba(255,255,255,.68), transparent 35%),
    linear-gradient(135deg, #dedacf, #cbc7bb);
  color: var(--flipbook-ink);
  font-family: Arial, sans-serif;
}
.flipbook-room {
  position: relative;
  min-height: 100svh;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 12px;
  overflow: hidden;
  padding: 24px 32px 20px;
  isolation: isolate;
  /* 午后窗光：中心聚光 + 底部桌面渐深 + 暖沙底色 */
  background:
    radial-gradient(circle at 50% 40%, rgba(255, 255, 255, 0.5), transparent 45%),
    linear-gradient(180deg, transparent 50%, rgba(88, 74, 56, 0.24) 100%),
    linear-gradient(160deg, #ece4d3, #b0a388);
  opacity: 0;
  animation: flipbook-room-in 0.9s ease-out forwards;
}
/* 斜射光束 + 纸张肌理：一道暖光从左上方斜射入 */
.flipbook-room::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    linear-gradient(105deg, transparent 28%, rgba(255, 246, 222, 0.5) 46%, transparent 62%),
    url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-blend-mode: screen;
  opacity: 0.5;
  animation: flipbook-light-breathe 7s ease-in-out infinite;
}
@keyframes flipbook-light-breathe {
  0%, 100% { opacity: 0.32; }
  50% { opacity: 0.58; }
}
/* 角落暗角：增加纵深，聚焦中央画册 */
.flipbook-room::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(ellipse 90% 80% at 50% 45%, transparent 55%, rgba(60, 50, 35, 0.18) 100%);
}
@keyframes flipbook-room-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
.flipbook-room .photo-book-rig {
  transform: rotateX(5deg) rotateZ(-.18deg) scale(0.94);
  animation: flipbook-open 1.2s cubic-bezier(.2,.7,.1,1) 0.35s forwards;
}
@keyframes flipbook-open {
  from {
    transform: rotateX(5deg) rotateZ(-.18deg) scale(0.94);
    filter: brightness(0.9);
  }
  to {
    transform: rotateX(5deg) rotateZ(-.18deg) scale(1);
    filter: brightness(1);
  }
}
.flipbook-header {
  opacity: 0;
  animation: flipbook-fade 0.7s ease-out 0.5s forwards;
}
@keyframes flipbook-fade {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.flipbook-header {
  position: relative; z-index: 30;
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
  font-size: 10px; letter-spacing: .13em; text-transform: uppercase;
}
.flipbook-header h1 { margin: 0; font: 500 10px/1 Arial, sans-serif; }
.flipbook-header span:last-child { justify-self: end; color: var(--flipbook-muted); }
.flipbook-stage {
  position: relative; z-index: 2; min-height: 0;
  display: grid; place-items: center; perspective: 1900px;
}
.photo-book-rig {
  position: relative; z-index: 4;
  width: min(82vw, calc((100svh - 150px) * var(--flipbook-spread-ratio)), var(--flipbook-max-spread));
  display: grid; place-items: center;
  transform: rotateX(5deg) rotateZ(-.18deg);
  transform-style: preserve-3d;
  transition: transform .7s cubic-bezier(.2,.7,.1,1);
}
.is-turning .photo-book-rig { transform: rotateX(6.5deg) rotateZ(-.08deg) translateY(-.5%); }
.photo-book { filter: drop-shadow(0 30px 22px rgba(47,42,32,.22)); transition: filter .7s ease; }
.is-turning .photo-book { filter: drop-shadow(0 36px 28px rgba(47,42,32,.26)); }
.flipbook-ground-shadow {
  position: absolute; z-index: 1; left: 50%; top: 57%;
  width: min(78vw, 960px); height: 130px;
  transform: translate(-50%, -50%); border-radius: 50%;
  background: rgba(62,55,43,.18); filter: blur(30px);
  transition: width .7s ease, filter .7s ease, opacity .7s ease;
}
.is-turning .flipbook-ground-shadow { width: min(73vw, 900px); filter: blur(36px); opacity: .78; }
.photo-leaf.stf__item {
  --leaf-color: var(--flipbook-page-color);
  --leaf-texture: var(--flipbook-page-texture);
  position: absolute; overflow: hidden;
  background:
    linear-gradient(90deg, rgba(70,64,52,.045), transparent 5%, transparent 94%, rgba(70,64,52,.075)),
    var(--leaf-color);
  border: 1px solid rgba(70,64,52,.12);
  box-shadow: inset 0 0 22px rgba(70,64,52,.04);
  color: var(--flipbook-ink);
}
.photo-leaf.stf__item.photo-leaf--cover {
  --leaf-color: var(--flipbook-cover-color);
  --leaf-texture: var(--flipbook-cover-texture);
}
.photo-leaf.stf__item.photo-leaf--back-cover {
  --leaf-color: var(--flipbook-back-cover-color);
  --leaf-texture: var(--flipbook-back-cover-texture);
  background: var(--flipbook-back-cover-color);
}
.photo-leaf::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  opacity: .08; mix-blend-mode: multiply; background-image: var(--leaf-texture);
}
.photo-leaf img {
  display: block; width: calc(100% - var(--photo-inset, 0px));
  height: calc(100% - var(--photo-inset, 0px)); margin: var(--photo-padding, 0px);
  object-position: center; user-select: none; -webkit-user-drag: none;
}
.photo-leaf--fit-fill img { object-fit: fill; }
.photo-leaf--fit-cover img { object-fit: cover; }
.photo-leaf--fit-contain img { object-fit: contain; }
.photo-leaf__copy { position: absolute; z-index: 2; inset: auto 8% 7%; }
.photo-leaf__copy p { margin: .4em 0 0; }
.photo-leaf__caption { font-size: 9px; letter-spacing: .12em; text-transform: uppercase; }
/* 独立封皮：雪山照片背景 + 大标题 + 朱印 */
.photo-leaf__cover { position: absolute; inset: 0; z-index: 2; color: var(--flipbook-ink); }
.cover-art { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; user-select: none; -webkit-user-drag: none; }
.cover-art-shade { position: absolute; inset: 0; pointer-events: none; background: linear-gradient(180deg, rgba(255,255,255,.38), rgba(255,255,255,.08) 38%, rgba(18,40,62,.28) 100%); }
.cover-frame { position: absolute; inset: 12px; display: flex; flex-direction: column; padding: 18px 22px 20px; border: 1px solid rgba(30,74,102,.32); outline: 1px solid rgba(30,74,102,.12); outline-offset: 4px; }
.cover-body { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 12px; padding: 10px 0; text-align: center; }
.cover-title { font-family: Georgia, 'Times New Roman', 'Songti SC', serif; font-size: 40px; font-weight: 600; letter-spacing: .1em; line-height: 1.25; margin: 0; color: #1e4a66; text-shadow: 0 1px 0 rgba(255,255,255,.5), 0 2px 14px rgba(255,255,255,.65); }
.cover-footer { display: flex; justify-content: flex-end; align-items: center; gap: 10px; }
.cover-brand { font-family: Georgia, 'Times New Roman', 'Songti SC', serif; font-size: 13px; font-weight: 600; letter-spacing: .14em; color: #f8f5ee; text-shadow: 0 1px 3px rgba(18,40,62,.45); }
.cover-seal { width: 34px; height: 34px; display: grid; place-items: center; border-radius: 50%; background: #c8442b; color: #f5f2ec; font-family: Georgia, 'Songti SC', serif; font-size: 15px; border: 1px solid rgba(140,42,26,.6); box-shadow: 0 2px 8px rgba(140,42,26,.32); }
/* 封底：朱印 + 出品标记 */
.photo-leaf__back {
  position: absolute; inset: 0; z-index: 2;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 16px; color: var(--flipbook-ink);
}
.photo-leaf__back-seal { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 6px; background: #a8361f; color: #f5f2ec; font-family: Georgia, 'Songti SC', serif; font-size: 24px; box-shadow: 0 2px 8px rgba(168,54,31,.3); }
.photo-leaf__back-mark { font-size: 9px; letter-spacing: .28em; text-transform: uppercase; color: var(--flipbook-muted); }
.flipbook-controls {
  position: relative; z-index: 30;
  display: flex; justify-content: center; align-items: center; gap: 16px;
}
.flipbook-controls button {
  width: 38px; height: 38px; display: grid; place-items: center;
  border: 1px solid rgba(41,41,35,.18); border-radius: 50%;
  background: rgba(255,255,255,.25); color: var(--flipbook-ink); cursor: pointer;
  font: 24px/1 Georgia, serif;
  transition: transform .16s ease, background .16s ease, opacity .16s ease;
}
.flipbook-controls button:hover:not(:disabled) { transform: translateY(-2px); background: rgba(255,255,255,.55); }
.flipbook-controls button:disabled { opacity: .25; cursor: default; }
.flipbook-controls .flipbook-music { font-size: 14px; margin-left: 8px; background: rgba(255,255,255,.25); color: var(--flipbook-muted); transition: transform .16s ease, background .16s ease, color .2s ease; }
.flipbook-controls .flipbook-music:hover:not(:disabled) { background: rgba(255,255,255,.6); color: var(--flipbook-ink); }
.flipbook-controls .flipbook-music.is-playing { background: rgba(200,68,43,.12); border-color: rgba(200,68,43,.35); color: #a8361f; }
.flipbook-volume { width: 64px; height: 4px; margin-left: 10px; appearance: none; -webkit-appearance: none; border-radius: 999px; background: rgba(41,41,35,.18); cursor: pointer; }
.flipbook-volume::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 12px; height: 12px; border-radius: 50%; background: #292923; border: 2px solid rgba(255,255,255,.85); box-shadow: 0 1px 3px rgba(41,41,35,.3); }
.flipbook-volume::-moz-range-thumb { width: 12px; height: 12px; border-radius: 50%; background: #292923; border: 2px solid rgba(255,255,255,.85); box-shadow: 0 1px 3px rgba(41,41,35,.3); }
.flipbook-status { min-width: 170px; color: var(--flipbook-muted); text-align: center; text-transform: uppercase; }
.flipbook-status span { display: block; font-size: 9px; letter-spacing: .12em; }
.flipbook-status small { display: block; margin-top: 5px; font-size: 8px; letter-spacing: .09em; }
@media (max-width: 720px) {
  .flipbook-room { gap: 8px; padding: 18px 14px 14px; }
  .flipbook-header { grid-template-columns: 1fr 1fr; }
  .flipbook-header h1 { display: none; }
  .photo-book-rig { width: min(92vw, calc((100svh - 135px) * var(--flipbook-page-ratio))); transform: rotateX(3deg); }
  .is-turning .photo-book-rig { transform: rotateX(4.5deg) translateY(-.5%); }
  .flipbook-ground-shadow { width: 68vw; height: 92px; }
}
@media (max-height: 650px) {
  .flipbook-room { padding-block: 14px 10px; }
  .flipbook-status small { display: none; }
  .flipbook-controls button { width: 34px; height: 34px; }
}
@media (prefers-reduced-motion: reduce) {
  .flipbook-room, .flipbook-room::before, .photo-book-rig, .photo-book, .flipbook-ground-shadow, .flipbook-header, .flipbook-controls button {
    transition-duration: .01ms; animation-duration: .01ms; animation-delay: 0ms;
  }
}
"""

# 初始化脚本模板（页面数据由服务端注入；占位符使用唯一长标识避免误替换）
_INIT_JS = """
(function () {
  var bookEl = document.getElementById('book');
  if (!bookEl) return;
  var layout = {width: __WIDTH__, height: __HEIGHT__,
                minWidth: __MIN_WIDTH__, minHeight: __MIN_HEIGHT__,
                maxWidth: __MAX_WIDTH__, maxHeight: __MAX_HEIGHT__};
  var book = new St.PageFlip(bookEl, {
    width: layout.width,
    height: layout.height,
    size: 'stretch',
    minWidth: layout.minWidth,
    maxWidth: layout.maxWidth,
    minHeight: layout.minHeight,
    maxHeight: layout.maxHeight,
    startPage: 0,
    drawShadow: true,
    flippingTime: 780,
    usePortrait: true,
    startZIndex: 10,
    autoSize: true,
    maxShadowOpacity: 0.42,
    showCover: true,
    mobileScrollSupport: false,
    clickEventForward: true,
    useMouseEvents: true,
    swipeDistance: 26,
    showPageCorners: true,
    disableFlipByClick: false
  });
  var leaves = document.querySelectorAll('#book article');
  book.loadFromHTML(leaves);

  var current = 0;
  var isTurning = false;
  var total = __TOTAL_PAGES__;

  book.on('flip', function (e) {
    current = Number(e.data);
    updateStatus();
  });
  book.on('changeState', function (e) {
    isTurning = e.data !== 'read';
  });

  /* 开场仪式：就绪后展示封面，短暂停留再自动翻开第一页 */
  book.on('init', function () {
    setTimeout(function () {
      if (!isTurning) book.flipNext('bottom');
    }, 1000);
    /* 打开时默认静音，首次翻页动作（用户手势）触发音乐播放 */
  });

  function updateStatus() {
    var info = document.getElementById('pageInfo');
    var label;
    if (current === leaves.length - 1) {
      label = 'Back cover';
    } else if (current >= total) {
      label = 'Inside back cover';
    } else {
      var v = String(Math.min(current + 1, total)).padStart(2, '0');
      label = v + ' / ' + String(total).padStart(2, '0');
    }
    info.textContent = label;
  }

  document.getElementById('prevBtn').addEventListener('click', function () {
    if (!isTurning) book.flipPrev('bottom');
    /* 翻页动作触发音乐播放（用户手势内，浏览器允许） */
    musicEnsurePlaying();
  });
  document.getElementById('nextBtn').addEventListener('click', function () {
    if (!isTurning) book.flipNext('bottom');
    musicEnsurePlaying();
  });

  /* 背景音乐：翻页时自动开始播放，音乐按钮可手动切换 */
  var musicAudio = null;
  var musicPlaying = false;

  function musicStart() {
    if (musicPlaying) return;
    if (!musicAudio) {
      var src = '__MUSIC_SRC__';
      if (!src) return;
      musicAudio = new Audio(src);
      musicAudio.loop = true;
      musicAudio.volume = parseFloat(document.getElementById('volumeBtn') ? document.getElementById('volumeBtn').value : '0.5');
    }
    var p = musicAudio.play();
    if (p && p.catch) {
      p.catch(function () {
        /* 被浏览器拦截：重置状态，下次翻页再试 */
        musicPlaying = false;
        var btn = document.getElementById('musicBtn');
        if (btn) btn.classList.remove('is-playing');
      });
    }
    musicPlaying = true;
    var btn = document.getElementById('musicBtn');
    if (btn) btn.classList.add('is-playing');
  }

  function musicStop() {
    if (musicAudio) { musicAudio.pause(); musicAudio.currentTime = 0; }
    musicPlaying = false;
    var btn = document.getElementById('musicBtn');
    if (btn) btn.classList.remove('is-playing');
  }

  /* 未播放时开始播放（翻页 / 键盘触发） */
  function musicEnsurePlaying() {
    if (!musicPlaying) musicStart();
  }

  var musicBtn = document.getElementById('musicBtn');
  if (musicBtn) {
    musicBtn.addEventListener('click', function () {
      if (musicPlaying) { musicStop(); } else { musicStart(); }
    });
  }

  var volumeBtn = document.getElementById('volumeBtn');
  if (volumeBtn) {
    volumeBtn.addEventListener('input', function () {
      var v = parseFloat(volumeBtn.value) || 0;
      if (musicAudio) musicAudio.volume = v;
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.altKey || e.ctrlKey || e.metaKey || isTurning) return;
    if (e.key === 'ArrowLeft') { e.preventDefault(); book.flipPrev('bottom'); musicEnsurePlaying(); }
    if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); book.flipNext('bottom'); musicEnsurePlaying(); }
    if (e.key === 'Home') book.flip(0, 'bottom');
    if (e.key === 'End') book.flip(leaves.length - 1, 'bottom');
  });

  updateStatus();
})();
"""


class FlipbookExportService:
    """画册导出服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def export_html(self, user_id: str, project_id: str) -> str:
        """生成画册的静态 HTML"""
        project = await self._get_project(project_id)
        if project is None:
            raise NotFoundException(f"画册 [{project_id}] 不存在")
        if project.user_id != user_id:
            raise ForbiddenException("无权导出该画册")

        pages = await self._get_pages(project_id)
        if not pages:
            raise NotFoundException("画册没有页面，无法导出")

        theme = self._parse_theme(project.theme_json)

        # 1. 构建叶子页面（独立封皮 + 照片 + 补页 + 封底）
        leaves = self._make_leaves(
            pages,
            project.title,
            project.kicker,
            theme.get("mood", ""),
            _load_cover_art(),
        )

        # 2. 渲染页面 HTML
        pages_html = "\n".join(
            self._render_leaf(leaf, index) for index, leaf in enumerate(leaves)
        )

        # 3. 内联样式（主题变量）
        css_vars = self._theme_css_vars(theme)
        css = f""":root {{
  --flipbook-room: #d7d3c8;
  --flipbook-ink: #292923;
  --flipbook-muted: #77746b;
{css_vars}  --flipbook-page-ratio: {_DEFAULT_WIDTH / _DEFAULT_HEIGHT:.4f};
  --flipbook-spread-ratio: {_DEFAULT_WIDTH * 2 / _DEFAULT_HEIGHT:.4f};
  --flipbook-max-spread: {_DEFAULT_WIDTH * 2 * 1.04:.0f}px;
}}
""" + _FLIPBOOK_CSS

        # 4. 内联 page-flip 库（优先本地，缺失用 CDN）
        lib_script = self._load_page_flip_lib()

        # 5. 初始化脚本（注入布局参数）
        init_js = (
            _INIT_JS
            .replace("__WIDTH__", str(_DEFAULT_WIDTH))
            .replace("__HEIGHT__", str(_DEFAULT_HEIGHT))
            .replace("__MIN_WIDTH__", str(round(_DEFAULT_WIDTH * 0.56)))
            .replace("__MIN_HEIGHT__", str(round(_DEFAULT_HEIGHT * 0.56)))
            .replace("__MAX_WIDTH__", str(round(_DEFAULT_WIDTH * 1.04)))
            .replace("__MAX_HEIGHT__", str(round(_DEFAULT_HEIGHT * 1.04)))
            .replace("__TOTAL_PAGES__", str(len(pages)))
        )

        # 背景音乐：优先使用后台配置的 URL，未配置则内联内置 mp3
        from app.services.model_config_store import model_config_store

        music_src = model_config_store.get_bgm_music_url()
        if music_src:
            music_src_value = music_src.replace("\\", "\\\\").replace("'", "\\'")
        else:
            music_src_value = f"data:audio/mpeg;base64,{_load_music_b64()}"
        init_js = init_js.replace("__MUSIC_SRC__", music_src_value)

        # 6. 组装完整 HTML
        title = html.escape(project.title or "Photo Book")
        kicker = html.escape(project.kicker or "Folio")
        doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - 3D 相册</title>
<style>
{css}
</style>
</head>
<body>
<main class="flipbook-room" id="bookRoom">
  <header class="flipbook-header">
    <span>{kicker}</span>
    <h1>{title}</h1>
    <span>Open spread</span>
  </header>

  <section class="flipbook-stage" aria-label="{title} interactive photo book">
    <div class="flipbook-ground-shadow" aria-hidden="true"></div>
    <div class="photo-book-rig">
      <div id="book" class="photo-book">
{pages_html}
      </div>
    </div>
  </section>

  <footer class="flipbook-controls" aria-label="Book controls">
    <button type="button" id="prevBtn" aria-label="Previous page">&#8249;</button>
    <div class="flipbook-status" aria-live="polite">
      <span id="pageInfo">01 / {len(pages)}</span>
      <small>拖拽、滑动或使用方向键翻页</small>
    </div>
    <button type="button" id="nextBtn" aria-label="Next page">&#8250;</button>
    <button type="button" id="musicBtn" class="flipbook-music" aria-label="播放背景音乐" title="播放/暂停背景音乐">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 9l12-3"/>
      </svg>
    </button>
    <input type="range" id="volumeBtn" class="flipbook-volume" min="0" max="1" step="0.05" value="0.5" aria-label="背景音乐音量" title="音量" />
  </footer>
</main>
{lib_script}
<script>
{init_js}
</script>
</body>
</html>
"""
        return doc

    # -------------------- 内部方法 --------------------

    def _make_leaves(
        self,
        pages: list[FlipbookPage],
        title: str = "Photo Book",
        kicker: str = "Folio",
        mood: str = "",
        cover_art: str = "",
    ) -> list[dict]:
        """补全叶子：独立封皮 + 用户照片 + 补页 + 封底"""
        leaves = [self._page_to_dict(p) for p in pages]
        # 独立封皮（不使用第一张照片），携带封面排版信息
        leaves.insert(
            0,
            {
                "id": "cover",
                "alt": "Cover",
                "cover_title": title,
                "cover_kicker": kicker,
                "cover_mood": mood,
                "cover_meta": "FOLIO",
                "cover_count": len(pages),
                "cover_art": cover_art,
            },
        )
        if (len(leaves) + 1) % 2:
            leaves.append({"id": "inside-back-cover", "alt": "Blank inside back cover"})
        leaves.append({"id": "back-cover", "alt": "Solid-color back cover"})
        return leaves

    @staticmethod
    def _page_to_dict(page: FlipbookPage) -> dict:
        return {
            "id": page.page_id,
            "image": page.image_url,
            "alt": page.alt or "",
            "caption": page.caption,
            "text": page.text,
        }

    def _render_leaf(self, leaf: dict, index: int = 0) -> str:
        """渲染单个叶子页面 HTML"""
        blank = not leaf.get("image") and not leaf.get("text") and not leaf.get("caption")
        fit = "contain"
        padding = _DEFAULT_PADDING

        classes = ["photo-leaf", f"photo-leaf--fit-{fit}"]
        if leaf["id"] == "back-cover":
            classes.append("photo-leaf--back-cover")
        elif leaf["id"] == "cover":
            classes.append("photo-leaf--cover")
        elif blank:
            classes.append("photo-leaf--blank")

        # 硬页规则：仅首页（封面）与末页（封底）；中间页为软页
        is_cover = index == 0
        is_back_cover = leaf["id"] == "back-cover"
        density = "hard" if (is_cover or is_back_cover) else "soft"

        img_html = ""
        copy_html = ""

        # 独立封皮：标题 + 朱印
        if leaf["id"] == "cover":
            cover_title = html.escape(leaf.get("cover_title") or "Photo Book")
            cover_art = leaf.get("cover_art") or ""
            art_html = (
                f'\n          <img class="cover-art" src="data:image/jpeg;base64,{cover_art}" alt="" />'
                if cover_art
                else ""
            )
            copy_html = f"""        <div class="photo-leaf__cover">{art_html}
          <span class="cover-art-shade" aria-hidden="true"></span>
          <div class="cover-frame">
            <div class="cover-body">
              <h2 class="cover-title">{cover_title}</h2>
            </div>
            <div class="cover-footer">
              <span class="cover-brand">PhotoStyle</span>
              <span class="cover-seal">影</span>
            </div>
          </div>
        </div>"""
        # 封底：朱印
        elif leaf["id"] == "back-cover":
            copy_html = """        <div class="photo-leaf__back">
          <span class="photo-leaf__back-seal">影</span>
          <span class="photo-leaf__back-mark">PhotoStyle</span>
        </div>"""
        else:
            if leaf.get("image"):
                alt = html.escape(leaf.get("alt") or "")
                img_html = (
                    f'        <img src="{html.escape(leaf["image"])}" alt="{alt}" draggable="false" />'
                )
            if leaf.get("caption") or leaf.get("text"):
                parts = []
                if leaf.get("caption"):
                    parts.append(
                        f'<p class="photo-leaf__caption">{html.escape(leaf["caption"])}</p>'
                    )
                if leaf.get("text"):
                    parts.append(f"<p>{html.escape(leaf['text'])}</p>")
                copy_html = (
                    f'        <div class="photo-leaf__copy">{"".join(parts)}</div>'
                )

        return f"""      <article
        class="{' '.join(classes)}"
        aria-label="{html.escape(leaf.get('alt') or '')}"
        data-density="{density}"
        data-page-id="{html.escape(leaf['id'])}"
        style="--photo-padding: {padding}px; --photo-inset: {padding * 2}px;"
      >
{img_html}
{copy_html}
      </article>"""

    @staticmethod
    def _parse_theme(theme_json: str | None) -> dict:
        if not theme_json:
            return {}
        try:
            data = json.loads(theme_json)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _theme_css_vars(theme: dict) -> str:
        """将 AI 主题映射为 CSS 变量行"""
        lines = []
        mapping = {
            "pageColor": "--flipbook-page-color: {};",
            "coverColor": "--flipbook-cover-color: {};",
            "backCoverColor": "--flipbook-back-cover-color: {};",
        }
        for key, fmt in mapping.items():
            val = theme.get(key)
            if val:
                lines.append(f"  {fmt.format(val)}")

        texture = theme.get("pageTexture", "paper")
        if texture == "smooth":
            lines.append("  --flipbook-page-texture: none;")
        elif texture == "grainy":
            lines.append(
                "  --flipbook-page-texture: url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E\");"
            )
        elif texture == "fiber":
            lines.append(
                "  --flipbook-page-texture: repeating-linear-gradient(45deg, transparent 0 2px, rgba(72,62,44,.025) 3px);"
            )
        return "\n".join(lines) + ("\n" if lines else "")

    @staticmethod
    def _load_page_flip_lib() -> str:
        """加载 page-flip 库脚本标签（优先内联本地文件，缺失回退 CDN）"""
        try:
            if _PAGE_FLIP_LIB_PATH.exists():
                content = _PAGE_FLIP_LIB_PATH.read_text(encoding="utf-8")
                if content.strip():
                    return f"<script>\n{content}\n</script>"
        except OSError as e:
            logger.warning(f"[FlipbookExport] 读取 page-flip 本地文件失败: {e}")
        return f'<script src="{_PAGE_FLIP_CDN}"></script>'

    async def _get_project(self, project_id: str) -> FlipbookProject | None:
        result = await self.db.execute(
            select(FlipbookProject).where(FlipbookProject.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def _get_pages(self, project_id: str) -> list[FlipbookPage]:
        result = await self.db.execute(
            select(FlipbookPage)
            .where(FlipbookPage.project_id == project_id)
            .order_by(FlipbookPage.page_order)
        )
        return list(result.scalars().all())
