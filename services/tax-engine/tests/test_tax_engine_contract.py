import pytest
from pact import Pact, match

# Определяем пути для Pact
PACT_DIR = 'pacts'
CONSUMER_NAME = 'TaxEngineService'
PROVIDER_NAME = 'TransactionsService'

@pytest.fixture(scope="module")
def pact():
    pact = Pact(CONSUMER_NAME, PROVIDER_NAME)
    yield pact
    pact.write_file(PACT_DIR, overwrite=True)

def test_get_all_transactions_for_a_user(pact):
    # 1. Определяем, какой ответ мы ожидаем от TransactionsService
    expected = match.each_like(
        {
            "id": match.uuid("123e4567-e89b-12d3-a456-426614174000"),
            "account_id": match.uuid("123e4567-e89b-12d3-a456-426614174001"),
            "user_id": match.str("test_user"),
            "provider_transaction_id": match.str("txn_abc"),
            "date": match.date("2023-10-10"),
            "description": match.str("Tesco"),
            "amount": match.float(123.45),
            "currency": match.str("GBP"),
            "category": match.str("groceries"),
            "created_at": match.datetime("2023-10-10T10:00:00Z"),
        }
    )

    # 2. Определяем, какой запрос мы будем отправлять
    (pact
     .upon_receiving('a request for all of a user\'s transactions')
     .given('transactions exist for a user')
     .with_request('GET', '/transactions/me')
     .with_header('Authorization', 'Bearer fake-token')
     .will_respond_with(200)
     .with_body(expected, content_type='application/json'))

    # 3. Выполняем наш код, который делает этот запрос
    with pact.serve() as server:
        # В реальном тесте здесь был бы вызов функции из tax-engine,
        # которая делает запрос. Мы имитируем его для простоты.
        import httpx
        transactions_url = f"{server.url}/transactions/me"
        response = httpx.get(transactions_url, headers={'Authorization': 'Bearer fake-token'})
        assert response.status_code == 200

    # После этого теста будет сгенерирован файл pacts/TaxEngineService-TransactionsService.json
