import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        # Просим молдавский прокси
        proxy_configuration = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code='MD'
        )
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            # Запускаем браузер с расширенными аргументами
            browser = await p.chromium.launch(
                headless=True,
                proxy={'server': proxy_url} if proxy_url else None,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--use-fake-ui-for-media-stream',
                    '--window-size=1920,1080'
                ]
            )
            
            # Создаем контекст с полной маскировкой
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                extra_http_headers={
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Referer': 'https://999.md/ru/'
                }
            )
            
            page = await context.new_page()

            # Глубокая маскировка параметров браузера
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru']});
            """)

            print(f"Захожу на {url}...")
            
            try:
                # Пытаемся зайти и ждем чуть дольше
                await page.goto(url, wait_until="load", timeout=90000)
                await asyncio.sleep(20) # Даем максимум времени на прогрузку скриптов

                # 1. ПРОВЕРКА: ЧТО ЖЕ ТАМ НА САМОМ ДЕЛЕ?
                html_preview = await page.content()
                print(f"Первые 200 символов страницы: {html_preview[:200]}")
                page_title = await page.title()
                print(f"Заголовок: {page_title}")

                # 2. СОБИРАЕМ ДАННЫЕ
                data = {"url": url, "browser_title": page_title}

                # Заголовок объявления
                title_el = await page.query_selector('h1')
                data["title"] = await title_el.inner_text() if title_el else "N/A"

                # Цена
                price_el = await page.query_selector('.adPage__content__price-feature')
                data["price"] = await price_el.inner_text() if price_el else "N/A"

                # Телефон
                phone = "Не найден"
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.click()
                    await asyncio.sleep(5)
                    phone = await phone_btn.inner_text()
                data["phone"] = phone

                await Actor.push_data(data)
                print(f"Готово: {data}")

            except Exception as e:
                print(f"Критическая ошибка: {e}")
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
