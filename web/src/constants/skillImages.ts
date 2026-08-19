// 各 skill 的示例效果图（与 web/src/skill1|skill2|skill3 目录一一对应）
// 图片通过 import 显式引入（Vite 要求），避免运行时字符串拼接不被打包

import skill1_img1 from '@/skill1/01_car_page.png'
import skill1_img2 from '@/skill1/01_moon_gate.png'
import skill1_img3 from '@/skill1/03_pagoda.png'
import skill1_img4 from '@/skill1/06_mask_dance.png'
import skill2_img1 from '@/skill2/1.jpg'
import skill2_img2 from '@/skill2/2.jpg'
import skill2_img3 from '@/skill2/3.jpg'
import skill2_img4 from '@/skill2/4.jpg'
import skill3_img1 from '@/skill3/case-1.jpg'
import skill3_img2 from '@/skill3/case-2.jpg'
import skill3_img3 from '@/skill3/case-4.jpg'
import skill3_img4 from '@/skill3/case-6.jpg'
import skill4_img1 from '@/skill4/01.png'
import skill4_img2 from '@/skill4/02.png'

/** skill_id → 示例图列表（每技能 4 张） */
export const SKILL_IMAGES: Record<string, string[]> = {
  'photo-revival': [skill1_img1, skill1_img2, skill1_img3, skill1_img4],
  'city-editorial': [skill2_img1, skill2_img2, skill2_img3, skill2_img4],
  'photo-abstract-editorial': [skill3_img1, skill3_img2, skill3_img3, skill3_img4],
  'fridge-magnet': [skill4_img1, skill4_img2],
}

/** 获取某 skill 的示例图（无则返回空数组） */
export function getSkillImages(skillId: string): string[] {
  return SKILL_IMAGES[skillId] ?? []
}
