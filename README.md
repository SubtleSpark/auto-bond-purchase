# Auto Bond Purchase

自动新债申购工具，支持深度学习验证码识别。

## 功能

- 自动登录证券交易平台
- 深度学习模型自动识别验证码（VGG 网络）
- 批量申购新债
- 支持多账户
- 微信推送申购结果

## 快速开始

### Docker 运行（推荐）

```bash
# 拉取镜像
docker pull ghcr.io/subtlespark/auto-bond-purchase:latest

# 运行（需要挂载配置文件）
docker run --rm \
  -v /path/to/cfg.yml:/app/cfg.yml \
  ghcr.io/subtlespark/auto-bond-purchase:latest
```

### 本地运行

```bash
# 安装依赖
uv sync

# 运行
uv run python main.py
```

## 配置文件

创建 `cfg.yml` 配置文件：

```yaml
user:
  - zjzh: "你的资金账号1"
    pwd: "密码1"
  - zjzh: "你的资金账号2"
    pwd: "密码2"
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BROWSER` | `chrome` | 浏览器类型 (`chrome` 或 `edge`) |
| `HEADLESS` | `true` (Docker) / `false` (本地) | 是否使用无头模式 |

### 示例

```bash
# 使用 Edge 浏览器
BROWSER=edge python main.py

# 启用无头模式
HEADLESS=true python main.py

# Docker 中禁用无头模式（需要 X11 转发）
docker run --rm -e HEADLESS=false -v /path/to/cfg.yml:/app/cfg.yml ghcr.io/subtlespark/auto-bond-purchase:latest
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
├── cfg.yml              # 配置文件（不提交）
├── Dockerfile           # Docker 构建文件
└── pyproject.toml       # 项目依赖
```

## 依赖

- Python >= 3.9
- TensorFlow >= 2.15.0
- Selenium >= 4.6.0
- OpenCV

## 构建 Docker 镜像

```bash
# 本地构建
docker build -t auto-bond-purchase .

# 使用代理构建
docker build --network=host \
  --build-arg HTTP_PROXY=http://127.0.0.1:7890 \
  --build-arg HTTPS_PROXY=http://127.0.0.1:7890 \
  -t auto-bond-purchase .
```

## CI/CD

项目使用 GitHub Actions 自动构建 Docker 镜像：

- 推送到 `master` 分支时自动触发构建
- 镜像发布到 GitHub Container Registry (`ghcr.io`)
- 支持手动触发构建

## License

MIT
