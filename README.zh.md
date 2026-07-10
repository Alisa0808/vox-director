<p align="right"><a href="README.md">English</a> · <b>简体中文</b></p>

# 🎬 Vox Director(拼贴动效导演）

**一个选题进,一条成片出——脚本、拼贴关键帧、动效、旁白、配乐、字幕,全流程自动化的 Vox 风格拼贴讲解/广告视频。**

一个 [Claude](https://claude.com/claude-code) 技能(skill),后端全跑 [Atlas Cloud](https://www.atlascloud.ai) API,本地用 `ffmpeg` 合成。你给一句话选题,它给你一个 `mp4`。

![License: MIT](https://img.shields.io/badge/License-MIT-black.svg) ![Powered by Atlas Cloud](https://img.shields.io/badge/powered%20by-Atlas%20Cloud-ff5a1f.svg) ![Claude Skill](https://img.shields.io/badge/Claude-Skill-d97757.svg)

https://github.com/user-attachments/assets/ed08d230-7bcb-4b48-a17d-23c079208f9f

<p align="center">
  <em>主题《中华文明的变迁》——一句选题进,这条片子出。▶ <a href="https://github.com/Alisa0808/vox-director/blob/main/assets/showcase-tang.mp4">视频加载不出来?点这里看</a>。</em>
</p>

---

## 这是什么

风格是 Vox 讲解片和 Stav Zilber、rom1trs 等创作者带火的现代编辑感**纸质拼贴**:手撕纸片、毛边、胶带、半调网点、报纸剪贴、每一拍一块大胆平涂色、大号剪纸标题——再配上动效、旁白、配乐和字幕,让整张海报活过来。

Vox Director 把三套工作流融进一条可复用的管线:

| 来源 | 贡献 |
|---|---|
| **Stav Zilber**(原始) | 访谈式产品广告 · Omni Flash 纸片/拼贴动效引擎 · 尾帧链接 · 参考图一致性 · 旁白纪律 |
| **rom1trs / Remotion** | 代码渲染 Vox 视效(文字、数据绝对清晰) |
| **Higgsfield Explainer** | 自动调研选题 · 任意语言旁白 · 长片讲解 |

## 工作原理

一个选题依次流过每个阶段一个脚本,全程由每个项目一份 `beats.json` 驱动:

```
选题
  │
  ├─ 1. 分镜脚本   选叙事弧线 → 写 beats.json          ◀── 决策点 1:你确认分镜脚本
  ├─ 2. 风格试片   同一拍渲成 3–4 种主题               ◀── 决策点 2:你看图挑风格
  ├─ 3. 关键帧     每拍一张拼贴海报   (nano-banana-2)
  ├─ 4. 动效       让每张海报动起来   (gemini-omni-flash 图生视频)
  ├─ 5. 旁白+配乐  统一旁白 (xai/tts) + 背景乐 (minimax/music)
  ├─ 6. 合成       ffmpeg:拼接、配乐在旁白下自动闪避、烧字幕+水印
  └─ final.mp4
```

两个关键理念决定成败,技能就是围绕它们搭的:

1. **风格诞生在生图这一步。** 每一拍是一张成品拼贴*海报*,所有拼贴基因(撕纸、剪纸、网点、标题文字)都长在这张图里——图不够拼贴,后面再怎么救也救不回来。
2. **动效是后加的。** 默认由 AI 视频模型把整张海报动起来(「活海报」路径);要那种戏剧化的**零件逐个飞入拼合**,可选的本地关键帧引擎会把海报拆成零件逐帧驱动(无内容审核、像素级精确,尤其适合真人)。

两个人工决策点让你始终掌控(确认分镜脚本、挑风格),其余全自动。

## 模型(已在 Atlas Cloud 上验证)

| 用途 | 模型 |
|---|---|
| 关键帧 / 拼贴海报 | `google/nano-banana-2/text-to-image` |
| 动效(非真人内容) | `google/gemini-omni-flash/image-to-video` |
| 动效(**真人 / 品牌**) | `kwaivgi/kling-video-o3-pro/image-to-video` |
| 旁白 | `xai/tts-v1` |
| 配乐 | `minimax/music-2.6` |
| 抠素材(高级路径) | `youchuan/v8.1/remove-background` |

模型 ID 会变——技能运行前会先从 `GET https://api.atlascloud.ai/api/v1/models` 拉取最新列表。

## 安装

这是一个 Claude 技能(在 Claude Code 及支持 skill 的 Claude 应用里可用)。

**方式 A —— 从本仓库:**
```bash
git clone https://github.com/Alisa0808/vox-director.git ~/.claude/skills/vox-director
```

**方式 B —— 用打包好的技能文件:** 下载 [`vox-director.skill`](vox-director.skill),在你的 Claude 技能界面里安装。

然后设置 Atlas Cloud API key(在 <https://www.atlascloud.ai/console/api-keys> 获取):
```bash
export ATLASCLOUD_API_KEY="sk-..."
```

## 快速开始

装好技能后,直接跟 Claude 说:

> *「做一条 Vox 风格的拼贴视频,讲货币简史——全英文,9:16,60 秒。」*

Claude 会先起草分镜脚本给你确认,再跑一轮风格试片让你挑,然后生成关键帧 → 动效 → 旁白 → 配乐,合成 `out/<项目>/final.mp4`。

## 环境要求

- **Claude** 且支持 skill(如 Claude Code)
- **Atlas Cloud** API key
- **ffmpeg** + **ffprobe**(`brew install ffmpeg`)
- **Python 3** + **Pillow**(`pip install pillow`)——用于字幕/水印叠加

## 目录结构

```
SKILL.md              技能本体(英文)——Claude 遵循的工作流
SKILL.zh.md           同一技能的中文版
references/           创意引擎
  prompt-guide.md       生图 + 生视频的提示词结构
  vocab-bank.md         8 个生图维度 + 9 个生视频轴 + 8 套主题预设
  beat-layer.md         14 种叙事弧线 + 钩子/节奏 + 镜头模式
  models-and-gotchas.md 每一个 API / ffmpeg 坑,都已填平
  local-engine.md       高级的元素级动效引擎
scripts/              每个管线阶段一个脚本
examples/             可直接跑的 beats.json 示例
assets/               样片
```

## 致谢

灵感来自 **[Stav Zilber](https://x.com/StavZilber)**、**[rom1trs](https://x.com/rom1trs)**、**[Higgsfield](https://x.com/higgsfield_ai)** 的拼贴广告工作流,以及 **[Vox](https://www.vox.com)** 的讲解片视觉语言。

全流程基于 **[Atlas Cloud](https://www.atlascloud.ai)** 构建——一个提示词,一条成片。

## 许可

[MIT](LICENSE) © 2026 Atlas Cloud
