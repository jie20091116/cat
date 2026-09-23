# coding=utf-8
import os
import logging
import sys
import asyncio
import aiohttp

BASE_URL = "http://api.hclyz.com:81/mf"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "lib"))
M3U_FILE = os.path.join(TARGET_DIR, "sbjh.m3u")

HEADERS = {"User-Agent": "Mozilla/5.0"}

MAX_WORKERS = 5

def setup_logging():
    logger = logging.getLogger("ScraperLogger")
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)
    
    return logger

log = setup_logging()

async def safeGetJson(url, session, maxRetries=3, retryDelay=2):
    for attemptCount in range(maxRetries):
        try:
            # Set 10 seconds timeout to prevent freezing
            async with session.get(url, headers=HEADERS, timeout=10) as responseObj:
                if responseObj.status == 200:
                    return await responseObj.json(content_type=None)
                
                # Log non-200 status codes like 412
                log.warning(f"HTTP {responseObj.status} for {url}. Attempt {attemptCount + 1} of {maxRetries}")
        except Exception as e:
            log.error(f"Request Exception: {url} -> {e}. Attempt {attemptCount + 1} of {maxRetries}")
        
        # Wait before the next retry
        if attemptCount < maxRetries - 1:
            await asyncio.sleep(retryDelay)
            
    return None

async def processPlatform(item, session, sem):
    async with sem:
        roomTitle = item.get("title", "").strip()
        number = item.get("Number", "")
        address = item.get("address", "")
        
        xinImg = item.get("xinimg", "")
        platformLogo = xinImg.replace("clun.top", "cdn.gcufbd.top")

        log.info(f"📺 Fetching Platform: {roomTitle} (Resource count: {number})")

        detail = await safeGetJson(f"{BASE_URL}/{address}", session)
        if not detail:
            return roomTitle, [], 1

        zhubo = detail.get("zhubo", [])
        if not zhubo:
            return roomTitle, [], 1

        groupName = f"{roomTitle}"
        results = []
        errors = 0

        for vod in zhubo:
            name = vod.get("title", "").strip()
            url = vod.get("address", "").strip()

            if not url:
                errors += 1
                continue

            results.append((groupName, name, url, platformLogo))

        return roomTitle, results, errors

async def mainAsync():
    totalError = 0
    totalSuccess = 0

    log.info("🚀 Enhanced task initiated.")
    
    # Increase limit_per_host to prevent DNS resolution issues
    connector = aiohttp.TCPConnector(limit=MAX_WORKERS, limit_per_host=10)
    async with aiohttp.ClientSession(connector=connector) as session:

        home = await safeGetJson(f"{BASE_URL}/json.txt", session)
        if not home:
            log.error("❌ Retrieval failed, collection terminated.")
            sys.exit(1)

        # Retrieve platform list and remove the first element
        data = home.get("pingtai", [])[1:]

        m3uLines = ["#EXTM3U x-tvg-url=\"\""]
        seenUrls = set()

        log.info(f"⚡ Found {len(data)} platforms in total.")

        sem = asyncio.Semaphore(MAX_WORKERS)

        tasks = [processPlatform(item, session, sem) for item in data]
        results = await asyncio.gather(*tasks)

        for roomTitle, res, errors in results:
            totalError += errors
            
            for groupName, name, url, logo in res:
                if url in seenUrls:
                    continue

                seenUrls.add(url)
                # Generate M3U tag with Logo
                m3uLines.append(f'#EXTINF:-1 tvg-logo="{logo}" group-title="{groupName}",{name}')
                m3uLines.append(url)
                totalSuccess += 1

    try:
        os.makedirs(os.path.dirname(M3U_FILE), exist_ok=True)
        
        with open(M3U_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(m3uLines))
        log.info(f"📄 Generation successful. Total Streams: {totalSuccess}")
    except Exception as e:
        log.error(f"❌ Failed to write to file: {e}")
        sys.exit(1)

    summaryMsg = f"Collection completed, valid: {totalSuccess}, Abnormal: {totalError}"
    print(f"::notice title=📁 Save path: {M3U_FILE}::{summaryMsg}")

def main():
    asyncio.run(mainAsync())

if __name__ == "__main__":
    main()
