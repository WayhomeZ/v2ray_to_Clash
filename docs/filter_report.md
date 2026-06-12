# 节点过滤与评估报告 (Node Filtering Evaluation Report)

*生成时间 (UTC): 2026-06-12 16:05:53*

### 📊 过滤层级度量数据 (Metrics by Filtering Layer)

| 过滤层级 (Filter Layer) | 输入节点数 | 留存节点数 | 过滤节点数 | 过滤占比 | 耗时 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 1. Server 主机过滤 | 466 | 466 | 0 | 0.00% | 0.0724 ms |
| 2. Port 端口过滤 | 466 | 466 | 0 | 0.00% | 0.0610 ms |
| 3. TCP 连通性过滤 | 466 | 462 | 4 | 0.86% | 2060.5939 ms |
| 4. GeoIP 地区标记 | 462 | 462 | 0 | 0.00% | 0.9260 ms |
| 5. SS Cipher 过滤 | 462 | 462 | 0 | 0.00% | 0.1124 ms |
| 6. Reality Short-ID 过滤 | 462 | 462 | 0 | 0.00% | 0.1498 ms |
| 7. UUID 格式过滤 | 462 | 462 | 0 | 0.00% | 0.1358 ms |
| 8. Identity 节点去重 | 462 | 462 | 0 | 0.00% | 0.4058 ms |

### 📈 过滤效果综合评价 (Overall Evaluation)

- **原始节点总数 (Initial Nodes)**: `466`
- **净化后有效节点数 (Retained Nodes)**: `462`
- **过滤及去重节点总数 (Filtered Total)**: `4`
- **整体过滤/去重率 (Overall Filtering Rate)**: `0.86%`
- **总处理耗时 (Total Duration)**: `2062.4571 ms`

---
*注：本报告由自动化节点净化脚本自动生成。*
