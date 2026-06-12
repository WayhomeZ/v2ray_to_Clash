# 节点过滤与评估报告 (Node Filtering Evaluation Report)

*生成时间 (UTC): 2026-06-12 04:55:20*

### 📊 过滤层级度量数据 (Metrics by Filtering Layer)

| 过滤层级 (Filter Layer) | 输入节点数 | 留存节点数 | 过滤节点数 | 过滤占比 | 耗时 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 1. Server 主机过滤 | 3901 | 3888 | 13 | 0.33% | 0.8525 ms |
| 2. Port 端口过滤 | 3888 | 3888 | 0 | 0.00% | 0.9393 ms |
| 3. Protocol 协议过滤 | 3888 | 3825 | 63 | 1.62% | 2.4702 ms |
| 4. Identity 节点去重 | 3825 | 1871 | 1954 | 51.08% | 4.1186 ms |

### 📈 过滤效果综合评价 (Overall Evaluation)

- **原始节点总数 (Initial Nodes)**: `3901`
- **净化后有效节点数 (Retained Nodes)**: `1871`
- **过滤及去重节点总数 (Filtered Total)**: `2030`
- **整体过滤/去重率 (Overall Filtering Rate)**: `52.04%`
- **总处理耗时 (Total Duration)**: `8.3806 ms`

---
*注：本报告由自动化节点净化脚本自动生成。*
