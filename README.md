# V2Ray to Mihomo/Clash Converter 🚀

这是一个高度自动化的 GitHub 仓库模板，旨在通过 **GitHub Actions** 和 **Docker版 Subconverter**，将 V2Ray/Sing-Box 订阅源全自动转换为适用于 Mihomo (Clash Meta) 及 FlClash 的高级配置文件。

## 🌟 项目亮点

*   **完全自动化**：无需自行搭建后端，全程由 GitHub Actions 定时执行。
*   **双模式支持**：
    *   **Proxy-Provider 模式**：极速加载，生成专门的节点集合文件，即使上千节点也毫无压力。
    *   **Monolithic 模式**：单文件配置，方便基础客户端使用。
*   **内置 Loyalsoldier 规则集**：完美支持去广告、流媒体解锁、国内直连和全局路由。
*   **零代码修改**：通过 GitHub 环境自动注入域名，Fork 后只需修改 `config/source.txt` 即可运行！

## ⚙️ 工作原理

```mermaid
graph TD;
    A[V2Ray/Sing-Box 订阅源] -->|定期拉取| B(GitHub Actions);
    B -->|自动转换 + 净化| C(节点池 + 配置文件);
    C --> F[GitHub Pages 发布];
    F -->|直连导入| G[FlClash / Mihomo / OpenClash];
```

## 🚀 快速开始

### 1. Fork 本仓库
点击页面右上角的 `Fork` 按钮，将本仓库复制到你的账户下。

### 2. 修改订阅源
编辑 `config/source.txt`，将其中的默认链接替换为你自己的机场订阅链接（支持填写多行，会自动合并）。

### 3. 启用 GitHub Actions
*   进入你 Fork 后的仓库，点击顶部标签页的 **Actions**。
*   点击 **"I understand my workflows, go ahead and enable them"**。
*   在左侧选中 **Update Proxy Configuration**，点击右侧的 **Run workflow** 即可手动运行一次，进行初始转换。

### 4. 启用 GitHub Pages
*   点击顶部标签页的 **Settings** -> **Pages**。
*   在 **Build and deployment** 下的 **Source**，选择 **GitHub Actions**（如果不可选，请确保上一步已成功运行一次）。
*   注意：部署需要一点时间。完成之后，即可获得你的订阅链接。

---

## 🔗 获取订阅链接

你的专属配置链接格式如下（请将 `<username>` 和 `<repo>` 替换为你的 GitHub 用户名和仓库名）：

**推荐（Proxy-Provider 极速模式）：**
`https://<username>.github.io/<repo>/config.yaml`

**备选（传统单文件模式）：**
`https://<username>.github.io/<repo>/config_monolithic.yaml`

---

## 📱 客户端导入步骤

### FlClash / Mihomo / Clash Verge Rev
1. 打开客户端，进入 **配置 / Profiles** 页面。
2. 点击 **新建 / 导入**，选择 **URL导入**。
3. 填入你的 `config.yaml` 链接，并点击保存/下载。
4. 切换到此配置，进入 **代理 / Proxies** 页面，点击左上角的“测速”图标。
5. 在 `🚀 节点选择` 中选择 `♻️ 自动选择` 或你心仪的节点。

### OpenClash
1. 进入 OpenClash 控制面板，在 **配置订阅** 中新增。
2. 粘贴上述 `config.yaml` 链接。
3. 关闭“自动更新配置”（建议通过 GitHub Actions 处理更新，无需路由器承担）。
4. 保存配置并启动。

---

## 🌐 节点地区识别与智能分组

导入配置后，你会在客户端里看到：

- **节点名称自动带地区前缀**：如 `[HK] 香港节点`、`[JP] 日本节点`、`[US] 美国节点`，从名称就能知道节点物理位置。
- **策略组按地区自动归类**：客户端中自动生成对应的地区策略组（如 🇭🇰 香港节点、🇩🇪 德国节点）。
- **节点多的地区独立分组，少的自动合并**：节点数达到一定数量的地区会独立成组；节点稀少的地区会自动归入「🌍 其他地区」，避免策略组列表过长。
- **自动生成过滤报告**：每次构建后可在 `docs/filter_report.md` 查看节点数量、存活率、地区分布等统计。

---

## 🛠 高级设置与进阶

### 更新频率说明
默认的更新频率为 **每 1 小时** 执行一次。
如需调整，请编辑 `.github/workflows/update.yml` 中的 `cron: '0 * * * *'`。

### 自定义配置
所有可编辑的配置文件都在 `config/` 目录下：
- **`config_template.yaml`**：Proxy-Provider 模式的策略组、规则、DNS 设定
- **`flclash.ini`**：Monolithic 单文件模式的策略组与规则集
- **`source.txt`**：订阅源链接列表

### 常见问题

**Q: Actions 执行失败？**
A: 点击 Actions → 失败任务 → "Re-run all jobs" 重试即可。

**Q: 客户端无法获取节点？**
A: 确保 GitHub Pages 已开启，浏览器直接访问你的 `.yaml` 链接应能正常显示内容。

## 🙏 致谢

默认订阅源来自 [ShatakVPN/ConfigForge-V2Ray](https://github.com/ShatakVPN/ConfigForge-V2Ray)，感谢作者提供的优质节点聚合。

## 🤖 AI 生成声明

本项目完全由 AI（opencode + DeepSeek V4 Flash）生成，仅作为 AI 相关技术的学习和实践用途。

## 📜 License
GNU General Public License v3.0. 欢迎随时提交 PR 与建议！
