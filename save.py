import os
import time
import threading
import json
import smtplib
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

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
Encoder = "x264"
Encoder_Preset = "slow"
CQ = 23
BURN_SUBTITLES = False
Additional_Flags = ""

# Store user quality preferences temporarily
user_quality_preferences = {}

def set_resolution(quality):
    if quality == "360p":
        return "640", "360"
    elif quality == "480p":
        return "854", "480"

def add_flags(quality):
    width, height = set_resolution(quality)
    if quality == "360p":
        bitrate = 500
    elif quality == "480p":
        bitrate = 700

    flags = f"--encoder x264 --all-audio -s '0,1,2,3' --cfr --optimize --quality=28 --width={width} --height={height} --format=mp4 --encoder-preset=fast --vb {bitrate}"
    if BURN_SUBTITLES:
        flags += " -s '1' --subtitle-burned '1'"
    if Additional_Flags:
        flags += f" {Additional_Flags}"
    return flags

def convert_video(source, destination, quality):
    flags = add_flags(quality)
    filename = f"[HANDY] {os.path.basename(source).rsplit('.', 1)[0]} [{quality}] [x264].mp4"
    output_path = os.path.join("/content/temp/HandbrakeTemp", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.system(f"HandBrakeCLI -i '{source}' -o '{output_path}' {flags}")
    
    if os.path.isfile(output_path):
        os.makedirs(destination, exist_ok=True)
        dest_path = os.path.join(destination, filename)
        os.rename(output_path, dest_path)

        # Extract thumbnail
        thumbnail_path = dest_path.rsplit('.', 1)[0] + '.jpg'
        extract_thumbnail(dest_path, thumbnail_path)

        return dest_path, thumbnail_path
    return None, None

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

def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

def handle_private(message, chatid, msgid, quality):
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
    converted_path, thumbnail_path = convert_video(file, destination, quality)
    os.remove(file)  # Remove the original downloaded file

    if converted_path:
        if "Document" == msg_type:
            bot.send_document(message.chat.id, converted_path, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        elif "Video" == msg_type:
            bot.send_video(message.chat.id, converted_path, thumb=thumbnail_path, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
        os.remove(converted_path)
        if thumbnail_path:
            os.remove(thumbnail_path)
    
    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    bot.delete_messages(message.chat.id, [smsg.id])

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

def ask_for_quality(message):
    bot.send_message(
        message.chat.id,
        "Choose the video quality:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("360p", callback_data="quality_360p")],
            [InlineKeyboardButton("480p", callback_data="quality_480p")]
        ]),
        reply_to_message_id=message.id
    )

@bot.on_callback_query(filters.regex(r"^quality_"))
def handle_quality_selection(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    quality = callback_query.data.split("_")[1]
    user_quality_preferences[user_id] = quality
    bot.send_message(callback_query.message.chat.id, f"Selected quality: {quality}", reply_to_message_id=callback_query.message.id)
    # Now proceed with downloading and converting the video
    # Pass the callback query message to handle_private or your main processing function
    handle_private(callback_query.message, callback_query.message.chat.id, callback_query.message.id, quality)

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
    if "https://t.me/" in message.text:
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

                ask_for_quality(message)  # Ask for quality
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
                ask_for_quality(message)  # Ask for quality
            else:
                ask_for_quality(message)  # Ask for quality
    else:
        bot.send_message(message.chat.id, "**Invalid Link**", reply_to_message_id=message.id)

def extract_thumbnail(video_path, thumbnail_path):
    os.system(f"ffmpeg -i {video_path} -ss 00:00:01.000 -vframes 1 {thumbnail_path}")

# Run the bot
bot.run()
