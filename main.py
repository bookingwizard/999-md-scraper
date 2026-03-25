import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        # Просим молдавский прокси (MD)
        proxy_configuration = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code='MD'
        )
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            # Возвращаемся на Chromium — он лучше дружит с прокси Apify
            browser = await p.chromium.launch(
                headless=True, 
                proxy={'server': proxy_url} if proxy_url else None
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()

            # Скрываем автоматизацию
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Отключаем лишнее для скорости
            await page.route("**/*.{png,jpg,jpeg,css,woff,woff2,svg,gif}", lambda route: route.abort())

            print(f"Захожу на {url}...")
            
            try:
                # Пытаемся зайти
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Даем время скриптам
                await asyncio.sleep(10)

                # Собираем данные
                title = await page.title()
                
                # Пытаемся найти цену
                price = "N/A"
                price_el = await page.query_selector('.adPage__content__price-feature')
                if price_el:
                    price = await price_el.inner_text()

                # Если цена N/A, попробуем другой селектор
                if price == "N/A":
                    price_el = await page.query_selector('[itemprop="price"]')
                    if price_el:
                        price = await price_el.get_attribute("content")

                result = {
                    "url": url,
                    "title": title,
                    "price": price.strip() if price else "N/A",
                }

                # Если мы хоть что-то нашли (заголовок не пустой)
                if title:
                    await Actor.push_data(result)
                    print(f"Победа! Данные собраны: {result}")
                else:
                    await Actor.fail("Сайт открылся, но данных нет (пустая страница)")

            except Exception as e:
                # Исправленный вызов ошибки
                error_msg = f"Ошибка: {str(e)}"
                print(error_msg)
                await Actor.fail(error_msg)
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
