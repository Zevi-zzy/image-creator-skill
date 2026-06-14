---
name: image-creator
description: "通用图片创作 Skill - 基于 OpenRouter API (openai/gpt-5.4-image-2)，支持文生图和图生图两种模式。从需求确认到 Prompt 构建再到 API 调用，全流程自动化。关键词：图片生成、生成图片、文生图、图生图、海报、海报创作、宣传图、海报设计、创作图片、生成海报、做海报"
version: "1.0.0"
author: "CodeBuddy AI"
agent_created: true
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# 通用图片创作 Skill

> **Goal**: 基于 OpenRouter API 调用 `openai/gpt-5.4-image-2` 模型，支持文生图（从零创作）和图生图（基于参考图改造）两种模式，为用户生成高质量图片。

## When to Use

**以下场景触发此 skill**：
- 用户说"生成海报"、"做一张海报"、"帮我做海报"、"来张宣传图"
- 用户提到"海报创作"、"海报设计"、"图片生成"、"文生图"、"图生图"
- 用户提供参考图片，要求基于参考图改造/调整/重新设计
- 用户要求创作营销海报、活动海报、社交媒体图片等

## When NOT to Use

- 用户要求生成视频 → 不适用
- 用户要求编辑现有图片（裁剪/调色/加水印等）→ 不适用
- 用户明确要求使用其他模型/API → 按用户指定

---

## 核心工作流

整个工作流分为 **5 个阶段**，任何阶段都不允许跳过。

### 两种模式

根据用户是否提供参考图，自动选择模式：

| 模式 | 触发条件 | 说明 |
|------|----------|------|
| **文生图（text2img）** | 用户未提供参考图 | 从零创作，需走完整 5 阶段 |
| **图生图（img2img）** | 用户提供参考图（@image 或图片路径） | 基于参考图改造，阶段2直接分析参考图 |

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  1.需求确认  │───▶│  2.方案设计  │───▶│  3.用户确认  │───▶│  4.海报生成  │───▶│  5.输出总结  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       ▲                                                          │
       └────────────────── 用户要求调整 ◀─────────────────────────┘
```

---

### 阶段 1：需求确认

**目标**：明确海报的使用场景、视觉风格和核心诉求，并检测模式。

#### 1.1 模式自动检测

检查用户消息中是否包含参考图（`@image` 标记、图片本地路径）：
- **有参考图** → 进入图生图模式，记录参考图路径
- **无参考图** → 进入文生图模式

#### 1.2 API Key 检查

**⚠️ 在进入需求确认之前，必须先确保有可用的 OpenRouter API Key。**

检查顺序：
1. 检查环境变量 `OPENROUTER_API_KEY`
2. 读取 `~/.workbuddy/skills/image-creator/.api_key` 文件（如果存在）
3. 如果都没找到 → **直接用 AskUserQuestion 问用户**：

```
AskUserQuestion({
  questions: [{
    question: "需要你的 OpenRouter API Key 才能调用图片生成。请在下方「其他」输入框中粘贴你的 Key（在 https://openrouter.ai/keys 获取）",
    header: "API Key",
    options: [
      { label: "我已有 Key，直接粘贴", description: "在下方输入框粘贴你的 OpenRouter API Key" },
      { label: "我还没有 Key", description: "需要先去 OpenRouter 创建 API Key" }
    ]
  }]
})
```

获取到 Key 后：
- 存储到 `~/.workbuddy/skills/image-creator/.api_key`（纯文本，仅 Key 值）
- 后续使用直接从该文件读取，不再重复询问

#### 1.3 需求确认（AskUserQuestion）

> **⚠️ AskUserQuestion 使用规范**：
> - 每个问题的 `question` 字段必须是一句完整的问题
> - `header` 是短标签（最多12字符）
> - `options` 每项必须有 `label` 和 `description`
> - 一次最多 4 个问题，优先问最重要的

**文生图模式**——用 AskUserQuestion 收集以下信息：

```
AskUserQuestion({
  questions: [
    {
      question: "海报将用于什么投放场景？",
      header: "投放场景",
      options: [
        { label: "私域1V1私聊", description: "偏情感化文案，竖版为主" },
        { label: "社群群发", description: "偏社交化，方图或竖版" },
        { label: "朋友圈", description: "视觉冲击优先，竖版为主" },
        { label: "通用", description: "不限场景，用户自定义" }
      ]
    },
    {
      question: "你希望什么视觉调性？",
      header: "调性风格",
      options: [
        { label: "高端奢华", description: "深色调、金色点缀、精致质感" },
        { label: "温柔治愈", description: "暖色调、柔和光影、舒适放松" },
        { label: "科技专业", description: "冷色调、简洁线条、数据感" },
        { label: "清新自然", description: "浅色调、自然元素、干净通透" }
      ]
    },
    {
      question: "海报需要包含中文文案吗？",
      header: "文案需求",
      options: [
        { label: "需要中文文案", description: "在 Prompt 中描述文案内容和排版" },
        { label: "纯视觉，不需要文案", description: "只生成视觉画面，不包含文字" }
      ]
    }
  ]
})
```

**图生图模式**——用 AskUserQuestion 收集以下信息：

```
AskUserQuestion({
  questions: [
    {
      question: "你想对参考图做哪种改造？",
      header: "改造方向",
      options: [
        { label: "换场景/背景", description: "保留主体，更换背景场景" },
        { label: "换风格/调性", description: "改变整体视觉风格和色调" },
        { label: "综合改造", description: "场景、风格、元素一起调整" },
        { label: "加文案/文字", description: "在图片上添加营销文案" }
      ]
    },
    {
      question: "参考图中哪些要素必须保留？",
      header: "保留要素",
      multiSelect: true,
      options: [
        { label: "人物面部", description: "五官特征与原图一致" },
        { label: "整体构图", description: "主体位置和视角不变" },
        { label: "产品外观", description: "产品形态颜色不变" },
        { label: "色调氛围", description: "保持原图的色彩感觉" }
      ]
    }
  ]
})
```

**处理逻辑**：
1. 根据使用场景自动推荐海报尺寸：
   - 私域1V1 / 朋友圈：竖版 9:16（1024×1792）
   - 社群群发：方图 1:1（1024×1024）或竖版
   - 通用：默认竖版 9:16
2. 记录用户所有选择，作为阶段2的输入

---

### 阶段 2：方案设计

**目标**：基于需求设计海报方案，构建详细 Prompt。

#### 文生图模式 - 设计方案模板

```markdown
## 海报设计方案

### 基本信息
- **模式**：文生图
- **场景**：[投放场景]
- **尺寸**：[宽×高]
- **调性**：[视觉风格]

### 视觉设计
- **主题概念**：[一句话概括]
- **主色调**：[主色 + 辅色]
- **构图方式**：[居中/三分/对角线/分层]

### 图像元素
- **主体**：[核心视觉元素描述]
- **辅助元素**：[装饰性元素]
- **背景**：[渐变/纯色/场景化]
- **光影效果**：[光线方向和质感]

### 文案内容（如需要）
- **主标题**：[5-10字]
- **副标题**：[补充说明]
- **卖点/描述**：[核心信息]
- **CTA**：[行动号召]

### Prompt（英文，用于 API 调用）
```
[完整的英文 Prompt，详见 Prompt 构建指南]
```
```

#### 图生图模式 - 设计方案模板

```markdown
## 海报改造设计方案

### 基本信息
- **模式**：图生图
- **参考图**：[参考图路径]
- **尺寸**：[宽×高]

### 参考图分析
- **原图内容**：[主体、场景、风格描述]
- **保留要素**：[必须保留的元素]
- **替换要素**：[需要改变的元素]

### 改造方案
- **目标效果**：[改造后的整体效果描述]
- **新元素**：[新增/替换的视觉元素]
- **色调调整**：[新色调方向]

### Prompt（英文，用于 API 调用）
```
[完整的英文 Prompt，详见 Prompt 构建指南]
```
```

#### Prompt 构建指南

> **⚠️ 核心原则：Prompt 用英文编写，因为 GPT 系列模型对英文 Prompt 的理解和执行更精准。如需中文文案出现在图片中，在 Prompt 中用引号标注中文文案内容。**

##### 文生图 Prompt 模板

```
A [style/mood] poster design for [purpose/scene]. [Main subject description with details on color, material, angle]. [Background description]. [Lighting and shadow effects].

[If text needed]: The poster features Chinese text at the top in large elegant font reading "[主标题]", with a subtitle below reading "[副标题]". [Text layout details].

[Key visual elements description]. Overall color palette: [colors]. Style: [style keywords]. High quality, professional design, [aspect ratio hint].
```

**文生图 Prompt 示例**：

```
A luxurious and elegant poster design for a skincare product. Center composition featuring a golden-amber gradient eye serum bottle with a gold cap, surrounded by white chrysanthemum petals and golden light particles. Deep brown to burgundy gradient background with warm golden lighting from the upper left, golden rim light on the bottle edges.

The poster features Chinese text at the top in large elegant Song typeface reading "一笑 不见纹", with a golden decorative line below, and a subtitle reading "千日菊植物肉毒 · 涂抹式抗皱". Three selling points listed at the bottom area in rounded tag style: "千日菊植物肉毒，涂抹即抗皱", "8:2水油配比，即渗不起脂肪粒", "2项国家专利 · 3份功效检测". A golden rounded button at the bottom reading "配方师为你定制方案", and small text at the very bottom reading "TWO POSTDOCS · 两个博士后".

Overall color palette: warm gold, amber, deep brown. Eastern luxury aesthetic. High quality, professional poster design, vertical 9:16 composition.
```

##### 图生图 Prompt 模板

```
Based on the reference image, preserve [elements to keep, e.g.: the person's facial features, hairstyle, and overall composition]. Transform [elements to change, e.g.: the background from XX to XX, the outfit from XX to XX]. 

[New scene/details description]. [New outfit description]. [New lighting/mood description]. 

Maintain the original [preserved elements] exactly. [Style/mood keywords]. High quality, natural integration.
```

**图生图 Prompt 示例（实验室→咖啡店）**：

```
Based on the reference image, preserve the young woman's facial features, hairstyle, and overall body proportions exactly. Transform the scene from a laboratory to a cozy coffee shop. Change the white lab coat to a beige knit cardigan over a simple white shirt. Change the laboratory action to sitting at a wooden coffee shop table, hands naturally holding a latte.

New scene details: Modern cozy coffee shop with wooden furniture, green plants, a coffee machine on the counter, warm-toned pendant lights, large windows letting in soft natural light, bookshelves and framed art near the window. The woman sits by the window, slightly turned toward the camera, natural relaxed pose, gentle smile.

Warm and comfortable atmosphere, color tones leaning toward warm brown, beige, and creamy white. Maintain the person's face exactly as in the original. High quality, natural integration.
```

**Prompt 构建要点**：

1. **英文为主**：GPT 模型英文 Prompt 效果更稳定
2. **中文文案用引号包裹**：如 `reading "中文文案"`，明确告诉模型这是要显示的文字
3. **描述要具体**：颜色、材质、角度、光影都用具体词汇
4. **构图和比例**：在 Prompt 末尾指明构图方向（如 "vertical 9:16 composition"）
5. **图生图特有**：先说 "preserve..." 保持什么不变，再说 "Transform..." 改变什么，末尾再强调 "Maintain ... exactly"
6. **风格关键词**：末尾加 "High quality, professional design" 提升输出品质

---

### 阶段 3：用户确认

**目标**：将设计方案展示给用户，获得确认或调整意见。

**展示方式**：
1. 设计方案全文（含视觉描述 + 文案内容）
2. 关键设计决策说明
3. 预期效果的文字描述

**用户可能的反馈**：
- ✅ **确认**：进入阶段4
- 🔄 **调整文案**：修改主标题/副标题/卖点
- 🎨 **调整视觉**：修改配色/风格/构图
- 📐 **调整布局**：修改排版方式
- ❌ **推翻重来**：回到阶段1

**处理调整**：根据用户反馈修改方案，重新确认。不跳过确认直接生成。

---

### 阶段 4：海报生成

**目标**：调用 OpenRouter API 生成海报图片。

#### 4.1 API 配置

| 参数 | 值 |
|------|-----|
| Base URL | `https://openrouter.ai/api/v1` |
| 文生图端点 | `/images/generations` |
| 图生图端点 | `/chat/completions`（多模态输入） |
| 模型 | `openai/gpt-5.4-image-2` |
| 认证 | `Authorization: Bearer <API_KEY>` |

**⚠️ API Key 获取方式**（按优先级）：
1. 读取环境变量 `OPENROUTER_API_KEY`
2. 读取 `~/.workbuddy/skills/image-creator/.api_key` 文件
3. 以上都没有 → 回到阶段 1.2 向用户询问

#### 4.2 调用生成脚本

使用 `scripts/generate.py` 执行 API 调用：

**文生图**：

```bash
/Users/admin/.workbuddy/binaries/python/envs/default/bin/python3 {baseDir}/scripts/generate.py \
  --mode text2img \
  --prompt "<英文Prompt>" \
  --size "1024x1792" \
  --output "/Users/admin/WorkBuddy/$(date +%Y-%m-%d-%H-%M-%S)/poster-output.png"
```

**图生图**：

```bash
/Users/admin/.workbuddy/binaries/python/envs/default/bin/python3 {baseDir}/scripts/generate.py \
  --mode img2img \
  --prompt "<英文Prompt>" \
  --input-image "/path/to/reference.jpg" \
  --size "1024x1792" \
  --output "/Users/admin/WorkBuddy/$(date +%Y-%m-%d-%H-%M-%S)/poster-output.png"
```

**尺寸参数对照**：

| 场景 | 比例 | size 参数 |
|------|------|-----------|
| 私域1V1 / 朋友圈 | 9:16 | `1024x1792` |
| 社群方图 | 1:1 | `1024x1024` |
| 通用竖版 | 9:16 | `1024x1792` |
| 通用横版 | 16:9 | `1792x1024` |

**⚠️ 如果脚本运行报错**（如依赖缺失），先安装依赖：

```bash
/Users/admin/.workbuddy/binaries/python/envs/default/bin/pip install requests
```

#### 4.3 备用方案：直接 Bash 调用

如果脚本不可用，可直接用 curl + Python 调用 API：

**文生图**：

```bash
curl -s https://openrouter.ai/api/v1/images/generations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "openai/gpt-5.4-image-2",
    "prompt": "<英文Prompt>",
    "n": 1,
    "size": "1024x1792"
  }' | /Users/admin/.workbuddy/binaries/python/envs/default/bin/python3 -c "
import sys, json, urllib.request, os
data = json.load(sys.stdin)
url = data['data'][0].get('url') or ''
b64 = data['data'][0].get('b64_json') or ''
if url:
    urllib.request.urlretrieve(url, '/tmp/poster-output.png')
    print('Saved from URL')
elif b64:
    import base64
    with open('/tmp/poster-output.png', 'wb') as f:
        f.write(base64.b64decode(b64))
    print('Saved from base64')
else:
    print('Error: no image data in response')
    print(json.dumps(data, indent=2))
"
```

**图生图**（通过 Chat Completions 多模态）：

```bash
# 先将图片转为 Base64
INPUT_B64=$(/Users/admin/.workbuddy/binaries/python/envs/default/bin/python3 -c "
import base64, sys
with open('/path/to/reference.jpg', 'rb') as f:
    print(base64.b64encode(f.read()).decode())
")

curl -s https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d "{
    \"model\": \"openai/gpt-5.4-image-2\",
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"text\", \"text\": \"<英文Prompt>\"},
        {\"type\": \"image_url\", \"image_url\": {\"url\": \"data:image/jpeg;base64,$INPUT_B64\"}}
      ]
    }]
  }" | /Users/admin/.workbuddy/binaries/python/envs/default/bin/python3 -c "
import sys, json, base64, re, urllib.request
data = json.load(sys.stdin)
content = data['choices'][0]['message']['content']
# 从 content 中提取图片 URL 或 base64
if isinstance(content, list):
    for part in content:
        if part.get('type') == 'image_url':
            img_url = part['image_url']['url']
            if img_url.startswith('data:'):
                b64_data = img_url.split(',', 1)[1]
                with open('/tmp/poster-output.png', 'wb') as f:
                    f.write(base64.b64decode(b64_data))
                print('Saved from base64')
            else:
                urllib.request.urlretrieve(img_url, '/tmp/poster-output.png')
                print('Saved from URL')
            break
elif isinstance(content, str):
    # 可能在文本中包含 markdown 图片链接
    urls = re.findall(r'https?://\S+\.(?:png|jpg|jpeg|webp)', content)
    if urls:
        urllib.request.urlretrieve(urls[0], '/tmp/poster-output.png')
        print('Saved from URL in text')
    else:
        print('No image found in response')
        print(content[:500])
"
```

---

### 阶段 5：输出总结

**目标**：向用户展示最终海报，总结设计思路。

**输出内容**：

1. **海报文件**：将生成的海报图片展示给用户（使用 `open_result_view` 或 `preview_url`）
2. **设计思路总结**：

```markdown
### 设计思路

- 🎨 **视觉策略**：[为什么选择这种配色和构图]
- ✍️ **文案策略**：[文案如何传达核心信息]
- 🎯 **场景适配**：[设计如何适配目标场景]
- 📐 **尺寸选择**：[为什么选择这个比例]
```

3. **迭代提示**：告知用户如需调整，可以描述修改方向

---

## 用户要求调整时的处理

| 修改类型 | 处理方式 |
|----------|----------|
| **微调文案** | 回到阶段2修改 Prompt 中的文案部分，重新确认后重新生成 |
| **调整视觉风格** | 回到阶段2修改视觉描述，重新确认后生成 |
| **完全不满意** | 回到阶段1重新确认需求 |
| **图生图人物不像** | 在 Prompt 中强化 "preserve ... exactly"，减少改造幅度，重新生成 |
| **文字有误** | 修改 Prompt 中的文案描述，重新生成 |

**重要**：任何调整都必须经过用户确认（阶段3）后再生成。

---

## 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| API 返回 401 / 认证失败 | API Key 无效或过期，删除 `.api_key` 后重新询问用户 |
| API 返回 429 / 限速 | 告知用户稍等重试，或检查 OpenRouter 账户余额 |
| API 返回 400 / 参数错误 | 检查 size 格式、prompt 长度，调整后重试 |
| 生成超时 | API 默认 180s 超时，可增加到 300s |
| 生成结果质量不佳 | 调整 Prompt，增加具体描述，重新生成（最多3次） |
| 图生图输入图片过大 | 压缩图片后重试（建议 < 20MB） |
| API 返回模型不支持 | 确认模型名为 `openai/gpt-5.4-image-2`，检查 OpenRouter 是否可用 |
| images/generations 不可用 | 改用 chat/completions 端点（图生图模式的方式） |
| chat/completions 无图片输出 | 检查模型是否支持图片生成，尝试 images/generations 端点 |

---

## 快速参考

### API Key 位置

| 优先级 | 位置 | 说明 |
|--------|------|------|
| 1 | 环境变量 `OPENROUTER_API_KEY` | 首选 |
| 2 | `~/.workbuddy/skills/image-creator/.api_key` | 备选存储 |

### 尺寸与场景对照

| 场景 | 比例 | size 参数 |
|------|------|-----------|
| 私域1V1 / 朋友圈 | 9:16 | `1024x1792` |
| 社群方图 | 1:1 | `1024x1024` |
| 横版 | 16:9 | `1792x1024` |

### 生成脚本路径

```
{baseDir}/scripts/generate.py
```

### 关键 Prompt 技巧

1. 英文为主，中文文案用引号包裹
2. 先描述主体，再描述背景和细节
3. 图生图：先说"preserve"，再说"transform"，末尾再强调
4. 末尾加 "High quality, professional design" 提升品质
5. 指明比例："vertical 9:16 composition" 或 "square 1:1 composition"
