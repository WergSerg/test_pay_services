#!/bin/bash

API_URL="http://localhost:8000"
API_KEY="secret-api-key-2024"

echo "=== Тестирование Payment Service ==="
echo

# 1. Health check
echo "1. Health check:"
curl -s $API_URL/health/ | jq '.'
echo

# 2. Создание платежа
echo "2. Создание платежа:"
PAYMENT_RESPONSE=$(curl -s -X POST $API_URL/api/v1/payments \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: test-idemp-$(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000.50,
    "currency": "RUB",
    "description": "Test payment",
    "webhook_url": "https://webhook.site/99c26b19-ef92-4d37-8ecb-c4a8c9772d7b",
    "metadata_json": {
      "order_id": "order-123",
      "customer_email": "test@example.com"
    }
  }')

echo $PAYMENT_RESPONSE | jq '.'
PAYMENT_ID=$(echo $PAYMENT_RESPONSE | jq -r '.id')
echo "Payment ID: $PAYMENT_ID"
echo

# 3. Проверка идемпотентности (повторный запрос с тем же ключом)
echo "3. Проверка идемпотентности (должен вернуть тот же платеж):"
curl -s -X POST $API_URL/api/v1/payments \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: test-idemp-$(date +%s)" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000.50,
    "currency": "RUB",
    "description": "Test payment",
    "webhook_url": "https://webhook.site/12345678-1234-1234-1234-123456789012"
  }' | jq '.'
echo

# 4. Получение информации о платеже
echo "4. Получение информации о платеже:"
curl -s -X GET $API_URL/api/v1/payments/$PAYMENT_ID \
  -H "X-API-Key: $API_KEY" | jq '.'
echo

# 5. Создание нескольких платежей для тестирования очереди
echo "5. Создание 5 тестовых платежей:"
for i in {1..5}; do
  curl -s -X POST $API_URL/api/v1/payments \
    -H "X-API-Key: $API_KEY" \
    -H "Idempotency-Key: bulk-test-$i-$(date +%s)" \
    -H "Content-Type: application/json" \
    -d "{
      \"amount\": $((i * 100)),
      \"currency\": \"USD\",
      \"description\": \"Bulk test payment $i\",
      \"webhook_url\": \"https://webhook.site/test-$i\"
    }" | jq -r '.id'
done
echo "Done"
echo

echo "=== Тестирование завершено ==="