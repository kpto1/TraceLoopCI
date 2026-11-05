# 首次评测

1. 在数据集页面创建数据集。
2. 填入用例 JSON，或提供 Trace ID 将历史请求提升为用例。
3. 设置模型与版本标识。无模型 Key 的本地演示使用 mock；仅演示时取消“要求真实裁判”。
4. 保存一次基线，然后选择该基线运行候选评测。
5. 查看 gate_passed、gate_reasons、comparison.regressed_cases 和 per_case。

PR 中的业务 prompt/RAG 改动必须通过 CLI adapter 执行实际 checkout；远端 API 的 revision 字段只是调用方声明。
