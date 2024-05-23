
import os
import time
import threading
import json
import smtplib
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load configuration
with open('config.json', 'r') as f:
    DATA = json.load(f)

def getenv(var):
    return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN")
api_hash = getenv("HASH")
api_id = getenv("ID")
bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
    acc.start()
else:
    acc = None

# Download and install tools
os.system("wget -qq https://github.com/vot/ffbinaries-prebuilt/releases/download/v4.2.1/ffmpeg-4.2.1-linux-64.zip")
os.system("unzip -qq ffmpeg-4.2.1-linux-64.zip -d /usr/local/bin/")
os.system("rm -f ffmpeg-4.2.1-linux-64.zip")
os.system("add-apt-repository ppa:stebbins/handbrake-releases -y")
os.system("apt-get update")
os.system("apt-get install -y handbrake-cli")

# Configuration for conversion
RESOLUTION = "360p"
Encoder = "x265"
Encoder_Preset = "ultrafast"
CQ = 30
BURN_SUBTITLES = False
Additional_Flags = ""

def set_resolution():
    return "480", "360"

def add_flags():
    width, height = set_resolution()
    flags = f"--encoder {Encoder} --all-audio -s '0,1,2,3' --cfr --optimize --quality={CQ} --width={width} --height={height} --format=mp4 --encoder-preset={Encoder_Preset}"
    if BURN_SUBTITLES:
        flags += " -s '1' --subtitle-burned '1'"
    if Additional_Flags:
        flags += f" {Additional_Flags}"
    return flags

def convert_video(source, destination):
    flags = add_flags()
    filename = f"[HANDY] {os.path.basename(source).rsplit('.', 1)[0]} [360p] [x265].mp4"
    output_path = os.path.join("/content/temp/HandbrakeTemp", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.system(f"HandBrakeCLI -i '{source}' -o '{output_path}' {flags}")
    
    if os.path.isfile(output_path):
        os.makedirs(destination, exist_ok=True)
        dest_path = os.path.join(destination, filename)
        os.rename(output_path, dest_path)
        return dest_path
    return None

# Download status
def downstatus(statusfile, message):
    while True:
        if os.path.exists(statusfile):
            break
        time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Downloaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

# Upload status
def upstatus(statusfile, message):
    while True:
        if os.path.exists(statusfile):
            break
        time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Uploaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

# Progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

# Handle private messages
def handle_private(message, chatid, msgid):
    msg = acc.get_messages(chatid, msgid)
    msg_type = get_message_type(msg)
    
    if "Text" == msg_type:
        bot.send_message(message.chat.id, msg.text, entities=msg.entities, reply_to_message_id=message.id)
        return
    
    smsg = bot.send_message(message.chat.id, '__Downloading__', reply_to_message_id=message.id)
    dosta = threading.Thread(target=lambda: downstatus(f'{message.id}downstatus.txt', smsg), daemon=True)
    dosta.start()
    file = acc.download_media(msg, progress=progress, progress_args=[message, "down"])
    os.remove(f'{message.id}downstatus.txt')

    upsta = threading.Thread(target=lambda: upstatus(f'{message.id}upstatus.txt', smsg), daemon=True)
    upsta.start()

    # Convert video
    destination = "/content/temp/HandbrakeOutput"
    converted_path = convert_video(file, destination)
    os.remove(file)  # Remove the original downloaded file

    if converted_path:
        if "Document" == msg_type:
            bot.send_document(message.chat.id, converted_path, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        elif "Video" == msg_type:
            bot.send_video(message.chat.id, converted_path, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        os.remove(converted_path)
    
    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id, [smsg.id])

# Get the type of message
def get_message_type(msg):
    try:
        msg.document.file_id
        return "Document"
    except: pass
    try:
        msg.video.file_id
        return "Video"
    except: pass
    try:
        msg.animation.file_id
        return "Animation"
    except: pass
    try:
        msg.sticker.file_id
        return "Sticker"
    except: pass
    try:
        msg.voice.file_id
        return "Voice"
    except: pass
    try:
        msg.audio.file_id
        return "Audio"
    except: pass
    try:
        msg.photo.file_id
        return "Photo"
    except: pass
    try:
        msg.text
        return "Text"
    except: pass

@bot.on_message(filters.command(["start"]))
def send_start(client, message):
    bot.send_message(message.chat.id, 
                     f"👋 Hi **{message.from_user.mention}**, I am Save Restricted Bot, I can send you restricted content by its post link\n\n{USAGE}",
                     reply_markup=InlineKeyboardMarkup([
                         [InlineKeyboardButton("🌐 Source Code", url="https://github.com/bipinkrish/Save-Restricted-Bot")]
                     ]), 
                     reply_to_message_id=message.id)

@bot.on_message(filters.text)
def save(client, message):
    # Logic to handle the message content and trigger download, conversion, and upload
    # joining chats
    if "https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text:
        if acc is None:
            bot.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
            return

        try:
            acc.join_chat(message.text)
            bot.send_message(message.chat.id, "**Chat Joined**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            bot.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            bot.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)
        except Exception as e:
            bot.send_message(message.chat.id, f"**Error** : __{e}__", reply_to_message_id=message.id)
    elif "https://t.me/" in message.text:
        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())
        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        for msgid in range(fromID, toID + 1):
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])

                if acc is None:
                    bot.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                    return

                handle_private(message, chatid, msgid)
            elif "https://t.me/b/" in message.text:
                username = datas[4]

                if acc is None:
                    bot.send_message(message.chat.id, f"**String Session is not Set**", reply_to_message_id=message.id)
                    return

                try:
                    chatid = acc.get_chat(username).id
                except UsernameNotOccupied:
                    bot.send_message(message.chat.id, "**Invalid Username**", reply_to_message_id=message.id)
                    return
                handle_private(message, chatid, msgid)
            else:
                handle_private(message, datas[3], msgid)
    else:
        bot.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)

# Run the bot
bot.run()
