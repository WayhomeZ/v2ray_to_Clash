# 节点过滤与评估报告 (Node Filtering Evaluation Report)

*生成时间 (UTC): 2026-08-17 17:18:24*

### 📊 过滤层级度量数据 (Metrics by Filtering Layer)

| 过滤层级 (Filter Layer) | 输入节点数 | 留存节点数 | 过滤节点数 | 过滤占比 | 耗时 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| 1. Server 主机过滤 | 1 | 1 | 0 | 0.00% | 0.0020 ms |
| 2. Port 端口过滤 | 1 | 1 | 0 | 0.00% | 0.0017 ms |
| 3. SS Cipher 过滤 | 1 | 1 | 0 | 0.00% | 0.0010 ms |
| 4. Reality Short-ID 过滤 | 1 | 1 | 0 | 0.00% | 0.0005 ms |
| 5. UUID 格式过滤 | 1 | 1 | 0 | 0.00% | 0.0008 ms |
| 6. Identity 节点去重 | 1 | 1 | 0 | 0.00% | 0.0017 ms |
| 7. TCP 连通性过滤(1s) | 1 | 1 | 0 | 0.00% | 3.8492 ms |
| 8. TLS 握手验证 | 1 | 1 | 0 | 0.00% | 0.0049 ms |
| 9. Trojan 协议验证 | 1 | 1 | 0 | 0.00% | 0.0028 ms |
| 10. GeoIP 地区标记 | 1 | 1 | 0 | 0.00% | 0.2308 ms |

### 📈 过滤效果综合评价 (Overall Evaluation)

- **原始节点总数 (Initial Nodes)**: `1`
- **净化后有效节点数 (Retained Nodes)**: `1`
- **过滤及去重节点总数 (Filtered Total)**: `0`
- **整体过滤/去重率 (Overall Filtering Rate)**: `0.00%`
- **总处理耗时 (Total Duration)**: `4.0955 ms`

---
*注：本报告由自动化节点净化脚本自动生成。*
