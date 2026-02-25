# Auto Bond Purchase

基于 Playwright + 深度学习验证码识别（VGG）的东方财富自动新债申购工具。

## 功能

- 自动登录东方财富网上交易平台
- 深度学习模型自动识别验证码（VGG）
- 验证码识别失败自动刷新重试
- 批量申购新债
- 多账户批量执行
- PushPlus 推送申购结果
- 异常自动截图，支持主流程重试

## 快速开始

### 1. 本地运行

```bash
# 安装依赖
uv sync

# 安装 Playwright 浏览器
uv run playwright install --with-deps chromium

# 配置环境变量
cp .env.example .env
vi .env

# 运行
uv run python main.py
```

### 2. Docker 运行

```bash
docker run --rm \
  -e USERS="账号1:密码1,账号2:密码2" \
  -e PUSHPLUS_TOKEN="your_token" \
  -e HEADLESS=true \
  ghcr.io/subtlespark/auto-bond-purchase:latest
```

### 3. GitHub Actions 定时运行

1. 在仓库 Settings → Secrets → Actions 添加：
   - `USERS`: `账号1:密码1,账号2:密码2`
   - `PUSHPLUS_TOKEN`: pushplus 推送 token
2. 默认每个交易日北京时间 9:30、13:30 自动运行
3. 可在 Actions 页面手动触发

## 配置

所有配置通过环境变量管理，本地开发可使用 `.env` 文件。

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `USERS` | 是 | - | 用户列表，格式: `账号1:密码1,账号2:密码2` |
| `PUSHPLUS_TOKEN` | 否 | - | PushPlus 推送 token |
| `BROWSER` | 否 | `chromium` | 浏览器类型: `chromium` / `chrome` / `edge` |
| `HEADLESS` | 否 | `false` | 是否无头模式 |
| `CAPTCHA_RETRIES` | 否 | `3` | 验证码最大重试次数 |
| `FLOW_RETRIES` | 否 | `2` | 主流程最大重试次数 |
| `TIMEOUT_MS` | 否 | `30000` | 页面操作超时时间（毫秒） |
| `SCREENSHOT_DIR` | 否 | `artifacts/screenshots` | 异常截图目录 |

## 项目结构

```text
auto-bond-purchase/
├── autobond/
│   ├── config.py        # 环境变量与配置解析
│   ├── notifier.py      # PushPlus 推送
│   ├── purchaser.py     # Playwright 申购主流程
│   └── runner.py        # 多账户运行入口
├── captcha/             # 验证码识别模块
├── models/              # VGG 模型文件（Git LFS）
├── .github/workflows/   # 定时运行与镜像构建
├── Dockerfile
└── main.py
```

## 免责声明

- 本项目仅供学习和个人使用，不构成任何投资建议。
- 使用本工具产生的一切后果由使用者自行承担。
- 请遵守相关法律法规及券商用户协议。

## License

MIT
