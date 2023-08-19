import sys
import os

CURR_DIR = os.getcwd()
#print(CURR_DIR)

loaded_packages = False
try:
    os.chdir("..")
    #print(os.getcwd())
    sys.path.append(f"{os.getcwd()}/site-packages")
    loaded_packages = True
except Exception as e:
    print(e)

os.chdir(CURR_DIR)
if (not loaded_packages):
    raise Exception("Could not load site-packages")

# load bot key
with open(".env") as file:
    KEY = file.readline().strip()


import discord
from discord.ext import commands, tasks

import re
import random

from asyncio import sleep, get_event_loop


help_command = commands.DefaultHelpCommand(
    no_category = "Commands"
)

bot = commands.Bot(command_prefix="!", intents = discord.Intents.all(), help_command=help_command)

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
        if (len({die.split("d")[-1] for die in dice}) > 1):
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

            if dice[0] in ["1", "d"]:
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


bot.run(KEY)



