# 用例规则

```json
{"input_text":"退款政策？","expected_keywords":["7天","退款"],"forbidden_keywords":["不能退款"],"must_cite_docs":["refund-policy"],"expected_json_schema":null}
```

可附带 messages 或 system_prompt 保存对话上下文。从 Trace 创建时自动保留消息与 system prompt。规则修改会改变数据集 hash，需要重新审核基线。

自定义 evaluator 当前通过 app/services/evaluators 的代码注册，尚无动态插件加载协议。PR 应用 adapter 示例见 examples/regression_app.py。
