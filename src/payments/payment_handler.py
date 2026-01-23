import asyncio
import datetime as dt
import logging
import os
from decimal import Decimal
from typing import Optional

from yookassa import Configuration, Payment

from databaseAPI import rep_chess_db
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters, Application
from telegram.error import TelegramError
from payments.yookassa_client import YooKassaClient, _money_str
from util import BACK_TO_MENU_KEYBOARD, MOSCOW_TZ, UTC, _coerce_datetime, _now_tz, _reply_managed, _send_managed_message

logger = logging.getLogger(__name__)

# пользователь id - идентификатор способа оплаты
# Удаление идентификатора сохраненного способа оплаты равноценно отключению автоплатежа для пользователя.

ACCOUNT_ID = os.getenv("ACCOUNT_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

if not ACCOUNT_ID or not SECRET_KEY:
    logger.warning("YooKassa credentials missing: ACCOUNT_ID/SECRET_KEY")
    
Configuration.account_id = ACCOUNT_ID
Configuration.secret_key = SECRET_KEY

# config
SUBSCRIPTION_AMOUNT = Decimal("10.00")
SUBSCRIPTION_PERIOD_DAYS = 30
RETURN_URL = os.getenv("PAYMENT_RETURN_URL", "https://t.me/repchessbot")
POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 12

# keys
SUBSCRIPTION_TASKS_KEY = "subscription_tasks"
PHONE_STATE_KEY = "collect_subscription_phone"
PENDING_SUBSCRIPTION_DATA_KEY = "pending_subscription_request"

# callbacks
RESUME_SUB_CONFIRM_CALLBACK = "resume_sub_confirm"
RESUME_SUB_CANCEL_CALLBACK = "resume_sub_cancel"
CONFIRM_SUBSCRIPTION_CALLBACK = "confirm_subscription"
STOP_SUBSCRIPTION_PROCESS_CALLBACK = "stop_subscription_process"
PAYMENT_PROMPTS_KEY = "payment_prompts"
DELETE_PAYMENT_METHOD_CALLBACK = "delete_payment_method"
MANAGE_SUB_CALLBACK = "manage_subscription"


# DB logic
def add_auth(
    telegram_id: int,
    *,
    months: int = 1,
    payment_method_id: Optional[str] = None,
    auto_renew: bool = True,
) -> dt.datetime:
    valid_until = _now_tz(UTC) + dt.timedelta(days=SUBSCRIPTION_PERIOD_DAYS * months)
    rep_chess_db.set_user_subscription(telegram_id, True, valid_until.isoformat())

    if payment_method_id:
        rep_chess_db.update_subscription_payment_method(telegram_id, payment_method_id)
    elif auto_renew is False:
        rep_chess_db.update_subscription_payment_method(telegram_id, None)

    rep_chess_db.update_subscription_auto_renew(telegram_id, auto_renew and bool(payment_method_id))
    next_charge = valid_until if (auto_renew and payment_method_id) else None
    rep_chess_db.update_subscription_next_charge(
        telegram_id, next_charge.isoformat() if next_charge else None
    )
    return valid_until.astimezone(MOSCOW_TZ)

async def _request_phone_number(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    telegram_id: int,
) -> None:
    context.user_data[PHONE_STATE_KEY] = True
    context.user_data[PENDING_SUBSCRIPTION_DATA_KEY] = {"telegram_id": telegram_id, "chat_id": chat_id}
    context.user_data["text_state"] = process_phone_number

    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("📱 Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await _send_managed_message(
        context,
        chat_id=chat_id,
        text=(
            "Для оформления подписки нужен номер телефона, чтобы отправить фискальный чек "
            "в YooKassa. Пожалуйста, отправьте контакт."
        ),
        reply_markup=keyboard,
    )

async def ensure_user_phone(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    telegram_id: int,
) -> Optional[str]:
    phone = rep_chess_db.get_user_phone(telegram_id)
    if phone:
        return phone
    await _request_phone_number(update, context, chat_id, telegram_id)
    return None

async def process_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    pending = context.user_data.get(PENDING_SUBSCRIPTION_DATA_KEY)
    if pending is None:
        context.user_data["text_state"] = None
        return
    if not update.message.contact or not update.message.contact.phone_number:
        await _reply_managed(update, context, cleanup=False, text="Пожалуйста, воспользуйтесь кнопкой отправки контакта.")
        return

    phone = update.message.contact.phone_number
    if not phone:
        await _reply_managed(update, context, cleanup=False, text="Не удалось получить номер из контакта. Попробуйте еще раз.")
        return

    rep_chess_db.set_user_phone(pending["telegram_id"], phone)
    context.user_data.pop(PHONE_STATE_KEY, None)
    context.user_data.pop(PENDING_SUBSCRIPTION_DATA_KEY, None)
    context.user_data["text_state"] = None

    await _reply_managed(update, context, text="Спасибо! Номер сохранён.", reply_markup=ReplyKeyboardRemove())

    await initiate_subscription_payment(
        context=context,
        update=update,
        chat_id=pending["chat_id"],
        telegram_id=pending["telegram_id"],
    )

# payments
async def initiate_subscription_payment(
    *,
    context: ContextTypes.DEFAULT_TYPE,
    update: Update,
    chat_id: int,
    telegram_id: int,
) -> None:
    phone = rep_chess_db.get_user_phone(telegram_id)
    if not phone:
        await _send_managed_message(
            context,
            chat_id=chat_id,
            text="Номер телефона не найден. Повторите попытку оформления подписки.",
            reply_markup=BACK_TO_MENU_KEYBOARD,
        )
        return

    if rep_chess_db.check_user_active_subscription(telegram_id):
        await _send_managed_message(
            context,
            chat_id=chat_id,
            text="У вас уже активирована подписка!",
            reply_markup=BACK_TO_MENU_KEYBOARD,
        )
        return

    confirmation_url, payment_id = await asyncio.to_thread(
        YooKassaClient.create_subscription_payment,
        telegram_id,
        phone,
    )

    if not confirmation_url or not payment_id:
        await _send_managed_message(
            context,
            chat_id=chat_id,
            text="❌ Не удалось создать платеж. Попробуйте позже.",
            reply_markup=BACK_TO_MENU_KEYBOARD,
        )
        return

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Оплатить", url=confirmation_url)]])
    msg = await _send_managed_message(
        context,
        chat_id=chat_id,
        text=(
            "Перейдите по ссылке ниже для оформления ежемесячной подписки на сайте ЮKКасса.\n"
            "Для тестовой среды используйте карту 5555 5555 5555 4477 (12/22, CVC 000)."
        ),
        reply_markup=keyboard,
        cleanup=False,
        track=False
    )
    
    prompts = context.application.bot_data.setdefault(PAYMENT_PROMPTS_KEY, {})
    prompts[telegram_id] = {"chat_id": chat_id, "message_id": msg.message_id}

    context.application.create_task(
        poll_payment_status(
            context=context,
            application=context.application,
            chat_id=chat_id,
            telegram_id=telegram_id,
            payment_id=payment_id,
        )
    )

async def poll_payment_status(
    *,
    context,
    application,
    chat_id: int,
    telegram_id: int,
    payment_id: str,
) -> None:
    for attempt in range(MAX_POLL_ATTEMPTS):
        try:
            payment = await asyncio.to_thread(Payment.find_one, payment_id)
        except Exception as error:
            logger.error(
                "Error polling payment %s for user %s (attempt %s/%s): %s",
                payment_id, telegram_id, attempt + 1, MAX_POLL_ATTEMPTS, error,
            )
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            continue

        status = payment.status
        if status == "succeeded":
            await finalize_successful_payment(
                application=application,
                chat_id=chat_id,
                telegram_id=telegram_id,
                payment=payment,
                is_recurring=False,
            )
            logger.debug("Payment for user %s succeeded", telegram_id)
            return

        if status in {"canceled", "expired", "refunded"}:
            await application.bot.send_message(chat_id=chat_id, text="❌ Платеж не прошёл. Попробуйте ещё раз.")
            logger.error("Payment %s failed with status %s", payment_id, status)
            entry = application.bot_data.get(PAYMENT_PROMPTS_KEY, {}).pop(telegram_id, None)
            if entry:
                try:
                    await application.bot.delete_message(chat_id=entry["chat_id"], message_id=entry["message_id"])
                except TelegramError:
                    pass
            return

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    
    context.user_data["text_state"] = None
    await application.bot.send_message(
        chat_id=chat_id,
        text=(
            "Не удалось подтвердить платеж. Если деньги были списаны, "
            "пожалуйста, обратитесь в @RepChess_helper."
        ),
        reply_markup=BACK_TO_MENU_KEYBOARD,
    )

async def finalize_successful_payment(
    *,
    application,
    chat_id: int,
    telegram_id: int,
    payment: Payment,
    is_recurring: bool = False,
) -> None:
    entry = application.bot_data.get(PAYMENT_PROMPTS_KEY, {}).pop(telegram_id, None)
    if entry:
        try:
            await application.bot.delete_message(chat_id=entry["chat_id"], message_id=entry["message_id"])
        except TelegramError as e:
            logger.debug("Could not delete payment prompt for %s: %s", telegram_id, e)
            
    payment_method_id = None
    auto_renew = False

    payment_method = getattr(payment, "payment_method", None)
    if payment_method:
        payment_method_id = getattr(payment_method, "id", None)
        auto_renew = bool(getattr(payment_method, "saved", False)) and bool(payment_method_id)

    valid_until_moscow = add_auth(
        telegram_id,
        payment_method_id=payment_method_id,
        auto_renew=auto_renew,
    )

    if is_recurring:
        text = f"✅ Подписка успешно продлена!\nСледующий платёж: {valid_until_moscow:%d.%m.%Y}"
    else:
        text=(
            "Ваша подписка активирована!\n\n"
            "Теперь вы имеете доступ к видеоурокам в разделе 🎯 Обучение!\n"
            "Спасибо за поддержку проекта!"
        )

    await application.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=BACK_TO_MENU_KEYBOARD
    )

# scheduler (move to jobs)
async def subscription_scheduler(application: Application):
    """
    Фоновая задача: каждый час проверяет БД на наличие подписок,
    для которых пришло время автопродления.
    """
    logger.info("Subscription scheduler started")
    while True:
        try:
            logger.debug("Checking for due subscriptions...")
            due_subscriptions = rep_chess_db.get_due_subscriptions()
            logger.debug("Found %d due subscriptions", len(due_subscriptions))

            for record in due_subscriptions:
                telegram_id = record["telegram_id"]
                chat_id = telegram_id
                phone = record["phone"]
                payment_method_id = record["subscription_payment_method_id"]

                if not phone or not payment_method_id:
                    logger.warning(
                        "Skipping renewal for user %s: missing phone or payment method",
                        telegram_id
                    )
                    continue

                application.create_task(
                    process_single_renewal(
                        application=application,
                        telegram_id=telegram_id,
                        chat_id=chat_id,
                    )
                )

        except Exception as e:
            logger.error("Error in subscription scheduler: %s", e, exc_info=True)

        # ждём час
        await asyncio.sleep(3600)


async def process_single_renewal(
    *,
    application: Application,
    telegram_id: int,
    chat_id: int,
) -> None:
    """Выполняет один автоплатёж для пользователя."""
    try:
        logger.info("Starting renewal process for user %s", telegram_id)

        details = rep_chess_db.get_subscription_details(telegram_id)
        if not details:
            logger.warning("No subscription details found for user %s", telegram_id)
            return

        if not details.get("subscription_auto_renew"):
            logger.info("Auto-renew disabled for user %s, skipping", telegram_id)
            return

        payment_method_id = details.get("subscription_payment_method_id")
        phone = details.get("user_phone") 

        if not payment_method_id or not phone:
            logger.error("Missing payment method or phone for user %s", telegram_id)
            _disable_auto_renew_due_to_error(application, telegram_id, chat_id)
            return

        payment = await asyncio.to_thread(
            YooKassaClient.create_subscription_payment,
            payment_method_id,
            telegram_id,
            phone,
        )

        if not payment or payment.status != "succeeded":
            logger.error("Recurring payment failed for user %s", telegram_id)
            _disable_auto_renew_due_to_error(application, telegram_id, chat_id)
            return

        valid_until_moscow = add_auth(
            telegram_id,
            payment_method_id=payment_method_id,
            auto_renew=True,
        )

        await application.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Подписка успешно продлена!\nСледующий платёж: {valid_until_moscow:%d.%m.%Y}",
        )
        logger.info("Renewal succeeded for user %s", telegram_id)

    except Exception as e:
        logger.error("Unexpected error during renewal for user %s: %s", telegram_id, e, exc_info=True)
        _disable_auto_renew_due_to_error(application, telegram_id, chat_id)


def _disable_auto_renew_due_to_error(
    application: Application,
    telegram_id: int,
    chat_id: int,
) -> None:
    """Отключает автопродление и уведомляет пользователя."""
    rep_chess_db.update_subscription_auto_renew(telegram_id, False)
    rep_chess_db.update_subscription_next_charge(telegram_id, None)
    application.create_task(
        application.bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ Автопродление остановлено из-за ошибки.\n"
                "Подписка останется активной до конца текущего периода.\n"
                "Чтобы возобновить — обновите способ оплаты в разделе профиля."
            ),
        )
    )
    
# user interface
async def subscribe_button_clicked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        telegram_id = query.from_user.id
        chat_id = query.message.chat_id
    else:
        telegram_id = update.message.from_user.id
        chat_id = update.message.chat_id

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Давайте оформим подписку!", callback_data=CONFIRM_SUBSCRIPTION_CALLBACK)],
            [InlineKeyboardButton("Нет, пока не нужно.", callback_data=STOP_SUBSCRIPTION_PROCESS_CALLBACK)],
        ]
    )

    subscription_details = rep_chess_db.get_subscription_details(telegram_id)
    subscription_active = rep_chess_db.check_user_active_subscription(telegram_id)

    if subscription_active and subscription_details:
        valid_until = _coerce_datetime(subscription_details.get("subscription_valid_until"))
        next_charge = _coerce_datetime(subscription_details.get("subscription_next_charge"))

        if not next_charge:
            await _send_managed_message(
                context,
                chat_id=chat_id,
                text=(
                    "У вас уже активирована подписка! "
                    f"Она действует до {valid_until:%d.%m.%Y}\n\n"
                    "У вас отключено автопродление. Следующий платеж не будет списан."
                    "Чтобы возобновить автопродление отправьте /resume_sub."
                    if valid_until
                    else "У вас уже активирована подписка! Автопродление отключено."
                ),
            )
        else:
            await _send_managed_message(
                context,
                chat_id=chat_id,
                text=(
                    "У вас уже активирована подписка!\n"
                    f"📆 Следующий автоплатёж: {_money_str(SUBSCRIPTION_AMOUNT)} RUB, {next_charge:%d.%m.%Y}.\n\n"
                    "Отказаться от дальнейших платежей можно при помощи /stop_sub."
                ),
            )
    else:
        await _send_managed_message(
            context,
            chat_id=chat_id,
            text=(
                "У вас ещё нет подписки!\n\n"
                f"Оформить за {_money_str(SUBSCRIPTION_AMOUNT)} RUB в месяц? "
                "Списание происходит ежемесячно. Чтобы отказаться от ежемесячного платежа отправьте команду /stop_sub."
            ),
            reply_markup=keyboard,
        )
    context.user_data["text_state"] = None

async def stop_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    details = rep_chess_db.get_subscription_details(telegram_id)
    if not details or not details.get("subscription_auto_renew"):
        await _send_managed_message(context, chat_id=chat_id, text="Автопродление уже отключено.")
        return

    rep_chess_db.update_subscription_auto_renew(telegram_id, False)
    rep_chess_db.update_subscription_next_charge(telegram_id, None)

    await _send_managed_message(
        context,
        chat_id=chat_id,
        text="Автопродление отключено. Подписка останется активной до окончания оплаченного периода. Для удаления привязанных данных отправьте команду /delete_payment_method",
    )

async def resume_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    details = rep_chess_db.get_subscription_details(telegram_id)
    if not details or not details.get("active_subscription"):
        await _send_managed_message(context, chat_id=chat_id, text="У вас нет активной подписки.")
        return

    if details.get("subscription_auto_renew"):
        await _send_managed_message(context, chat_id=chat_id, text="Автопродление уже включено.")
        return

    valid_until = _coerce_datetime(details.get("subscription_valid_until"))
    if not valid_until:
        await _send_managed_message(context, chat_id=chat_id, text="Произошла непредвиденная ошибка.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Я согласен(на), возобновите платежи", callback_data=RESUME_SUB_CONFIRM_CALLBACK)],
        [InlineKeyboardButton("Я передумал(ла), не возобновляйте", callback_data=RESUME_SUB_CANCEL_CALLBACK)],
    ])
    await _send_managed_message(
        context,
        chat_id=chat_id,
        text=(
            "Вы собираетесь возобновить регулярные платежи за подписку Repchess Bot 🌟.\n\n"
            f"Следующий платеж: {_money_str(SUBSCRIPTION_AMOUNT)} RUB, {valid_until:%d.%m.%Y}."
        ),
        reply_markup=keyboard,
    )

# callbacks 
async def resume_subscription_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except TelegramError as error:
        logger.warning("Failed to answer resume confirmation callback for %s: %s", query.id, error)

    telegram_id = query.from_user.id
    chat_id = query.message.chat_id

    details = rep_chess_db.get_subscription_details(telegram_id)
    if not details or not details.get("active_subscription"):
        await query.edit_message_text("Подписка не найдена. Оформите новый платеж, чтобы активировать автопродление.")
        return
    if details.get("subscription_auto_renew"):
        await query.edit_message_text("Автопродление уже включено.")
        return

    valid_until = _coerce_datetime(details.get("subscription_valid_until"))
    if not valid_until:
        await query.edit_message_text("Произошла ошибка создания автопродления.")
        return

    rep_chess_db.update_subscription_auto_renew(telegram_id, True)
    rep_chess_db.update_subscription_next_charge(telegram_id, valid_until.astimezone(UTC).isoformat())

    await query.edit_message_text(
        "Автопродление возобновлено.\n\n"
        f"Следующий платеж: {_money_str(SUBSCRIPTION_AMOUNT)} RUB, {valid_until:%d.%m.%Y}."
    )

async def subscription_process_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except TelegramError as error:
            logger.warning("Failed to answer confirm callback for %s: %s", query.id, error)
        telegram_id = query.from_user.id
        chat_id = query.message.chat_id
    else:
        telegram_id = update.message.from_user.id
        chat_id = update.message.chat_id
        
    rep_chess_db.ensure_subscription_row(telegram_id)

    phone = await ensure_user_phone(update, context, chat_id, telegram_id)
    if phone:
        await initiate_subscription_payment(context=context, update=update, chat_id=chat_id, telegram_id=telegram_id)

async def subscription_process_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except TelegramError as error:
        logger.warning("Failed to answer resume cancel callback for %s: %s", query.id, error)
    await query.edit_message_text("Подписка не была оформлена.")

async def resume_subscription_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except TelegramError as error:
        logger.warning("Failed to answer resume cancel callback for %s: %s", query.id, error)
    await query.edit_message_text("Автопродление не возобновлено.")

async def delete_payment_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()

    telegram_id = query.from_user.id
    chat_id = query.message.chat_id

    details = rep_chess_db.get_subscription_details(telegram_id)
    if not details or not details.get("subscription_payment_method_id"):
        await query.edit_message_text("У вас нет сохранённого способа оплаты.")
        return

    rep_chess_db.update_subscription_payment_method(telegram_id, None)

    rep_chess_db.update_subscription_auto_renew(telegram_id, False)
    rep_chess_db.update_subscription_next_charge(telegram_id, None)

    valid_until = _coerce_datetime(details.get("subscription_valid_until"))
    if valid_until:
        valid_until_moscow = valid_until.astimezone(MOSCOW_TZ)
        message = (
            "✅ Способ оплаты удалён и автопродление отключено.\n"
            f"Подписка остаётся действующей до: {valid_until_moscow:%d.%m.%Y}."
        )
    else:
        message = (
            "✅ Способ оплаты удалён и автопродление отключено.\n"
            "Подписка остаётся активной до окончания текущего периода."
        )

    await query.edit_message_text(message)


async def delete_payment_method_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id

    details = rep_chess_db.get_subscription_details(telegram_id)
    if not details or not details.get("subscription_payment_method_id"):
        await _send_managed_message(
            context,
            chat_id=chat_id,
            text="У вас нет сохранённого способа оплаты."
        )
        return

    rep_chess_db.update_subscription_payment_method(telegram_id, None)
    rep_chess_db.update_subscription_auto_renew(telegram_id, False)
    rep_chess_db.update_subscription_next_charge(telegram_id, None)

    valid_until = _coerce_datetime(details.get("subscription_valid_until"))
    if valid_until:
        valid_until_moscow = valid_until.astimezone(MOSCOW_TZ)
        message = (
            "✅ Способ оплаты удалён и автопродление отключено.\n"
            f"Подписка остаётся действующей до: {valid_until_moscow:%d.%m.%Y}."
        )
    else:
        message = (
            "✅ Способ оплаты удалён и автопродление отключено.\n"
            "Подписка остаётся активной до окончания текущего периода."
        )

    await _send_managed_message(context, chat_id=chat_id, text=message)

payment_callback_handlers = [
    MessageHandler(filters.Regex("^🌟 Подписка$"), subscribe_button_clicked),
    CommandHandler("stop_sub", stop_subscription_command),
    CommandHandler("resume_sub", resume_subscription_command),
    CommandHandler("delete_payment_method", delete_payment_method_command),
    CallbackQueryHandler(resume_subscription_confirmation_callback, pattern=f"^{RESUME_SUB_CONFIRM_CALLBACK}$"),
    CallbackQueryHandler(resume_subscription_cancel_callback, pattern=f"^{RESUME_SUB_CANCEL_CALLBACK}$"),
    CallbackQueryHandler(subscription_process_confirm_callback, pattern=f"^{CONFIRM_SUBSCRIPTION_CALLBACK}$"),
    CallbackQueryHandler(subscription_process_cancel_callback, pattern=f"^{STOP_SUBSCRIPTION_PROCESS_CALLBACK}$"),
]
