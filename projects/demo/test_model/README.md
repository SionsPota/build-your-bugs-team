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

## 运行

确保你的 LLM Key 和 Base URL 配置正确（无需启动本地后端），然后执行：

```bash
python test_model/eval_models.py test_model/config.local.yaml
```

脚本会把指标和每条样本的评分结果以 JSON 打印到终端。需要更多样本时，按 `question_score_variant` 规则新增文件即可。
