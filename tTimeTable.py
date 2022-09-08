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
from Errors import *
load_dotenv(dotenv_path="tTimeTableTokens.env")

mongo = MongoClient(os.getenv('DATABASE_CREDS'))

intents = nextcord.Intents.all()
tTimeTable = commands.Bot(intents = intents, command_prefix='tmt',activity = nextcord.Game("Academic Offense Simulator")) #initializing the bot

UTMCourses = json.load(open("UTMCourses.json"))

def validateCourse(courseCode, semester, activityCode, activityPrefix, activityType, courseCodeOnly = False):
    """
    Method which takes a course code and a semester, and validates both the coursecode and the semester within the course
    :param courseCode: The course code
    :param semester: The semester
    :return: The coursecode of the valid course
    """
    #Check if course code exists in any way shape or form
    if (not courseCode in UTMCourses and not courseCode + "H5" in UTMCourses and not courseCode + "Y5" in UTMCourses):
        raise CourseNotFoundException(courseCode + " not found")
    #Add the necissary H5 or Y5 to the course code
    if (not courseCode[-2:] == "H5" and not courseCode[-2:] == "Y5"):
        courseCode = courseCode + "H5"
        if (not courseCode in UTMCourses):
            courseCode = courseCode[:-2] + "Y5"
    course = UTMCourses[courseCode] #Getting course info from JSON
    if (semester not in course["validSemesters"]):  #Is the semester provided valid for the course: i.e is the course offered in the semester
        raise SemesterNotValidForCourseException(semester + " is not a valid semester for " + courseCode)
    if (courseCodeOnly): #If we only want to validate the course code, we return the course code
        return courseCode
    #In order for an activity code to be valid, it must follow the format of "XXXYYYY" where XXX are letters and YYYY are numbers - XXX is one of LEC, TUT, PRA
    if (len(activityCode) < 4 or (activityCode.isdigit() and len(activityCode) > 4)): #If the activity code is not 4 digits, it is invalid
        #If the activity code is less than four characters, or it's only made of numbers and hss more than 4 characters, it's invalid
        raise ActivityNotFoundException(activityCode + " is not a valid activity code")
    if (not activityCode[:3] == activityPrefix): #If the activity code does not start with the activity prefix (LEC, PRA, TUT), add it
        activityCode = activityPrefix + activityCode
    if (not activityCode[4:].isdigit()): #if the last four digits of the activity code are not numbers, it's invalid
        raise ActivityNotFoundException(activityCode + " is not a valid activity code")

    if (not UTMCourses[courseCode][activityType]): #Check if the course has any activities of the type specified
        raise ActivityNotValidForCourseException(activityType + " is not a valid activity for " + courseCode)

    #At this point we know the formatting is correct - now we need to check if the activity section is valid
    if (not activityCode in course["sections"]): #Check if the session code is valid for that course
        raise ActivityNotFoundException(activityCode + " is not a valid activity code for this course")
    return [courseCode, activityCode] ##If we get to this point, the course code and activity code are valid - return them

def initDatabase(interaction: Interaction, courseCode, semester, activity):
    """
    Method which initializes the database for a user - Ensuring the database environment is ready and setup for adding the user's courses 
    This method assumes validateCourse has already been called
    :param interaction: The interaction object
    :param courseCode: The course code
    :param semester: The semester
    :param activity: The activity (tutorial, lecture, etc)
    """
    db = mongo.tTimeTableUniEdition
    if (db.courses.find_one({"_id": courseCode}) == None):
        #add courseCode to database
        db.courses.insert_one({"_id": courseCode})
    if (not semester in db.courses.find_one({"_id":courseCode})):
        #create the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester:{}}})
    if (not activity in db.courses.find_one({"_id":courseCode})[semester]):
        #append the lecturesection array to the semester object
        db.courses.update_one({"_id":courseCode},{"$set":{semester+"."+activity:[]}})
    if (not db.users.find_one({"_id":interaction.user.id})): # Add course to database
            db.users.insert_one({"_id":interaction.user.id}) #If they don't have a profile, we create one for them
    #Check if they have the semester in their profile
    if (semester not in db.users.find_one({"_id":interaction.user.id})):
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester:{}}})       
    if (semester not in db.courses.find_one({"_id": courseCode})): #Add semester to database
        db.courses.update_one({"_id": courseCode}, {"$set": {semester: {}}})
    if (not courseCode in db.users.find_one({"_id":interaction.user.id})[semester]):
        #Setup user profile for the course
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester + "." +courseCode:{}}}, upsert=True)
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseCode":courseCode}})
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+".courseName":UTMCourses[courseCode]["courseTitle"]}})

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "addtimetable", description = "Import all your courses at once using an Acorn HTML file")
async def addtimetable(interaction: Interaction, htmlfile: Optional[Attachment] = SlashOption(required=True)):
    #Check if the file is an HTML file
    if (not htmlfile.filename.endswith(".html")):
        await interaction.response.send_message("Please upload an HTML file", ephemeral=True)
        return
    #Check if the file is an Acorn HTML file
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
    tutorialsection = tutorialsection.upper()
    try:
        courseCode, tutorialsection = validateCourse(courseCode, semester, tutorialsection, "TUT", "tutorial")
    except CourseNotFoundException: 
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message("Looks like this course isn't offered in your selected semester, try again. If you think this is an error, please contact my owner", ephemeral=True)
        return
    except ActivityNotFoundException:
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again", ephemeral=True)
        return
    except ActivityNotValidForCourseException:
        await interaction.response.send_message("This course does not have a tutorial", ephemeral=True)
        return
    initDatabase(interaction, courseCode, semester, tutorialsection)
    if (not "tutorialSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        #Add the tutorial section to the user's profile
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
    practicalSection = practicalsection.upper()
    try:
        courseCode, practicalSection = validateCourse(courseCode, semester, practicalSection, "PRA", "practical")
    except CourseNotFoundException:
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message("Looks like this course isn't offered in your selected semester, try again. If you think this is an error, please contact my owner", ephemeral=True)
        return
    except ActivityNotFoundException:
        await interaction.response.send_message("Invalid practical section, check your spelling and try again", ephemeral=True)
        return
    except ActivityNotValidForCourseException:
        await interaction.response.send_message("This course does not have a practical", ephemeral=True)
        return
    initDatabase(interaction, courseCode, semester, practicalSection)
    if (not "practicalSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        #Add the practical to the user's profile
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+"."+"practicalSection":practicalSection}}, upsert=True)
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
    lectureSection = lecturesection.upper()
    try:
        courseCode, lectureSection = validateCourse(courseCode, semester, lectureSection, "LEC", "lecture")
    except CourseNotFoundException:
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message("Looks like this course isn't offered in your selected semester, try again. If you think this is an error, please contact my owner", ephemeral=True)
        return
    except ActivityNotFoundException:
        await interaction.response.send_message("Invalid lecture section, check your spelling and try again", ephemeral=True)
        return
    except ActivityNotValidForCourseException:
        await interaction.response.send_message("This course does not have a lecture? This is probably a mistake - Please contact my owner", ephemeral=True)
        return
    initDatabase(interaction, courseCode, semester, lectureSection)
    if (not "lectureSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        #Add the lecture to the user's profile
        db.users.update_one({"_id":interaction.user.id},{"$set":{semester+"."+courseCode+"."+"lectureSection":lectureSection}}, upsert=True)
        db.courses.update_one({"_id":courseCode},{"$push":{semester+"."+lectureSection:interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[courseCode]['courseTitle']} Added!")
        return
    await interaction.response.send_message("You already have this course in your timetable. Use /remove to remove this course from your timetable", ephemeral=True)

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "viewclassmates", description = "See who else is in your class!")
async def viewclassmates(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True, description="The course you'd like to view classmates in. Optional: Leave blank to search all courses", name="coursecode"), semester: str= SlashOption(name="semester", choices={"F":"F", "S": "S", "Y":"Y"}, description="The semester you'd like to view classmates in. Optional: Leave blank to search all semesters", required=True)):
    """
    Command which allows the user to view the classmates in a course
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    """
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
    try:
        courseCode = validateCourse(courseCode, semester, "", "", "lecture", True)
    except CourseNotFoundException:
        await interaction.response.send_message("Invalid course code, check your spelling and try again", ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message("Looks like this course isn't offered in your selected semester, try again. If you think this is an error, please contact my owner", ephemeral=True)
    #check if user has course in their profile
    if (not courseCode in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester]):
        await interaction.response.send_message("You don't have this course in your profile, use /addlecture to add a course to your profile", ephemeral=True)
        return
    #If we're here, we know the course code is valid, and the user has the course in their profile
    embed = nextcord.embeds.Embed(title=f"Classmates in {UTMCourses[courseCode]['courseTitle']}", description="Here are the people in your class", color=0x00ff00)
    embedPhrase = ["Lecture: ", "Tutorial: ", "Practical: "] 
    loopPhrase = ["lectureSection", "tutorialSection", "practicalSection"]
    for i in loopPhrase: #Loop through lecture, tutorial, practical
        if (i in mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode]): #If the user has that activity in their profile, get their classmates and add it to the embed
            section = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode][i]
            classmates = ""
            for user in mongo.tTimeTableUniEdition.courses.find_one({"_id":courseCode})[semester][section]:
                user = await tTimeTable.fetch_user(user)
                #if the user if the person who ran the command, don't add them to the list
                if (user.id == interaction.user.id):
                    continue
                #if the user is in this server
                if (user in interaction.guild.members):
                    classmates = classmates + user.mention + "\n"
                    continue
                #Otherwise add their name
                classmates = f"{classmates} {user.name}#{user.discriminator}\n"
            section = mongo.tTimeTableUniEdition.users.find_one({"_id":interaction.user.id})[semester][courseCode][i]
            if (classmates == ""):
                continue
            embed.add_field(name=f"{embedPhrase[loopPhrase.index(i)]} {section}", value=classmates, inline=False)
    #check if embed is empty - how many fields does it have?
    if (len(embed.fields) == 0):
        await interaction.response.send_message("You don't have any classmates in this course :(", ephemeral=True)
        return
    await interaction.response.send_message(embed=embed)

@tTimeTable.slash_command(guild_ids=[518573248968130570], name = "remove", description = "Remove a course from your profile")
async def remove(interaction:Interaction, courseCode: Optional[str] = SlashOption(required=True, name="coursecode"), semester: Optional[str] = SlashOption(required=True, name="semester", choices={"F":"F", "S": "S", "Y":"Y"}), objecttoremove: Optional[str] = SlashOption(required=True, name="objecttoremove", choices={"Lecture":"lec", "Tutorial":"tut", "Practical":"prac", "All":"lec_prac_tut"})):
    """
    Command to remove a course from a user's profile
    :param interaction: The interaction object
    :param courseCode: The course code of the course to remove
    :param semester: The semester of the course to remove
    :param objecttoremove: The object to remove
    :return: None
    """
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
    removed = False #This will tell us if we actually removed anything
    if ("lec" in objecttoremove and "lectureSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        lec = db.users.find_one({"_id":interaction.user.id})[semester][courseCode]["lectureSection"]
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{f"{semester}.{courseCode}.lectureSection":lec}})
        db.courses.update_one({"_id":courseCode}, {"$pull":{f"{semester}.{lec}":interaction.user.id}})
        removed = True
    #remove the user from the lecture section
        db.courses.update_one({"_id":courseCode}, {"$pull":{semester + ".lectureSections." + lec:interaction.user.id}})
        #remove the lecture section from the user's profile
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode + ".lectureSection":""}})
    if ("tutorialSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode] and "tut" in objecttoremove):
        removed = True
        tut = db.users.find_one({"_id":interaction.user.id})[semester][courseCode]["tutorialSection"]
        db.courses.update_one({"_id":courseCode},{"$pull":{semester+"."+tut:interaction.user.id}})
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode + ".tutorialSection":""}})
    if ("practicalSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode] and "prac" in objecttoremove):
        removed = True
        pra = db.users.find_one({"_id":interaction.user.id})[semester][courseCode]["practicalSection"]
        db.courses.update_one({"_id":courseCode},{"$pull":{semester+"."+pra:interaction.user.id}})
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode + ".practicalSection":""}})
    if (objecttoremove == "lec_prac_tut" or (not "tutorialSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode] and not "practicalSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]) and not "lectureSection" in db.users.find_one({"_id":interaction.user.id})[semester][courseCode]):
        #remove the course from the user's profile
        db.users.update_one({"_id":interaction.user.id}, {"$unset":{semester + "." + courseCode:""}})
        removed = True
    if (not removed): #If we didn't remove anything, then the user didn't have it in their timetable
        await interaction.followup.send("You don't have this sections in this course", ephemeral=True)
        return
    await interaction.followup.send(f"Removed {courseCode} - {UTMCourses[courseCode]['courseTitle']} from your profile", ephemeral=True)
#on ready
@tTimeTable.event
async def on_ready():
    print(f"Logged in as {tTimeTable.user.name}#{tTimeTable.user.discriminator}")
    print("Ready to go!")    

tTimeTable.run(os.getenv('DISCORD_TOKEN')) #token for the bot