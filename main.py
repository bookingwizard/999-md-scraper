import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}
        original_url = actor_input.get('url')

        if not original_url:
            print("URL не указан!")
            return

        # ПЛАН НИНДЗЯ: Переходим на мобильную версию сайта
        url = original_url.replace("999.md", "m.999.md")

        proxy_configuration = await Actor.create_proxy_configuration(
            groups=['RESIDENTIAL'],
            country_code='MD'
        )
        proxy_url = await proxy_configuration.new_url() if proxy_configuration else None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={'server': proxy_url} if proxy_url else None
            )
            
            # Настраиваемся как iPhone — мобильные версии сайтов им доверяют больше
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                viewport={'width': 390, 'height': 844}
            )
            
            page = await context.new_page()
            
            # Скрываем автоматизацию
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print(f"Захожу через мобильный вход: {url}")
            
            try:
                # Пытаемся зайти
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Ждем именно появления любого текста на странице
                await asyncio.sleep(10)

                # Собираем данные по мобильным селекторам
                title = await page.title()
                print(f"Что увидел мобильный браузер: {title}")

                # Ищем цену (на мобильной версии селекторы могут отличаться)
                price = "N/A"
                price_selectors = [
                    '.item__price-value', 
                    '.adPage__content__price-feature',
                    '[itemprop="price"]',
                    '.price'
                ]
                
                for selector in price_selectors:
                    el = await page.query_selector(selector)
                    if el:
                        price = await el.inner_text()
                        break

                result = {
                    "url": url,
                    "title": title.strip() if title else "Пусто",
                    "price": price.strip() if price else "N/A",
                    "status": "Успех" if title and title != "Пусто" else "Заблокировано"
                }

                # Пушим данные только если заголовок не пустой
                await Actor.push_data(result)
                print(f"Результат: {result}")

            except Exception as e:
                print(f"Не удалось: {e}")
            
            finally:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
