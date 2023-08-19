import sys
import os

CURR_DIR = os.path.dirname(os.path.abspath(__file__)).split(os.sep)
#print(CURR_DIR)

sys.path.append(f"{os.sep.join(CURR_DIR[:-1])}/site-packages")
# print(__file__)
# print(CURR_DIR)

# load bot key
with open(f"{os.sep.join(CURR_DIR)}{os.sep}.env") as file:
    KEY = file.readline().strip()


import discord
from discord.ext import commands, tasks

import re
import random
from asyncio import sleep, get_event_loop

from yt_dlp import YoutubeDL




help_command = commands.DefaultHelpCommand(
    no_category = "Commands"
)

bot = commands.Bot(command_prefix="!", intents = discord.Intents.all(), help_command=help_command)

bot.playing = False
bot.looping = False
bot.paused = False



async def ainput(string: str="") -> str:
    await get_event_loop().run_in_executor(
        None, lambda s=string: sys.stdout.write(s)
    )
    return await get_event_loop().run_in_executor(
        None, sys.stdin.readline
    )


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Your Suffering | !help"))
    print('Bot {0.user} is up and running!'.format(bot))
    print("separate commands with '::'")
    while False:
        cmd = await ainput()
        if cmd in ["exit\n", "exit()\n"]:
            raise KeyboardInterrupt
            cmd = cmd.split("::")

        if cmd[0] == "!send" and len(cmd)==3:
            try:
                await bot.get_channel(int(cmd[1])).send(cmd[2])
            except Exception as e:
                print(e)
        else:
            print("unknown command")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

ROLL_ADVANTAGE_MODIFIERS = {
    "adv",
    "advantage",
}

ROLL_DISADVANTAGE_MODIFIERS = {
    "dis",
    "disadv",
    "disadvantage",
}

ROLL_MISC_MODIFIERS = {
    "show",
    "showall",
    "list"
}

ROLL_KEYWORDS = ROLL_ADVANTAGE_MODIFIERS | ROLL_DISADVANTAGE_MODIFIERS | ROLL_MISC_MODIFIERS

ROLL_SYNTAX = "Syntax: !roll <quantity><dice> <modifier(s)>"
@bot.command(
    brief=ROLL_SYNTAX,
    description=f"{ROLL_SYNTAX}\nModifier Options: 'adv', 'dis', 'show', '+<roll modifier>'\nExample: !roll 5d8 adv +5"
)
async def roll(ctx, *args): 
    retval   = ""
    roll_results = []
 
    dice = []

    adv = False
    disadv = False
    show = False

    num_modifier = 0

    try:
        if len(args) < 1:
            retval = f"Error: must specify what dice to roll. {ROLL_SYNTAX}"
            raise Exception
        
        # suffix parser
        suffixes = set([arg for arg in args[1:] if arg in ROLL_KEYWORDS])
        if (len(suffixes & ROLL_ADVANTAGE_MODIFIERS)):
            adv = True
        if (len(suffixes & ROLL_DISADVANTAGE_MODIFIERS)):
            disadv = True 
        if (len(suffixes & ROLL_MISC_MODIFIERS)):
            show = True
        
        if (adv and disadv):
            retval = f"Error: cannot roll with both advantage and disadvantage. {ROLL_SYNTAX}"
            raise Exception

        # modifier parser
        num_modifiers = [arg for arg in args[1:] if arg[0] in ['+', '-']]

        if (len(num_modifiers) > 0):
            if (len(num_modifiers) > 1):
                retval = f"Error: only include one numerical modifier. Example: '!roll d20 +5'"
                raise Exception
        
            try:
                num_modifier = int(num_modifiers[0][1:])
            except Exception:   
                retval = f"Error: invalid numerical modifier: '{num_modifier}'. Syntax: '+<modifier>'"
                raise Exception
        
        dice = [arg.lower() for arg in args if re.fullmatch(r"\d*[dD]\d+$", arg)]
        
        if (len(dice) < 1):
            retval = f"Error: no dice found. {ROLL_SYNTAX}"
            raise Exception

        # make sure dice make sense with modifiers
        if (len({die.split("d")[-1] for die in dice}) > 1 and (adv or disadv)):
            retval = f"Error: can only use advantage/disadvantage with a single type of die"
            raise Exception

        # total dice rolled
        dice_qty = 0

        for die in dice:
            values = [int(i) if i != '' else 1 for i in die.split("d")]
            
            dice_qty += values[0]
            # check quantity of dice
            if (dice_qty > 100 or dice_qty < 1):
                retval = f"Error: must roll between 1 and 100 dice."
                raise Exception

            # if adv or disadv, ensure atleast 2 dice are rolled
            if ((adv or disadv) and len(dice) == 1):
                if (values[0] < 2):
                    values[0] = 2
            
            # check how many faces die has
            if (values[1] > 100 or values[1] < 2):
                retval = f"Error: dice must have between 2 and 100 faces. (You tried: {die})"
                raise Exception
            
            # actually roll
            for i in range(values[0]):
                roll_results.append(random.randint(1, int(values[1])))
        
        # make response
        retval += "**"
        if adv:
            retval += f"{max(roll_results) + num_modifier} "
        elif disadv:
            retval += f"{min(roll_results) + num_modifier} "
        else:
            retval += f"{sum(roll_results) + num_modifier} "
        retval += "**"

        # check for natural 20 or natural 1
        if (
            len(dice) == 1 and
            dice[0][-2:] == "20"
        ):
            l = len(roll_results)

            if adv:
                if (max(roll_results) == 20):
                    retval += "(Natural 20)"
                elif (roll_results == [1 for _ in range(l)]):
                    # check for case where even with adv, all rolls are 1
                    retval += "(Natural 1)"

            if disadv:
                if (min(roll_results) == 1):
                    retval += "(Natural 1)"
                elif (roll_results == [20 for _ in range(l)]):
                    retval += "(Natural 20)"

            if dice[0][0] in ["1", "d"]:
                if (roll_results[0] == 1):
                    retval += "(Natural 1)"
                elif (roll_results[0] == 20):
                    retval += "(Natural 20)"

        # show raw rolls
        if (adv or disadv or show):
            if (len(roll_results) > 30):
                retval += "\nWarning: cannot show more than 30 dice rolls"
            else:
                retval += f"\nAll rolls: {', '.join([str(i) for i in roll_results])}"
    
        # print(retval)
    #finally:
    #    pass
    except Exception as e:
        print(e)
    
    # print(retval)
    await ctx.reply(retval)


JOIN_SYNTAX = "Syntax: !join <channel>"

@bot.command(
    brief=JOIN_SYNTAX,
    description=f"{JOIN_SYNTAX}\n Bot will join the specified channel, or user's channel if not specified"
)
async def join(ctx, *args):

    if (len(args) > 0):
        for c in (c for c in ctx.guild.channels if c.type==discord.ChannelType.voice):
            if (c.name == args[0]):
                channel = c
                break
        else:
            channel = None
    else:
        if (ctx.author.voice is None):
            channel = None
        else:
            channel = ctx.author.voice.channel
    if (channel is None):
        await ctx.reply(f"Error: voice channel {(args[0] + ' ' if (len(args)>0) else '')}not found")
        return

    try:
        await channel.connect()
    except discord.ClientException: #if in another channel
        voice = ctx.voice_client
        await ctx.voice_client.move_to(channel)

        
LEAVE_SYNTAX = "Syntax: !leave"
@bot.command(
    brief=LEAVE_SYNTAX,
    description=f"{LEAVE_SYNTAX}\nBot will leave its current channel"
)
async def leave(ctx):

    if (ctx.voice_client is None):
        await ctx.reply("Error: bot is not in a channel")
        return
    await ctx.voice_client.disconnect()


PAUSE_SYNTAX = "Syntax: !pause"
@bot.command(
    brief=PAUSE_SYNTAX,
    description=f"{PAUSE_SYNTAX}\nIf the bot is playing a song, pause. '!resume' to resume"
)
async def pause(ctx):
    
    voice = ctx.voice_client

    if (voice is None):
        await ctx.reply("Error: bot is not connected to a channel")
        return

    if (bot.paused):
        await ctx.reply("Error: bot is already paused")
        return

    voice.pause()
    bot.paused = True


RESUME_SYNTAX = "Syntax: !resume"
@bot.command(
    brief=PAUSE_SYNTAX,
    description=f"{RESUME_SYNTAX}\nIf the bot is paused, resume"
)
async def resume(ctx):
    voice = ctx.voice_client

    if (not bot.playing):
        await ctx.reply("Error: bot is not playing a song")
        return

    if (bot.paused == False):
        await ctx.reply("Error: bot is already playing")
        return

    bot.paused = False
    if (not voice.is_playing()):
        voice.resume()


STOP_SYNTAX = "Syntax: !stop"
@bot.command(
    brief=STOP_SYNTAX,
    description=f"{STOP_SYNTAX}\nStop the current song the bot is playing"
)
async def stop(ctx):
    
    if (not bot.playing):
        await ctx.reply("Error: bot is not currently playing a song")
        return

    voice = ctx.voice_client

    #reset bot stat
    bot.playing = False
    bot.looping = False
    bot.paused = False

    voice.stop()


SKIP_SYNTAX = "Syntax: !skip"
@bot.command(
    brief=SKIP_SYNTAX,
    description=f"{SKIP_SYNTAX}\nIf the bot is playing a playlist, skip current song"
)
async def skip(ctx):

    if (not bot.playing):
        await ctx.reply("Error: bot is not currently playing a song")
        return
    ctx.voice_client.stop()



YDL_OPTIONS = {'format': 'bestaudio', 'youtube_include_dash_manifest':'False'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

bot.song_index = 0

PLAY_SYNTAX = "Syntax: !play <url> <options>"
@bot.command(
    brief=PLAY_SYNTAX,
    description=f"{PLAY_SYNTAX}\nPlay the specified song/playing (youtube link). Play options: 'loop', '<volume>%'"
)
async def play(ctx, url, *args):

    vol = .2 #default
    for i in args:
        if (i[-1] == '%'):
            vol = int(i[:-1])//100

    voice = ctx.voice_client
    if (voice == None): # join if not connected
        await ctx.author.voice.channel.connect()
        voice = ctx.voice_client

    # with YoutubeDL(YDL_OPTIONS) as ydl:
      #  info = ydl.extract_info(url, download=False)
    

    # if ('entries' in info):
      #  bot.queue = [i for i in info['entries']]
    # else:
      #  bot.queue = [info]
    
    # check for specified playlist index
    check = re.findall("&index=\d+", url)
    if (len(check) > 0):
        bot.song_index = int(check[-1].split('=')[-1]) - 1
    else:
        bot.song_index = 0


    bot.playing = True
    is_playlist = False

    while bot.playing:
        

        specific_options = {**YDL_OPTIONS, **{'playlist_items': f'{bot.song_index+1}'}}
        
        with YoutubeDL(specific_options) as ydl:
            current_song = ydl.extract_info(url, download=False)
            # print(bot.queue[bot.queue_index]['original_url'])
            #URL = vid_info['']

        

        # print([key for key in bot.queue[bot.queue_index]])
        # URL = bot.queue[bot.queue_index]['format'][0]['url']
        # print(bot.queue[bot.queue_index]['original_url'])
        # URL = bot.queue[bot.queue_index]['original_url']
        # URL = bot.queue[bot.queue_index]['url']
        length = 1

        try:
            URL = current_song['entries'][0]['url']
            is_playlist = True
            length = int(current_song['playlist_count'])
        except KeyError:
            URL = current_song['url']

        bot.looping = False
        bot.paused = False
        if voice.is_playing():
            voice.stop()

        if ("loop" in args):
            bot.looping = True
        
        
        #source = await ydl.YTDLSource.create_source(ctx, URL, loop=self.bot.loop, download=False)    
        #voice.play(source)
        
        voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
        voice.source = discord.PCMVolumeTransformer(voice.source, volume=vol)
        
        if (is_playlist):
            message = f"Playing **{current_song['entries'][0]['title']}** ({bot.song_index+1}/{length})"
        else:
            message = f"Playing **{current_song['title']}**"
        await ctx.send(message)


        while (voice.is_playing() or bot.paused):
            await sleep(5)

        if (bot.song_index+1 < length):
            bot.song_index += 1
        else:
            if not bot.looping:
                bot.playing = False
            bot.song_index = 0


    bot.playing = False
    bot.looping = False
    bot.paused = False




bot.run(KEY)

