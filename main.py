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

        proxy_configuration = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code='MD'
        )
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, proxy={'server': proxy_url} if proxy_url else None)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            print(f"Захожу на {url}...")
            
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(10)

                # --- ОТЛАДКА: ЧТО ВИДИТ БОТ? ---
                page_title = await page.title()
                print(f"Заголовок страницы в браузере: {page_title}")
                # -------------------------------

                # Новые, более широкие селекторы
                title = "N/A"
                title_el = await page.query_selector('h1, .adPage__header h1')
                if title_el:
                    title = await title_el.inner_text()

                price = "N/A"
                # Пробуем найти по itemprop или по классу цены
                price_el = await page.query_selector('[itemprop="price"], .adPage__content__price-feature')
                if price_el:
                    price = await price_el.inner_text()

                phone = "Не найден"
                # Кнопка телефона часто имеет специфический класс
                phone_btn = await page.query_selector('button.adPage__content__phone-button, .js-phone-number')
                if phone_btn:
                    await phone_btn.click()
                    await asyncio.sleep(3)
                    phone = await phone_btn.inner_text()

                result = {
                    "url": url,
                    "browser_title": page_title,
                    "title": title.strip(),
                    "price": price.strip().replace('\n', ' '),
                    "phone": phone.strip()
                }

                await Actor.push_data(result)
                print(f"Результат записан: {result}")

                # Скриншот без ожидания шрифтов
                await page.screenshot(path="result.png", timeout=5000)
                with open("result.png", "rb") as f:
                    await Actor.set_value('FINAL_CHECK', f.read(), content_type='image/png')

            except Exception as e:
                print(f"Ошибка: {e}")
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
