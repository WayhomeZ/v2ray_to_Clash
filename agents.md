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

## 2. 核心踩坑点与 Agent 约束 (Constraints & Anti-Patterns)

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
  * 遍历 `proxy-groups` 下的 `proxies` 数组，将记录的非法节点名称从策略组的列表中彻底移除。

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
