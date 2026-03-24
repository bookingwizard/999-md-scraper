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
            
            # Настраиваем контекст как у реального человека
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                device_scale_factor=1,
                is_mobile=False,
                has_touch=False,
                locale="ru-RU",
                timezone_id="Europe/Chisinau"
            )
            
            page = await context.new_page()

            # --- РУЧНАЯ МАСКИРОВКА (Вместо stealth библиотеки) ---
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
            """)
            # ----------------------------------------------------

            print(f"Захожу на страницу через прокси: {url}")
            
            try:
                # Заходим и ждем
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(5) 

                # Делаем скриншот (самая важная проверка!)
                screenshot = await page.screenshot(full_page=True)
                await Actor.set_value('DEBUG_SCREENSHOT', screenshot, content_type='image/png')

                data = {"url": url}

                # Собираем данные
                title_el = await page.query_selector('h1')
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                
                data["title"] = await title_el.inner_text() if title_el else "N/A"
                data["price"] = await price_el.get_attribute("content") if price_el else "N/A"

                # Нажимаем на телефон
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await phone_btn.click()
                    await asyncio.sleep(3)
                    data["phone"] = await phone_btn.inner_text()
                else:
                    data["phone"] = "Кнопка не найдена"

                await Actor.push_data(data)

            except Exception as e:
                print(f"Ошибка: {e}")
                err_scr = await page.screenshot()
                await Actor.set_value('ERROR_SCREENSHOT', err_scr, content_type='image/png')

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
