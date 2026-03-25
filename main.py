import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            # Исправленный вызов выхода
            await Actor.exit(status_message="URL не указан!")
            return

        # Используем молдавский прокси
        proxy_configuration = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code='MD'
        )
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            # Chromium остается самым мощным инструментом
            browser = await p.chromium.launch(
                headless=True,
                proxy={'server': proxy_url} if proxy_url else None
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()

            # Убираем все картинки и стили, чтобы прорваться сквозь защиту
            await page.route("**/*.{png,jpg,jpeg,css,woff,woff2,svg,gif}", lambda route: route.abort())

            print(f"Захожу на {url} (Таймаут 120 сек)...")
            
            try:
                # Ждем только 'commit' (самое начало) и даем 120 секунд
                await page.goto(url, wait_until="commit", timeout=120000)
                
                # Даем 15 секунд, чтобы текст просто "выпал" в код
                await asyncio.sleep(15)

                # Проверяем заголовок
                title = await page.title()
                print(f"Браузер говорит, что открыл: {title}")

                price = "N/A"
                # Пробуем вытянуть цену самым простым способом
                price_el = await page.query_selector('.adPage__content__price-feature')
                if price_el:
                    price = await price_el.inner_text()

                result = {
                    "url": url,
                    "title": title.strip() if title else "Пусто",
                    "price": price.strip() if price else "N/A"
                }

                await Actor.push_data(result)
                print(f"Данные в базе: {result}")

            except Exception as e:
                error_msg = f"Осада не удалась: {str(e)}"
                print(error_msg)
                # Безопасный выход без ошибки TypeError
                await Actor.exit(exit_code=1, status_message=error_msg)
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
