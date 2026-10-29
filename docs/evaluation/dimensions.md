# 评测与门禁

- keyword：expected_keywords 全部出现，forbidden_keywords 全部不出现；字面匹配不等于事实正确。
- json_schema：提供 schema 时检查输出 JSON，缺少 schema 时不惩罚纯文本。
- llm_judge：中文裁判提示词，0–10 分，6 分及以上通过。没有 Key 时产生 mock/degraded，正式门禁阻断。调用或解析错误不降级放行。
- citations：must_cite_docs 中的文档标识必须出现在回答；不检验引用真实性。

报告有 passed/failed/evaluation_error/degraded 状态。综合得分是用例通过率，不是平均语义分。默认最低 80%，基线下降容忍 0 个百分点，任何新增失败用例都会阻断。成本未测量返回 null，P95 按最近秩取值。

基线必须来自相同数据集及相同评测配置。模型或应用版本可变，裁判参数和断言应保持稳定。API 使用 baseline_run_id，CLI 使用 --baseline 文件。基线是审核结果，不应在每次候选运行中自动覆盖。
