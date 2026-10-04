# Copyright (c) 2025 Nand Yaduwanshi <NoxxOP>
# Location: Supaul, Bihar
#
# All rights reserved.
#
# This code is the intellectual property of Nand Yaduwanshi.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: badboy809075@gmail.com

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle
import config
from ARUSHxVCBOT import app

def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true", style=ButtonStyle.PRIMARY
            ),
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_GROUP, style=ButtonStyle.SUCCESS),
        ],
        [
            InlineKeyboardButton(text=_["S_B_5"], user_id=config.OWNER_ID, style=ButtonStyle.DANGER),
            InlineKeyboardButton(text=_["S_B_4"], callback_data="help_page_1", style=ButtonStyle.PRIMARY)  # About button
        ],
    ]
    return buttons

def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(text=_["S_B_3"], url=f"https://t.me/{app.username}?startgroup=true", style=ButtonStyle.PRIMARY)
        ],
        [
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_GROUP, style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=_["S_B_6"], url=config.SUPPORT_CHANNEL, style=ButtonStyle.PRIMARY)
        ],
        [
            InlineKeyboardButton(text=_["S_H_4"], url=config.DONATE, style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=_["S_B_5"], user_id=config.OWNER_ID, style=ButtonStyle.DANGER),
        ],
        [
            InlineKeyboardButton(text=_["S_B_4"], callback_data="help_page_1", style=ButtonStyle.PRIMARY)
        ],
    ]
    return buttons

def about_panel(_):
    buttons = [
        [
            InlineKeyboardButton(text=_["S_B_6"], url=config.SUPPORT_CHANNEL, style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_GROUP, style=ButtonStyle.SUCCESS),
        ],
        [
            InlineKeyboardButton(text=_["BACK_BUTTON"], callback_data="settingsback_helper", style=ButtonStyle.DANGER)
        ]
    ]
    return buttons

def owner_panel(_):
    buttons = [
        [
            InlineKeyboardButton(text=_["S_H_1"], url=config.INSTAGRAM, style=ButtonStyle.DANGER),
            InlineKeyboardButton(text=_["S_H_2"], url=config.YOUTUBE, style=ButtonStyle.DANGER),
        ],
        [
            InlineKeyboardButton(text=_["S_H_3"], url=config.GITHUB, style=ButtonStyle.PRIMARY),
            InlineKeyboardButton(text=_["S_H_4"], url=config.DONATE, style=ButtonStyle.SUCCESS),
        ],
        [
            InlineKeyboardButton(text=_["BACK_BUTTON"], callback_data="settingsback_helper", style=ButtonStyle.DANGER)
        ]
    ]
    return buttons


# ©️ Copyright Reserved - @NoxxOP  Nand Yaduwanshi

# ===========================================
# ©️ 2025 Nand Yaduwanshi (aka @NoxxOP)
# 🔗 GitHub : https://github.com/opanshuff2k/arush-vc-bot
# 📢 Telegram Channel : https://t.me/ARUSHxVCBOT
# ===========================================


# ❤️ Love From ARUSHxVCBOT
