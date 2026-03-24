import asyncio
from apify import Actor
from playwright.async_api import async_playwright

async def main():
    async with Actor:
        # 1. Получаем входные данные (ссылку на объявление)
        actor_input = await Actor.get_input() or {}
        url = actor_input.get('url')

        if not url:
            await Actor.fail('Вы не указали URL для парсинга!')

        async with async_playwright() as p:
            # Запускаем браузер (используем Firefox или Chromium)
            browser = await p.chromium.launch(headless=True)
            # Важно: имитируем реального пользователя
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            print(f"Открываю страницу: {url}")
            await page.goto(url, wait_until="networkidle")

            # 2. Извлекаем данные (селекторы актуальны для 999.md)
            # Если 999 обновит дизайн, нужно будет просто поменять эти строки
            try:
                data = {
                    "url": url,
                    "title": await page.inner_text('h1') if await page.query_selector('h1') else "N/A",
                    "price": await page.inner_text('.adPage__content__price-feature') if await page.query_selector('.adPage__content__price-feature') else "N/A",
                    "description": await page.inner_text('.adPage__content__description') if await page.query_selector('.adPage__content__description') else "N/A",
                    "region": await page.inner_text('.adPage__content__region') if await page.query_selector('.adPage__content__region') else "N/A",
                }

                # 3. Пытаемся достать телефон (он скрыт кнопкой)
                phone_button = await page.query_selector('.adPage__content__phone .js-phone-number')
                if phone_button:
                    await phone_button.click()
                    await asyncio.sleep(1) # Ждем секунду, пока подгрузится номер
                    data["phone"] = await phone_button.inner_text()
                else:
                    data["phone"] = "Скрыт или не найден"

            except Exception as e:
                print(f"Ошибка при парсинге: {e}")
                data = {"error": str(e), "url": url}

            # 4. Отправляем результат в хранилище Apify
            await Actor.push_data(data)
            await browser.close()

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
