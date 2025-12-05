import httpx
from app.settings import get_settings

settings = get_settings()


async def summarize(content: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个专业的邮件总结助手。请用简洁中文总结邮件核心内容，突出重要信息和行动项，不超过80字。"},
            {"role": "user", "content": f"请总结以下邮件内容，提取关键信息：\n\n{content}"},
        ],
        "temperature": 0.3,
        "max_tokens": 250,
    }
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"].strip()


async def select_top5(formatted_messages: list[str]) -> list[str]:
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    combined = "\n\n".join(formatted_messages)
    user_prompt = (
        "下面是过去24小时的邮件，请挑选信息价值最高的5封，只输出它们的主题，按重要度从高到低，每行一个主题。\n\n"
        + combined
    )
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是邮件筛选助手，只返回主题行，不添加其他描述。"},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
        resp.raise_for_status()
        result = resp.json()
        text = result["choices"][0]["message"]["content"].strip()
        lines = [line.strip("- ") for line in text.splitlines() if line.strip()]
        return lines[:5]
