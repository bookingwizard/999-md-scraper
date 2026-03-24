import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            print("URL не указан!")
            return

        # Используем молдавский прокси
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
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Скрываем следы бота
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print(f"Захожу на {url}...")
            
            try:
                # Заходим и ждем только самого важного
                await page.goto(url, wait_until="commit", timeout=60000)
                await asyncio.sleep(10) # Даем время прогрузиться цене

                # 1. Сначала собираем данные!
                title = await page.locator('h1').inner_text() if await page.locator('h1').count() > 0 else "N/A"
                
                # Ищем цену (пробуем разные варианты)
                price = "N/A"
                price_el = await page.query_selector('[itemprop="price"]')
                if price_el:
                    price = await price_el.get_attribute("content")
                
                # Пробуем нажать телефон
                phone = "Не найден"
                phone_btn = await page.query_selector('.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.click()
                    await asyncio.sleep(3)
                    phone = await phone_btn.inner_text()

                # Сохраняем то, что нашли
                result = {
                    "url": url,
                    "title": title.strip(),
                    "price": price,
                    "phone": phone.strip()
                }
                await Actor.push_data(result)
                print(f"Успех! Данные: {result}")

                # 2. А теперь пробуем сделать скриншот "на удачу" (быстрый)
                try:
                    scr = await page.screenshot(timeout=5000, animations="disabled")
                    await Actor.set_value('RESULT_SCREENSHOT', scr, content_type='image/png')
                except:
                    print("Скриншот не успел, но данные уже в базе!")

            except Exception as e:
                print(f"Ошибка в процессе: {e}")
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
