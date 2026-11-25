# 《全球科技产业观察》云端全自动部署指南

本方案使用 **GitHub Actions（免费定时） + Python 抓取（0 token） + Gemini API 单次成稿（极低成本） + GitHub Pages（免费 HTTPS 网页） + Gmail 自动推送**。

## 一、5 分钟完成部署

### 第 1 步：创建 GitHub 仓库并上传代码
1. 登录 GitHub，新建一个仓库（例如 `global-tech-brief`，推荐设为 Public 以免费使用 GitHub Pages；若为 Pro 账号也可 Private）。
2. 把本压缩包解压后的所有文件（注意包含隐藏目录 `.github/workflows/daily-brief.yml`）上传到仓库根目录。

### 第 2 步：开启 GitHub Pages（自动生成公开网页网址）
1. 进入仓库 **Settings → Pages**。
2. **Source** 选 `Deploy from a branch`。
3. **Branch** 选 `main`，文件夹选 `/docs`，点击 **Save**。
4. 你的固定网址格式为：`https://<你的GitHub用户名>.github.io/<仓库名>`。

### 第 3 步：获取 Gmail 应用专用密码（App Password）
1. 打开 Google 账号安全设置：https://myaccount.google.com/apppasswords
2. 先确保已开启“两步验证”，然后创建一个名为 `GitHub Actions` 的应用专用密码，复制生成的 16 位密码。

### 第 4 步：配置 4 个 Repository Secrets
进入仓库 **Settings → Secrets and variables → Actions → New repository secret**，依次添加：
* `GEMINI_API_KEY`：你的 Google AI Studio API Key（https://aistudio.google.com/apikey）
* `GMAIL_USER`：用于发信的 Gmail 邮箱地址（例如 `you@gmail.com`）
* `GMAIL_APP_PASSWORD`：第 3 步生成的 16 位应用专用密码（去掉空格）
* `SITE_BASE_URL`：第 2 步生成的 GitHub Pages 网址（例如 `https://yourname.github.io/global-tech-brief`，末尾不加 `/`）
* *(可选)* `GMAIL_TO`：收件邮箱；不填则默认发给 `GMAIL_USER` 自己。

### 第 5 步：手动试跑一次
1. 进入仓库顶部的 **Actions** 标签页，点击左侧 **Daily Global Tech Brief**。
2. 点击右侧 **Run workflow** 按钮，等待约 1–2 分钟即可在 Gmail 收到第一封带微信纯文本、公开网址和单文件 HTML 附件的邮件。

## 二、定时说明与排错
* 默认每天 **北京时间 07:23**（UTC 23:23）自动触发，周一自动回溯 72 小时覆盖周末，其余日期回溯 24 小时。
* 如果某天部分站点抓不到满 5 条，脚本会按规范**保留原首页不被覆盖**，把内部核验稿发到你邮箱并在邮件底部注明缺口站点。核验稿仅作为邮件附件发送，不生成公开链接。
