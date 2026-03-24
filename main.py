import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        # 1. Получаем входные данные
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        async with async_playwright() as p:
            # Используем Firefox — он часто лучше обходит защиты
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
                viewport={'width': 1280, 'height': 720}
            )
            page = await context.new_page()

            print(f"Захожу на страницу: {url}")
            
            # Ждем загрузки
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5) # Даем время на подгрузку скриптов

            # Делаем скриншот для проверки (в Key-Value Store)
            screenshot = await page.screenshot()
            await Actor.set_value('DEBUG_SCREENSHOT', screenshot, content_type='image/png')

            try:
                # Извлекаем основные данные
                title_el = await page.query_selector('h1')
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                desc_el = await page.query_selector('.adPage__content__description')

                data = {
                    "url": url,
                    "title": await title_el.inner_text() if title_el else "N/A",
                    "price": await price_el.get_attribute("content") if price_el else "N/A",
                    "description": await desc_el.inner_text() if desc_el else "N/A",
                }

                # Кликаем на телефон
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.scroll_into_view_if_needed()
                    await phone_btn.click()
                    await asyncio.sleep(2)
                    data["phone"] = await phone_btn.inner_text()
                else:
                    data["phone"] = "Кнопка не найдена"

            except Exception as e:
                print(f"Ошибка парсинга: {e}")
                data = {"error": str(e), "url": url}

            # Сохраняем результат
            await Actor.push_data(data)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
