# Kubernetes 部署

> 如果你已经在用 K8s，也不想碰 Docker Compose。这里只给基本配置，不做过多编排。

## 前提

一个可用的 K8s 集群（minikube、kind 或云厂商的集群）。

## ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: traceloop-config
data:
  DATABASE_URL: "postgresql+asyncpg://traceloop:traceloop_dev@postgres-service:5432/traceloop"
  REDIS_URL: "redis://redis-service:6379/0"
  MOCK_LLM_URL: "http://mock-llm-service:9876"
  REDIS_STREAM_NAME: "traceloop:traces"
  REDIS_CONSUMER_GROUP: "trace-writers"
```

## Deployment：API

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: traceloop-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: traceloop-api
  template:
    metadata:
      labels:
        app: traceloop-api
    spec:
      containers:
      - name: api
        image: traceloop/ci-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: traceloop-config
        env:
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: traceloop-secret
              key: API_KEY
        resources:
          requests:
            cpu: "0.5"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
```

## Deployment：Mock LLM（仅开发环境）

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mock-llm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mock-llm
  template:
    metadata:
      labels:
        app: mock-llm
    spec:
      containers:
      - name: mock-llm
        image: traceloop/ci-api:latest
        command: ["uvicorn", "app.services.mock_llm:app", "--host", "0.0.0.0", "--port", "9876"]
        ports:
        - containerPort: 9876
```

生产环境不会用 Mock LLM，这里只为开发/预发布环境保留。

## Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: traceloop-api-service
spec:
  selector:
    app: traceloop-api
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

暴露到外部用 Ingress，或者直接改 Service type 为 LoadBalancer。

## 数据库和 Redis

在 K8s 里跑有状态服务需要 StatefulSet + PVC，配置会复杂很多。**建议直接用托管服务**：

```yaml
# 还是 ConfigMap，但指向托管服务
apiVersion: v1
kind: ConfigMap
metadata:
  name: traceloop-config
data:
  DATABASE_URL: "postgresql+asyncpg://user:password@your-supabase-host:5432/postgres"
  REDIS_URL: "redis://your-upstash-host:6379"
```

## 完整启动

```bash
kubectl create secret generic traceloop-secret --from-literal=API_KEY=$(openssl rand -hex 32)
kubectl apply -f k8s-configmap.yaml
kubectl apply -f k8s-api-deployment.yaml
kubectl apply -f k8s-mock-llm.yaml
kubectl apply -f k8s-service.yaml
```

## 局限

- 2 个 replica 的 api deployment 共享一个 Redis consumer group，理论上会有重复消费。当前 consumer 设计是 at-least-once，不影响数据完整性。
- 没有配置 HPA（水平自动扩缩）。目前流量下不需要，trace 写入是异步的，CPU 负载很低。
- 没有 sidecar 或 mesh。需要的话自己加。
