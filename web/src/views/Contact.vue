<script setup lang="ts">
// 联系方式页面
</script>

<template>
  <div class="legal-page">
    <div class="legal-page__inner">
      <header class="legal-page__header">
        <span class="legal-page__label font-mono-label">CONTACT</span>
        <h1 class="legal-page__title font-display">联系我们</h1>
        <p class="legal-page__meta">我们期待听到你的声音</p>
      </header>

      <div class="legal-page__body">
        <section>
          <h2>一般咨询</h2>
          <p>
            无论是产品建议、合作机会还是任何想说的话，都欢迎通过以下方式联系我们。
            我们通常会在 1-2 个工作日内回复。
          </p>
        </section>

        <section class="contact-card">
          <div class="contact-card__item">
            <span class="contact-card__label font-mono-label">EMAIL</span>
            <a href="mailto:utopiancoding@gmail.com" class="contact-card__value">
              utopiancoding@gmail.com
            </a>
            <p class="contact-card__desc">一般咨询、合作与反馈</p>
          </div>
          <div class="contact-card__item">
            <span class="contact-card__label font-mono-label">SUPPORT</span>
            <a href="mailto:utopiancoding@gmail.com" class="contact-card__value">
              utopiancoding@gmail.com
            </a>
            <p class="contact-card__desc">技术支持与问题反馈</p>
          </div>
        </section>

        <section>
          <h2>常见问题</h2>
        </section>

        <section>
          <h3>如何删除我的账户？</h3>
          <p>
            目前请联系 utopiancoding@gmail.com 申请账户删除。
            我们会在收到请求后 3 个工作日内完成删除，同时清除所有关联数据。
          </p>
        </section>

        <section>
          <h3>生成的图片版权归谁？</h3>
          <p>
            你上传的照片版权仍归你所有。AI 生成的风格化图片，你可以在合法范围内自由使用。
            详见<RouterLink to="/terms">用户协议</RouterLink>。
          </p>
        </section>

        <section>
          <h3>每日使用次数不够用怎么办？</h3>
          <p>
            每日额度会在次日自动重置。如果额度不足，可以等待次日重置，
            或通过邮件联系我们申请临时提额。
          </p>
        </section>

        <section>
          <h3>生成效果不满意？</h3>
          <p>
            你可以在结果页使用「重新生成」功能，添加修改意见让 AI 调整效果。
            也可以尝试切换不同的风格或 AI 模型。如果问题持续，欢迎邮件反馈。
          </p>
        </section>

        <section>
          <h2>开源</h2>
          <p>
            PhotoStyle 是一个开源项目。如果你对我们的技术栈或实现感兴趣，
            欢迎在 Gitee 上查看源码并参与贡献。
          </p>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './legal-shared.css';

/* 联系方式卡片 */
.contact-card {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin: 0 0 36px;
}
.contact-card__item {
  padding: 20px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}
.contact-card__label {
  display: block;
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--color-text-placeholder);
  text-transform: uppercase;
  margin-bottom: 8px;
}
.contact-card__value {
  display: block;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 6px;
  word-break: break-all;
  text-decoration: none;
  transition: opacity 0.2s;
}
.contact-card__value:hover {
  opacity: 0.8;
}
.contact-card__desc {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  margin: 0;
  line-height: 1.5;
}

/* 常见问题 h3 */
.legal-page__body h3 {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 8px;
}

@media (max-width: 480px) {
  .contact-card {
    grid-template-columns: 1fr;
  }
}
</style>
