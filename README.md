# Auto Bond Purchase

自动新债申购工具，支持深度学习验证码识别。

## 功能

- 自动登录证券交易平台
- 深度学习模型自动识别验证码（VGG 网络）
- 识别失败自动刷新重试（最多 3 次）
- 批量申购新债
- 支持多账户
- 微信推送申购结果

## 快速开始

### 1. 本地运行

```bash
# 安装依赖
uv sync

# 编辑 .env 文件配置账号
cp .env.example .env
vi .env

# 运行
uv run python main.py
```

### 2. Docker 运行

```bash
# 拉取镜像
docker pull ghcr.io/subtlespark/auto-bond-purchase:latest

# 运行
docker run --rm \
  -e USERS="账号1:密码1,账号2:密码2" \
  -e WECHAT_TOKEN="your_token" \
  -e HEADLESS=true \
  ghcr.io/subtlespark/auto-bond-purchase:latest
```

### 3. GitHub Actions 定时运行

项目支持通过 GitHub Actions 定时自动执行，无需自建服务器。

1. 在仓库 Settings → Secrets → Actions 添加：
   - `USERS`: `账号1:密码1,账号2:密码2`
   - `PUSHPLUS_TOKEN`: pushplus 推送 token（[获取地址](https://www.pushplus.plus)）
2. 默认每个交易日北京时间 9:30 自动运行
3. 也可在 Actions 页面手动触发

## 配置

所有配置通过**环境变量**管理，本地开发可使用 `.env` 文件。

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `USERS` | 是 | - | 用户列表，格式: `账号1:密码1,账号2:密码2` |
| `PUSHPLUS_TOKEN` | 否 | - | [pushplus](https://www.pushplus.plus) 推送 token，不设置则不推送 |
| `BROWSER` | 否 | `chrome` | 浏览器类型 (`chrome` 或 `edge`) |
| `HEADLESS` | 否 | `false` | 是否使用无头模式 |

### .env 文件示例

```env
USERS=账号1:密码1,账号2:密码2
PUSHPLUS_TOKEN=your_token
# BROWSER=chrome
# HEADLESS=true
```

## 项目结构

```
auto_bond_purchase/
├── main.py              # 主程序
├── captcha/             # 验证码识别模块
│   ├── recognizer.py    # 识别器
│   ├── image_process.py # 图像预处理
│   ├── label_process.py # 标签解码
│   └── model_utils.py   # 模型工具
├── models/
│   └── VGG.keras        # 预训练模型 (Git LFS)
├── .env                 # 本地配置（不提交）
├── Dockerfile           # Docker 构建文件
└── pyproject.toml       # 项目依赖
```

## 依赖

- Python >= 3.9
- TensorFlow >= 2.15.0
- Selenium >= 4.6.0
- OpenCV
- python-dotenv

## 构建 Docker 镜像

```bash
docker build -t auto-bond-purchase .
```

## CI/CD

项目使用 GitHub Actions：

- **自动构建镜像**: 推送到 `master` 分支时自动构建，发布到 `ghcr.io`
- **定时运行**: 每个交易日北京时间 9:30 自动执行申购

## License

MIT