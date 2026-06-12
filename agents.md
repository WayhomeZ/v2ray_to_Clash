# V2Ray to Clash Converter - AI Agent Guideline / 规范指南

本文件定义了本项目的设计架构、已知踩坑点以及针对未来 AI Agent 协作开发的**核心约束与开发规范**。任何在此仓库工作的 AI 助理在修改代码前，均须严格遵守本文档。

---

## 1. 架构与核心流程 (Architecture)

本项目是一个高度自动化的 Clash/Mihomo 订阅转换器，核心处理链条如下：

```
[config/source.txt] (订阅源)
       │
       ▼ (curl 下载并拼接)
[sub_tmp/merged_final.txt] (Base64 编码)
       │
       ▼ (通过本地 Python HTTP 服务分发给 Docker)
[Docker: metacubex/subconverter] (生成基础 Clash YAML)
       │
       ▼ (Python 脚本正则预处理 & PyYAML 结构清洗)
[docs/proxies.yaml & docs/config_monolithic.yaml] (输出)
```

1. **订阅合并**：`scripts/convert.sh` 读取 `config/source.txt`，用 `curl` 爬取节点并拼接，自动转换为 Base64 格式。
2. **Subconverter 转换**：启动本地 Python HTTP 服务器并拉起 `metacubex/subconverter` 容器，生成 Clash 基础配置。
3. **YAML 净化（核心修改点）**：通过内嵌的 Python 代码修复各种 Subconverter 导出的格式 Bug，并对节点数据进行过滤。
4. **发布发布**：`scripts/publish.sh` 将清理好的节点池拼装为 `config.yaml`（Proxy-Provider 模式），由 GitHub Actions 部署至 GitHub Pages。

---

## 2. 节点筛选设计哲学 (Node Filtering Philosophy)

本项目对“可用节点”的筛选采用**构建期与运行时分离**的设计思路，开发后续功能时须遵循此原则：

### 🛠️ 构建期过滤（Server-side / Actions 阶段）
在 GitHub Actions 构建配置文件时对节点进行初步筛选与清洗。
* **环境差异与潜在问题**：GitHub Actions 构建环境与用户本地真实网络存在较大差异（例如构建服务器能连通 the 节点在用户本地可能超时，反之亦然），且在 Actions 构建服务器上直接进行大规模 Ping/Curl 测速会显着延长执行时间。**但如果能针对性解决这些环境与效率问题，后续仍可在此阶段前置引入节点存活与可用性测试。**
* **过滤与分类模块设计**（已全部集成于 `scripts/purify.py`）：
  * **1. Server 主机过滤模块（已启用）**
    * **解决的问题**：空 `server`、回环地址（如 `127.0.0.1`、`localhost`）或非法主机。
    * **解决方法**：静态匹配校验，直接丢弃回环或非法域名/IP 节点。
    * **预计结果**：拦截最底层的无效配置。
  * **2. Port 端口过滤模块（已启用）**
    * **解决的问题**：空端口、非数字端口、超出正常网络范围的端口（不在 1-65535 范围内）。
    * **解决方法**：强转整型验证并执行边界范围过滤。
    * **预计结果**：确保所有代理配置的端口号完全合法合规。
  * **3. TCP 连通性过滤模块（已启用）**
    * **解决的问题**：大量彻底失效、停机或无法连接的废节点占用配置，导致客户端无意义地测速发包。
    * **解决方法**：利用 Python 线程池（`ThreadPoolExecutor` 并发 100 线程）向存活的节点 `(server, port)` 发起超时为 2.0 秒的 TCP 三次握手测试。握手失败的节点直接丢弃，成功的节点同时获取其已解析的物理 IP。
    * **预计结果**：筛掉 100% 物理死节点，仅留存具备连通性的活性节点。
  * **4. GeoIP 地区标记模块（已启用）**
    * **解决的问题**：原有的节点名称正则地区分类准确率低（部分节点乱码无地区、部分节点命名欺诈）。
    * **解决方法**：读取离线版 `GeoLite2-Country.mmdb` 二进制数据库，以第三步解析的 IP 地址查找国家 ISO 代码。为存活节点名称统一加前缀 `[国家代码]` (如 `[HK]`)，并在 `proxy-groups` 策略组中同步重命名和引用。
    * **预计结果**：节点物理地区识别率和分流准确率达到 100%，并在 `docs/filter_report.md` 中留存各阶段指标。
  * **5. SS Cipher 过滤模块（已启用）**
    * **解决的问题**：非法的 `cipher: ss` 字段以及已弃用的加密协议如 `chacha20-poly1305`。
    * **解决方法**：丢弃 `cipher: ss` 的节点，并自动将 `chacha20-poly1305` 更正为 Mihomo 兼容的 `chacha20-ietf-poly1305`。
    * **预计结果**：解决由 Shadowsocks 协议配置不兼容导致的内核报错。
  * **6. Reality Short-ID 过滤模块（已启用）**
    * **解决的问题**：格式非法的 REALITY `short-id`（非偶数长度、非十六进制或长度超限），导致解析崩溃。
    * **解决方法**：强制进行十六进制解码检查、长度偶数验证以及最大长度（16字节）控制。
    * **预计结果**：节点完美通过 REALITY 特征校验，不会引起内核解析崩溃。
  * **7. UUID 格式过滤模块（已启用）**
    * **解决的问题**：VMess/VLESS 节点中 uuid 丢失或不符合 36 位标准 uuid 格式。
    * **解决方法**：验证凭证格式与 36 位长度，剔除畸形节点。
    * **预计结果**：保障核心认证密钥有效性，记录过滤数量与耗时。
  * **8. 节点去重模块（已启用）**
    * **解决的问题**：不同订阅源（特别是免费聚合源）中存在大量**重复节点**（相同 IP、端口及加密密钥，但节点命名不同）。重复节点会成倍增加客户端的解析负担，并在后续的客户端/服务端 Ping 测速阶段造成大量无意义 of 重复发包，导致带宽浪费和节点端误判防刷限制。
    * **解决方法**：在 Python 净化阶段（`scripts/purify.py`），基于节点的唯一特征（如 `(type, server, port, uuid/password)` 组合 of 哈希值）进行去重判断。若检测到重复节点，仅保留第一个，并同步清理策略组中的冗余引用。
    * **预计结果**：显著压缩配置文件体积，减轻后续客户端/服务端测速阶段的网络和性能开销。生成评估报告于 `docs/filter_report.md`。
  * **关键词/黑白名单过滤模块（后续可扩展）**
    * **解决的问题**：根据用户个性化偏好，排除或筛选特定节点（如过滤掉“免费”、“剩余流量”等垃圾节点，或排除特定故障 IP 段）。
    * **解决方法**：在 Python 解析节点后，依据节点名称或服务器 IP/域名进行正则/字符串规则匹配，执行静态剔除或分类。
    * **预计结果**：生成高度个性化、无广告/无垃圾节点的纯净节点列表。
  * **可用性与存活测速模块（后续可扩展）**
    * **解决的问题**：Actions 构建服务器端与用户本地真实网络虽有差异，但前置测试仍能粗筛掉大面积彻底失效的废节点。
    * **解决方法**：利用局域代理网关或分流测速框架，在构建期对提取出的节点进行连通性（Ping/Curl）嗅探，丢弃无响应节点。
    * **预计结果**：Actions 端初步剔除死节点，提升本地加载时的节点整体存活率。

### ⚡ 运行时动态筛选（Client-side / 客户端阶段）
真实的节点存活和延迟筛选应**完全交给客户端内核**动态完成。
* **筛选模块设计**：
  * **存活探测与健康检查模块（已启用）**
    * **解决的问题**：在实际使用过程中，某些原本合规的节点可能因服务器故障、网络阻塞或 IP 被封锁而变得临时不可用。
    * **解决方法**：在模板中通过 `proxy-providers` 的 `health-check` 字段配置动态探测，设定其每 5 分钟向指定的测速 URL（如 Cloudflare 204）发送一次轻量请求。
    * **预计结果**：在客户端运行期间动态检测节点活性，实时剔除死节点，提升节点整体可用率。
  * **自动低延迟优选模块（已启用）**
    * **解决的问题**：可用节点群中各节点延迟表现各异，手动切换最优节点体验不佳且缺乏及时性。
    * **解决方法**：在策略组中配置 `type: url-test` 组（如 `♻️ 自动选择`），对健康节点自动执行并发延迟测速，并在设定的容差值（tolerance 50ms）内自动切换指向最低延迟节点。
    * **预计结果**：实现用户无感知的低延迟节点自动漂移，始终维持最优的网络质量。
  * **区域规则分流策略组模块（已启用）**
    * **解决的问题**：针对部分特定地区流媒体解锁或特定访问需求，需要定向使用某一区域节点，避免全局流量胡乱漂移。
    * **解决方法**：在策略组中通过名称正则表达式（`filter`，如 `(?i)港|hk`）智能过滤并组合出对应的国家/地区节点组（香港、日本、美国等），并在区域组内执行独立的优选测速。
    * **预计结果**：实现精细的按国家/地区规则分流，且能维持该区域内最优的节点性能。

---

## 3. 核心踩坑点与 Agent 约束 (Constraints & Anti-Patterns)

Mihomo (Clash Meta) 内核的 YAML 解析器极其严格，任何单个节点的格式不合法都会导致**整个订阅配置文件导入失败**。以下是已解决的致命格式问题，未来修改代码时**严禁回退**：

### ⚠️ 约束 1：未加引号的 IPv6 地址导致解析崩溃 (Unquoted IPv6)
* **现象**：Subconverter 在流格式（Flow Style，如 `{name: x, server: ::1}`）中生成的 IPv6 地址没有双引号。这会导致 `PyYAML` 的 `safe_load` 以及 Mihomo 的解析器在解析冒号（`:`）时抛出 `expected the node content, but found ':'` 崩溃。
* **开发约束**：
  * 在将 YAML 传给 `yaml.safe_load()` 之前，**必须**先用正则表达式对原始文本进行清洗，为所有未加引号的 `server` 字段强行包裹双引号：
    `content = re.sub(r'server:\s+([^\s\"\'\{][^,\}\n]*)', r'server: "\1"', content)`
  * 在 `yaml.safe_dump()` 之后，由于 PyYAML 在 Block 格式下仍可能输出未加引号的 IPv6，**必须**再次执行该正则清洗后才能写入文件。

### ⚠️ 约束 2：策略组同步清理 (Proxy-Group Synchronization)
* **现象**：如果仅从 `proxies` 列表中删除了失效或不合规的节点（例如使用正则删减行），但没有同步清理 `proxy-groups`（策略组）中对应的节点名称，Mihomo 会报错 `proxy group[0]: ♻️ 自动选择: '@Hope_Net 6' not found`。
* **开发约束**：
  * **禁止使用正则直接删除节点行**。
  * 必须使用 `PyYAML` 载入结构：遍历 `proxies`，将非法节点剔除，同时记录被删除节点的 `name`。
  * 遍历 `proxy-groups` 下 the `proxies` 数组，将记录的非法节点名称从策略组的列表中彻底移除。

### ⚠️ 约束 3：REALITY short-id 校验
* **现象**：Mihomo 要求 REALITY 的 `short-id` 必须是**偶数长度**的合法十六进制字符串，且长度不超过 16（如 `01`，`1234`，`0a1b2c3d` 等）。Subconverter 可能会导出非法的 `short-id`（如 `@FREE_VPN`，或者 `01` 在未加引号时被 PyYAML 自动解析为整数 `1` 导致长度变为了奇数）。
* **开发约束**：
  * 读取 `reality-opts -> short-id` 时，必须强制转换为字符串 `str(sid)`。
  * 验证其是否能被十六进制解析（`bytes.fromhex(sid_str)`）。
  * 确保 `len(sid_str) % 2 == 0` 且 `len(sid_str) <= 16`，否则必须丢弃该节点。

### ⚠️ 约束 4：无效与过时的 Cipher 过滤与更正
* **现象**：部分 Shadowsocks 节点中 `cipher` 字段可能被错误填充为 `ss`；部分老的节点会使用已被弃用的 `chacha20-poly1305` 加密协议。
* **开发约束**：
  * 直接丢弃 `cipher` 为 `ss` 的节点。
  * 将 `chacha20-poly1305` 自动更正为 Mihomo 支持的 `chacha20-ietf-poly1305`。

### ⚠️ 约束 5：GitHub Action 依赖限制
* **现象**：工作流运行在云端的最小化系统 `ubuntu-latest` 上，默认的 Python 环境不一定包含 `PyYAML`。
* **开发约束**：
  * 任何在 `convert.sh` 中使用的 Python 第三方库，都必须在 `.github/workflows/update.yml` 中对应的转换步骤前进行预先安装（如使用 `sudo apt-get install -y python3-yaml`）。

---

## 3. 本地开发与测试方法 (Local Verification)

为确保修改不会引发解析故障，本地开发时请务必使用 Mihomo 内核进行配置校验。
```bash
# 测试 Monolithic 配置是否能通过 Mihomo 内核解析
docker run --rm -v "$(pwd):/config" metacubex/mihomo -d /config -t -f /config/docs/config_monolithic.yaml

# 测试 Proxies 配置是否能通过 Mihomo 内核解析
docker run --rm -v "$(pwd):/config" metacubex/mihomo -d /config -t -f /config/docs/proxies.yaml
```
测试通过（输出 `configuration file test passed`）后方可提交推送。
