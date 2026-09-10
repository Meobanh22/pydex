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
    sig = re.sub(r"(\*+)\s+", r"\1", sig)
    if "(" not in sig or ")" not in sig:
        return []
    sig = sig[sig.index("(")+1:sig.rindex(")")]
    parts = [p.strip() for p in sig.split(",")]
    params = []
    idx = 1
    for p in parts:
        if p in ("/","*","**",""):
            continue
        required=True
        if p.startswith("[") and p.endswith("]"):
            p = p[1:-1].strip()
            required = False
        elif "=" in p:
            name, default = p.split('=',1)
            name = name.strip()
            default = default.strip().strip("'\"")
            required = False
        else:
            name = p
            default = None
        params.append({"name": name,"default_value": default,"required": required,"order_index": idx})
        idx+=1
    return params
def get_id(dl):
    dt=dl.find("dt")
    if dt:
        sig_name = dt.find(class_="sig-name")
        if sig_name:
            return sig_name.get_text(strip=True)
        if dt.get("id"):
            return dt["id"]
    if dl.get("id") and not dl["id"].startswith("index-"):
        return dl["id"]
    return None

def clean_name(name):
    if name.startswith("func-"):
        return name[len("func-"):]
    return name

def fetch_bultin_docs():
    resp = requests.get(DOCS_URL)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, "html.parser")
    blocks = soup.select("dl.py")
    result = []

    for dl in blocks:
        func_id = get_id(dl)
        if not func_id:
            continue
        func_id = clean_name(func_id)

        all_dts = dl.find_all("dt")
        signatures = []
        for dt in all_dts:
            sig_text = dt.get_text(" ", strip=True)
            if "(" in sig_text and ")" in sig_text:
                params=extra_params(sig_text)
                params_str = ", ".join(f"{p['name']}={p['default_value']}" if p['default_value'] else p['name'] for p in params)
                raw_sig = f"{func_id}({params_str})"
                signatures.append({
                    "raw_signature": raw_sig,
                    "params": params
                })
        if not signatures:
            signatures.append({
                "raw_signature": f"{func_id}()",
                "params": []
            })
        dd = dl.find("dd")
        description = clean_text(dd.get_text(" ",strip=True)) if dd else ""
        
        try:
            description = summarize_description(func_id, description)
        except Exception as e:
            print(f"{func_id}: {e}")
        time.sleep(1)

        result.append({
            "name": func_id,
            "signatures": signatures,
            "description": description
        })
    return result

if __name__ == "__main__":
    docs = fetch_bultin_docs()
    print(f"l{len(docs)}")

    with open("builtin.json","w",encoding="utf-8") as f:
        json.dump(docs,f,ensure_ascii=False,indent=2)
    print("Done")

