from code import interact
from typing import Optional
import nextcord 
from nextcord.ext import commands
import json
from pymongo import MongoClient
import os
from nextcord import Interaction, SlashOption, ChannelType
from nextcord.abc import GuildChannel #Tentative import - gonna be used later
from nextcord import Attachment #Tentative import - gonna be used later (ACORN HTML parsing)
from dotenv import load_dotenv
from Buttons import ConfirmDialogue

load_dotenv(dotenv_path="tTimeTableTokens.env")

mongo = MongoClient(os.getenv('DATABASE_CREDS'))

intents = nextcord.Intents.all()
tTimeTable = commands.Bot(intents = intents, command_prefix='tmt',activity = nextcord.Game("Academic Offense Simulator")) #initializing the bot

UTMCourses = json.load(open("UTMCourses.json"))

print(len(UTMCourses))

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "addtutorial", description = "Add a tutorial to your timetable")
async def addtutorial(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True), semester: str= SlashOption(name="semester", choices={"F":"F", "S": "S", "Y":"Y"}), tutorialsection: Optional[str] = SlashOption(required=True)):
    """
    Command which adds a lecture to a user's profile, and creates a user profile if one does not exist
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    :param tutorialsection: Tutorial section of the course to be added
    """
    db = mongo.tTimeTableUniEdition
    #These are checks to make sure the inputted info is valid
    #Step One: Check if the course code is valid - check if it is in the json file
    courseCode = coursecode.upper()
    if (not courseCode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    #If we're here, we know the course code is at least half valid, we don't know if it has the proper ending. We need to check if it has the proper ending, and if not we need to add the correct ending
    if (not courseCode[-2:] == "H5" and not courseCode[-2:] == "Y5"):
        courseCode = courseCode + "H5"
        if (not courseCode in UTMCourses):
            courseCode = courseCode[:-2] + "Y5"
    #Easiest thing to check first - check if semester is valid
    course = UTMCourses[courseCode]
    if (semester not in course["validSemesters"]):
        await interaction.response.send_message("Looks like this course isn't offered in your selected semester, try again. If you think this is an error, please contact my owner", ephemeral=True)
        return
    #check if course needs tutorial in the first place
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
    if (len(tutorialsection) < 4 or (tutorialsection.isdigit() and len(tutorialsection) > 4)):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    if (not tutorialsection[:3] == "TUT"):
        tutorialsection = "TUT" + tutorialsection
    if (not tutorialsection[4:].isdigit()):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    #At this point we know the formatting is correct - now we need to check if the tutorial section is valid
    if (not tutorialsection in course["sections"]):
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
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester + "." +courseCode:{}}}, upsert=True)
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseCode":courseCode}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseName":UTMCourses[courseCode]["courseTitle"]}})
    if (not "tutorialSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+"."+"tutorialSection":tutorialsection}}, upsert=True)
        db.courses.update_one({"_id":courseCode},{"$push":{semester+"."+tutorialsection:interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[courseCode]['courseTitle']} Added!")
        return
    await interaction.response.send_message("You already have this course in your timetable. Use /remove to remove this course from your timetable", ephemeral=True)

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "addpractical", description = "Add a practical to your timetable")
async def addpractical(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True), semester: str= SlashOption(name="semester", choices={"F":"F", "S": "S", "Y":"Y"}), practicalsection: Optional[str] = SlashOption(required=True)):
    """
    Command which adds a lecture to a user's profile, and creates a user profile if one does not exist
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    :param practicalsection: Practical section of the course to be added
    """
    db = mongo.tTimeTableUniEdition
    #These are checks to make sure the inputted info is valid
    #Step One: Check if the course code is valid - check if it is in the json file
    courseCode = coursecode.upper()
    if (not courseCode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    #If we're here, we know the course code is at least half valid, we don't know if it has the proper ending. We need to check if it has the proper ending, and if not we need to add the correct ending
    if (not courseCode[-2:] == "H5" and not courseCode[-2:] == "Y5"):
        courseCode = courseCode + "H5"
        if (not courseCode in UTMCourses):
            courseCode = courseCode[:-2] + "Y5"
    #Easiest thing to check first - check if semester is valid
    course = UTMCourses[courseCode]
    if (semester not in course["validSemesters"]):
        await interaction.response.send_message("Looks like this course isn't offered in your selected semester, try again. If you think this is an error, please contact my owner", ephemeral=True)
        return

    #check if course needs tutorial in the first place
    if (not UTMCourses[courseCode]["practical"]):
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
    practicalSection = practicalsection.upper()
    if (len(practicalSection) < 4 or (practicalSection.isdigit() and len(practicalSection) > 4)):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    if (not practicalSection[:3] == "PRA"):
        practicalSection = "PRA" + practicalSection
    if (not practicalSection[4:].isdigit()):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    if (not practicalSection in course["sections"]):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    #If we're here, we know the tutorial section is valid. 
    #The Semester is apart of a picker - it's guaranteed to be valid
    
    if (not practicalSection in db.courses.find_one({"_id":courseCode})[semester]):
        #append the lecturesection array to the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester+"."+practicalsection:[]}})
    
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
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester + "." +courseCode:{}}}, upsert=True)
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseCode":courseCode}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseName":UTMCourses[courseCode]["courseTitle"]}})
    if (not "practicalSession" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+"."+"practicalSession":practicalSection}}, upsert=True)
        db.courses.update_one({"_id":courseCode},{"$push":{semester+"."+practicalSection:interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[courseCode]['courseTitle']} Added!")
        return
    await interaction.response.send_message("You already have this course in your timetable. Use /remove to remove this course from your timetable", ephemeral=True)

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "addlecture", description = "Add a lecture to your timetable")
async def addlecture(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True), semester: str= SlashOption(name="semester", choices={"F":"F", "S": "S", "Y":"Y"}), lecturesection: Optional[str] = SlashOption(required=True)):
    """
    Command which adds a lecture to the user's timetable
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    :param lecturesection: Lecture section of the course to be added
    """
    db = mongo.tTimeTableUniEdition
    #These are checks to make sure the inputted info is valid
    #Step One: Check if the course code is valid - check if it is in the json file
    courseCode = coursecode.upper()
    if (not courseCode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
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
    if (len(lectureSection) < 4 or (lectureSection.isdigit() and len(lectureSection) > 4)):
        await interaction.response.send_message("Invalid lecture section, check your spelling and try again", ephemeral=True)
        return
    if (not lectureSection[:3] == "LEC"):
        lectureSection = "LEC" + lectureSection
    if (not lectureSection[4:].isdigit()):
        await interaction.response.send_message("Invalid lecture section, check your spelling and try again", ephemeral=True)
        return

    #If we're here, we know the lecture section is valid. 
    course = UTMCourses[courseCode]
    if (not lectureSection in course["sections"]):
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    
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
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester + "." +courseCode:{}}}, upsert=True)
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseCode":courseCode}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseName":UTMCourses[courseCode]["courseTitle"]}})
    if (not "lectureSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+"."+"lectureSection":lectureSection}}, upsert=True)
        db.courses.update_one({"_id":courseCode},{"$push":{semester+"."+lectureSection:interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[courseCode]['courseTitle']} Added!")
        return
    await interaction.response.send_message("You already have this course in your timetable. Use /remove to remove this course from your timetable", ephemeral=True)

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "viewclassmates", description = "See who else is in your class!")
async def viewclassmates(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True, description="The course you'd like to view classmates in. Optional: Leave blank to search all courses", name="coursecode"), semester: str= SlashOption(name="semester", choices={"F":"F", "S": "S", "Y":"Y"}, description="The semester you'd like to view classmates in. Optional: Leave blank to search all semesters", required=True)):
    #Step One: Check if user has a profile
    if (not mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})):
        await interaction.response.send_message("You don't have a profile, use /addlecture to add a course to your profile", ephemeral=True)
        return
    #Step Two: Check if the user has the semester in their profile
    if (not semester in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})):
        await interaction.response.send_message("You don't have any courses in this semester, use /addlecture to add a course to your profile", ephemeral=True)
        return
    #Step Three: Validate coursecode
    courseCode = coursecode.upper()
    if (not coursecode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    course = UTMCourses[courseCode]
    #Step Four: Check if semester is valid for that course
    if (not semester in course["semesters"]):
        await interaction.response.send_message("Invalid semester, check your spelling and try again", ephemeral=True)
        return
    #If we're here, we know the course code is at least half valid, we don't know if it has the proper ending. We need to check if it has the proper ending, and if not we need to add the correct ending
    if (not courseCode[-2:] == "H5" and not courseCode[-2:] == "Y5"):
        courseCode = courseCode + "H5"
        if (not courseCode in UTMCourses):
            courseCode = courseCode[:-2] + "Y5"
    #check if user has course in their profile
    if (not courseCode in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester]):
        await interaction.response.send_message("You don't have this course in your profile, use /addlecture to add a course to your profile", ephemeral=True)
        return
    #If we're here, we know the course code is valid, and the user has the course in their profile
    embed = nextcord.embeds.Embed(title=f"Classmates in {UTMCourses[courseCode]['courseTitle']}", description="Here are the people in your class", color=0x00ff00)
    if ("lectureSection" in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        lectureSection = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]["lectureSection"]
        lectureClassmates = ""
        for user in mongo.tTimeTableUniEdition.courses.find_one({"_id":courseCode})[semester][lectureSection]:
            user = await tTimeTable.fetch_user(user)
            lectureClassmates = lectureClassmates + user.mention + "\n"
        lecSection = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]["lectureSection"]
        embed.add_field(name=f"Lecture Section {lecSection}", value=lectureClassmates, inline=False)
    if ("tutorialSection" in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        tutorialSection = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]["tutorialSection"]
        tutorialClassmates = ""
        for user in mongo.tTimeTableUniEdition.courses.find_one({"_id":courseCode})[semester][tutorialSection]:
            user = await tTimeTable.fetch_user(user)
            tutorialClassmates = tutorialClassmates + user.mention + "\n"
        tutSection = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]["tutorialSection"]
        embed.add_field(name=f"Tutorial Section {tutSection}", value=tutorialClassmates, inline=False)
    if ("practiceSection" in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        practiceSection = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]["practiceSection"]
        practiceClassmates = ""
        for user in mongo.tTimeTableUniEdition.courses.find_one({"_id":courseCode})[semester][practiceSection]:
            user = await tTimeTable.fetch_user(user)
            practiceClassmates = practiceClassmates + user.mention + "\n"
        pracSec = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]["practicalSection"]
        embed.add_field(name=f"Practical Section Section {pracSec}", value=practiceClassmates, inline=False)
    await interaction.response.send_message(embed=embed)


@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "remove", description = "Remove a course from your profile")
async def remove(interaction:Interaction, courseCode: Optional[str] = SlashOption(required=True, name="coursecode"), semester: Optional[str] = SlashOption(required=True, name="semester", choices={"F":"F", "S": "S", "Y":"Y"}), objecttoremove: Optional[str] = SlashOption(required=True, name="objecttoremove", choices={"Lecture":"lec", "Tutorial":"tut", "Practical":"prac", "All":"lec_prac_tut"})):
    db = mongo.tTimeTableUniEdition
    #check if user has courses setup
    if (not mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})):
        await interaction.response.send_message("You don't have any courses in your profile, use /addlecture to add a course to your profile", ephemeral=True)
        return
    #check if courseCode is valid
    courseCode = courseCode.upper()
    if (not courseCode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    #If we're here, we know the course code is at least half valid, we don't know if it has the proper ending. We need to check if it has the proper ending, and if not we need to add the correct ending
    if (not courseCode[-2:] == "H5" and not courseCode[-2:] == "Y5"):
        courseCode = courseCode + "H5"
        if (not courseCode in UTMCourses):
            courseCode = courseCode[:-2] + "Y5"
    #Check is semester is valid for course 
    if (not semester in UTMCourses[courseCode]["validSemesters"]):
        await interaction.response.send_message("This course is not offered in the semester you specified", ephemeral=True)
        return
    #check if semester is in userprofile
    if (not semester in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})):
        await interaction.response.send_message("You don't have any courses in this semester, use /addlecture to add a course to your profile", ephemeral=True)
        return
    #Now we know both the course and the semester are valid, we need to check if the user has the course in their profile
    
    if (not courseCode in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester]):
        await interaction.response.send_message("You don't have this course in your profile, use /addlecture to add a course to your profile", ephemeral=True)
        return
    #If we're here we know the course is valid, and the user has the course in their profile. We also know the semester is valid for the course

    #Now we need to actually remove the course from the user's profile - Check if the requested removal is valid
    confirmButton = ConfirmDialogue()
    await interaction.response.send_message(f"Are you sure you want to remove this course from your profile? ({courseCode} - {UTMCourses[courseCode]['courseTitle']})", view=confirmButton)   
    await confirmButton.wait()    
    if (not confirmButton.value):
        await interaction.followup.send("Cancelled", ephemeral=True)
        return
    #If we're here, we know the user confirmed the removal - Get the course info from the user's profile
    #get tutorial, practical, and lecture sections
    if ("lec" in objecttoremove):
        lec = db.users.find_one({"_id":interaction.user.id})[semester][courseCode]["lectureSection"]
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{f"{semester}.{courseCode}.lectureSection":lec}})
        db.courses.update_one({"_id":courseCode}, {"$pull":{f"{semester}.{lec}":interaction.user.id}})
    #remove the user from the lecture section
        db.courses.update_one({"_id":courseCode}, {"$pull":{semester + ".lectureSections." + lec:interaction.user.id}})
        #remove the lecture section from the user's profile
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode + ".lectureSection":""}})
    if ("tutorialSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode] and "tut" in objecttoremove):
        tut = db.users.find_one({"_id":interaction.user.id})[semester][courseCode]["tutorialSection"]
        db.courses.update_one({"_id":courseCode},{"$pull":{semester+"."+tut:interaction.user.id}})
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode + ".tutorialSection":""}})
    if ("practicalSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode] and "prac" in objecttoremove):
        pra = db.users.find_one({"_id":interaction.user.id})[semester][courseCode]["practicalSection"]
        db.courses.update_one({"_id":courseCode},{"$pull":{semester+"."+pra:interaction.user.id}})
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode + ".practicalSection":""}})
    if (objecttoremove == "lec_prac_tut"):
        #remove the course from the user's profile
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode:""}})
    await interaction.followup.send(f"Removed {courseCode} - {UTMCourses[courseCode]['courseTitle']} from your profile", ephemeral=True)
#on ready
@tTimeTable.event
async def on_ready():
    print(f"Logged in as {tTimeTable.user.name}#{tTimeTable.user.discriminator}")
    print("Ready to go!")    

tTimeTable.run(os.getenv('DISCORD_TOKEN')) #token for the bot