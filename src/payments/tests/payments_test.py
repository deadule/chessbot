import asyncio
import logging
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import pytest
from telegram.ext import Application

logging.getLogger().setLevel(logging.CRITICAL)

from payments.payment_handler import process_single_renewal, add_auth
from databaseAPI import rep_chess_db


@pytest.fixture(autouse=True)
def mock_db_methods(mocker):
    """Мокаем все методы БД, чтобы избежать ошибок при инициализации."""
    mocker.patch.object(rep_chess_db, 'get_subscription_details')
    mocker.patch.object(rep_chess_db, 'update_subscription_auto_renew')
    mocker.patch.object(rep_chess_db, 'update_subscription_next_charge')


@pytest.fixture
def mock_application():
    app = Mock(spec=Application)
    app.bot = AsyncMock()
    app.create_task = lambda coro: asyncio.create_task(coro)
    return app


@pytest.mark.asyncio
async def test_process_single_renewal_success(mock_application, mocker):
    """
    Успешное автопродление: 
    - Пользователь имеет активную подписку с включённым автопродлением
    - Способ оплаты и телефон указаны
    - Платёж проходит успешно
    - Отправляется уведомление об успешном продлении
    """
    telegram_id = 12345
    chat_id = 12345

    mocker.patch.object(rep_chess_db, 'get_subscription_details', return_value={
        "subscription_auto_renew": True,
        "subscription_payment_method_id": "pm_123",
        "user_phone": "+79991234567",
    })

    mock_payment = Mock()
    mock_payment.status = "succeeded"
    create_payment_mock = mocker.patch(
        "payments.payment_handler.create_recurring_payment_sync",
        return_value=mock_payment
    )

    add_auth_mock = mocker.patch(
        "payments.payment_handler.add_auth",
        return_value=datetime(2026, 2, 1)
    )

    await process_single_renewal(
        application=mock_application,
        telegram_id=telegram_id,
        chat_id=chat_id,
    )

    create_payment_mock.assert_called_once_with("pm_123", 12345, "+79991234567")
    add_auth_mock.assert_called_once_with(12345, payment_method_id="pm_123", auto_renew=True)
    mock_application.bot.send_message.assert_called_once()
    assert "✅ Подписка успешно продлена!" in mock_application.bot.send_message.call_args[1]["text"]


@pytest.mark.asyncio
async def test_process_single_renewal_no_subscription_details(mock_application, mocker):
    """
    Нет данных о подписке в БД:
    - Пользователь не найден или нет записи о подписке
    - Функция завершается без ошибок и без отправки сообщений
    """
    mocker.patch.object(rep_chess_db, 'get_subscription_details', return_value=None)
    await process_single_renewal(
        application=mock_application,
        telegram_id=12345,
        chat_id=12345,
    )
    mock_application.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_single_renewal_auto_renew_disabled(mock_application, mocker):
    """
    Автопродление отключено:
    - Пользователь имеет подписку, но автопродление выключено
    - Функция завершается без ошибок и без отправки сообщений
    """
    mocker.patch.object(rep_chess_db, 'get_subscription_details', return_value={
        "subscription_auto_renew": False,
        "subscription_payment_method_id": "pm_123",
        "user_phone": "+79991234567",
    })
    await process_single_renewal(
        application=mock_application,
        telegram_id=12345,
        chat_id=12345,
    )
    mock_application.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_single_renewal_missing_payment_data(mock_application, mocker):
    """
    Отсутствуют данные для платежа:
    - У пользователя включено автопродление, но отсутствует способ оплаты
    - Автопродление отключается
    - Отправляется уведомление об ошибке
    """
    mocker.patch.object(rep_chess_db, 'get_subscription_details', return_value={
        "subscription_auto_renew": True,
        "subscription_payment_method_id": None,
        "user_phone": "+79991234567",
    })
    await process_single_renewal(
        application=mock_application,
        telegram_id=12345,
        chat_id=12345,
    )

    rep_chess_db.update_subscription_auto_renew.assert_called_with(12345, False)
    rep_chess_db.update_subscription_next_charge.assert_called_with(12345, None)
    mock_application.bot.send_message.assert_called_once()
    assert "❌ Автопродление остановлено из-за ошибки" in mock_application.bot.send_message.call_args[1]["text"]


@pytest.mark.asyncio
async def test_process_single_renewal_payment_failed(mock_application, mocker):
    """
    Платёж не удался:
    - ЮKassa вернул None или статус != 'succeeded'
    - Автопродление отключается
    - Отправляется уведомление об ошибке
    """
    mocker.patch.object(rep_chess_db, 'get_subscription_details', return_value={
        "subscription_auto_renew": True,
        "subscription_payment_method_id": "pm_123",
        "user_phone": "+79991234567",
    })
    mocker.patch("payments.payment_handler.create_recurring_payment_sync", return_value=None)

    await process_single_renewal(
        application=mock_application,
        telegram_id=12345,
        chat_id=12345,
    )

    rep_chess_db.update_subscription_auto_renew.assert_called_with(12345, False)
    rep_chess_db.update_subscription_next_charge.assert_called_with(12345, None)
    mock_application.bot.send_message.assert_called_once()
    assert "❌ Автопродление остановлено из-за ошибки" in mock_application.bot.send_message.call_args[1]["text"]


@pytest.mark.asyncio
async def test_process_single_renewal_already_disabled(mock_application, mocker):
    """
    Подписка уже отключена до начала обработки:
    - Планировщик запустил задачу, но пользователь уже отменил автопродление
    - Функция завершается без ошибок и без отправки сообщений
    """
    mocker.patch.object(rep_chess_db, 'get_subscription_details', return_value={
        "subscription_auto_renew": False,
        "subscription_payment_method_id": "pm_123",
        "user_phone": "+79991234567",
    })
    await process_single_renewal(
        application=mock_application,
        telegram_id=12345,
        chat_id=12345,
    )
    mock_application.bot.send_message.assert_not_called()