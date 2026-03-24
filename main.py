import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        # 1. Создаем конфигурацию прокси
        proxy_configuration = await Actor.create_proxy_configuration()
        # 2. Генерируем URL прокси (это исправляет твою ошибку!)
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            # 3. Передаем прокси в правильном формате для Playwright
            launch_args = {'headless': True}
            if proxy_url:
                launch_args['proxy'] = {'server': proxy_url}

            browser = await p.chromium.launch(**launch_args)
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            print(f"Захожу на страницу через прокси: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Имитируем активность человека
            await asyncio.sleep(3)
            for _ in range(2):
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(1)

            # Делаем скриншот для проверки
            screenshot = await page.screenshot(full_page=True)
            await Actor.set_value('DEBUG_SCREENSHOT', screenshot, content_type='image/png')

            data = {"url": url}

            try:
                # Парсим данные (новые селекторы)
                title_el = await page.query_selector('h1')
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                
                data["title"] = await title_el.inner_text() if title_el else "N/A"
                data["price"] = await price_el.get_attribute("content") if price_el else "N/A"
                
                desc_el = await page.query_selector('.adPage__content__description')
                data["description"] = await desc_el.inner_text() if desc_el else "N/A"

                # Нажимаем кнопку телефона
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await phone_btn.click()
                    await asyncio.sleep(3) # Ждем прогрузки цифр
                    data["phone"] = await phone_btn.inner_text()
                else:
                    data["phone"] = "Кнопка не найдена"

            except Exception as e:
                print(f"Ошибка при парсинге данных: {e}")
                data["error"] = str(e)

            await Actor.push_data(data)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
