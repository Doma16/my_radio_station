#!/usr/bin/env python3
"""
mini_search_llm.py - a tiny chat assistant that can search the web and read pages.

One script, two ways to run the "brain":
  * LOCAL  : Ollama on your own machine (completely free, offline model)
  * REMOTE : free-tier APIs (Groq, Google Gemini, OpenRouter ":free" models)

All of them speak the same OpenAI-compatible /chat/completions format,
so the script only needs `requests`. Web search uses DuckDuckGo (no API key).

Install:
    pip install requests beautifulsoup4 ddgs

Local:
    # install Ollama from https://ollama.com, then:
    ollama pull qwen3:8b
    python mini_search_llm.py --provider ollama

Remote (pick one, get a free key from the provider's website):
    export GROQ_API_KEY=...        && python mini_search_llm.py --provider groq
    export GEMINI_API_KEY=...      && python mini_search_llm.py --provider gemini
    export OPENROUTER_API_KEY=...  && python mini_search_llm.py --provider openrouter

One-shot question instead of chat:
    python mini_search_llm.py --provider groq -q "What's new in Python this year?"

Model names change over time - override with --model if a default stops working.
"""

import argparse
import datetime
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS  # current package name
except ImportError:
    from duckduckgo_search import DDGS  # older package name

# --------------------------------------------------------------------------
# Providers (all OpenAI-compatible)
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# LLM call
# --------------------------------------------------------------------------
def chat(cfg, messages, temperature=0.2):
    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    r = requests.post(
        cfg["base_url"].rstrip("/") + "/chat/completions",
        headers=headers,
        json={"model": cfg["model"], "messages": messages, "temperature": temperature},
        timeout=300,
    )
    if r.status_code != 200:
        raise RuntimeError(f"API error {r.status_code}: {r.text[:500]}")
    content = r.json()["choices"][0]["message"].get("content") or ""
    # Reasoning models (qwen3, deepseek-r1...) may include <think> blocks
    return re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()


# --------------------------------------------------------------------------
# Browsing tools
# --------------------------------------------------------------------------
def web_search(query, n=5):
    try:
        results = list(DDGS().text(query, max_results=n))
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results."
    return "\n\n".join(
        f"[{i}] {r.get('title', '')}\nURL: {r.get('href', '')}\n{r.get('body', '')}"
        for i, r in enumerate(results, 1)
    )


def fetch_page(url, max_chars=6000):
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


# --------------------------------------------------------------------------
# Agent loop (plain-text protocol: works even with models lacking tool-calling)
# --------------------------------------------------------------------------
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


def run_turn(cfg, history, user_msg, max_steps=6, verbose=True):
    history.append({"role": "user", "content": user_msg})
    work = list(history)  # scratch copy; tool dumps don't pollute long-term history

    answer = None
    for _ in range(max_steps):
        reply = chat(cfg, work)
        m = ACTION_RE.search(reply)
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
        result = web_search(arg) if action == "SEARCH" else fetch_page(arg)
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
        answer = re.sub(r"^\s*ANSWER:\s*", "", chat(cfg, work))

    history.append({"role": "assistant", "content": answer})
    # keep system prompt + last 10 messages so context stays small
    if len(history) > 11:
        del history[1:-10]
    return answer


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Tiny web-browsing LLM assistant")
    p.add_argument("--provider", choices=PROVIDERS, default="ollama")
    p.add_argument("--model", help="override the default model name")
    p.add_argument("--base-url", help="override the API base URL")
    p.add_argument("--api-key", help="API key (otherwise read from env var)")
    p.add_argument("--steps", type=int, default=6, help="max tool steps per question")
    p.add_argument("-q", "--question", help="ask one question and exit")
    p.add_argument("--quiet", action="store_true", help="hide tool activity")
    args = p.parse_args()

    prov = PROVIDERS[args.provider]
    api_key = args.api_key or (os.getenv(prov["key_env"]) if prov["key_env"] else None)
    if prov["key_env"] and not api_key:
        sys.exit(
            f"Set {prov['key_env']} or pass --api-key for provider '{args.provider}'."
        )

    cfg = {
        "base_url": args.base_url or prov["base_url"],
        "model": args.model or prov["model"],
        "api_key": api_key,
    }
    system = {
        "role": "system",
        "content": SYSTEM_PROMPT.format(date=datetime.date.today().isoformat()),
    }
    history = [system]

    def ask(q):
        try:
            print("\n" + run_turn(cfg, history, q, args.steps, not args.quiet) + "\n")
        except Exception as e:
            print(f"\nError: {e}\n")

    if args.question:
        ask(args.question)
        return

    print(f"Using {args.provider} / {cfg['model']}. Commands: /reset, /quit")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in ("/quit", "/exit"):
            break
        if q == "/reset":
            history[:] = [system]
            print("History cleared.")
            continue
        ask(q)


if __name__ == "__main__":
    main()
