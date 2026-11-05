# TypeScript SDK

```typescript
import { configure, recordTrace } from 'trace-loop-ci';
configure({apiUrl:'http://localhost:8000', apiKey:'your-workspace-key'});
await recordTrace('question', 'answer', 'model');
```

不要在公开浏览器代码中包含工作区 Key。SDK 使用 10 秒 HTTP 超时；失败时警告。传统方法装饰器 traceLoop 记录成功和异常调用，保留原始业务异常。装饰器不自动捕获完整工具链或所有模型 SDK。
