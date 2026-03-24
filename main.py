import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        proxy_configuration = await Actor.create_proxy_configuration()
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            launch_args = {'headless': True}
            if proxy_url:
                launch_args['proxy'] = {'server': proxy_url}

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            
            page = await context.new_page()

            # Маскировка
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)

            print(f"Захожу на страницу: {url}")
            
            try:
                # Заходим и ждем только самого важного
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(5) 

                # Пытаемся сделать скриншот, но не умираем, если он не выйдет
                try:
                    # animations="disabled" — чтобы не ждать шрифты и анимации
                    screenshot = await page.screenshot(timeout=10000, animations="disabled")
                    await Actor.set_value('DEBUG_SCREENSHOT', screenshot, content_type='image/png')
                except:
                    print("Скриншот не удался, но продолжаем собирать данные...")

                data = {"url": url}

                # Собираем данные (упрощенные селекторы)
                title_el = await page.query_selector('h1')
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                
                data["title"] = await title_el.inner_text() if title_el else "N/A"
                if price_el:
                    data["price"] = await price_el.get_attribute("content")
                else:
                    # Пробуем достать текст цены напрямую
                    p_text = await page.locator('.adPage__content__price-feature').first.inner_text()
                    data["price"] = p_text.strip().split('\\n')[0] if p_text else "N/A"

                # Нажимаем на телефон
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.scroll_into_view_if_needed()
                    await phone_btn.click()
                    await asyncio.sleep(2)
                    data["phone"] = await phone_btn.inner_text()
                else:
                    data["phone"] = "Кнопка не найдена"

                await Actor.push_data(data)

            except Exception as e:
                print(f"Ошибка парсинга: {e}")

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
