# 节点过滤与评估报告 (Node Filtering Evaluation Report)

*生成时间 (UTC): 2026-06-12 06:31:09*

### 📊 过滤层级度量数据 (Metrics by Filtering Layer)

| 过滤层级 (Filter Layer) | 输入节点数 | 留存节点数 | 过滤节点数 | 过滤占比 | 耗时 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 1. Server 主机过滤 | 998 | 996 | 2 | 0.20% | 0.1483 ms |
| 2. Port 端口过滤 | 996 | 996 | 0 | 0.00% | 0.1832 ms |
| 3. SS Cipher 过滤 | 996 | 996 | 0 | 0.00% | 0.0844 ms |
| 4. Reality Short-ID 过滤 | 996 | 976 | 20 | 2.01% | 0.2182 ms |
| 5. UUID 格式过滤 | 976 | 976 | 0 | 0.00% | 0.1781 ms |
| 6. Identity 节点去重 | 976 | 529 | 447 | 45.80% | 0.5515 ms |

### 📈 过滤效果综合评价 (Overall Evaluation)

- **原始节点总数 (Initial Nodes)**: `998`
- **净化后有效节点数 (Retained Nodes)**: `529`
- **过滤及去重节点总数 (Filtered Total)**: `469`
- **整体过滤/去重率 (Overall Filtering Rate)**: `46.99%`
- **总处理耗时 (Total Duration)**: `1.3637 ms`

---
*注：本报告由自动化节点净化脚本自动生成。*
