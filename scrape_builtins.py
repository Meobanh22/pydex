import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from dotenv import load_dotenv
from groq import Groq

DOCS_URL = "https://docs.python.org/3/library/functions.html"


load_dotenv(override=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def summarize_description(name, description):
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        max_tokens=300,
        reasoning_effort="low",
        messages=[{
            "role": "user",
            "content": (
                f"Summarize the purpose of the Python function `{name}()` in EXACTLY 1 sentence. "
                f"Do not use markdown, bold text, bullet points, or headers. "
                f"Return plain text only, no formatting.\n\n"
                f"Original description: {description}"
            )
        }]
    )
    return response.choices[0].message.content.strip()

def clean_text(text):
    text = text.replace("¶","")
    text = text.replace("\n","")
    text = re.sub(r"\s+"," ",text)
    return text.strip()
def extra_params(sig):
    sig = clean_text(sig)
    if "(" not in sig or ")" not in sig:
        return []
    sig = sig[sig.index("(")+1:sig.rindex(")")]
    parts = [p.strip() for p in sig.split(",")]
    params = []
    for i,p in enumerate(parts,1):
        if p in ("/","*","**",""):
            continue
        else:
            params.append({"name": p,"order_index": i})
    return params
def get_id(dl):
    if dl.get("id"):
        return dl["id"]
    dt=dl.find("dt")
    if dt and dt.get("id"):
        return dt["id"]
    return None
def fetch_bultin_docs():
    resp = requests.get(DOCS_URL)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "html.parser")
    blocks =soup.select("dl.py")
    result = []

    for dl in blocks:
        func_id = get_id(dl)
        if not func_id:
            continue

        dt=dl.find("dt")
        dd=dl.find("dd")
        params = extra_params(dt.get_text(" ",strip=True)) if dt else []
        description = clean_text(dd.get_text(" ",strip=True)) if dd else ""
        try:
            description = summarize_description(func_id, description)
        except Exception as e:
            print(f"{func_id}: {e}")
        time.sleep(1)

        result.append({
            "name": func_id,
            "params": params,
            "description": description
        })
    return result

if __name__ == "__main__":
    docs = fetch_bultin_docs()
    print(f"l{len(docs)}")

    with open("builtin.json","w",encoding="utf-8") as f:
        json.dump(docs,f,ensure_ascii=False,indent=2)
    print("Done")

