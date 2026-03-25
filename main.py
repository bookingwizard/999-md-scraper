import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        proxy_configuration = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code='MD'
        )
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            # Пробуем Firefox — он часто пролетает там, где Chrome тормозят
            browser = await p.firefox.launch(headless=True, proxy={'server': proxy_url} if proxy_url else None)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0"
            )
            
            # ОТКЛЮЧАЕМ КАРТИНКИ И СТИЛИ (для скорости и обхода защиты)
            page = await context.new_page()
            await page.route("**/*.{png,jpg,jpeg,css,woff,woff2,svg,gif}", lambda route: route.abort())

            print(f"Захожу на {url} через Firefox (MD Proxy)...")
            
            try:
                # Ждем только самого начала передачи данных
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(10) # Просто ждем появления текста

                # Собираем то, что есть
                title = await page.title()
                content = await page.content()
                
                print(f"Заголовок: {title}")
                print(f"Размер кода: {len(content)} символов")

                # Пробуем вытянуть цену по очень простому признаку
                price = "N/A"
                price_elements = await page.query_selector_all(".adPage__content__price-feature, [itemprop='price']")
                if price_elements:
                    price = await price_elements[0].inner_text()

                data = {
                    "url": url,
                    "title": title,
                    "price": price.strip() if price else "N/A",
                    "phone": "Требует клика (пока пропустим для теста захода)"
                }

                if len(content) > 500:
                    await Actor.push_data(data)
                    print("Есть контакт! Данные в базе.")
                else:
                    await Actor.fail("Сайт отдал пустую страницу. Защита не пройдена.")

            except Exception as e:
                print(f"Ошибка: {e}")
                # Если упали, сохраняем то, что успели увидеть в лог
                await Actor.fail(f"Не удалось прорваться: {str(e)}")
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
