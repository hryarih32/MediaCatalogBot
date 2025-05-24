import logging
from telegram import Update, Bot, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.ext import ContextTypes, Application, CallbackContext
from telegram.error import BadRequest, RetryAfter, TimedOut, NetworkError

import src.app.app_config_holder as app_config_holder
from .bot_message_persistence import (
    load_menu_message_id, save_menu_message_id, delete_menu_id_file,
    load_universal_status_message_id, save_universal_status_message_id, delete_universal_status_message_id_file
)
from src.handlers.menu_handler_main_builder import build_main_menu_content

logger = logging.getLogger(__name__)


async def send_or_edit_universal_status_message(
    bot_or_app: Bot | Application,
    chat_id: int,
    text: str,
    parse_mode="MarkdownV2",
    reply_markup=None,
    force_send_new=False
) -> int | None:
    if isinstance(bot_or_app, Application):
        bot = bot_or_app.bot
    else:
        bot = bot_or_app

    existing_message_id = load_universal_status_message_id(str(chat_id))

    should_send_new = force_send_new or not existing_message_id

    if should_send_new:
        if existing_message_id:
            logger.info(
                f"UniversalStatus: Force sending new or no existing ID for chat {chat_id}. Deleting old uni_msg {existing_message_id} if it exists.")
            try:
                await bot.delete_message(chat_id=chat_id, message_id=existing_message_id)
            except Exception:
                pass
            delete_universal_status_message_id_file(str(chat_id))

        logger.info(
            f"UniversalStatus: Sending new universal status message to chat {chat_id}.")
        try:
            sent_message = await bot.send_message(
                chat_id=chat_id, text=text, parse_mode=parse_mode,
                reply_markup=reply_markup, disable_web_page_preview=True
            )
            new_id = sent_message.message_id
            save_universal_status_message_id(new_id, str(chat_id))
            logger.info(
                f"UniversalStatus: Sent new uni_msg {new_id} for chat {chat_id}.")
            return new_id
        except BadRequest as e:
            logger.error(
                f"UniversalStatus: BadRequest sending new uni_msg to chat {chat_id} (text: '{text[:50]}...'): {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"UniversalStatus: Failed to send new uni_msg to chat {chat_id}: {e}", exc_info=True)
        return None

    else:
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=existing_message_id, text=text,
                parse_mode=parse_mode, reply_markup=reply_markup, disable_web_page_preview=True
            )
            logger.info(
                f"UniversalStatus: Edited uni_msg {existing_message_id} for chat {chat_id}.")
            return existing_message_id
        except BadRequest as e:
            err_lower = str(e).lower()
            if "message is not modified" in err_lower:
                logger.debug(
                    f"UniversalStatus: uni_msg {existing_message_id} for chat {chat_id} not modified.")
                return existing_message_id
            logger.warning(
                f"UniversalStatus: Edit failed for uni_msg {existing_message_id} for chat {chat_id} ('{err_lower}'). Deleting ID and sending new.")
            delete_universal_status_message_id_file(str(chat_id))
            return await send_or_edit_universal_status_message(bot, chat_id, text, parse_mode, reply_markup, force_send_new=True)
        except (NetworkError, TimedOut, RetryAfter) as e:
            logger.warning(
                f"UniversalStatus: Network/Timeout error editing uni_msg {existing_message_id} for chat {chat_id}: {e}. Preserving ID.")
            return existing_message_id
        except Exception as e:
            logger.error(
                f"UniversalStatus: Unexpected error editing uni_msg {existing_message_id} for chat {chat_id}: {e}", exc_info=True)
            delete_universal_status_message_id_file(str(chat_id))
            return await send_or_edit_universal_status_message(bot, chat_id, text, parse_mode, reply_markup, force_send_new=True)
    return None


async def show_or_edit_main_menu(
    chat_id_str: str,
    context_or_app: Application | CallbackContext,
    force_send_new=False
) -> int | None:
    if not chat_id_str or not chat_id_str.lstrip('-').isdigit():
        logger.error(
            f"show_or_edit_main_menu: Invalid chat_id_str: {chat_id_str}")
        return None
    chat_id = int(chat_id_str)

    bot_obj: Bot
    bot_data_obj: dict

    if isinstance(context_or_app, Application):
        bot_obj = context_or_app.bot
        bot_data_obj = context_or_app.bot_data
    elif isinstance(context_or_app, CallbackContext):
        bot_obj = context_or_app.bot
        bot_data_obj = context_or_app.bot_data
    else:
        logger.error(
            f"show_or_edit_main_menu: Unexpected type for context_or_app: {type(context_or_app)}")
        return None

    user_role = app_config_holder.get_user_role(str(chat_id))
    version = app_config_holder.get_project_version()
    dynamic_menu_text, reply_markup = build_main_menu_content(
        version, user_role, str(chat_id))

    menu_msg_id_persisted = load_menu_message_id(str(chat_id))

    should_send_new_menu = force_send_new or not menu_msg_id_persisted

    if should_send_new_menu:
        if menu_msg_id_persisted:
            logger.info(
                f"MainMenu: Force sending new or no ID for chat {chat_id}. Deleting old menu_msg {menu_msg_id_persisted} if it exists.")
            try:
                await bot_obj.delete_message(chat_id=chat_id, message_id=menu_msg_id_persisted)
            except Exception:
                pass
            delete_menu_id_file(str(chat_id))
            bot_data_obj.pop(
                f"menu_message_content_{chat_id}_{menu_msg_id_persisted}", None)

        logger.info(
            f"MainMenu: Sending new main menu to chat {chat_id} (Role: {user_role}). Text: '{dynamic_menu_text[:100]}...'")
        try:
            sent_message = await bot_obj.send_message(
                chat_id=chat_id, text=dynamic_menu_text,
                reply_markup=reply_markup, parse_mode="MarkdownV2"
            )
            new_id = sent_message.message_id
            save_menu_message_id(new_id, str(chat_id))
            bot_data_obj[f"menu_message_content_{chat_id}_{new_id}"] = (
                dynamic_menu_text, reply_markup.to_json())
            logger.info(
                f"MainMenu: Sent new menu_msg {new_id} to chat {chat_id}.")
            return new_id
        except BadRequest as e:
            logger.error(
                f"MainMenu: BadRequest sending new menu_msg to chat {chat_id} (text: '{dynamic_menu_text[:100]}...'): {e}", exc_info=True)
        except Exception as e:
            logger.error(
                f"MainMenu: Failed to send new menu_msg to chat {chat_id}: {e}", exc_info=True)
        return None

    else:
        try:
            current_content_key = f"menu_message_content_{chat_id}_{menu_msg_id_persisted}"
            old_content_tuple_json = bot_data_obj.get(current_content_key)
            new_content_tuple_json = (
                dynamic_menu_text, reply_markup.to_json())

            if old_content_tuple_json != new_content_tuple_json:
                logger.info(
                    f"MainMenu: Editing menu_msg {menu_msg_id_persisted} for chat {chat_id}. Text: '{dynamic_menu_text[:100]}...'")
                await bot_obj.edit_message_text(
                    chat_id=chat_id, message_id=menu_msg_id_persisted,
                    text=dynamic_menu_text, reply_markup=reply_markup, parse_mode="MarkdownV2"
                )
                bot_data_obj[current_content_key] = new_content_tuple_json
                logger.info(
                    f"MainMenu: Edited menu_msg {menu_msg_id_persisted} for chat {chat_id}.")
            else:
                logger.debug(
                    f"MainMenu: menu_msg {menu_msg_id_persisted} for chat {chat_id} content not modified, edit skipped.")

            if load_menu_message_id(str(chat_id)) != menu_msg_id_persisted:
                save_menu_message_id(menu_msg_id_persisted, str(chat_id))
            return menu_msg_id_persisted
        except BadRequest as e:
            err_lower = str(e).lower()
            if "message is not modified" in err_lower:
                logger.debug(
                    f"MainMenu: menu_msg {menu_msg_id_persisted} for chat {chat_id} not modified (API).")
                if load_menu_message_id(str(chat_id)) != menu_msg_id_persisted:
                    save_menu_message_id(menu_msg_id_persisted, str(chat_id))
                return menu_msg_id_persisted

            logger.warning(
                f"MainMenu: Edit failed for menu_msg {menu_msg_id_persisted} for chat {chat_id} ('{err_lower}'). Text was '{dynamic_menu_text[:100]}...'. Deleting ID and sending new.")
            delete_menu_id_file(str(chat_id))
            if menu_msg_id_persisted:
                bot_data_obj.pop(
                    f"menu_message_content_{chat_id}_{menu_msg_id_persisted}", None)
            return await show_or_edit_main_menu(chat_id_str, context_or_app, force_send_new=True)
        except Exception as e:
            logger.error(
                f"MainMenu: Unexpected error editing menu_msg {menu_msg_id_persisted} for chat {chat_id}: {e}. Text was '{dynamic_menu_text[:100]}...'", exc_info=True)
            delete_menu_id_file(str(chat_id))
            if menu_msg_id_persisted:
                bot_data_obj.pop(
                    f"menu_message_content_{chat_id}_{menu_msg_id_persisted}", None)
            return await show_or_edit_main_menu(chat_id_str, context_or_app, force_send_new=True)
    return None


async def set_bot_commands(application: Application):

    general_commands = [
        BotCommand("start", "Show the main menu / Request access"),
        BotCommand("home", "Show the main menu / Request access"),
    ]

    primary_admin_commands = [
        BotCommand("start", "Show the main menu (Admin)"),
        BotCommand("home", "Show the main menu (Admin)"),
        BotCommand("status", "Show current bot status message"),
        BotCommand("settings", "Open bot configuration panel"),
    ]

    try:

        await application.bot.set_my_commands(general_commands, scope=BotCommandScopeDefault())
        logger.info(
            "General bot commands updated successfully for default scope.")

        primary_admin_chat_id_str = app_config_holder.get_chat_id_str()
        if primary_admin_chat_id_str:
            try:
                primary_admin_chat_id_int = int(primary_admin_chat_id_str)
                await application.bot.set_my_commands(primary_admin_commands, scope=BotCommandScopeChat(chat_id=primary_admin_chat_id_int))
                logger.info(
                    f"Admin-specific commands set for primary admin chat ID {primary_admin_chat_id_int}.")
            except ValueError:
                logger.error(
                    f"Primary admin CHAT_ID '{primary_admin_chat_id_str}' is not a valid integer. Cannot set admin-specific commands.")
            except Exception as e_admin_cmd:
                logger.warning(
                    f"Could not set admin-specific commands for {primary_admin_chat_id_str}: {e_admin_cmd}", exc_info=False)
        else:
            logger.info(
                "Primary admin CHAT_ID not configured; only general commands will be set.")

    except Exception as e:
        logger.warning(
            f"Could not set bot commands generally: {e}", exc_info=False)
