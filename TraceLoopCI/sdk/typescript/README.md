# TraceLoop CI — TypeScript SDK

LLM behavioral regression testing for Node.js apps.

## Install

```bash
npm install trace-loop-ci
```

## Usage

```typescript
import { configure, recordTrace } from "trace-loop-ci";

configure({ apiUrl: "http://localhost:8000", apiKey: "your-key" });

const output = await callLLM("退款政策?");
await recordTrace("退款政策?", output, "deepseek-chat");
```
