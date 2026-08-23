<script setup lang="ts">
// 用户协议页面
</script>

<template>
  <div class="legal-page">
    <div class="legal-page__inner">
      <header class="legal-page__header">
        <span class="legal-page__label font-mono-label">TERMS OF SERVICE</span>
        <h1 class="legal-page__title font-display">用户协议</h1>
        <p class="legal-page__meta">最后更新：2026 年 1 月 1 日 &middot; 生效日期：2026 年 1 月 1 日</p>
      </header>

      <div class="legal-page__body">
        <section>
          <h2>服务概述</h2>
          <p>
            PhotoStyle 是一款 AI 驱动的照片风格转换工具。我们提供照片风格化处理、IP 表情包生成等创意服务。
            使用本服务即表示你同意本协议的所有条款。
          </p>
        </section>

        <section>
          <h2>账户注册</h2>
          <p>
            使用本服务需要注册账户。你需要提供有效的邮箱地址，并对账户下的所有活动负责。
            每个邮箱仅可注册一个账户。
          </p>
          <ul>
            <li>你必须年满 13 周岁</li>
            <li>你提供的注册信息必须真实准确</li>
            <li>你有责任保护账户密码的安全</li>
            <li>发现账户被盗用时应立即通知我们</li>
          </ul>
        </section>

        <section>
          <h2>使用规范</h2>
          <p>在使用 PhotoStyle 时，你同意不会：</p>
          <ul>
            <li>上传侵犯他人肖像权、著作权或其他合法权益的照片</li>
            <li>上传含有暴力、色情、仇恨或违法内容的照片</li>
            <li>将生成的内容用于欺诈、诽谤或侵犯隐私的目的</li>
            <li>试图干扰或破坏服务的正常运行</li>
            <li>使用自动化脚本或爬虫批量访问服务</li>
            <li>绕过每日使用限额或积分系统</li>
          </ul>
        </section>

        <section>
          <h2>内容所有权</h2>
          <p>
            你上传的照片的版权仍归你所有。使用 PhotoStyle 生成的风格化图片，
            你拥有在合法范围内使用该图片的权利。
          </p>
          <p>
            但请注意：AI 生成的内容可能与你上传的原图存在差异，我们不对生成内容的准确性、
            完整性或适用性做出任何保证。
          </p>
        </section>

        <section>
          <h2>使用限额</h2>
          <p>
            免费用户每日享有有限次数的风格转换额度。具体额度以系统当前配置为准。
            我们保留根据运营需要调整额度的权利。
          </p>
        </section>

        <section>
          <h2>服务可用性</h2>
          <p>
            我们尽力保障服务的稳定运行，但不保证服务不会中断或出现错误。
            以下情况可能导致服务暂时不可用：
          </p>
          <ul>
            <li>计划内的系统维护</li>
            <li>第三方 AI 服务提供商的故障</li>
            <li>不可抗力因素（网络中断、自然灾害等）</li>
          </ul>
        </section>

        <section>
          <h2>责任限制</h2>
          <p>
            在法律允许的最大范围内，PhotoStyle 不对以下情况承担责任：
          </p>
          <ul>
            <li>因使用或无法使用服务导致的任何直接或间接损失</li>
            <li>AI 生成内容的质量、准确性或适用性</li>
            <li>第三方服务提供商的行为或疏忽</li>
            <li>数据丢失或损坏（我们会尽力恢复但无法保证）</li>
          </ul>
        </section>

        <section>
          <h2>账户终止</h2>
          <p>
            你可以随时通过删除账户来终止本协议。我们保留在以下情况下暂停或终止账户的权利：
          </p>
          <ul>
            <li>违反本协议的任何条款</li>
            <li>长期不使用账户（超过 12 个月）</li>
            <li>涉嫌违法或侵害他人权益的行为</li>
          </ul>
          <p>
            账户终止后，你上传的照片和生成的结果将被删除，但已在公共领域传播的内容除外。
          </p>
        </section>

        <section>
          <h2>协议修改</h2>
          <p>
            我们保留修改本协议的权利。重大修改将通过应用内通知或邮件告知。
            继续使用服务即表示你接受修改后的条款。
          </p>
        </section>

        <section>
          <h2>争议解决</h2>
          <p>
            因本协议引起的争议应首先通过友好协商解决。协商不成的，
            任一方有权向有管辖权的人民法院提起诉讼。
          </p>
        </section>

        <section class="legal-page__contact">
          <h2>联系我们</h2>
          <p>
            如果你对本用户协议有任何疑问，欢迎通过
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
