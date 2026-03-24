import asyncio
from apify import Actor
from playwright.async_api import async_playwright
from playwright_stealth import stealth

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        # Подключаем прокси
        proxy_configuration = await Actor.create_proxy_configuration()
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            launch_args = {'headless': True}
            if proxy_url:
                launch_args['proxy'] = {'server': proxy_url}

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # --- ПРИМЕНЯЕМ МАСКИРОВКУ (Исправлено) ---
            await stealth(page)
            # ----------------------------

            print(f"Захожу на 999.md как невидимка: {url}")
            
            try:
                # Заходим на страницу
                await page.goto(url, wait_until="commit", timeout=60000)
                await asyncio.sleep(10) 

                # Делаем скриншот для проверки
                screenshot = await page.screenshot(full_page=True)
                await Actor.set_value('DEBUG_SCREENSHOT', screenshot, content_type='image/png')

                # Собираем данные
                title_el = await page.query_selector('h1')
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                desc_el = await page.query_selector('.adPage__content__description')

                data = {
                    "url": url,
                    "title": await title_el.inner_text() if title_el else "N/A",
                    "price": await price_el.get_attribute("content") if price_el else "N/A",
                    "description": await desc_el.inner_text() if desc_el else "N/A"
                }

                # Прокрутка и нажатие на телефон
                await page.mouse.wheel(0, 800)
                await asyncio.sleep(2)

                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.click()
                    await asyncio.sleep(3)
                    data["phone"] = await phone_btn.inner_text()
                else:
                    data["phone"] = "Кнопка не найдена"

                await Actor.push_data(data)

            except Exception as e:
                print(f"Произошла ошибка: {e}")
                scr = await page.screenshot()
                await Actor.set_value('ERROR_SCREENSHOT', scr, content_type='image/png')

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
