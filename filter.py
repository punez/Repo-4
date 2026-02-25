import asyncio
import aiohttp
import base64
import json
import yaml
import re

TIMEOUT = 5
CONCURRENCY = 100
MAX_OUTPUT = 800

def try_base64_decode(text):
    try:
        decoded = base64.b64decode(text).decode()
        if "://" in decoded:
            return decoded
    except:
        pass
    return text

def extract_from_yaml(text):
    links = []
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict) and "proxies" in data:
            for p in data["proxies"]:
                if "server" in p and "port" in p:
                    links.append(f"{p.get('type','unknown')}://{p['server']}:{p['port']}")
    except:
        pass
    return links

def extract_from_json(text):
    links = []
    try:
        data = json.loads(text)
        if "outbounds" in data:
            for o in data["outbounds"]:
                if "server" in o and "server_port" in o:
                    links.append(f"{o.get('type','unknown')}://{o['server']}:{o['server_port']}")
    except:
        pass
    return links

def extract_host_port(link):
    try:
        if "@" in link:
            body = link.split("@")[1]
        else:
            body = link.split("://")[1]
        host_port = re.split(r"[/?#]", body)[0]
        host, port = host_port.split(":")
        return host, int(port)
    except:
        return None, None

async def tcp_check(host, port):
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=TIMEOUT
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

async def main():
    sources = open("subs.txt").read().splitlines()
    links = set()

    async with aiohttp.ClientSession() as session:
        for url in sources:
            try:
                async with session.get(url, timeout=15) as resp:
                    text = await resp.text()
                    text = try_base64_decode(text)

                    if "://" in text:
                        for line in text.splitlines():
                            if "://" in line:
                                links.add(line.strip())

                    links.update(extract_from_yaml(text))
                    links.update(extract_from_json(text))
            except:
                pass

    sem = asyncio.Semaphore(CONCURRENCY)
    healthy = []

    async def check(link):
        async with sem:
            host, port = extract_host_port(link)
            if host and port:
                if await tcp_check(host, port):
                    healthy.append(link)

    await asyncio.gather(*(check(l) for l in links))

    healthy = healthy[:MAX_OUTPUT]

    with open("healthy.txt", "w") as f:
        f.write("\n".join(healthy))

asyncio.run(main())
