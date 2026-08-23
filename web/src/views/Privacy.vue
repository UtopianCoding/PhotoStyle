<script setup lang="ts">
// 隐私政策页面：编辑式排版，干净可读
</script>

<template>
  <div class="legal-page">
    <div class="legal-page__inner">
      <!-- 页眉 -->
      <header class="legal-page__header">
        <span class="legal-page__label font-mono-label">PRIVACY POLICY</span>
        <h1 class="legal-page__title font-display">隐私政策</h1>
        <p class="legal-page__meta">最后更新：2026 年 1 月 1 日 &middot; 生效日期：2026 年 1 月 1 日</p>
      </header>

      <div class="legal-page__body">
        <section>
          <h2>我们收集什么</h2>
          <p>
            当你注册 PhotoStyle 账号时，我们会收集你提供的邮箱地址和昵称。在使用风格转换功能时，
            我们会处理你上传的照片——这些照片仅用于 AI 图像生成，不会被用于训练任何模型。
          </p>
          <p>
            我们自动收集的使用数据包括：访问时间、页面浏览记录、设备类型和浏览器信息。
            这些数据以聚合形式存在，不会关联到你的个人身份。
          </p>
        </section>

        <section>
          <h2>我们如何使用你的信息</h2>
          <p>你的照片和信息仅用于以下目的：</p>
          <ul>
            <li>提供风格转换和 IP 表情包生成服务</li>
            <li>保存你的历史记录，方便你回看和管理作品</li>
            <li>维护账户安全和防止滥用</li>
            <li>改善产品体验（仅使用聚合匿名数据）</li>
          </ul>
        </section>

        <section>
          <h2>你的照片</h2>
          <p>
            你上传的照片存储在我们安全的对象存储服务中。AI 模型通过 API 临时访问你的照片进行处理，
            处理完成后不会在第三方服务中保留副本。
          </p>
          <p>
            你可以随时删除你的历史记录和上传的照片。删除操作会同时移除存储中的原始文件和所有生成的结果。
          </p>
        </section>

        <section>
          <h2>第三方服务</h2>
          <p>
            风格转换功能依赖以下第三方 AI 服务提供商。当你选择对应的模型时，你的照片和提示词
            会被发送至该服务商进行处理：
          </p>
          <ul>
            <li><strong>阿里云 DashScope</strong>（千问）— 图像生成与视觉分析</li>
            <li><strong>OpenAI</strong>（DALL·E）— 图像生成</li>
            <li><strong>MiniMax</strong> — 图像生成</li>
            <li><strong>火山引擎</strong>（豆包）— 图像生成</li>
          </ul>
          <p>
            各服务商均有各自的隐私政策。我们仅将处理所必需的最少信息传递给它们。
          </p>
        </section>

        <section>
          <h2>数据存储与安全</h2>
          <p>
            所有数据存储在经过加密的云服务器中。密码使用 bcrypt 哈希存储，不会被明文保存。
            账户认证基于 JWT Token，传输过程使用 HTTPS 加密。
          </p>
        </section>

        <section>
          <h2>你的权利</h2>
          <ul>
            <li>查看、修改或删除你的个人信息</li>
            <li>导出你的历史数据</li>
            <li>随时注销你的账户</li>
            <li>撤回对任何数据处理的同意</li>
          </ul>
          <p>
            如需行使上述权利，请通过页脚的联系方式与我们联系。
          </p>
        </section>

        <section>
          <h2>Cookies</h2>
          <p>
            我们仅使用维持登录状态所必需的技术性 Cookie。不使用追踪 Cookie 或第三方广告 Cookie。
          </p>
        </section>

        <section>
          <h2>未成年人保护</h2>
          <p>
            PhotoStyle 不面向 13 岁以下的用户。如果我们得知某位用户未满 13 岁，
            我们将尽快删除其账户和相关数据。
          </p>
        </section>

        <section>
          <h2>政策更新</h2>
          <p>
            我们可能会不时更新本隐私政策。重大变更会通过应用内通知或邮件告知。
            更新后的政策自发布之日生效。
          </p>
        </section>

        <section class="legal-page__contact">
          <h2>联系我们</h2>
          <p>
            如果你对本隐私政策有任何疑问，欢迎通过
            <a href="mailto:utopiancoding@gmail.com">utopiancoding@gmail.com</a>
            或我们的<RouterLink to="/contact">联系页面</RouterLink>与我们取得联系。
          </p>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import './legal-shared.css';
</style>
