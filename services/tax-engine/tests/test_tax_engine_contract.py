import pytest
from pact import Consumer, Provider, Like

# Определяем пути для Pact
PACT_DIR = 'pacts'
CONSUMER_NAME = 'TaxEngineService'
PROVIDER_NAME = 'TransactionsService'

@pytest.fixture(scope="module")
def pact():
    pact = Consumer(CONSUMER_NAME).has_pact_with(Provider(PROVIDER_NAME), pact_dir=PACT_DIR)
    pact.start_service()
    yield pact
    pact.stop_service()

def test_get_all_transactions_for_a_user(pact):
    # 1. Определяем, какой ответ мы ожидаем от TransactionsService
    expected = [
        {
            "id": Like("123e4567-e89b-12d3-a456-426614174000"),
            "account_id": Like("123e4567-e89b-12d3-a456-426614174001"),
            "user_id": "test_user",
            "provider_transaction_id": Like("txn_abc"),
            "date": Like("2023-10-10"),
            "description": Like("Tesco"),
            "amount": Like(123.45),
            "currency": Like("GBP"),
            "category": Like("groceries"),
            "created_at": Like("2023-10-10T10:00:00Z")
        }
    ]

    # 2. Определяем, какой запрос мы будем отправлять
    (pact
     .given('transactions exist for a user')
     .upon_receiving('a request for all of a user\'s transactions')
     .with_request('GET', '/transactions/me', headers={'Authorization': 'Bearer fake-token'})
     .will_respond_with(200, body=expected))

    # 3. Выполняем наш код, который делает этот запрос
    with pact:
        # В реальном тесте здесь был бы вызов функции из tax-engine,
        # которая делает запрос. Мы имитируем его для простоты.
        import httpx
        transactions_url = f"{pact.uri}/transactions/me"
        response = httpx.get(transactions_url, headers={'Authorization': 'Bearer fake-token'})
        assert response.status_code == 200

    # После этого теста будет сгенерирован файл pacts/TaxEngineService-TransactionsService.json
