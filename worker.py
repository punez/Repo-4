import asyncio
import aiohttp
import base64
import time

TIMEOUT = 3
CONCURRENCY = 100
MAX_PER_SOURCE = 20000

async def fetch(session, url):
    try:
        async with session.get(url, timeout=20) as resp:
            return await resp.text()
    except:
        return ""

def try_base64_decode(text):
    try:
        decoded = base64.b64decode(text.strip()).decode("utf-8")
        if "://" in decoded:
            return decoded
        return text
    except:
        return text

def extract_links(text):
    lines = text.splitlines()
    results = []
    for line in lines:
        line = line.strip()
        if "://" in line:
            results.append(line)
    return results

async def tcp_check(host, port):
    try:
        start = time.time()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)),
            timeout=TIMEOUT
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def parse_host_port(link):
    try:
        after_scheme = link.split("://",1)[1]
        host_part = after_scheme.split("@")[-1]
        host = host_part.split(":")[0]
        port = host_part.split(":")[1].split("?")[0]
        return host, port
    except:
        return None, None

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
