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
            print(f"推送成功: {result.get('data')}")
        else:
            print(f"推送失败: [{result.get('code')}] {result.get('msg')}")
    except Exception as exc:
        print(f"推送异常: {exc}")
