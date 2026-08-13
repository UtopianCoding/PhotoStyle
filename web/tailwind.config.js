/** @type {import('tailwindcss').Config} */
// Tailwind CSS 配置：扫描模板文件并扩展水墨纸砚主题色
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F5F2EC', // 米纸
        ink: '#1C1C1A', // 墨黑
        cinnabar: {
          // 朱砂（唯一强调色）
          DEFAULT: '#C8442B',
          light: '#D65B3F',
          dark: '#A8361F',
        },
        tea: '#E8E0D5', // 茶色
        stone: {
          // 石灰
          DEFAULT: '#9C968B',
          light: '#B5AFA3',
          dark: '#7A7468',
        },
        bamboo: '#5B7C5A', // 竹绿
      },
      borderRadius: {
        xl: '12px',
      },
      fontFamily: {
        display: ['"Noto Serif SC"', 'serif'],
        body: ['"Noto Sans SC"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
