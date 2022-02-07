import datetime
from time import time
from click import pass_context
import discord
from discord import message
from discord.ext import commands
from collections import defaultdict
from pymongo import MongoClient

client = commands.Bot(command_prefix='tmt',activity = discord.Game("hide and seek with guidance counselors")) #initializing the bot

mongo = MongoClient("mongodb+srv://IbraTech:ibratech@cluster0.mj3ax.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")

db = client.testdb = mongo["myFirstDatabase"] #selecting the database

timetables = defaultdict(dict)
@client.command(pass_context=True)
async def setup(ctx):
    #if the author is in the db database
    if (db.users.find_one({"_id": ctx.message.author.id})):
        embed = discord.Embed(title="❌ TMtimeTable Error", description="You already have a timetable set up", color=0x1F99CD)
        await ctx.send(embed=embed)        
    else:
        dict = {"_id": ctx.message.author.id, "timetable": {"p1": "", "p2": "", "p3": "", "p4": ""}}
        embed = discord.Embed(title="❓ TMtimeTable Input", description="Please enter your period one class", color=0x1F99CD)
        await ctx.send(embed=embed)
        #get the first class, make sure the original author is the author of the message
        p1 = await client.wait_for('message', check=lambda message: message.author == ctx.message.author)
        #add the class to the database
        dict["timetable"]["p1"] = p1.content
        embed = discord.Embed(title="❓ TMtimeTable Input", description="Please enter your period two class", color=0x1F99CD)
        await ctx.send(embed=embed)
        p2 = await client.wait_for('message', check=lambda message: message.author == ctx.message.author)
        dict["timetable"]["p2"] = p2.content
        embed = discord.Embed(title="❓ TMtimeTable Input", description="Please enter your period three class", color=0x1F99CD)
        await ctx.send(embed=embed)
        p3 = await client.wait_for('message', check=lambda message: message.author == ctx.message.author)
        dict["timetable"]["p3"] = p3.content
        embed = discord.Embed(title="❓ TMtimeTable Input", description="Please enter your period four class", color=0x1F99CD)
        await ctx.send(embed=embed)
        p4 = await client.wait_for('message', check=lambda message: message.author == ctx.message.author)
        dict["timetable"]["p4"] = p4.content
        embed = discord.Embed(title="🔔TMTimeTable Notification", description="Success! Your timetable has been setup", color=0x1F99CD)
        await ctx.send(embed=embed)
        db.users.insert_one(dict)
        
@client.command(pass_context=True)
async def viewTimeTable(ctx, person: discord.Member = None):
    #check if the author is in the timetables dictonary
    if (person == None):
        #if the author is in the db database
        if (not db.users.find_one({"_id": ctx.message.author.id})):
            embed = discord.Embed(title="❌ TMtimeTable Error", description="You don't have a timetable setup yet. Use tmtsetup to setup a timetable!", color=0x1F99CD)
            await ctx.send(embed=embed)  
        else:
            #get day of month
            dayOfMonth = datetime.datetime.now().day
            day = dayOfMonth % 2
            if (day == 1):
                embed = discord.Embed(title="📅 TMtimeTable TimeTable", description="Today is " + str(dayOfMonth) + "th of the month. Your timetable is:", color=0x1F99CD)
                #add from db[user][timetable]
                embed.add_field(name="Period 1", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p1"], inline=False)
                embed.add_field(name="Period 2", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p2"], inline=False)
                embed.add_field(name="Period 3", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p3"], inline=False)
                embed.add_field(name="Period 4", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p4"], inline=False)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title="📅 TMtimeTable TimeTable", description="Today is " + str(dayOfMonth) + "th of the month. Your timetable is:", color=0x1F99CD)
                #add from db[user][timetable]
                embed.add_field(name="Period 1", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p2"], inline=False)
                embed.add_field(name="Period 2", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p1"], inline=False)
                embed.add_field(name="Period 3", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p4"], inline=False)
                embed.add_field(name="Period 4", value=db.users.find_one({"_id": ctx.message.author.id})["timetable"]["p3"], inline=False)
                await ctx.send(embed=embed)
    else:
        #check if person is in the db database
        if (db.users.find_one({"_id": person.id})):
            #get day of month
            dayOfMonth = datetime.datetime.now().day
            day = dayOfMonth % 2
            if (day == 1):
                embed = discord.Embed(title="📅 TMtimeTable TimeTable", description="Today is " + str(dayOfMonth) + "th of the month. Your timetable is:", color=0x1F99CD)
                #add from db[user][timetable]
                embed.add_field(name="Period 1", value=db.users.find_one({"_id": person.id})["timetable"]["p1"], inline=False)
                embed.add_field(name="Period 2", value=db.users.find_one({"_id": person.id})["timetable"]["p2"], inline=False)
                embed.add_field(name="Period 3", value=db.users.find_one({"_id": person.id})["timetable"]["p3"], inline=False)
                embed.add_field(name="Period 4", value=db.users.find_one({"_id": person.id})["timetable"]["p4"], inline=False)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title="📅 TMtimeTable TimeTable", description="Today is " + str(dayOfMonth) + "th of the month. Your timetable is:", color=0x1F99CD)
                #add from db[user][timetable]
                embed.add_field(name="Period 1", value=db.users.find_one({"_id": person.id})["timetable"]["p2"], inline=False)
                embed.add_field(name="Period 2", value=db.users.find_one({"_id": person.id})["timetable"]["p1"], inline=False)
                embed.add_field(name="Period 3", value=db.users.find_one({"_id": person.id})["timetable"]["p4"], inline=False)
                embed.add_field(name="Period 4", value=db.users.find_one({"_id": person.id})["timetable"]["p3"], inline=False)
                await ctx.send(embed=embed)
        else:
            #ping user that they don't have a timetable setup
            embed = discord.Embed(title="❌ TMtimeTable Error", description="{person.mention} doesn't have a timetable setup yet. Tell them to use tmtsetup to setup a timetable!", color=0x1F99CD)
            await ctx.send(embed=embed)

@client.command(pass_context=True)
async def reset(ctx):
    #check if the author is in the timetables db['users']
    if (not db.users.find_one({"_id": ctx.message.author.id})):
        embed = discord.Embed(title="❌ TMtimeTable Error", description="You don't have a timetable setup yet. Use tmtsetup to setup a timetable!", color=0x1F99CD)
        await ctx.send(embed=embed)  
    else:
        #remove thier timetable from the db
        db.users.delete_one({"_id": ctx.message.author.id})
        embed = discord.Embed(title="🔔TMtimeTable Notification", description="Your timetable has been cleared! Don't forget to reset it with tmtsetup", color=0x1F99CD)
        await ctx.send(embed=embed)  

#send message when bot is ready
@client.event
async def on_ready():
    print("The bot is ready!")

client.run("OTQwMDM0NDQ0OTgxNTkyMDk2.YgBhTA.0deI66Jn4Fp4M3S1WLxdA0wlSNo") #token