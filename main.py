import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        # Получаем настройки прокси от Apify
        proxy_config = await Actor.create_proxy_configuration()

        async with async_playwright() as p:
            # Используем Chromium
            browser = await p.chromium.launch(headless=True, proxy=proxy_config)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                locale="ru-RU",
                timezone_id="Europe/Chisinau"
            )
            page = await context.new_page()

            print(f"Захожу на страницу: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # --- СКРОЛЛИНГ "как человек" ---
            # Медленно прокручиваем страницу вниз, чтобы подгрузить всё
            for _ in range(3):
                await page.mouse.wheel(0, 500)
                await asyncio.sleep(1)
            # -------------------------------

            # Сохраняем скриншот, чтобы видеть, что получилось
            screenshot = await page.screenshot(full_page=True)
            await Actor.set_value('DEBUG_SCREENSHOT', screenshot, content_type='image/png')

            data = {"url": url}

            try:
                # Парсим цену (пробуем разные селекторы)
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                if price_el:
                    data["price"] = await price_el.get_attribute("content")
                else:
                    price_text = await page.locator('.adPage__content__price-feature').inner_text()
                    data["price"] = price_text.strip() if price_text else "N/A"

                data["title"] = await page.locator('header h1').inner_text()
                data["description"] = await page.locator('.adPage__content__description').inner_text()

                # Пытаемся нажать телефон в нижнем блоке (фото 4)
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await phone_btn.click()
                    await asyncio.sleep(2) # Ждем подгрузки номера
                    data["phone"] = await phone_btn.inner_text()
                else:
                    data["phone"] = "Кнопка не найдена"

            except Exception as e:
                print(f"Ошибка парсинга: {e}")
                data["error"] = str(e)

            await Actor.push_data(data)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
