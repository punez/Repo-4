import asyncio
import aiohttp
import base64
import json
from urllib.parse import urlparse

TIMEOUT = 3
CONCURRENCY = 100
MAX_PER_SOURCE = 20000

async def fetch(session, url):
    try:
        async with session.get(url, timeout=20) as resp:
            return await resp.text()
    except:
        return ""

def safe_b64_decode(data):
    try:
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return base64.b64decode(data).decode("utf-8")
    except:
        return None

def try_base64_decode(text):
    decoded = safe_b64_decode(text.strip())
    if decoded and "://" in decoded:
        return decoded
    return text

def extract_links(text):
    lines = text.splitlines()
    results = []
    for line in lines:
        line = line.strip()
        if "://" in line:
            results.append(line)
    return results

def parse_host_port(link):
    try:
        if link.startswith("vmess://"):
            raw = link.replace("vmess://", "")
            decoded = safe_b64_decode(raw)
            if not decoded:
                return None, None
            data = json.loads(decoded)
            return data.get("add"), data.get("port")

        if link.startswith("ss://"):
            raw = link.replace("ss://", "").split("#")[0]
            decoded = safe_b64_decode(raw.split("@")[0])
            if decoded and ":" in decoded:
                host_port = raw.split("@")[-1]
                host = host_port.split(":")[0]
                port = host_port.split(":")[1]
                return host, port

        parsed = urlparse(link)
        return parsed.hostname, parsed.port
    except:
        return None, None

async def tcp_check(host, port):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)),
            timeout=TIMEOUT
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

async def main():
    sources = open("inputs.txt").read().splitlines()
    all_links = set()

    async with aiohttp.ClientSession() as session:
        for url in sources:
            text = await fetch(session, url)
            if not text:
                continue

            text = try_base64_decode(text)
            links = extract_links(text)

            for link in links[:MAX_PER_SOURCE]:
                all_links.add(link.strip())

    sem = asyncio.Semaphore(CONCURRENCY)
    healthy = []

    async def check(link):
        async with sem:
            host, port = parse_host_port(link)
            if host and port:
                ok = await tcp_check(host, port)
                if ok:
                    healthy.append(link)

    await asyncio.gather(*(check(link) for link in all_links))

    with open("healthy.txt", "w") as f:
        f.write("\n".join(healthy))

asyncio.run(main())
