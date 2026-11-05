# 裁判配置

使用 JUDGE_BASE_URL（不含 /v1）、JUDGE_MODEL、JUDGE_API_KEY。它们与被测模型 LLM_BASE_URL/LLM_API_KEY 分开。

缺少 Key 是 degraded；调用失败或分数无效是 evaluation_error。正式门禁要求真实裁判，演示可显式允许 mock。启发式结果仅检查字面规则，不提供语义评分保证。

裁判仍可能受被测回答中的指令影响，也存在打分波动。建议保留人工标注集、重复实验，并将重要安全/业务断言写成确定性规则。
