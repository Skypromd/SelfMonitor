import pytest
from pact import Verifier
import os

# Важно: Этот тест должен запускаться ПОСЛЕ того, как consumer-тест
# сгенерировал файл контракта. В CI/CD это настраивается как зависимость.

PACT_FILE = os.path.join(
    # Мы "смотрим" на два уровня вверх, чтобы найти корень проекта,
    # а затем спускаемся в папку с контрактом tax-engine
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    'tax-engine/pacts/TaxEngineService-TransactionsService.json'
)

@pytest.mark.skipif(not os.path.exists(PACT_FILE), reason="Pact file not found")
def test_transaction_service_honours_pact_with_tax_engine(live_server):
    """
    This test verifies that the TransactionsService provider honors the
    contract expected by the TaxEngineService consumer.
    """
    # 1. Настраиваем Verifier
    verifier = Verifier(
        provider='TransactionsService',
        provider_base_url=live_server.url # URL работающего инстанса нашего сервиса
    )

    # 2. Указываем, где найти состояние "given" из контракта.
    # Это URL, по которому Pact будет делать POST-запросы, чтобы настроить
    # состояние нашего приложения перед проверкой. Мы его не реализуем,
    # так как наш API "чистый" и не требует предварительной настройки.
    # В реальном приложении здесь бы создавались нужные транзакции в БД.

    # 3. Запускаем проверку
    # success, logs = verifier.verify_pacts(PACT_FILE, provider_states_setup_url=f"{live_server.url}/_pact/provider_states")
    # В нашем случае мы не реализуем provider_states, поэтому упрощаем.
    success, logs = verifier.verify_pacts(PACT_FILE)

    # 4. Проверяем результат
    # Если `success` будет False, pytest и так "упадёт", но для наглядности:
    assert success == True

@pytest.fixture(scope="session")
def live_server():
    """A fixture to run the FastAPI app in a live server."""
    # Этот код требует, чтобы в тестах был настроен live_server.
    # Для простоты демонстрации, мы оставим его как плейсхолдер.
    # В реальном проекте мы бы использовали pytest-fastapi-deps или подобную библиотеку.
    class MockServer:
        url = "http://localhost:8002" # Предполагаем, что сервис запущен локально для теста

    return MockServer()
