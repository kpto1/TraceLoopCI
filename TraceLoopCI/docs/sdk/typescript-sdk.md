# TypeScript SDK

在 Node.js 应用中记录 LLM 调用 trace。

SDK 源码在 `sdk/typescript/`，纯 TypeScript，无运行时依赖。

## 安装

```bash
npm install trace-loop-ci
```

要求 Node.js 18+。

## 快速开始

```typescript
import { configure, recordTrace } from 'trace-loop-ci';

// 初始化（在应用启动时执行一次）
configure({
  apiUrl: 'http://localhost:8000',
  apiKey: 'dev-api-key-change-in-production',
  projectId: 'my-app',
});

// 记录一次 LLM 调用
async function chat(input: string) {
  const start = Date.now();
  const response = await callLLM(input);
  const latency = Date.now() - start;

  await recordTrace(input, response, 'deepseek-chat', {
    latency_ms: latency,
    tokens_total: response.length, // 可选
  });
}
```

## configure()

```typescript
configure(config: TraceLoopConfig): void;
```

`TraceLoopConfig`：

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `apiUrl` | `string` | 必填 | TraceLoop API 地址，如 `http://localhost:8000` |
| `apiKey` | `string` | `undefined` | API Key |
| `projectId` | `string` | `'default'` | 项目标识 |

未调用 `configure()` 时，`recordTrace()` 和装饰器会打印 warning 并跳过。

## recordTrace()

```typescript
recordTrace(
  input: string,
  output: string,
  model: string,
  extra?: Partial<Omit<TraceRecord, 'user_input' | 'model_output' | 'model'>>
): Promise<void>;
```

发送 POST 请求到 `{apiUrl}/v1/traces`。

`extra` 可选字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `project_id` | `string` | 覆盖 configure 中的 project id |
| `provider` | `string` | 模型提供商，如 `"deepseek"` |
| `tokens_total` | `number` | 总 token 数 |
| `cost` | `number` | 调用成本（美元） |
| `latency_ms` | `number` | 延迟（毫秒） |
| `status` | `string` | `"success"` 或 `"error"` |
| `tags` | `string[]` | 标签列表 |

发送失败不会抛出异常，只在控制台输出 warning。

## traceLoop() 装饰器

```typescript
import { traceLoop } from 'trace-loop-ci';

class ChatService {
  @traceLoop('deepseek-chat')
  async ask(input: string): Promise<string> {
    const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: [{ role: 'user', content: input }],
      }),
    });
    const data = await response.json();
    return data.choices[0].message.content;
  }
}
```

装饰器会自动：
- 用方法参数作为 `user_input`
- 用返回值作为 `model_output`
- 计算 `latency_ms`（方法执行耗时）
- 捕获异常并将 `status` 设为 `"error"`

## 配置自动加载

推荐在应用入口处尽早调用 `configure()`：

```typescript
// app.ts 或 index.ts
import { configure } from 'trace-loop-ci';

configure({
  apiUrl: process.env.TRACELOOP_URL || 'http://localhost:8000',
  apiKey: process.env.TRACELOOP_KEY,
  projectId: process.env.TRACELOOP_PROJECT || 'default',
});
```

## 局限

- 装饰器只支持 `async` 方法。同步方法不会报错，但 latency 测量会不准。
- 装饰器版本需要 `experimentalDecorators: true` 或 TypeScript 5+ decorators 支持。
- 自动拦截只到方法级别 —— 方法内部如果有多个 LLM 调用，装饰器只能记录最外层。
- SDK 不处理重试。如果请求失败，trace 就丢了。
