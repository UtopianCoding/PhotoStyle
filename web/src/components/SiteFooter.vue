<script setup lang="ts">
// 站脚：编辑式 zine 风格，像一本小册子的封底
import { RouterLink } from 'vue-router'

const year = new Date().getFullYear()
</script>

<template>
  <footer class="site-footer">
    <!-- 撕纸边缘过渡 -->
    <div class="site-footer__torn-edge" aria-hidden="true"></div>

    <div class="site-footer__inner">
      <!-- 四列布局 -->
      <div class="site-footer__grid">
        <!-- 品牌列 -->
        <div class="site-footer__col site-footer__col--brand">
          <div class="site-footer__brand">
            <span class="site-footer__seal">影</span>
            <span class="site-footer__brand-name font-display">PhotoStyle</span>
          </div>
          <p class="site-footer__tagline">
            把普通画面，变成值得停留的一页。
          </p>
          <p class="site-footer__desc">
            AI 驱动的照片风格转换工具。保留真实场景，让纸面、插画和色彩继续生长。
          </p>
        </div>

        <!-- 法律列 -->
        <div class="site-footer__col">
          <h4 class="site-footer__col-title font-display">法律</h4>
          <ul class="site-footer__links">
            <li><RouterLink to="/privacy">隐私政策</RouterLink></li>
            <li><RouterLink to="/terms">用户协议</RouterLink></li>
          </ul>
        </div>

        <!-- 联系列 -->
        <div class="site-footer__col">
          <h4 class="site-footer__col-title font-display">联系</h4>
          <ul class="site-footer__links">
            <li><RouterLink to="/contact">联系我们</RouterLink></li>
            <li>
              <a href="mailto:hello@photostyle.app" class="site-footer__email">
                hello@photostyle.app
              </a>
            </li>
          </ul>
        </div>
      </div>

      <!-- 底部版权条 -->
      <div class="site-footer__bottom">
        <p class="site-footer__copyright">
          &copy; {{ year }} PhotoStyle. All rights reserved.
        </p>
        <p class="site-footer__made-with">
          Crafted with care
        </p>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  position: relative;
  background: var(--color-bg-card);
  margin-top: 80px;
}

/* 撕纸边缘：CSS 模拟不规则手撕纤维轮廓 */
.site-footer__torn-edge {
  position: absolute;
  top: -12px;
  left: 0;
  right: 0;
  height: 14px;
  background: var(--color-bg-card);
  clip-path: polygon(
    0% 60%, 2% 40%, 4% 70%, 6% 30%, 8% 55%, 10% 45%, 12% 65%,
    14% 35%, 16% 60%, 18% 40%, 20% 70%, 22% 30%, 24% 55%, 26% 50%,
    28% 65%, 30% 35%, 32% 60%, 34% 45%, 36% 70%, 38% 30%, 40% 55%,
    42% 40%, 44% 65%, 46% 35%, 48% 60%, 50% 45%, 52% 70%, 54% 30%,
    56% 55%, 58% 40%, 60% 65%, 62% 35%, 64% 60%, 66% 50%, 68% 70%,
    70% 30%, 72% 55%, 74% 45%, 76% 65%, 78% 35%, 80% 60%, 82% 40%,
    84% 70%, 86% 30%, 88% 55%, 90% 45%, 92% 65%, 94% 35%, 96% 60%,
    98% 40%, 100% 55%,
    100% 100%, 0% 100%
  );
}

.site-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 48px 24px 24px;
}

/* 三列网格 */
.site-footer__grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  gap: 40px;
  padding-bottom: 36px;
  border-bottom: 1px solid var(--color-border);
}

/* 品牌列 */
.site-footer__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.site-footer__seal {
  width: 28px;
  height: 28px;
  border-radius: 3px;
  background: var(--color-primary);
  color: #fff;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 17px;
  line-height: 28px;
  text-align: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-seal);
  position: relative;
}
.site-footer__seal::after {
  content: "";
  position: absolute;
  right: 2px;
  bottom: 2px;
  width: 5px;
  height: 5px;
  background: rgba(255, 255, 255, 0.18);
  border-radius: 50%;
}
.site-footer__brand-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.02em;
}
.site-footer__tagline {
  font-family: var(--font-display);
  font-size: 15px;
  color: var(--color-text);
  letter-spacing: 0.06em;
  margin: 0 0 8px;
  line-height: 1.6;
}
.site-footer__desc {
  font-size: 13px;
  line-height: 1.65;
  color: var(--color-text-secondary);
  margin: 0;
  max-width: 280px;
}

/* 列标题 */
.site-footer__col-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.08em;
  margin: 0 0 16px;
  text-transform: uppercase;
}

/* 链接列表 */
.site-footer__links {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.site-footer__links a {
  font-size: 13px;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
  transition: color 0.2s;
  line-height: 1.4;
}
.site-footer__links a:hover {
  color: var(--color-primary);
}
.site-footer__email {
  word-break: break-all;
}

/* 底部版权 */
.site-footer__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 20px;
}
.site-footer__copyright {
  font-size: 12px;
  color: var(--color-text-placeholder);
  letter-spacing: 0.04em;
  margin: 0;
}
.site-footer__made-with {
  font-size: 11px;
  color: var(--color-text-placeholder);
  letter-spacing: 0.08em;
  font-family: var(--font-mono);
  margin: 0;
  opacity: 0.7;
}

/* 响应式 */
@media (max-width: 768px) {
  .site-footer__grid {
    grid-template-columns: 1fr 1fr;
    gap: 28px;
  }
  .site-footer__col--brand {
    grid-column: 1 / -1;
  }
  .site-footer__inner {
    padding: 36px 16px 20px;
  }
}
@media (max-width: 480px) {
  .site-footer__grid {
    grid-template-columns: 1fr;
    gap: 24px;
  }
  .site-footer__bottom {
    flex-direction: column;
    gap: 8px;
    text-align: center;
  }
}
</style>
