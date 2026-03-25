import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.exit(status_message="URL не указан!")
            return

        # Используем автоматический выбор лучшего прокси
        proxy_configuration = await Actor.create_proxy_configuration()
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={'server': proxy_url} if proxy_url else None
            )
            
            # ПРИТВОРЯЕМСЯ GOOGLEBOT
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()

            print(f"Попытка прорыва 0.2.0 (Googlebot mode) на {url}...")
            
            try:
                # Ждем только самого начала ответа
                await page.goto(url, wait_until="commit", timeout=120000)
                
                # Даем сайту 15 секунд "продышаться"
                await asyncio.sleep(15)

                title = await page.title()
                print(f"Заголовок: {title}")

                price = "N/A"
                price_el = await page.query_selector('.adPage__content__price-feature, [itemprop="price"]')
                if price_el:
                    price = await price_el.inner_text()

                result = {
                    "url": url,
                    "title": title.strip() if title else "Пусто",
                    "price": price.strip() if price else "N/A",
                    "method": "Googlebot"
                }

                await Actor.push_data(result)
                print(f"Результат записан: {result}")

            except Exception as e:
                error_msg = f"Ошибка прорыва: {str(e)[:100]}"
                print(error_msg)
                await Actor.exit(exit_code=1, status_message=error_msg)
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
