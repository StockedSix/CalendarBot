# IMPORT
import discord
import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import time
from dateparser.search import search_dates

# OUTLINE
intents = discord.Intents.default()
intents.message_content = True
load_dotenv()

client = discord.Client(intents=intents)
operator = "("


reminders = []  # List of (user_id, message, trigger_time)



from dateparser.search import search_dates

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith(f'{operator}remindme'):
        try:
            content = message.content[len(f'{operator}remindme'):].strip()
            #print(f'Input: {content}')

            # Use dateparser's search_dates to extract datetime expressions
            results = search_dates(content, settings={"PREFER_DATES_FROM": "future"})
            if not results:
                await message.channel.send("⚠️ Couldn't understand the time. Try formats like `in 10 minutes`, `tomorrow 9am`, or `2025-6-1T21:57`.")
                return

            # Take the first matched date string and parsed datetime
            date_str, parsed_time = results[0]
            #print(f'Found time: "{date_str}" => {parsed_time}')

            if parsed_time < datetime.now():
                await message.channel.send("⚠️ That time is in the past!")
                return

            # Remove the time expression from the message to get the reminder text
            reminder_text = content.replace(date_str, "").strip()
            if not reminder_text:
                reminder_text = "(no message provided)"

            reminders.append((message.author.id, reminder_text, parsed_time))
            await message.channel.send(
                f"✅ Reminder set for {parsed_time.strftime('%Y-%m-%d %H:%M:%S')}!\nMessage: {reminder_text}"
            )
            print(f'Reminder set: {message.author.id} - "{reminder_text}" time: {parsed_time} at {datetime.now()}')

        except Exception as e:
            print("Error parsing reminder:", e)
            await message.channel.send("❌ Something went wrong. Try a format like:\n`(remindme in 10 minutes Take a break`")





# Background task to check for reminders every 60 seconds
async def check_reminders():
    await client.wait_until_ready()
    while not client.is_closed():
        now = datetime.now()
        due = [r for r in reminders if r[2] <= now]

        for user_id, message_text, _ in due:
            try:
                user = await client.fetch_user(user_id)
                await user.send(f"⏰ Reminder: {message_text}")
            except Exception as e:
                print(f"Could not send reminder to user {user_id}: {e}")

        # Remove sent reminders
        for r in due:
            reminders.remove(r)

        await asyncio.sleep(60)

# RUN

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    client.loop.create_task(check_reminders())  # Start the background reminder check

client.run(os.getenv("CALENDARBOT_KEY"))
