# 模型评测脚本

直接调用本地 `Evaluator`/`Polisher`（LLM 接口）对本地示例（`test_answer/*.txt`）做评分/润色评测，并输出指标：

- 评分一致性：准确率、MAE、MSE、偏差（高估/低估趋势）
- 保序性：Spearman 相关、是否存在排序违例
- 混淆矩阵：真实分 -> 预测分
- 润色不降分：non_drop_rate、improve_rate、avg/min/max Δ
- 详情：每条样本的预测与润色后预测

## 配置

复制示例配置：

```bash
cp test_model/config.example.yaml test_model/config.local.yaml
```

然后根据实际情况修改 `config.local.yaml`：

- `model_name`: LLM 模型名（传给 DashScope/兼容 OpenAI 接口）
- `base_url`: LLM API Base URL（兼容 OpenAI 协议的地址）
- `api_key`: LLM API Key
- `dataset_glob`: 样本通配符，默认 `test_answer/*.txt`（文件名形如 `44_5_2.txt`）
- `evaluate_polished`: 是否对润色结果再评一遍分数
- `runs`: 每个样本重复调用次数，用于降低 LLM 随机性（取平均，不再四舍五入）

## 运行

确保你的 LLM Key 和 Base URL 配置正确（无需启动本地后端），然后执行：

```bash
python test_model/eval_models.py test_model/config.local.yaml
```

示例输出（已裁剪）：

```json
{
  "model": "qwen-plus",
  "samples": 8,
  "metrics": {
    "exact_acc": 0.5,
    "mae": 0.625,
    "mse": 0.875,
    "bias": 0.625,
    "spearman": 0.8460,
    "order_non_violation": false
  },
  "polisher": {
    "non_drop_rate": 1.0,
    "improve_rate": 0.5,
    "avg_delta": 1.25,
    "min_delta": 0,
    "max_delta": 4
  },
  "confusion": { "...": "..." },
  "details": [ { "path": "...", "expected": 1, "pred": 2, "polished_pred": 5, "delta": 3 }, ... ]
}
```

指标释义（↑ 越大越好，↓ 越小越好）：

- `exact_acc` ↑：预测分数与期望分完全一致的比例。
- `mae` ↓：平均绝对误差。
- `mse` ↓：均方误差。
- `bias` 绝对值↓：平均预测-真实，>0 表示整体偏高，<0 偏低。
- `spearman` ↑：Spearman 排序相关；越接近 1 排序越一致，负值表示逆序。
- `order_non_violation` ↑：是否完全无排序违例（布尔）。
- `non_drop_rate` ↑：润色后分数未下降的比例。
- `improve_rate` ↑：润色后分数提升的比例。
- `avg_delta`：润色后分数变化均值，>0 平均提升。
- `min_delta`/`max_delta`：润色后分数变化的最小/最大值，关注是否有负值。
- `confusion`：真实分 -> 预测分的计数矩阵，便于看偏差方向。
- `details`：每条样本的路径、期望分、预测分、润色后分和分差。

脚本会把指标和每条样本的评分结果以 JSON 打印到终端。需要更多样本时，按 `question_score_variant` 规则新增文件即可。
