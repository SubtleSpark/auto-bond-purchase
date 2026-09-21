import requests


def send_pushplus(message: str, title: str, token: str) -> None:
    print(message)
    if not token:
        return

    try:
        response = requests.post(
            "https://www.pushplus.plus/send",
            json={
                "token": token,
                "title": title,
                "content": message,
                "template": "txt",
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        result = response.json()
        if result.get("code") == 200:
            print("推送成功")
        else:
            print(f"推送失败: code={result.get('code')}")
    except Exception as exc:
        print(f"推送异常: {type(exc).__name__}")
