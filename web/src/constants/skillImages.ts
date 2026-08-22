// 各 skill 的示例效果图
// 缩略图用于卡片拼贴预览（~40KB/张），原图用于点击后的大图预览弹窗

// 缩略图（卡片展示用，400px 宽 JPG）
import s1_t1 from '@/skill1/01_car_page_thumb.jpg'
import s1_t2 from '@/skill1/01_moon_gate_thumb.jpg'
import s1_t3 from '@/skill1/03_pagoda_thumb.jpg'
import s1_t4 from '@/skill1/06_mask_dance_thumb.jpg'
import s2_t1 from '@/skill2/1_thumb.jpg'
import s2_t2 from '@/skill2/2_thumb.jpg'
import s2_t3 from '@/skill2/3_thumb.jpg'
import s2_t4 from '@/skill2/4_thumb.jpg'
import s3_t1 from '@/skill3/case-1_thumb.jpg'
import s3_t2 from '@/skill3/case-2_thumb.jpg'
import s3_t3 from '@/skill3/case-4_thumb.jpg'
import s3_t4 from '@/skill3/case-6_thumb.jpg'
import s4_t1 from '@/skill4/01_thumb.jpg'
import s4_t2 from '@/skill4/02_thumb.jpg'
import s5_t1 from '@/skill5/1_thumb.jpg'
import s5_t2 from '@/skill5/2_thumb.jpg'
import s5_t3 from '@/skill5/3_thumb.jpg'
import s5_t4 from '@/skill5/4_thumb.jpg'
import s6_t1 from '@/skill6/reference-01_thumb.jpg'
import s7_t1 from '@/skill7/01.jpg'
import s7_t2 from '@/skill7/02.jpg'

// 原图（预览弹窗用）
import s1_f1 from '@/skill1/01_car_page.png'
import s1_f2 from '@/skill1/01_moon_gate.png'
import s1_f3 from '@/skill1/03_pagoda.png'
import s1_f4 from '@/skill1/06_mask_dance.png'
import s2_f1 from '@/skill2/1.jpg'
import s2_f2 from '@/skill2/2.jpg'
import s2_f3 from '@/skill2/3.jpg'
import s2_f4 from '@/skill2/4.jpg'
import s3_f1 from '@/skill3/case-1.jpg'
import s3_f2 from '@/skill3/case-2.jpg'
import s3_f3 from '@/skill3/case-4.jpg'
import s3_f4 from '@/skill3/case-6.jpg'
import s4_f1 from '@/skill4/01.png'
import s4_f2 from '@/skill4/02.png'
import s5_f1 from '@/skill5/1.jpg'
import s5_f2 from '@/skill5/2.jpg'
import s5_f3 from '@/skill5/3.jpg'
import s5_f4 from '@/skill5/4.jpg'
import s6_f1 from '@/skill6/reference-01.jpg'
import s7_f1 from '@/skill7/01.jpg'
import s7_f2 from '@/skill7/02.jpg'

/** skill_id → 缩略图列表（卡片展示用，每技能最多 4 张） */
export const SKILL_THUMBNAILS: Record<string, string[]> = {
  'photo-revival': [s1_t1, s1_t2, s1_t3, s1_t4],
  'city-editorial': [s2_t1, s2_t2, s2_t3, s2_t4],
  'photo-abstract-editorial': [s3_t1, s3_t2, s3_t3, s3_t4],
  'fridge-magnet': [s4_t1, s4_t2],
  'ink-minimalist': [s5_t1, s5_t2, s5_t3, s5_t4],
  'marker-child-doodle': [s6_t1],
  'scenes-gathered-zine': [s7_t1, s7_t2],
}

/** skill_id → 原图列表（预览弹窗用） */
export const SKILL_IMAGES: Record<string, string[]> = {
  'photo-revival': [s1_f1, s1_f2, s1_f3, s1_f4],
  'city-editorial': [s2_f1, s2_f2, s2_f3, s2_f4],
  'photo-abstract-editorial': [s3_f1, s3_f2, s3_f3, s3_f4],
  'fridge-magnet': [s4_f1, s4_f2],
  'ink-minimalist': [s5_f1, s5_f2, s5_f3, s5_f4],
  'marker-child-doodle': [s6_f1],
  'scenes-gathered-zine': [s7_f1, s7_f2],
}

/** 获取某 skill 的缩略图（卡片展示，无则返回空数组） */
export function getSkillThumbnails(skillId: string): string[] {
  return SKILL_THUMBNAILS[skillId] ?? []
}

/** 获取某 skill 的原图（预览弹窗，无则返回空数组） */
export function getSkillImages(skillId: string): string[] {
  return SKILL_IMAGES[skillId] ?? []
}
