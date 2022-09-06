from code import interact
from typing import Optional
import nextcord 
from nextcord.ext import commands
import json
from pymongo import MongoClient
import os
from nextcord import Interaction, SlashOption, ChannelType
from nextcord.abc import GuildChannel
from nextcord import Attachment
from dotenv import load_dotenv

load_dotenv(dotenv_path="tTimeTableTokens.env")

mongo = MongoClient(os.getenv('DATABASE_CREDS'))

intents = nextcord.Intents.all()
tTimeTable = commands.Bot(intents = intents, command_prefix='tmt',activity = nextcord.Game("Academic Offense Simulator")) #initializing the bot

UTMCourses = json.load(open("UTMCourses.json"))

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "addtutorial", description = "Add a tutorial to your timetable")
async def addlecture(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True), semester: str= SlashOption(name="semester", choices={"F":"F", "S": "S"}), tutorialsection: Optional[str] = SlashOption(required=True)):
    db = mongo.tTimeTableUniEdition
    #These are checks to make sure the inputted info is valid
    #Step One: Check if the course code is valid - check if it is in the json file
    courseCode = coursecode.upper()
    if (not coursecode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    #If we're here, we know the course code is at least half valid, we don't know if it has the proper ending. We need to check if it has the proper ending, and if not we need to add the correct ending
    if (not courseCode[-2:] == "H5" and not courseCode[-2:] == "Y5"):
        courseCode = courseCode + "H5"
        if (not courseCode in UTMCourses):
            courseCode = courseCode[:-2] + "Y5"
    #check if course needs tutorial in teh first place
    if (not UTMCourses[courseCode]["tutorial"]):
        await interaction.response.send_message("This course does not have a tutorial", ephemeral=True)
        return
    if (db.courses.find_one({"_id": courseCode}) == None):
        #add courseCode to database
        db.courses.insert_one({"_id": courseCode})
    if (not semester in db.courses.find_one({"_id":courseCode})):
        #create the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester:{}}})
    #If we're here, we know the course code is guaranteed to be valid. Now we need to check if the lecture section is valid
    #The Lecture section should either be in the format of LECXXXX, or just XXXX. 
    tutorialsection = tutorialsection.upper()
    if (len(tutorialsection) < 4):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    if (not tutorialsection[:3] == "LEC"):
        tutorialsection = "LEC" + tutorialsection
    if (not tutorialsection[4:].isdigit()):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return

    #If we're here, we know the tutorial section is valid. 
    #The Semester is apart of a picker - it's guaranteed to be valid
    
    if (not tutorialsection in db.courses.find_one({"_id":courseCode})[semester]):
        #append the lecturesection array to the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester+"."+tutorialsection:[]}})
    
    #Now we can interact with our database
    #Step one: Check if the user has a profile
    if (not db.users.find_one({"_id":interaction.user.id})): # Add course to database
        db.users.insert_one({"_id":interaction.user.id}) #If they don't have a profile, we create one for them
    #Check if they have the semester in their profile
    if (semester not in db.users.find_one({"_id":interaction.user.id})):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester:{}}})       
    if (semester not in db.courses.find_one({"_id": courseCode})): #Add semester to database
        db.courses.update_one({"_id": courseCode}, {"$set": {semester: {}}})
    
    if (not courseCode in db.users.find_one({"_id":interaction.user.id})[semester]):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester:{courseCode:{}}}})
    if (not "lectureSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester:{courseCode:{}}}})
        await interaction.response.send_message(f"{coursecode} Added!")
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseCode":courseCode}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseName":UTMCourses[courseCode]["courseTitle"]}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+"."+"tutorialSection":tutorialsection}})
        db.courses.update_one({"_id":courseCode},{"$push":{semester+"."+tutorialsection:interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[courseCode]['courseTitle']} Added!")
        return
    await interaction.response.send_message("You already have this course in your timetable. Use /remove to remove this course from your timetable", ephemeral=True)



@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "addlecture", description = "Add a lecture to your timetable")
async def addlecture(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True), semester: str= SlashOption(name="semester", choices={"F":"F", "S": "S"}), lecturesection: Optional[str] = SlashOption(required=True)):
    db = mongo.tTimeTableUniEdition
    #These are checks to make sure the inputted info is valid
    #Step One: Check if the course code is valid - check if it is in the json file
    courseCode = coursecode.upper()
    if (not coursecode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    #If we're here, we know the course code is at least half valid, we don't know if it has the proper ending. We need to check if it has the proper ending, and if not we need to add the correct ending
    if (not courseCode[-2:] == "H5" and not courseCode[-2:] == "Y5"):
        courseCode = courseCode + "H5"
        if (not courseCode in UTMCourses):
            courseCode = courseCode[:-2] + "Y5"
    if (db.courses.find_one({"_id": courseCode}) == None):
        #add courseCode to database
        db.courses.insert_one({"_id": courseCode})
    if (not semester in db.courses.find_one({"_id":courseCode})):
        #create the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester:{}}})
    #If we're here, we know the course code is guaranteed to be valid. Now we need to check if the lecture section is valid
    #The Lecture section should either be in the format of LECXXXX, or just XXXX. 
    lectureSection = lecturesection.upper()
    if (len(lectureSection) < 4):
        await interaction.response.send_message("Invalid lecture section, check your spelling and try again", ephemeral=True)
        return
    if (not lectureSection[:3] == "LEC"):
        lectureSection = "LEC" + lectureSection
    if (not lectureSection[4:].isdigit()):
        await interaction.response.send_message("Invalid lecture section, check your spelling and try again", ephemeral=True)
        return

    #If we're here, we know the lecture section is valid. 
    #The Semester is apart of a picker - it's guaranteed to be valid
    
    if (not lectureSection in db.courses.find_one({"_id":courseCode})[semester]):
        #append the lecturesection array to the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester+"."+lectureSection:[]}})
    
    #Now we can interact with our database
    #Step one: Check if the user has a profile
    if (not db.users.find_one({"_id":interaction.user.id})): # Add course to database
        db.users.insert_one({"_id":interaction.user.id}) #If they don't have a profile, we create one for them
    #Check if they have the semester in their profile
    if (semester not in db.users.find_one({"_id":interaction.user.id})):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester:{}}})       
    if (semester not in db.courses.find_one({"_id": courseCode})): #Add semester to database
        db.courses.update_one({"_id": courseCode}, {"$set": {semester: {}}})
    
    if (not courseCode in db.users.find_one({"_id":interaction.user.id})[semester]):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester:{courseCode:{}}}})
    if (not "lectureSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester:{courseCode:{}}}})
        await interaction.response.send_message(f"{coursecode} Added!")
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseCode":courseCode}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseName":UTMCourses[courseCode]["courseTitle"]}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+"."+"lectureSection":lectureSection}})
        db.courses.update_one({"_id":courseCode},{"$push":{semester+"."+lectureSection:interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[courseCode]['courseTitle']} Added!")
        return
    await interaction.response.send_message("You already have this course in your timetable. Use /remove to remove this course from your timetable", ephemeral=True)


@tTimeTable.command(pass_context=True)
async def addCourse(ctx):
    semester = None
    lectureSection = None
    tutorialSection = None
    practicalSection = None
    db = mongo.tTimeTableUniEdition
    await ctx.send("Please enter a course code")
    courseCode = await tTimeTable.wait_for('message', check=lambda message: message.author == ctx.message.author)
    courseCode = courseCode.content.upper()
    if (courseCode not in UTMCourses):
        await ctx.send("Course not found; try again. Make sure you use the course code, not the course name. Ensure you include the ending (H5/Y5) as well")
        return
    #check if courseCode object is in database
    if (db.courses.find_one({"_id": courseCode}) == None):
        #add courseCode to database
        db.courses.insert_one({"_id": courseCode})
    await ctx.send("Adding course " + (courseCode) + ": " + UTMCourses[(courseCode)]["courseTitle"])
    
    await ctx.send("Please enter a semester (F/S)")
    semester = await tTimeTable.wait_for('message', check=lambda message: message.author == ctx.message.author)
    semester = semester.content.upper()
    if (semester not in ["F", "S"]):
        await ctx.send("Invalid semester; try again. Only F and S are valid")
        return
    #check if semester object is in database
    if (semester not in db.courses.find_one({"_id": courseCode})):
        #add semester to database
        db.courses.update_one({"_id": courseCode}, {"$set": {semester: {}}})
    
    if (UTMCourses[courseCode]['lecture']):
        if (not lectureSection):
            await ctx.send("Please enter a lecture section (LECXXXX)")
            lectureSection = await tTimeTable.wait_for('message', check=lambda message: message.author == ctx.message.author)
            lectureSection = lectureSection.content.upper()
        #validate the lecture section and make sure it's valid
        #Valid Format: LECXXXX, XXXX being a number
        if (lectureSection[:3] != "LEC" or not lectureSection[4:].isdigit()):
            await ctx.send("Invalid lecture section; try again. Make sure you use the lecture section, not the course name")
            return
        if (not lectureSection in db.courses.find_one({"_id":courseCode})[semester]):
        #append the lecturesection array to the semester object
            db.courses.update_one({"_id":courseCode},{"$set":{semester+"."+lectureSection:[]}})
        #append the userID to the lecture section array
        
    if (UTMCourses[courseCode]['tutorial']):
        await ctx.send("Please enter a tutorial section (TUTXXXX)")
        tutorialSection = await tTimeTable.wait_for('message', check=lambda message: message.author == ctx.message.author)
        tutorialSection = tutorialSection.content.upper()
        if (tutorialSection[:3] != "TUT" or not tutorialSection[4:].isdigit()):
            await ctx.send("Invalid tutorial section; try again. Make sure you use the lecture section, not the course name")
            return
        if (not tutorialSection in db.courses.find_one({"_id":courseCode})[semester]):
            #append the tutorialsection array to the semester object
            db.courses.update_one({"_id":courseCode},{"$set":{semester+ "." +tutorialSection:[]}})  
        #append userID to the tutorialsection array


    if (UTMCourses[courseCode]['practical']):
        await ctx.send("Please enter a practical section (PRAXXXX)")
        practicalSection = await tTimeTable.wait_for('message', check=lambda message: message.author == ctx.message.author)
        practicalSection = practicalSection.content.upper()
        if (practicalSection[:3] != "PRA" or not practicalSection[4:].isdigit()):
            await ctx.send("Invalid practical section; try again. Make sure you use the lecture section, not the course name")
            return
        if (not practicalSection in db.courses.find_one({"_id":courseCode})[semester]):
            #append the practical array to the semester object
            db.courses.update_one({"_id":courseCode},{"$set":{semester+ "." +practicalSection:[]}})
        #add user id to the practical array
    
    if (not db.courses.find_one({"_id":courseCode})):
        #create the course object
        db.courses.insert_one({"_id":courseCode})

    #check if user already has the course - [userID][semester][courseCode]
    if (not db.users.find_one({"_id":ctx.message.author.id})):
        db.users.insert_one({"_id":ctx.message.author.id})
    if (semester not in db.users.find_one({"_id":ctx.message.author.id})):
        db.users.update_one({"_id":ctx.message.author.id},{"$set":{semester:{}}})   
    if (courseCode in db.users.find_one({"_id":ctx.message.author.id})[semester]):
        await ctx.send("You already have this course")
        return
    #add course object to semester object
    db.users.update_one({"_id":ctx.message.author.id},{"$set":{semester:{courseCode:{}}}})
    #add courseCode and courseName to course object
    db.users.update_one({"_id":ctx.message.author.id},{"$set":{semester+"."+courseCode+".courseCode":courseCode}})
    db.users.update_one({"_id":ctx.message.author.id},{"$set":{semester+"."+courseCode+".courseName":UTMCourses[courseCode]["courseTitle"]}})
    if (not semester in db.courses.find_one({"_id":courseCode})):
    #create the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester:{}}})
    #add course code to user's timetable
    if (practicalSection):
        db.courses.update_one({"_id":courseCode},{"$push":{semester+ "." +practicalSection:ctx.message.author.id}})
        db.users.update_one({"_id":ctx.message.author.id},{"$set":{semester+"."+courseCode+"."+"practicalSection":practicalSection}})
    if (lectureSection):
        db.courses.update_one({"_id":courseCode},{"$push":{semester+"."+lectureSection:ctx.message.author.id}})
        #add lecture section to user's courseCode object
        db.users.update_one({"_id":ctx.message.author.id},{"$set":{semester+"."+courseCode+"."+"lectureSection":lectureSection}})
    if (tutorialSection):
        db.courses.update_one({"_id":courseCode},{"$push":{semester+ "." +tutorialSection:ctx.message.author.id}})
        db.users.update_one({"_id":ctx.message.author.id},{"$set":{semester+"."+courseCode+"."+"tutorialSection":tutorialSection}})
    
    await ctx.send(f"{UTMCourses[courseCode]['courseTitle']} has been added to your profile")

@tTimeTable.command(pass_context=True)
async def viewClassmates(ctx, courseCode = None, semester = None):
#method which will show a user all the classmates in a course
    db = mongo.tTimeTableUniEdition
    if (not db.users.find_one({"_id":ctx.message.author.id})):
        await ctx.send("You don't have a profile yet. Use `tmtaddCourse` to add a course")
        return
    if (courseCode):
        #check if course code is valid
        if (not courseCode in UTMCourses):
            await ctx.send("Invalid course code")
            return
        # semester is valid
        if (semester.upper() not in ["F", "S"]):
            await ctx.send("Invalid semester")
            return
        #check if user has the course
        if (not courseCode in db.users.find_one({"_id":ctx.message.author.id})[semester]):
            await ctx.send("You don't have this course in your profile")
            return
        #if we're here all the checks have passed - we can show the classmates
        #Get the user's lecture
        lecture = db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]["lectureSection"]
        embed = nextcord.embeds.Embed(title=UTMCourses[courseCode]['courseTitle'], description="Classmates: ", color=0x00ff00)
        lectureClassmates = db.courses.find_one({"_id":courseCode})[semester][lecture]
        finalLectureString = ""
        for classmate in lectureClassmates:
            #convert the User ID to a discord user object
            user = tTimeTable.get_user(classmate)
            finalLectureString += f"{user.mention}\n"
        embed.add_field(name="Lecture", value=finalLectureString, inline=False)
        #check if course has a tutorial
        if (UTMCourses[courseCode]['tutorial']):
            #get the user's tutorial
            tutorial = db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]["tutorialSection"]
            tutorialClassmates = db.courses.find_one({"_id":courseCode})[semester][tutorial]
            finalTutorialString = ""
            for classmate in tutorialClassmates:
                #convert the User ID to a discord user object
                user = tTimeTable.get_user(classmate)
                finalTutorialString += f"{user.mention}\n"
            
            embed.add_field(name="Tutorial", value=finalTutorialString, inline=False)
        if (UTMCourses[courseCode]['practical']):
            #get the user's practical
            practical = db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]["practicalSection"]
            practicalClassmates = db.courses.find_one({"_id":courseCode})[semester][practical]
            finalPracticalString = ""
            for classmate in practicalClassmates:
                #convert the User ID to a discord user object
                user = tTimeTable.get_user(classmate)
                finalPracticalString += f"{user.mention}\n"
            embed.add_field(name="Practical", value=finalPracticalString, inline=False)
        await ctx.send(embed=embed)
        #check if course has a practical
        return
    #if we're here the user wants to see all their courses
    embed = nextcord.embeds.Embed(title="Your Courses", description="Classmates: ", color=0x00ff00)
    #get the users object
    user = db.users.find_one({"_id":ctx.message.author.id})
    if ("F" in user):
        semester = "F"
        #get the user's fall courses
        fallCourses = db.users.find_one({"_id":ctx.message.author.id})["F"]
        for course in fallCourses:
            course = db.users.find_one({"_id":ctx.message.author.id})["F"][course]
            #get courseCode and courseName
            courseCode = course["courseCode"]
            courseName = course["courseName"]
            if (UTMCourses[courseCode]['lecture']):
                lectureSection = course["lectureSection"]
                lectureInfo = db.courses.find_one({"_id":courseCode})[semester][lectureSection]
                lectureClassmates = ""
                for classmate in lectureInfo:
                    #convert the User ID to a discord user object
                    user = tTimeTable.get_user(classmate)
                    lectureClassmates += f"{user.mention}\n"
                embed.add_field(name=f"{courseCode} - {courseName}: Lecture {lectureSection}", value=lectureClassmates, inline=False)
            if (UTMCourses[courseCode]['tutorial']):
                tutorialSection = course["tutorialSection"]
                tutorialInfo = db.courses.find_one({"_id":courseCode})[semester][tutorialSection]
                tutorialClassmates = ""
                for classmate in tutorialInfo:
                    #convert the User ID to a discord user object
                    user = tTimeTable.get_user(classmate)
                    tutorialClassmates += f"{user.mention}\n"
                embed.add_field(name=f"{courseCode} - {courseName}: Tutorial {tutorialSection}", value=tutorialClassmates, inline=False)

            if (UTMCourses[courseCode]['practical']):
                practicalSection = course["practicalSection"]
                practicalInfo = db.courses.find_one({"_id":courseCode})[semester][practicalSection]
                practicalClassmates = ""
                for classmate in practicalInfo:
                    #convert the User ID to a discord user object
                    user = tTimeTable.get_user(classmate)
                    practicalClassmates += f"{user.mention}\n"
                embed.add_field(name=f"{courseCode} - {courseName}: Practical {practicalSection}", value=practicalClassmates, inline=False)
            #get info about the course from courses database
    await ctx.send(embed=embed)
@tTimeTable.command(name="remove", help="Remove a course from your timetable")
async def remove(ctx, courseCode, semester):
    db = mongo.tTimeTableUniEdition
    #check if courseCode is valid
    if (not courseCode in UTMCourses):
        await ctx.send("Invalid course code; try again")
        return
    if (not db.users.find_one({"_id":ctx.message.author.id}) or not semester in db.users.find_one({"_id":ctx.message.author.id}) or db.users.find_one({"_id":ctx.message.author.id})[semester] == {}):
        await ctx.send("You don't have any courses added in your timetable")
        return
    #check if course code obeject is in user's timetable
    print(db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode])
    if (not courseCode in db.users.find_one({"_id":ctx.message.author.id})[semester]):
        await ctx.send("You don't have this course in your timetable")
        return
    #get tutorial, practical, and lecture sections
    lec = db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]["lectureSection"]
    if ("tutorialSection" in db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]):
        tut = db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]["tutorialSection"]
        db.courses.update_one({"_id":courseCode},{"$pull":{semester+"."+tut:ctx.message.author.id}})
    if ("practicalSection" in db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]):
        pra = db.users.find_one({"_id":ctx.message.author.id})[semester][courseCode]["practicalSection"]
        db.courses.update_one({"_id":courseCode},{"$pull":{semester+"."+pra:ctx.message.author.id}})

    #remove user's ID from courses database
    db.courses.update_one({"_id":courseCode},{"$pull":{semester+"."+lec:ctx.message.author.id}})        
    #if we're here, we can remove the course
    db.users.update_one({"_id":ctx.message.author.id},{"$unset":{semester+"."+courseCode:None}})
    await ctx.send(f"{UTMCourses[courseCode]['courseTitle']} has been removed from your timetable")

#on ready
@tTimeTable.event
async def on_ready():
    print(f"Logged in as {tTimeTable.user.name}#{tTimeTable.user.discriminator}")
    print("Ready to go!")    

tTimeTable.run(os.getenv('DISCORD_TOKEN')) #token for the bot