import asyncio
import aiohttp
import re
from playwright.async_api import async_playwright

async def fetch_m3u8(session: aiohttp.ClientSession, name: str, link: str):
    """
    使用 aiohttp 高并发拉取单个直播间源码，并使用正则嗅探底层 .m3u8 流媒体链接
    优化逻辑：保持底层并发稳定，避免 GitHub Actions 中 OOM
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with session.get(link, headers=headers, timeout=120) as response:
            if response.status == 200:
                text = await response.text()
                match = re.search(r'(https?:[\\/]+[^"\'\s]+\.m3u8[^"\'\s]*)', text)
                if match:
                    m3u8_url = match.group(1).replace('\\/', '/')
                    # 【可视化新增】：实时输出成功嗅探到底层流的数据
                    print(f"  [√ 流捕获成功] {name.ljust(15)} -> {m3u8_url}")
                    return name, m3u8_url, link
    except Exception as e:
        print(f"  [x] 网络请求异常 ({name}): {e}")
        pass 
    
    # 【可视化新增】：实时输出未命中底层流，降级处理的数据
    print(f"  [- 嗅探失败/降级] {name.ljust(15)} -> 未发现直接 m3u8，保留原始跳转链接")
    return name, None, link

async def main():
    results = []
    
    # === 阶段 1：Playwright 全站分页抓取 ===
    async with async_playwright() as p:
        print("[*] 正在启动 Chromium 无头浏览器...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(ignore_https_errors=True)

        # 注入反爬虫绕过脚本，抹除自动化特征，欺骗防御蜘蛛的探测
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("[*] 已挂载 Stealth 反检测脚本，webdriver 特征已抹除，准备渗透。")

        page_num = 1
        while True:
            print(f"\n{'='*60}")
            print(f"[*] [抓取网站流程] 正在加载并抓取第 {page_num} 页... ")
            print(f"[*] [目标 URL] https://sinparty.com/?page={page_num}")
            # 动态改变 page=&& 参数
            url = f"https://sinparty.com/?page={page_num}"
            # 移除不可靠的 networkidle，使用默认导航机制
            response = await page.goto(url)
            
            if response:
                print(f"[*] [网络状态] 页面响应码: {response.status} (200为正常)")
            else:
                print(f"[!] [网络状态] 未获取到页面响应信息，可能存在拦截。")

            # 强制屏蔽拦截遮罩，破坏防御弹窗，恢复“可操作、可活动、可点击”状态
            await page.add_style_tag(content='''
                .app-modal__overlay, .modal-auth__inner { display: none !important; z-index: -9999 !important; }
                body, html { pointer-events: auto !important; overflow: auto !important; user-select: auto !important; }
            ''')
            # 使用 JS 直接从 DOM 树中强制物理删除这两个拦截节点
            await page.evaluate('''() => {
                document.querySelectorAll('.app-modal__overlay, .modal-auth__inner').forEach(el => el.remove());
            }''')
            print("[*] [防御突破] 拦截层 (.app-modal__overlay) 已强制物理摧毁，DOM 可点击限制解除。")

            # 定位目标：跳过 skeleton 骨架屏，直接锁定在线主播节点
            try:
                # 显式等待真实数据的 CSS 节点渲染到 DOM 中（最长容忍 100 秒）
                print("[*] [DOM 解析] 正在等待目标外层节点渲染: .content-gallery--live-listing ...")
                # 修复了原来类名中间缺漏的点
                await page.wait_for_selector(".content-gallery.content-gallery--live-listing", timeout=100000)
                print("[√] [DOM 解析] 外层数据容器已成功渲染！")
            except Exception:
                # 如果 20 秒后目标节点仍未出现，说明确实到达了没有数据的最后一页
                print(f"[!] [状态反馈] 第 {page_num} 页未检测到有效数据渲染，判断为到达最后一页，结束翻页。")
                break
                
            # 此时 DOM 中必定已有数据，安全执行并集提取
            elements = await page.locator(".content-gallery--live-listing .content-gallery__item").all()
            print(f"[*] [数据截胡] 成功获取当前页卡片数组，共包含 {len(elements)} 个目标节点。开始深度提取...\n")

            for idx, element in enumerate(elements, 1):
                print(f"  --- 正在分析第 {idx}/{len(elements)} 个节点 ---")
                
                # 【可视化新增】：抓取并显示底层 HTML 数据结构 (截取前150个字符防刷屏)
                raw_html = await element.inner_html()
                clean_html = raw_html.replace('\n', '').replace('  ', '')
                print(f"  [RAW HTML] 源码探针: {clean_html[:150]}...")

                # 抓取标题与名字
                title_loc = element.locator(".cam-tile__title")
                if await title_loc.count() > 0:
                    title = await title_loc.first.inner_text()
                    title = title.strip()
                else:
                    title = ""

                # 抓取 href 跳转链接
                a_loc = element.locator("a.cam-tile")
                if await a_loc.count() > 0:
                    href = await a_loc.first.get_attribute("href")
                else:
                    href = ""
                
                if href and href.startswith("/"):
                    href = f"https://sinparty.com{href}"
                
                # 【可视化新增】：判定成功与否，正常不正常
                if not title or not href:
                    print(f"  [x] 状态: 异常/失败！")
                    if not title: print("      -> 原因: 找不到 class='.cam-tile__title' 的名称节点")
                    if not href:  print("      -> 原因: 找不到 class='a.cam-tile' 的跳转链接")
                else:
                    print(f"  [√] 状态: 正常/成功！")
                    print(f"  [+] 提取结果 -> 标题: {title.ljust(15)} | 链接: {href}")
                    
                    results.append({
                        "name": title,
                        "link": href
                    })
                print("  " + "-"*40)

            page_num += 1

        await browser.close()
        print("\n[*] 浏览器引擎已关闭，第一阶段 DOM 提取结束。")

    # === 阶段 2：AIOHTTP 高性能并发抓取 m3u8 流 ===
    print(f"\n{'='*60}")
    print(f"[*] [流程进度] 全站遍历完毕，累计提取有效直播间链接数: {len(results)}")
    print("[*] [并发调度] 启动 aiohttp 协程池 (TCPConnector limit=100)，开始底层高并发嗅探...")
    print(f"{'='*60}\n")
    
    connector = aiohttp.TCPConnector(limit=100, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_m3u8(session, res["name"], res["link"]) for res in results]
        m3u8_results = await asyncio.gather(*tasks)

    # === 阶段 3：转换并格式化输出 M3U ===
    m3u_lines = ["#EXTM3U"]
    success_count = 0
    
    for name, m3u8_url, room_link in m3u8_results:
        # M3U 标准：需要直接填入可播放的流媒体链接 (.m3u8)
        # 如果底层抓不到 m3u8，则使用原始跳转链接作为 fallback
        final_link = m3u8_url if m3u8_url else room_link
        
        # 按照要求输出 group-title="女生" 及名称
        m3u_lines.append(f'#EXTINF:-1 group-title="女生",{name}')
        m3u_lines.append(final_link)
        
        if m3u8_url:
            success_count += 1
            
    m3u_content = "\n".join(m3u_lines)
    
    print(f"\n{'='*60}")
    print("=== [数据写入] 转换格式 M3U 最终输出 ===")
    print(m3u_content)
    print(f"{'='*60}")
    
    with open("lib/party.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
        
    print(f"\n[*] [任务终点] 所有并发处理彻底完成！")
    print(f"[*] [统计] 成功解析底层视频流: {success_count} 个")
    print(f"[*] [统计] 降级保留跳转链接: {len(results) - success_count} 个")
    print(f"[*] [统计] 总计写入数据: {len(results)} 条 -> 已保存至 lib/party.m3u")

if __name__ == "__main__":
    asyncio.run(main())
