import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re

# Load environment variables
load_dotenv()
TOKEN = os.getenv('discord_token')

# Set bot intents
intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix=".", intents=intents)

# Dictionary for voice clients
voice_clients = {}

# Set FFmpeg Path Manually (in case it's not detected)
FFMPEG_PATH = "ffmpeg"  # Assuming it's in the environment path

# YTDL options
yt_dl_options = {
    "format": "bestaudio/best",
    "noplaylist": True,  # Prevents downloading entire playlists
}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

# FFmpeg options for streaming
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"',
}

@client.event
async def on_ready():
    print(f'{client.user} is now jamming!')

async def join_voice_channel(ctx):
    """ Joins the user's voice channel if not already connected. """
    if ctx.author.voice:
        voice_channel = ctx.author.voice.channel
        if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
            voice_client = await voice_channel.connect()
            voice_clients[ctx.guild.id] = voice_client
        return voice_clients[ctx.guild.id]
    else:
        await ctx.send("You're not in a voice channel!")
        return None

@client.command(name="play")
async def play(ctx, *, query):
    """ Plays a song from YouTube by searching or using a direct link. """
    voice_client = await join_voice_channel(ctx)
    if not voice_client:
        return

    try:
        # If it's not a direct YouTube link, search for the video
        if "youtube.com" not in query and "youtu.be" not in query:
            query_string = urllib.parse.urlencode({"search_query": query})
            search_url = f"https://www.youtube.com/results?{query_string}"
            content = urllib.request.urlopen(search_url)
            search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
            query = f"https://www.youtube.com/watch?v={search_results[0]}"

        # Get the direct audio stream URL
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        audio_url = data["url"]

        # Play audio stream
        player = discord.FFmpegOpusAudio(audio_url, executable=FFMPEG_PATH, **ffmpeg_options)
        voice_client.play(player, after=lambda e: print(f"Player error: {e}") if e else None)

        await ctx.send(f"Now playing: **{data['title']}** 🎶")
    except Exception as e:
        await ctx.send("Error playing the song.")
        print(e)

@client.command(name="pause")
async def pause(ctx):
    """ Pauses the currently playing song. """
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_playing():
        voice_clients[ctx.guild.id].pause()
        await ctx.send("Paused ⏸️")

@client.command(name="resume")
async def resume(ctx):
    """ Resumes the paused song. """
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_paused():
        voice_clients[ctx.guild.id].resume()
        await ctx.send("Resumed ▶️")

@client.command(name="stop")
async def stop(ctx):
    """ Stops playing and disconnects from the voice channel. """
    if ctx.guild.id in voice_clients:
        await voice_clients[ctx.guild.id].disconnect()
        del voice_clients[ctx.guild.id]
        await ctx.send("Stopped and left the voice channel 🚪")

client.run(TOKEN)
