# IMPORT
import discord
import os
from dotenv import load_dotenv
import asyncio
import time
import re
from datetime import datetime
import mysql.connector






# OUTLINE
intents = discord.Intents.default()
intents.message_content = True
load_dotenv()

client = discord.Client(intents=intents)
operator = "("
dm = False
reminderCheckInterval = 20

db = mysql.connector.connect(host=os.getenv("SQLHOST"), user=os.getenv("SQLUSER"), password=os.getenv("SQLPASS"), database=os.getenv("SQLDB"))
cursor = db.cursor()



# COMMANDS
commandList = {
    "calendarset": "Make a repeating reminder message: {operator}calendarset {{UNIXTIMESTAMP}} {{INTERVAL}} {{MESSAGE}}",
    "delmes": "Delete a reminder or error message by replying to it: {operator}delmes",
    "curunix": "Print current unix timestamp",
    "interval": "View how Intervals work information",
    "help": "you're looking at it"
}

# MAIN
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower().startswith(f'{operator}calendarset'):
        try:
            content = message.content[len(f'{operator}calendarset'):].strip()
            #print(f'Input: {content}')

            contentSplit = content.split(None, 2)
            if len(contentSplit) < 3:
                raise ValueError("Missing components, obtained parts: " + str(contentSplit))
            
            unixValue = parseDuration(contentSplit[1])
            print(unixValue)
            curTime = int(datetime.now().timestamp())
            if int(contentSplit[0]) < int(curTime-unixValue+1):
                await message.channel.send("❌ The given time is too far in the past. Please provide a future timestamp or up to one interval in the past.", delete_after=5)
                #await message.channel.send(f"debug: Current time: <t:{curTime}:D> <t:{curTime}:T> MaxTime: <t:{int(contentSplit[0]) + int(unixValue)}:D> <t:{int(contentSplit[0]) + int(unixValue)}:T> \nGiven time: <t:{contentSplit[0]}:D> <t:{contentSplit[0]}:T> Interval: {contentSplit[1]} curTime: <t:{int(datetime.now().timestamp())}:D> <t:{int(datetime.now().timestamp())}:T>")
                return
            if unixValue < reminderCheckInterval:
                await message.channel.send("❌ The interval must be at least {reminderCheckInterval} seconds.")
                return

            reminderSend = await message.channel.send(
                f"{contentSplit[2]}: <t:{contentSplit[0]}:F> `(every {contentSplit[1]})`"
            )

            try: 
                await message.delete()
            except discord.Forbidden as df:
                print(f"No delete message permissions: {df}")
            except Exception as e: 
                print(f"delMessage missing: {message.id}: {e}")



            if dm == True: #DM user confirmation
                try:
                    await message.author.send(f"Reminder set for <t:{contentSplit[0]}:F> repeating every {contentSplit[1]} with message: {contentSplit[2]}")
                except Exception as e:
                    print(f"Could not send DM to user {message.author.id}: {e}")
                    await message.channel.send(f"❌ Could not send you a DM. Please check your privacy settings.", delete_after=2)


            newReminder = (reminderSend.id, reminderSend.channel.id, message.author.id, int(contentSplit[0]), int(unixValue), contentSplit[2], contentSplit[1])
            
            try:
                query = """ INSERT INTO reminder_table 
                (reminder_id, reminder_channel, reminder_user, reminder_nexttime, reminder_interval, reminder_content, reminder_intervalvar) 
                VALUES (%s, %s, %s, %s, %s, %s, %s) """
                cursor.execute(query, newReminder)
                db.commit()
            except mysql.connector.Error as err:
                print(f"Error inserting reminder into database: {err}")
                await message.channel.send("❌ An error occurred while saving the reminder. Please try again later.")
                return
            except Exception as e: 
                print(f"Unexpected error inserting reminder: {e}")



        except ValueError as ve:
            print("Error parsing reminder:", ve)
            await message.channel.send(f"❌ Invalid format. Format:\n`{operator}calendarset {{UNIXTIMESTAMP}} {{INTERVAL}} {{MESSAGE}}`")
        except Exception as e:
            print("Error parsing reminder:", e)
            await message.channel.send(f"❌An error occurred. Shout at Stocked cause he fucked up")

    if message.content.lower().startswith(f'{operator}delmes'):
        try:
            if message.author == client.user:
                return

            if message.reference is None or message.reference.message_id is None:
                await message.channel.send("❌ Please reply to the reminder message you want to delete.", delete_after=2)
                return

            try:
                query = """
                        SELECT reminder_user FROM reminder_table 
                            WHERE reminder_id = %s
                            """
                cursor.execute(query, (message.reference.message_id,))
                responser = cursor.fetchone()
                if responser is None:
                    try:
                        referencedMSG = await message.channel.fetch_message(message.reference.message_id)
                        await referencedMSG.delete()
                        await message.delete()
                    except discord.NotFound:
                        await message.channel.send("❌ The referenced message was not found.", delete_after=2)
                        return
                    return
                
                elif responser[0] == message.author.id:
                    try:
                        referencedMSG = await message.channel.fetch_message(message.reference.message_id)
                        await referencedMSG.delete()
                        await message.delete()
                    except discord.NotFound:
                        await message.channel.send("❌ The referenced message was not found.", delete_after=2)
                        return
                    return
                
                else:
                    await message.channel.send("❌ You can only delete your own reminders.", delete_after=2)
                    return
            except Exception as e:
                print(f"Error checking message reference: {e}")
                await message.channel.send("❌ An error occurred while trying to delete the message.", delete_after=2)
                return



        except Exception as e:
            print("Error parsing delmes command:", e)
            await message.channel.send("❌ An error occurred. Please try again.", delete_after=2)

    if message.content.lower().startswith(f'{operator}curunix'):
        try:
            current_unix = int(datetime.now().timestamp())
            await message.channel.send(f"Current Unix timestamp: {current_unix}")
        except Exception as e:
            print("Error getting current Unix timestamp:", e)

    if message.content.lower().startswith(f'{operator}help'):
        help_message = "Available commands:\n"
        for command, description in commandList.items():
            help_message += f"{command}: {description.format(operator=operator)}\n"
        await message.channel.send(help_message)

    if message.content.lower().startswith(f'{operator}interval'):
        interval_info = (
            f"Reminder intervals can be set using the following format:\n"
            f"`{operator}calendarset {{UNIXTIMESTAMP}} {{INTERVAL}} {{MESSAGE}}`\n"
            f"Where `INTERVAL` can be a combination of:\n"
            f"- `w`: weeks\n"
            f"- `d`: days\n"
            f"- `h`: hours\n"
            f"- `m`: minutes\n"
            f"- `s`: seconds\n"
            f"Examples:\n"
            f"`1w` for 1 week, `2d5h3m` for 2 days, 5 hours, and 3 minutes."
        )
        await message.channel.send(interval_info)



# Background task to check for reminders every 60 seconds
async def check_reminders():
    await client.wait_until_ready()
    while not client.is_closed():
        now = int(datetime.now().timestamp())

        try:
            query = """
            SELECT  reminder_id, reminder_channel, reminder_user, reminder_nexttime,
                    reminder_interval, reminder_content, reminder_intervalvar
            FROM reminder_table
            WHERE reminder_nexttime <= %s
            """
            cursor.execute(query, (now,))
            due = cursor.fetchall()

            if due:
                print(f"Checking reminders at {now}. Due reminders: {len(due)}")

            for messageID, channelID, authorID, reminderTime, intervalTime, messageContent, intervalVar in due:
                try:
                    channel = client.get_channel(channelID)
                    messageToEdit = await channel.fetch_message(messageID)
                    newTime = reminderTime + intervalTime

                    await messageToEdit.edit(content=f"{messageContent}: <t:{newTime}:F> `(every {intervalVar})`")

                    # Update reminder in DB
                    update_query = """
                    UPDATE reminder_table
                    SET reminder_nexttime = %s
                    WHERE reminder_id = %s
                    """
                    cursor.execute(update_query, (newTime, messageID))
                    db.commit()

                except discord.NotFound:
                    delete_query = "DELETE FROM reminder_table WHERE reminder_id = %s"
                    cursor.execute(delete_query, (messageID,))
                    db.commit()
                    print("Deleted reminder message with ID:", messageID)
                except Exception as e:
                    print(f"Could not process reminder for user {authorID}: {e}")

        except Exception as e:
            print(f"Error querying reminders: {e}")

        await asyncio.sleep(reminderCheckInterval)



def parseDuration(preDuration):
    pattern = r"(\d+)([wdhms])"
    matches = re.findall(pattern, preDuration)

    totalSeconds = 0
    unitMults = {
        'w': 604800, # 7*24*60*60
        'd': 86400,  # 24*60*60
        'h': 3600,   # 60*60
        'm': 60,
        's': 1
    }

    for value, unit in matches:
        totalSeconds += int(value) * unitMults[unit]

    return int(totalSeconds)

# RUN

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    client.loop.create_task(check_reminders())  # Start the background reminder check

client.run(os.getenv("CALENDARBOT_KEY"))
