import re
import os

from dotenv import load_dotenv
from typing import Self
import requests
import ddgs
from bs4 import BeautifulSoup

load_dotenv()

PROVIDERS = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "key_env": None,
        "model": "qwen3:8b",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "model": "gemini-2.5-flash",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
    },
}


UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) mini-search-llm/1.0"}


class MiniLLM:
    _instance = None
    cfg: dict

    SYSTEM_PROMPT = """You are a helpful assistant with web access. Today's date is {date}.
    
    To use a tool, reply with exactly ONE line and nothing else:
    SEARCH: <search query>
    FETCH: <url>
    
    When you have enough information, reply with:
    ANSWER: <your answer>
    
    Rules:
    - Search for anything current, recent, or that you are not sure about.
    - Search snippets are short; FETCH the most promising page when details matter.
    - In your ANSWER, mention the source URLs you used.
    - If the question needs no web info (chit-chat, math, general knowledge), answer directly."""

    ACTION_RE = re.compile(r"^\s*(SEARCH|FETCH|ANSWER):\s*(.*)", re.S | re.M)

    def __new__(cls, cfg={}) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.cfg = cfg
        return cls._instance

    def chat(self, messages, temperature=0.2):
        headers = {"Content-Type": "application/json"}
        if self.cfg["api_key"]:
            headers["Authorization"] = f"Bearer {self.cfg['api_key']}"
        r = requests.post(
            self.cfg["base_url"].rstrip("/") + "/chat/completions",
            headers=headers,
            json={
                "model": self.cfg["model"],
                "messages": messages,
                "temperature": temperature,
            },
            timeout=300,
        )
        if r.status_code != 200:
            raise RuntimeError(f"API error {r.status_code}: {r.text[:500]}")
        content = r.json()["choices"][0]["message"].get("content") or ""
        # Reasoning models (qwen3, deepseek-r1...) may include <think> blocks
        return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()

    def web_search(self, query, n=5):
        try:
            results = list(ddgs.DDGS().text(query, max_results=n))
        except Exception as e:
            return f"Search failed: {e}"
        if not results:
            return "No results."
        return "\n\n".join(
            f"[{i}] {r.get('title', '')}\nURL: {r.get('href', '')}\n{r.get('body', '')}"
            for i, r in enumerate(results, 1)
        )

    def fetch_page(self, url, max_chars=6000):
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
        except Exception as e:
            return f"Fetch failed: {e}"
        ctype = r.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype:
            return f"Cannot read this content type ({ctype}). Try another page."
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(
            ["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]
        ):
            tag.decompose()
        text = re.sub(r"\n\s*\n+", "\n\n", soup.get_text("\n")).strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"
        return text or "Page had no readable text."

    def run_turn(self, history, user_msg, max_steps=6, verbose=True):
        history.append({"role": "user", "content": user_msg})
        work = list(history)  # scratch copy; tool dumps don't pollute long-term history

        answer = None
        for _ in range(max_steps):
            reply = self.chat(work)
            m = self.ACTION_RE.search(reply)
            if not m:  # model answered without the protocol
                answer = reply
                break
            action, arg = m.group(1), m.group(2).strip()
            if action == "ANSWER":
                answer = arg
                break
            arg = arg.splitlines()[0].strip() if arg else ""
            if verbose:
                print(f"  [{action.lower()}] {arg}")
            result = (
                self.web_search(arg) if action == "SEARCH" else self.fetch_page(arg)
            )
            work.append({"role": "assistant", "content": reply})
            work.append(
                {
                    "role": "user",
                    "content": f"Tool result for {action} {arg}:\n\n{result}\n\n"
                    "Continue: use another tool, or give your ANSWER.",
                }
            )

        if answer is None:
            work.append(
                {
                    "role": "user",
                    "content": "Step limit reached. Give your best ANSWER now.",
                }
            )
            answer = re.sub(r"^\s*ANSWER:\s*", "", self.chat(work))

        history.append({"role": "assistant", "content": answer})
        # keep system prompt + last 10 messages so context stays small
        if len(history) > 11:
            del history[1:-10]
        return answer
