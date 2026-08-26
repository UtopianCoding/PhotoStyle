/**
 * 背景音乐
 *
 * 播放后台配置的远程 URL；未配置时使用内置 mp3（web/src/bj 目录，文件缺失则静音）。
 * 循环播放、支持音量调节。因浏览器自动播放限制，需用户点击按钮后启动。
 */

// 内置 mp3（web/src/bj 目录）用 glob 运行时收集：文件缺失不阻塞构建，放回后自动生效
const bgmModules = import.meta.glob('@/bj/*.mp3', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>
const BUILTIN_MUSIC_URL = Object.values(bgmModules)[0] || ''

export function useAmbientMusic(remoteMusicUrl?: () => string) {
  let audio: HTMLAudioElement | null = null
  let isPlaying = false
  let currentVolume = 0.5

  /** 启动音乐（首次创建 Audio 元素并循环播放） */
  function start() {
    if (isPlaying) return
    // 每次播放时读取最新 URL，避免异步配置未及时生效
    const src = (remoteMusicUrl && remoteMusicUrl()) || BUILTIN_MUSIC_URL
    if (!src) return
    if (!audio) {
      audio = new Audio(src)
      audio.loop = true
      audio.volume = currentVolume
    }
    // 自动播放可能被浏览器拦截，成功后标记播放中
    audio
      .play()
      .then(() => {
        isPlaying = true
      })
      .catch(() => {
        isPlaying = false
      })
  }

  /** 停止音乐并回到开头 */
  function stop() {
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    isPlaying = false
  }

  /** 播放 / 暂停切换，返回切换后的播放状态 */
  function toggle(): boolean {
    if (isPlaying) {
      stop()
    } else {
      start()
    }
    return isPlaying
  }

  /** 设置音量（0 ~ 1），未播放时先记录，播放时应用 */
  function setVolume(volume: number) {
    currentVolume = Math.min(1, Math.max(0, volume))
    if (audio) {
      audio.volume = currentVolume
    }
  }

  return {
    start,
    stop,
    toggle,
    setVolume,
    get playing() {
      return isPlaying
    },
    get volume() {
      return currentVolume
    },
  }
}
