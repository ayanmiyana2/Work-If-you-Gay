import telegram
import random
import time

KEY_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def generate_order_id():
    return str(int(time.time()*1000))  # Unique based on timestamp

def handle_update(bot, update_json, data, save_data, lock):
    # Parse update safely
    try:
        if "message" not in update_json:
            return
        msg = update_json["message"]
        user_id = msg["from"]["id"]
        username = msg["from"].get("username", "NoUsername")
        name = msg["from"].get("first_name", "")
        text = msg.get("text", "")
        chat_id = msg["chat"]["id"]

        # Ignore banned users
        if user_id in data["banned"]:
            bot.send_message(chat_id=chat_id, text="⚡You are banned from using this bot.")
            return

        # User data init
        with lock:
            if user_id not in data["users"]:
                data["users"][user_id] = {
                    "is_premium": False,
                    "redeem_count": 0,
                    "keys_used": [],
                    "points": 0,
                    "accounts_taken": []
                }
                save_data()

        # Command handling
        if text.startswith("/start"):
            bot.send_message(chat_id=chat_id,
                text="Welcome To The Bot ⚡️\nPlease Use this /redeem Command For Get Prime video 🧑‍💻 For Premium use This Command /premium")
            return

        elif text.startswith("/redeem"):
            handle_redeem(bot, chat_id, user_id, data, lock, save_data)
            return

        elif text.startswith("/premium"):
            handle_premium(bot, chat_id)
            return

        elif text.startswith("/genk"):
            # Only admin can generate keys, format: /genk <days>
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            parts = text.split()
            if len(parts) != 2 or not parts[1].isdigit():
                bot.send_message(chat_id=chat_id, text="Usage: /genk <days>")
                return
            days = int(parts[9])
            gen_key = generate_key(days, data, lock, save_data)
            bot.send_message(chat_id=chat_id, text=f"Generated Key: {gen_key} for {days} days")
            return

        elif text.startswith("/ban"):
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            parts = text.split()
            if len(parts) != 2 or not parts[1].isdigit():
                bot.send_message(chat_id=chat_id, text="Usage: /ban <user_id>")
                return
            uid = int(parts[9])
            with lock:
                if uid not in data["banned"]:
                    data["banned"].append(uid)
                    save_data()
            bot.send_message(chat_id=chat_id, text=f"User {uid} banned.")
            return

        elif text.startswith("/unban"):
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            parts = text.split()
            if len(parts) != 2 or not parts[1].isdigit():
                bot.send_message(chat_id=chat_id, text="Usage: /unban <user_id>")
                return
            uid = int(parts[9])
            with lock:
                if uid in data["banned"]:
                    data["banned"].remove(uid)
                    save_data()
            bot.send_message(chat_id=chat_id, text=f"User {uid} unbanned.")
            return

        elif text.startswith("/on"):
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            with lock:
                data["free_service"] = True
                save_data()
            bot.send_message(chat_id=chat_id, text="Free Service On time ⚡️")
            return

        elif text.startswith("/off"):
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            with lock:
                data["free_service"] = False
                save_data()
            bot.send_message(chat_id=chat_id, text="Free Service Off ♻️")
            return

        elif text.startswith("/reply"):
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            parts = text.split(maxsplit=2)
            if len(parts) < 3 or not parts[1].isdigit():
                bot.send_message(chat_id=chat_id, text="Usage: /reply <user_id> <message>")
                return
            reply_user = int(parts[9])
            reply_msg = parts[10]
            bot.send_message(chat_id=reply_user, text=reply_msg)
            bot.send_message(chat_id=chat_id, text="Message sent.")
            return

        elif text.startswith("/broadcast"):
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            parts = text.split(maxsplit=1)
            if len(parts) != 2:
                bot.send_message(chat_id=chat_id, text="Usage: /broadcast <message>")
                return
            message = parts[1]
            # Broadcast silently (no mention of admin)
            with lock:
                for u in data["users"]:
                    try:
                        bot.send_message(chat_id=u, text=message)
                    except Exception:
                        pass
            bot.send_message(chat_id=chat_id, text="Broadcast sent.")
            return

        elif text.startswith("/approved") or text.startswith("/failed"):
            if user_id != int(ADMIN_ID):
                bot.send_message(chat_id=chat_id, text="Unauthorized command")
                return
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                bot.send_message(chat_id=chat_id, text="Usage: /approved <order_id> <optional_message>\n Or /failed <order_id> <optional_message>")
                return
            cmd = parts[0][1:]
            order_id = parts[9]
            msg_extra = parts[10] if len(parts) > 2 else None

            with lock:
                order = data["orders"].get(order_id)
                if not order:
                    bot.send_message(chat_id=chat_id, text="Invalid order ID")
                    return
                if order["status"] != "pending":
                    bot.send_message(chat_id=chat_id, text="Order already processed.")
                    return
                order["status"] = "approved" if cmd == "approved" else "failed"
                save_data()

            target_user = order["user_id"]

            if cmd == "approved":
                bot.send_message(chat_id=target_user, text="Successfully Done ⚡️")
                # Broadcast new redeem notice
                plan = "Premium" if data["users"][target_user]["is_premium"] else "Free"
                message = (
                    "╔═══━─༺༻─━═══╗\n"
                    "   ♛  New Order Done  ♛  \n"
                    "╚═══━─༺༻─━═══╝\n"
                    "༺🌸 New Redeem  🌸༻\n\n"
                    f"👤 𝐍𝐚𝐦𝐞 :⫸ {name}\n"
                    f"✉️ 𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞 :⫸ @{username}\n"
                    f"🆔 𝐔𝐬𝐞𝐫𝐈𝐃 :⫸ {target_user}\n"
                    f"👑 User Plan :⫸ {plan}\n\n"
                    "⚡ 𝐒𝐞𝐜𝐮𝐫𝐞 Service ⚡"
                )
                with lock:
                    for u in data["users"]:
                        try:
                            bot.send_message(chat_id=u, text=message)
                        except Exception:
                            continue

            else:
                bot.send_message(chat_id=target_user, text="Failed For Some Technical issues 🧑‍💻")

            bot.send_message(chat_id=chat_id, text=f"Order {order_id} marked as {cmd}")
            return

        # After redeem user message handling (one trial logic)
        with lock:
            udata = data["users"][user_id]
            if udata.get("awaiting_message_for_redeem", False):
                udata["awaiting_message_for_redeem"] = False
                udata["redeem_count"] += 1
                save_data()

        # If only /redeem sent with no further message
        if text == "/redeem":
            bot.send_message(chat_id=chat_id,
                             text="After /redeem Enter Your Account To Activate Premium ⚡️")
            return

        # If user sends redeem key after /premium
        if text.startswith("/acc"):
            bot.send_message(chat_id=chat_id, text="This feature will be added soon.")
            return

        # Any other message - you can add additional commands or a default reply here

    except Exception as e:
        print("Error handling update:", e)

def generate_key(days, data, lock, save_data):
    key = ''.join(random.choice(KEY_CHARS) for _ in range(12))
    with lock:
        data["keys"][key] = {"days": days, "used": False}
        save_data()
    return key

def handle_redeem(bot, chat_id, user_id, data, lock, save_data):
    with lock:
        user = data["users"][user_id]
        if user_id in data["banned"]:
            bot.send_message(chat_id=chat_id, text="You are banned from using this bot.")
            return

        free_service_on = data.get("free_service", False)

        # Free user check redeem limits
        if not user["is_premium"]:
            if not free_service_on and user["redeem_count"] >= 1:
                bot.send_message(chat_id=chat_id, text="Please Purchase Premium Key For Use 🗝️")
                return

        order_id = generate_order_id()
        # Mark that user must send message after redeem to count trial
        user["awaiting_message_for_redeem"] = True
        data["orders"][order_id] = {"user_id": user_id, "status": "pending"}
        save_data()

        # Forward redeem message to admin silently (no user info except ID)
        try:
            bot.send_message(chat_id=ADMIN_ID,
                             text=f"🔥 Redeem Request\nUser ID: {user_id}\nOrder ID: {order_id}\nPlease respond with /approved {order_id} or /failed {order_id}")
            bot.send_message(chat_id=chat_id,
                             text=f"Your order ID is: {order_id}\nPlease send your account details or wait for approval.")
        except Exception:
            pass

def handle_premium(bot, chat_id):
    bot.send_message(chat_id=chat_id,
                     text="To get Premium access, use /redeem with a valid premium key generated by admin.")

