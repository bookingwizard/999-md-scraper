import asyncio
from apify import Actor
from playwright.async_api import async_playwright
# ИСПРАВЛЕННЫЙ ИМПОРТ
from playwright_stealth import stealth

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
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # --- ПРИМЕНЯЕМ МАСКИРОВКУ (БЕЗ AWAIT) ---
            stealth(page) 
            # ---------------------------------------

            print(f"Захожу на 999.md через прокси: {url}")
            
            try:
                # Используем 'load', чтобы страница успела полностью собраться
                await page.goto(url, wait_until="load", timeout=60000)
                await asyncio.sleep(5) 

                # Снимаем результат для отладки
                screenshot = await page.screenshot(full_page=True)
                await Actor.set_value('DEBUG_SCREENSHOT', screenshot, content_type='image/png')

                # Собираем данные
                title_el = await page.query_selector('h1')
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                
                data = {
                    "url": url,
                    "title": await title_el.inner_text() if title_el else "N/A",
                    "price": await price_el.get_attribute("content") if price_el else "N/A"
                }

                # Пытаемся добыть телефон
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.scroll_into_view_if_needed()
                    await phone_btn.click()
                    await asyncio.sleep(3)
                    data["phone"] = await phone_btn.inner_text()
                else:
                    data["phone"] = "Кнопка не найдена"

                await Actor.push_data(data)

            except Exception as e:
                print(f"Ошибка: {e}")
                scr = await page.screenshot()
                await Actor.set_value('ERROR_SCREENSHOT', scr, content_type='image/png')

            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
