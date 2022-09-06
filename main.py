from audioop import reverse
from cgitb import text
import codecs
import datetime
from email import message
import os
from time import time
import traceback
from click import pass_context
import discord
from discord.ext import commands
from pymongo import MongoClient
import requests
import time

maintenance_mode = False

intents = discord.Intents(messages = True, members = True, guilds = True, emojis = True, reactions = True,)

client = commands.Bot(intents = intents, command_prefix='tmt',activity = discord.Game("hide and seek with guidance counselors")) #initializing the bot
#remove help command
client.remove_command('help')

mongo = MongoClient("mongodb+srv://IbraTech:ibratech@cluster0.mj3ax.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")

db = client.testdb = mongo["myFirstDatabase"] #selecting the database

@client.command(pass_context=True)
async def setup(ctx):
    if maintenance_mode:
        await ctx.send("TMTimeTable is in maintenance mode. Please try again later.")
        return
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
        
@client.command(pass_context=True, aliases=["view", "show", "school", "timetable"])
async def viewTimeTable(ctx, person: discord.Member = None):
    if maintenance_mode:
        await ctx.send("TMTimeTable is in maintenance mode. Please try again later.")
        return 
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
            embed = discord.Embed(title="❌ TMtimeTable Error", description=person.mention + " doesn't have a timetable setup yet. Tell them to use tmtsetup to setup a timetable!", color=0x1F99CD)
            await ctx.send(embed=embed)

@client.command(pass_context=True)
async def reset(ctx):
    if maintenance_mode:
        await ctx.send("TMTimeTable is in maintenance mode. Please try again later.")
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
    global maintenance_mode
    print("Logged in as " + client.user.name)
    #get PC name
    pcName = os.getenv('COMPUTERNAME')
    print ("PC Name: " + pcName)
    if (pcName == "IBRAPC"):
        maintenance_mode = True
        print ("Maintenance Mode Enabled; Bot will not reply to messages")
    #set status as maintenance mode
    await client.change_presence(status=discord.Status.idle, activity=discord.Game("Maintenance Mode; bot will not reply to commands"))
    

@client.command(pass_context=True)
async def listAllPeople(ctx):
    #check if 516413751155621899 used the command
    if (ctx.message.author.id == 516413751155621899):
        #get all _id in the db
        users = db.users.find().distinct("_id")
        print(users)
        #for every user in the db, make an embed and send their schedule
        for i in range (0, len(users)):
            #get the user
            user = client.get_user(users[i])
            #get the timetable
            timetable = db.users.find_one({"_id": users[i]})["timetable"]
            #create embed
            embed = discord.Embed(title="📅 TMtimeTable TimeTable", description=f"{user.mention} timetable is:".format(user), color=0x1F99CD)
            #add from db[user][timetable]
            embed.add_field(name="Period 1", value=timetable["p1"], inline=False)
            embed.add_field(name="Period 2", value=timetable["p2"], inline=False)
            embed.add_field(name="Period 3", value=timetable["p3"], inline=False)
            embed.add_field(name="Period 4", value=timetable["p4"], inline=False)
            #send embed
            await ctx.send(embed=embed)
    else:
        await ctx.send("You don't have permission to use this command 🙄")

#method which gets last message in channel given guild id and channel id
@client.command(pass_context=True)
async def getLastMsg(ctx, guildID, channelID):
    guild = client.get_guild(int(guildID))
    channel = guild.get_channel(int(channelID))
    msg = await channel.history(limit=1).flatten()
    print(msg[0].content)
    print(msg[0].author.name)
    #print time
    print(msg[0].created_at.strftime("%d/%m/%Y %H:%M:%S"))
    

#method which lists all channels in a given guildID, and their ID
@client.command(pass_context=True)
async def listAll(ctx, id):
    #get guild
    guild = client.get_guild(int(id))
    
    #get channels in the guild
    channels = guild.channels
    for c in channels:
        #check if its a text channel
        if (c.type == discord.ChannelType.text):
            print(c.name + " " + str(c.id) + " " + str(c.type))
        
@client.command(pass_context=True)
async def getPerms(ctx, guild):
    #prints all the permissions a bot has ina server
    guild = client.get_guild(int(guild))
    perms = guild.me.guild_permissions
    print(perms['administrator'])

@client.command(pass_context=True)
async def getComputerName(ctx):
    #get computer name
    comName = os.environ['COMPUTERNAME']
    await ctx.send(comName)

@client.command(pass_context=True)
async def newBackup(ctx, guild, channel):
    if (ctx.message.author.id == 516413751155621899):
        guild = client.get_guild(int(guild))
        currentImg = 0
        currentMsg = 0
        #get the channel
        channel = guild.get_channel(int(channel))
        messages = await channel.history(limit=None).flatten()
        textFile = codecs.open("{0} - Backup.html".format(channel), "w", "utf-8")
        textFile.write("<!doctype html>\n<html>\n<head>\n<title>TMTimeTable Channel Backup V2</title>")
        textFile.write("<meta charset='utf-8'>\n <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n  <link rel='preconnect' href='https://fonts.googleapis.com'> \n<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin> \n<link href='https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&display=swap' rel='stylesheet'>\n")
        textFile.write("<style> body { background-color: #36393f; margin: 50px; } h1{ font-family: 'PT Sans', sans-serif; font-size: 1.2rem; color: #fff; margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; } p{ font-family: 'PT Sans', sans-serif; font-size: 0.8rem; color: #fff; margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; display:flex} span{ font-family: 'PT Sans', sans-serif; font-size: 0.8rem; color: #fff; margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; } div{display: inline-block;width: 100%;padding-top: 20px;padding-bottom: 20px;} a{color:white;}html {	scroll-behavior: smooth;} </style> </head> <body>")
        startTime = time.time()
              
        for message in reversed(messages):
            try:
                #check if message is a thread
                textFile.write("<div id = {}>".format(currentMsg))
                #get message author
                fileName = str(message.author)
                fileName = fileName[:-5]
                fileName += ".png"
                if (not os.path.isfile(fileName)):
                    if (message.author.avatar):
                        pfp = message.author.avatar.url
                        #download the profile picture and save it
                        r = requests.get(pfp, allow_redirects=True)
                        open('{}'.format(str(fileName)), 'wb').write(r.content)
                    else:
                        fileName = "data:image/png;base64,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"
                textFile.write("<img src='{0}' alt='{1}' width='50' height='50' style = 'float:left; ;border-radius:50%;margin-right: 20px;'>\n".format(fileName, message.author.name))   
                #check if message is a thread
                #check if author has a nickname
                try:
                    if (message.author.nick != None):
                        textFile.write("<h1>{0} ({1})<span> - {2}</span></h1>\n".format(message.author.name, message.author.nick, message.created_at.strftime("%d/%m/%Y %H:%M:%S")))
                    else:
                        textFile.write("<h1>{0}<span> - {1}</span></h1>\n".format(message.author.name, message.created_at.strftime("%d/%m/%Y %H:%M:%S")))           
                except:
                    print("Failed to get NickName")
                    textFile.write("<h1>{0}<span> - {1}</span></h1>\n".format(message.author.name, message.created_at.strftime("%d/%m/%Y %H:%M:%S")))                
                if(message.reference and not message.thread):
                    #get message reference ID
                    id = message.reference.resolved.id
                    #get message from ID
                    msg = await channel.fetch_message(int(id))
                    #reverse messages 
                    mese = messages[::-1]
                    index = mese.index(msg)
                    textFile.write("<p><a href ='#" + str(index) + "'> Replying to: {0} - <em>{1}</em></a></p>\n".format(message.reference.resolved.author.name ,message.reference.resolved.clean_content))            
                if (message.clean_content):
                    textFile.write("<p>{0}</p>\n".format(message.clean_content))
                if (message.embeds):
                    textFile.write("<p><strong>Embed</strong></p><br>")
                if (message.attachments):
                    for messageFile in message.attachments:
                        link = messageFile.url
                        r = requests.get(link, allow_redirects=True)
                        name = messageFile.filename
                        if (name.split(".")[-1] == "png" or name.split(".")[-1] == "jpg"):
                            open(str(currentImg) + '.png', 'wb').write(r.content)
                            textFile.write("<img src='" + str(currentImg) + ".png' width='100%'><br>")
                            currentImg += 1
                        elif (name.split(".")[-1] == "mp4"):
                            #if its a video, add it to the html
                            open(str(currentImg) + '.mp4', 'wb').write(r.content)
                            textFile.write("<video width='100%' controls><source src='" + str(currentImg) + ".mp4' type='video/mp4'></video><br>")
                        else:
                            fileName = name
                            i = 0
                            #check if filename exists
                            while (os.path.isfile(fileName)):
                                fileName =  "(" + str(i) + ")" + fileName
                                i+=1
                            open(fileName, 'wb').write(r.content)
                            textFile.write("<a href='" + fileName + "' target='_blank'>" + name + "</a><br>")
                if (message.thread):
                    #get thread ID
                    id = message.thread.id
                    currentImg = await threadBackup(id, message, currentImg)
                    textFile.write("<p>Keep Reading the thread <a href='{0} - Backup.html' target='_blank'>here</a></p>\n".format(message.thread.name))
                textFile.write("</div><br>")
                currentMsg += 1
            except Exception as e:
                print(e)
                #print traceback
                print(traceback.format_exc())
        textFile.write("<span>Backup created in {0} seconds at {1}</span>".format(time.time() - startTime, time.strftime("%d/%m/%Y %H:%M:%S")))
        textFile.write("</body>\n</html>")
        textFile.close()
        print("Done")

@client.command(pass_context=True)
async def changeNick(ctx, memberID, nickname):
    if (ctx.message.author.id == 516413751155621899):
        member = ctx.message.guild.get_member(int(memberID))
        await member.edit(nick=nickname)

async def threadBackup(threadID, firstMessage, cImg):
    #get the thread
    thread = client.get_channel(int(threadID))
    messages = await thread.history(limit=None).flatten()
    #add message argument to the list
    messages.append(firstMessage)
    textFile = codecs.open("{0} - Backup.html".format(thread.name), "w", "utf-8")
    textFile.write("<!doctype html>\n<html>\n<head>\n<title>TMTimeTable Thread Backup</title>")
    textFile.write("<meta charset='utf-8'>\n <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n  <link rel='preconnect' href='https://fonts.googleapis.com'> \n<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin> \n<link href='https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&display=swap' rel='stylesheet'>\n")
    textFile.write("<style> body { background-color: #36393f; margin: 50px; } h1{ font-family: 'PT Sans', sans-serif; font-size: 1.2rem; color: #fff; margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; } p{ font-family: 'PT Sans', sans-serif; font-size: 0.8rem; color: #fff; margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; } span{ font-family: 'PT Sans', sans-serif; font-size: 0.8rem; color: #fff; margin-top: 0; margin-bottom: 0; padding-top: 0; padding-bottom: 0; } div{display: inline-block;width: 100%;padding-top: 20px;padding-bottom: 20px;} a{color:white;}html {	scroll-behavior: smooth;} </style> </head> <body>")
    currentImg = cImg
    currentMsg = 0
    for message in reversed(messages):
        try:
            #check if message is a thread
            textFile.write("<div id = {}>".format(currentMsg))
            #get message author
            fileName = str(message.author)
            fileName = fileName[:-5]
            fileName += ".png"
            if (not os.path.isfile(fileName)):
                if (message.author.avatar):
                    pfp = message.author.avatar.url
                    #download the profile picture and save it
                    r = requests.get(pfp, allow_redirects=True)
                    open('{}'.format(str(fileName)), 'wb').write(r.content)
                else:
                    fileName = "data:image/png;base64,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"
            
            textFile.write("<img src='{0}' alt='{1}' width='50' height='50' style = 'float:left; ;border-radius:50%;margin-right: 20px;'>\n".format(fileName, message.author.name))   
            #check if message is a thread
            #check if author has a nickname
            if (message.author.nick != None):
                textFile.write("<h1>{0} ({1})<span> - {2}</span></h1>\n".format(message.author.name, message.author.nick, message.created_at.strftime("%d/%m/%Y %H:%M:%S")))
            else:
                textFile.write("<h1>{0}<span> - {1}</span></h1>\n".format(message.author.name, message.created_at.strftime("%d/%m/%Y %H:%M:%S")))                
            if(message.reference):
                try:
                    #get message reference ID
                    id = message.reference.resolved.id
                    #get message from ID
                    msg = await thread.fetch_message(int(id))
                    #reverse messages 
                    mese = messages[::-1]
                    index = mese.index(msg)
                    textFile.write("<p><a href ='#" + str(index) + "'> Replying to: {0} - <em>{1}</em></a></p>\n".format(message.reference.resolved.author.name ,message.reference.resolved.clean_content))            
                except:
                    print("Error In Thread")
            if (message.clean_content):
                textFile.write("<p>{0}</p>\n".format(message.clean_content))
            if (message.embeds):
                textFile.write("<p><strong>Embed</strong></p><br>")
            if (message.attachments):
                for messageFile in message.attachments:
                    link = messageFile.url
                    r = requests.get(link, allow_redirects=True)
                    name = messageFile.filename
                    if (name.split(".")[-1] == "png" or name.split(".")[-1] == "jpg"):
                        open(str(currentImg) + '.png', 'wb').write(r.content)
                        textFile.write("<img src='" + str(currentImg) + ".png' width='100%'><br>")
                        currentImg += 1
                    else:
                        fileName = name
                        i = 0
                        #check if filename exists
                        while (os.path.isfile(fileName)):
                            fileName =  "(" + str(i) + ")" + fileName
                            i+=1
                        open(fileName, 'wb').write(r.content)
                        textFile.write("<a href='" + fileName + "' target='_blank'>" + name + "</a><br>")
            
            textFile.write("</div><br>")
            currentMsg += 1
        except Exception as e:
            print(e)
            #print traceback
            print(traceback.format_exc())
    return currentImg
    
#method which backs up a chat, and creates an html file of it, and sends it to the user
async def backup(ctx, guildID, channelID):
    #check if user is 516413751155621899
    if (ctx.message.author.id == 516413751155621899):
        guild = client.get_guild(int(guildID))
        currentImg = 0
        #get the channel
        channel = guild.get_channel(int(channelID))
        messages = await channel.history(limit=None).flatten()
        #make an HTML file
        textFile = codecs.open("{0}Backup.html".format(channel), "w", "utf-8")
        textFile.write("<!doctype html>\n<html>\n<head>\n<title>TMtimeTable Channel Backup</title>\n</head>\n<body>\n")
        for message in reversed(messages):
            #check if message contains a file
            if (not message.attachments):
                try:
                    #save the message with author, time it was sent, and the content
                    if(message.reference):
                        textFile.write("<p>Replying to: {0} - <em>{1}</em></p>\n".format(message.reference.resolved.author.name ,message.reference.resolved.clean_content))
                    textFile.write("<p><strong>{0} - {1}</strong>: <br>{2}</p>\n".format(message.author.name, message.created_at.strftime("%d/%m/%Y %H:%M:%S"), message.clean_content))
                except:
                    print("Error writing to file")
                    print(message.content)
            else:
                # if its an image
                #get message link
                #check if message had content
                
                if (message.content):
                    textFile.write("<p><strong>{0}</strong>: <br>{1}</p>\n".format(message.author.name, message.content))
                
                for messageFile in message.attachments:
                    
                    link = messageFile.url
                    
                    r = requests.get(link, allow_redirects=True)

                    name = messageFile.filename
                    print(name)
                    if (name.split(".")[-1] == "png" or name.split(".")[-1] == "jpg"):
                        open(str(currentImg) + '.png', 'wb').write(r.content)
                        textFile.write("<img src='" + str(currentImg) + ".png' width='100%'><br>")
                        currentImg += 1
                    else:
                        fileName = name
                        i = 0
                        #check if filename exists
                        while (os.path.isfile(fileName)):
                            fileName =  "(" + str(i) + ")" + fileName
                            i+=1
                        open(fileName, 'wb').write(r.content)
                        textFile.write("<a href='" + fileName + "' target='_blank'>" + name + "</a><br>")
            if (message.mentions):
                for mention in message.mentions:
                    if (message.reference):
                        if (not mention.name == message.reference.resolved.author.name):
                            textFile.write("<strong>@" + mention.name + "</strong><br>")
                    else:
                        textFile.write("<strong>@" + mention.name + "</strong><br>")

            if (message.embeds):
                textFile.write("<strong>Embed</strong><br>")

        #make center aligned text saying "TMTimeTaable ChannelDump V1.0 backup created at {time}"
        textFile.write("<span>TMTimeTable ChannelDump V1.0 backup created at {0}</span>\n</body>\n</html>".format(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        textFile.close()
        print("Done")

@client.command(pass_context=True)
async def getServerOwner(ctx):
    #ping server owner
    await ctx.send("<@" + str(ctx.message.guild.owner.id) + ">")

@client.command(pass_context = True)
async def dmPerson(ctx, userID, msg):
    person = client.get_user(int(userID))
    await person.send(msg)

#method which edits a users timetable entry
@client.command(pass_context=True)
async def edit (ctx, period = None, *, new_entry = None):
    if maintenance_mode:
        await ctx.send("TMTimeTable is in maintenance mode. Please try again later.")
        return
    #check if user is in databse
    if (not db.users.find_one({"_id": ctx.message.author.id})):
        embed = discord.Embed(title="❌ TMtimeTable Error", description="You don't have a timetable setup yet. Use tmtsetup to setup a timetable!", color=0x1F99CD)
        await ctx.send(embed=embed)
    else:
        #check if period and newentry are none
        if (period == None or new_entry == None):
            embed = discord.Embed(title="❌ TMtimeTable Error", description="You need to specify a period and a new entry!", color=0x1F99CD)
            await ctx.send(embed=embed)
        else:
            #check if period is valid
            
            #check if period is a number
            if (period.isdigit() and int(period) >= 1 and int(period) <= 4):
                period = "p" + str(period)    
            if (period == "p1" or period == "p2" or period == "p3" or period == "p4"):
                #backup current timetable
                backup = db.users.find_one({"_id": ctx.message.author.id})["timetable"]
                
                #change the timetable entry
                backup[period] = new_entry
                
                #reset the users timetable
                db.users.delete_one({"_id": ctx.message.author.id})

                #append new timetable
                
                db.users.insert_one({"_id": ctx.message.author.id, "timetable": backup})
                embed = discord.Embed(title="🔔 TMtimeTable Notification", description="Your timetable has been updated!", color=0x1F99CD)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title="❌ TMtimeTable Error", description="You need to specify a valid period!", color=0x1F99CD)
                await ctx.send(embed=embed)

#command which lists the permissions the bot has
@client.command(pass_context=True)
async def perm(ctx, guild):
    guild = client.get_guild(int(guild))
    #get the list of permissions
    perms = guild.me.guild_permissions
    print(perms['administrator'])
client.run("OTQwMDM0NDQ0OTgxNTkyMDk2.YgBhTA.7qOWuvvjqoeRytIxHzijcK3iwK4") #token

#paragraph being sent to waterloo

#Hello Waterloo staff. I am a bot created by @TMTTimeTable. 
# I am currently in maintenance mode. Please try again later.