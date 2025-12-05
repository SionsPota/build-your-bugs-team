# TOEFL 写作评分与润色系统

一个基于 Flask 和 Vue 3 的 TOEFL 写作评分与润色系统，支持结构化评分、自动润色和历史记录管理。

## 主要功能

- 📊 **结构化评分**：自动生成包含优点、缺点、待提升建议和总评的详细评语
- 🎯 **总评分显示**：提取并显示 0-5 分的 TOEFL 标准评分
- ✨ **自动润色**：将作文润色提升到 5 分标准
- 📝 **历史记录**：保存和管理用户的评分历史
- 🔄 **流式传输**：实时显示评分和润色过程
- 👤 **用户认证**：支持用户注册、登录和 JWT 认证

## 最新更新

### 评分功能增强

- ✅ 添加了 `score` 字段到历史记录模型，支持存储和显示总评分
- ✅ 实现了 `CommentParser` 类，自动从结构化评语中解析评分
- ✅ 创建了数据库迁移脚本 `migrate_add_score.py`，用于升级现有数据
- ✅ 前端界面增强，在评分结果、历史记录列表等多个位置显示评分
- ✅ 扩展了 Prompt 文件，支持更丰富的评分和润色流程

### 数据库迁移

如果您的数据库是旧版本，需要运行迁移脚本添加 `score` 字段：

```bash
python migrate_add_score.py
```

该脚本会：

1. 为 `histories` 表添加 `score` 字段（如果不存在）
2. 从现有记录的 `comment` 字段中解析评分并更新到数据库

## 快速开始

### 使用 Docker

Build the project in docker:

```bash
docker build -t essay-service .
```

Run the project in docker (replace YOUR_API_KEY with your actual DashScope API key):

```bash
docker run -p 8000:8000 \
    -e DASHSCOPE_API_KEY=YOUR_API_KEY \
    essay-service
```

### 本地开发

#### 后端

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 配置环境变量：

创建 `.env` 文件，添加：

```env
DASHSCOPE_API_KEY=your_api_key_here
```

3. 初始化数据库：

```bash
python init_db.py
```

4. 运行数据库迁移（如果需要）：

```bash
python migrate_add_score.py
```

5. 启动后端服务：

```bash
python app.py
```

后端服务将在 `http://localhost:8000` 启动。

#### 前端

```bash
cd frontend
npm install
npm run dev
```

前端服务将在 `http://localhost:5173` 启动。

## API 使用示例

```bash
curl -X POST http://127.0.0.1:8000/grade_and_polish \
  -H "Content-Type: application/json" \
  -d '{"answer":"...", "question_file":"..."}'
```

## 项目结构

```text
.
├── app.py                  # Flask 后端主应用
├── model.py                # 评分模型和评语解析器
├── user_models.py          # 用户和历史记录数据模型
├── history_service.py       # 历史记录服务
├── migrate_add_score.py    # 数据库迁移脚本（添加评分字段）
├── init_db.py             # 数据库初始化脚本
├── prompt/                # AI Prompt 模板文件
│   ├── system_prompt.txt
│   ├── system_prompt_Evaluate.txt
│   ├── assistant_prompt_*.txt
│   └── user_prompt_*.txt
└── frontend/              # Vue 3 前端应用
    └── src/
        ├── components/    # Vue 组件
        ├── api/          # API 服务封装
        └── router/       # 路由配置
```

## 评分系统说明

系统采用结构化的评分方式，评语包含以下部分：

- **优点 (Strengths)**：列出作文的强项（0-4 个要点）
- **缺点 (Weaknesses)**：指出需要改进的地方（0-4 个要点）
- **待提升 (Opportunities)**：提供改进建议（0-4 个要点）
- **总评 (Overview)**：综合评估和总结
- **分数 (Score)**：0-5 分的 TOEFL 标准评分

评分会自动从评语中解析并存储在数据库中，方便后续查询和展示。

## 更多信息

详细的前端使用说明请参考 [frontend/README.md](frontend/README.md)。
