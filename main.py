import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('URL не указан!')

        # Просим прокси именно Молдовы (MD)
        proxy_configuration = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code='MD'
        )
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            launch_args = {'headless': True}
            if proxy_url:
                launch_args['proxy'] = {'server': proxy_url}

            browser = await p.chromium.launch(**launch_args)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            
            page = await context.new_page()

            # Скрываем автоматизацию
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print(f"Пытаюсь прорваться на {url} через молдавский прокси...")
            
            try:
                # Ждем только начала передачи данных ('commit')
                response = await page.goto(url, wait_until="commit", timeout=60000)
                
                if response.status == 403:
                    print("Доступ заблокирован (403). Пробуем подождать...")
                
                await asyncio.sleep(15) # Даем сайту "подумать"

                # Проверяем, есть ли заголовок (значит мы внутри)
                title_el = await page.query_selector('h1')
                if not title_el:
                    # Если не зашли, делаем скриншот ошибки и выходим с ошибкой
                    scr = await page.screenshot()
                    await Actor.set_value('FAIL_SCREENSHOT', scr, content_type='image/png')
                    await Actor.fail("Не удалось прогрузить страницу (застряли на защите)")

                # Если мы здесь, значит зашли!
                data = {
                    "url": url,
                    "title": await title_el.inner_text(),
                    "price": "Ищем...",
                    "phone": "Ищем..."
                }

                # Парсим цену
                price_el = await page.query_selector('.adPage__content__price-feature [itemprop="price"]')
                if price_el:
                    data["price"] = await price_el.get_attribute("content")

                # Парсим телефон
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.click()
                    await asyncio.sleep(5)
                    data["phone"] = await phone_btn.inner_text()

                await Actor.push_data(data)
                print("Данные успешно собраны!")

            except Exception as e:
                # Если упали, теперь Apify покажет честный "Failed"
                await Actor.fail(f"Ошибка: {str(e)}")

            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
