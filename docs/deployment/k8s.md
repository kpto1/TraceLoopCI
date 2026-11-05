# Kubernetes

本仓库当前没有维护 Helm Chart 或经验证的 Kubernetes 部署清单。不要把历史架构规划视为可直接投产的配置。

迁移到 Kubernetes 前，需自行实现单次迁移 job、外部持久化数据库/Redis、认证入口、资源与网络策略、健康检查和故障演练。优先完成单机部署验收。
