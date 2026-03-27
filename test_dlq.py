#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import time


async def test_dlq():
    """Test Dead Letter Queue functionality"""

    api_url = "http://localhost:8000"
    api_key = "test-api-key-2024"

    # Создаем платеж с webhook, который всегда возвращает 500 ошибку
    payload = {
        "amount": 777.77,
        "currency": "USD",
        "description": "DLQ Test - Should go to DLQ after 3 retries",
        "webhook_url": "https://httpbin.org/status/500",  # Всегда 500 ошибка
        "metadata_json": {"test": "dlq"}
    }

    headers = {
        "X-API-Key": api_key,
        "Idempotency-Key": f"dlq-test-{int(time.time())}",
        "Content-Type": "application/json"
    }

    print("1. Создаем платеж...")
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{api_url}/api/v1/payments", json=payload, headers=headers) as resp:
            payment = await resp.json()
            payment_id = payment['id']
            print(f"Payment created: {payment_id}")
            print(f"Status: {payment['status']}")

    # Ждем обработки
    print("\n2. Ожидаем обработку платежа (30 секунд)...")
    for i in range(30):
        await asyncio.sleep(1)
        if i % 10 == 0:
            print(f"   Прошло {i} секунд...")

    # Проверяем статус
    print("\n3. Проверяем статус платежа...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{api_url}/api/v1/payments/{payment_id}",
                               headers={"X-API-Key": api_key}) as resp:
            payment = await resp.json()
            print(f"Payment status: {payment['status']}")

    print("\n4. Проверяем DLQ в RabbitMQ...")
    # Эта команда должна быть выполнена в терминале отдельно


if __name__ == "__main__":
    asyncio.run(test_dlq())