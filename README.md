# image-creator-skill

WorkBuddy AI Skill - 通用图片创作技能，基于 OpenRouter API (openai/gpt-5.4-image-2)，支持文生图和图生图两种模式。

## 功能

- **文生图 (text2img)**：从零创作，根据文字描述生成高质量图片
- **图生图 (img2img)**：基于参考图改造，保持指定要素不变

## 适用场景

- 营销海报、活动海报生成
- 社交媒体图片创作（私域1V1、社群、朋友圈）
- 基于参考图的风格改造和场景替换

## 文件结构

```
image-creator-skill/
├── SKILL.md              # Skill 主文件（完整工作流定义）
├── scripts/
│   └── generate.py       # 图片生成脚本（OpenRouter API 调用）
├── .gitignore
└── README.md
```

## 使用前提

- 需要有效的 [OpenRouter API Key](https://openrouter.ai/keys)
- 模型：`openai/gpt-5.4-image-2`
- Python 3.9+（脚本依赖仅 `requests`/标准库）

## 快速开始

```bash
# 文生图
python3 scripts/generate.py \
  --mode text2img \
  --prompt "A luxurious skincare poster with golden gradient..." \
  --size "1024x1792" \
  --output output.png

# 图生图
python3 scripts/generate.py \
  --mode img2img \
  --prompt "Transform the background to a coffee shop..." \
  --input-image reference.jpg \
  --size "1024x1792" \
  --output output.png
```

## API Key 配置

按优先级读取：
1. 环境变量 `OPENROUTER_API_KEY`
2. `~/.workbuddy/skills/image-creator/.api_key` 文件
3. 命令行 `--api-key` 参数

## License

MIT
