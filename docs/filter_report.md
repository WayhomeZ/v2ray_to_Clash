# 节点过滤与评估报告 (Node Filtering Evaluation Report)

*生成时间 (UTC): 2026-06-12 10:53:47*

### 📊 过滤层级度量数据 (Metrics by Filtering Layer)

| 过滤层级 (Filter Layer) | 输入节点数 | 留存节点数 | 过滤节点数 | 过滤占比 | 耗时 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 1. Server 主机过滤 | 529 | 529 | 0 | 0.00% | 0.0648 ms |
| 2. Port 端口过滤 | 529 | 529 | 0 | 0.00% | 0.0658 ms |
| 3. TCP 连通性过滤 | 529 | 527 | 2 | 0.38% | 3784.8079 ms |
| 4. GeoIP 地区标记 | 527 | 527 | 0 | 0.00% | 5.4644 ms |
| 5. SS Cipher 过滤 | 527 | 527 | 0 | 0.00% | 0.0740 ms |
| 6. Reality Short-ID 过滤 | 527 | 527 | 0 | 0.00% | 0.2077 ms |
| 7. UUID 格式过滤 | 527 | 527 | 0 | 0.00% | 0.0638 ms |
| 8. Identity 节点去重 | 527 | 527 | 0 | 0.00% | 0.2118 ms |

### 📈 过滤效果综合评价 (Overall Evaluation)

- **原始节点总数 (Initial Nodes)**: `529`
- **净化后有效节点数 (Retained Nodes)**: `527`
- **过滤及去重节点总数 (Filtered Total)**: `2`
- **整体过滤/去重率 (Overall Filtering Rate)**: `0.38%`
- **总处理耗时 (Total Duration)**: `3790.9602 ms`

---
*注：本报告由自动化节点净化脚本自动生成。*
