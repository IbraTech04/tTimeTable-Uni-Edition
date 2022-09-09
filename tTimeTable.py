from typing import Optional
import nextcord
from nextcord.ext import commands
import json
from pymongo import MongoClient
import os
from nextcord import Interaction, SlashOption
# from nextcord.abc import GuildChannel  # Tentative import - going be used later
from nextcord import Attachment  # Tentative import - going be used later (ACORN HTML parsing)
from dotenv import load_dotenv
from Buttons import ConfirmDialogue
from Errors import *
from bs4 import BeautifulSoup
import ics # Importing the ics library for parsing the ACORN calendar
load_dotenv(dotenv_path="tTimeTableTokens.env")

mongo = MongoClient(os.getenv('DATABASE_CREDS'))

intents = nextcord.Intents.all()
#  Initializing the bot
tTimeTable = commands.Bot(intents=intents, command_prefix='tmt', activity=nextcord.Game("Academic Offense Simulator"))

UTMCourses = json.load(open("UTMCourses.json"))


def validate_course(course_code, semester, activity_code, activity_prefix, activity_type, course_code_only=False):
    """
    Method which takes a course code and a semester, and validates both the
    coursecode and the semester within the course
    :param course_code: The course code
    :param semester: The semester
    :param activity_code: The activity code (ex: TUT0108)
    :param activity_prefix: The activity prefix (ex: TUT)
    :param activity_type: The activity type (ex: Tutorial)
    :param course_code_only: Whether to only validate the course code
    :return: The course code of the valid course
    """
    # Check if the course code exists in any way shape or form
    if course_code not in UTMCourses and not course_code + "H5" in UTMCourses and not course_code + "Y5" in UTMCourses:
        raise CourseNotFoundException(course_code + " not found")
    # Add the necessary H5 or Y5 to the course code
    if not course_code[-2:] == "H5" and not course_code[-2:] == "Y5":
        course_code = course_code + "H5"
        if course_code not in UTMCourses:
            course_code = course_code[:-2] + "Y5"
    course = UTMCourses[course_code]  # Getting course info from JSON
    if semester not in course["validSemesters"]:
        # Is the semester provided valid for the course: i.e. is the course offered in the semester
        raise SemesterNotValidForCourseException(semester + " is not a valid semester for " + course_code)
    if course_code_only:  # If we only want to validate the course code, we return the course code
        return course_code
    # In order for an activity code to be valid, it must follow the format of "XXXYYYY"
    # where XXX are letters and YYYY are numbers - XXX is one of LEC, TUT, PRA
    if (len(activity_code) < 4 or (
            activity_code.isdigit() and len(activity_code) > 4)):  # If the activity code is not 4 digits, it is invalid
        # If the activity code is less than four characters, or it's only made of numbers
        # and has more than 4 characters, it's invalid
        raise ActivityNotFoundException(activity_code + " is not a valid activity code")
    if (not activity_code[
            :3] == activity_prefix):
        # If the activity code does not start with the activity prefix (LEC, PRA, TUT), add it
        activity_code = activity_prefix + activity_code
    if not activity_code[4:].isdigit():  # if the last four digits of the activity code are not numbers, it's invalid
        raise ActivityNotFoundException(activity_code + " is not a valid activity code")

    if not UTMCourses[course_code][activity_type]:  # Check if the course has any activities of the type specified
        raise ActivityNotValidForCourseException(activity_type + " is not a valid activity for " + course_code)

    # At this point we know the formatting is correct - now we need to check if the activity section is valid
    if activity_code not in course["sections"]:  # Check if the session code is valid for that course
        raise ActivityNotFoundException(activity_code + " is not a valid activity code for this course")
    return [course_code,
            activity_code]  # If we get to this point, the course code and activity code are valid - return them


def init_database(interaction: Interaction, course_code, semester, activity):
    """
    Method which initializes the database for a user - Ensuring the database environment
    is ready and setup for adding the user's courses
    This method assumes validateCourse has already been called
    :param interaction: The interaction object
    :param course_code: The course code
    :param semester: The semester
    :param activity: The activity (tutorial, lecture, etc)
    """
    db = mongo.tTimeTableUniEdition
    if db.courses.find_one({"_id": course_code}) is None:
        # add courseCode to database
        db.courses.insert_one({"_id": course_code})
    if semester not in db.courses.find_one({"_id": course_code}):
        # create the semester object
        db.courses.update_one({"_id": course_code}, {"$set": {semester: {}}})
    if activity not in db.courses.find_one({"_id": course_code})[semester]:
        # append the lecturesection array to the semester object
        db.courses.update_one({"_id": course_code}, {"$set": {semester + "." + activity: []}})
    if not db.users.find_one({"_id": interaction.user.id}):  # Add course to database
        db.users.insert_one({"_id": interaction.user.id})  # If they don't have a profile, we create one for them
    # Check if they have the semester in their profile
    if semester not in db.users.find_one({"_id": interaction.user.id}):
        db.users.update_one({"_id": interaction.user.id}, {"$set": {semester: {}}})
    if semester not in db.courses.find_one({"_id": course_code}):  # Add semester to database
        db.courses.update_one({"_id": course_code}, {"$set": {semester: {}}})
    if course_code not in db.users.find_one({"_id": interaction.user.id})[semester]:
        # Setup user profile for the course
        db.users.update_one({"_id": interaction.user.id}, {"$set": {semester + "." + course_code: {}}}, upsert=True)
        db.users.update_one({"_id": interaction.user.id},
                            {"$set": {semester + "." + course_code + ".courseCode": course_code}})
        db.users.update_one({"_id": interaction.user.id}, {
            "$set": {semester + "." + course_code + ".courseName": UTMCourses[course_code]["courseTitle"]}})


def fix_array(arr):
    return [x.strip() for x in arr if x.strip() != '']


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="addtimetable",
                          description="Import all your courses at once using an Acorn HTML file")
async def add_timetable(interaction: Interaction, html_file: Optional[Attachment] = SlashOption(required=True)):
    # Check if the file is an HTML file
    if html_file.filename.endswith(".html"):
        # Save file to disk
        await html_file.save(str(interaction.user.id) + ".html")
        # Check if the file is an Acorn HTML file
        site = BeautifulSoup(open(str(interaction.user.id) + ".html", 'r'), 'html.parser')
        try:
            div = site.find('div', class_='program-course-info')
            # get the table with the class called course-meeting
            table = div.find('table', class_='course-meeting')
            # get all the rows in the table
            rows = table.find_all('tr')
            # iterate through the rows
            for row in rows:
                # get all the columns in the row
                cols = row.find_all('td')
                # iterate through the columns
                for col in cols:
                    # get the text in the column
                    text = col.get_text()
                    print(fix_array(text.splitlines()))
        except:
            await interaction.response.send_message("Invalid HTML file - try again", ephemeral=True)
        finally:
            # Delete the file
            os.remove(str(interaction.user.id) + ".html")
        return
    if (html_file.filename.endswith(".ics")):
        await interaction.response.send_message("ICS files are not supported yet. Stay tuned!", ephemeral=True)
        return
    await interaction.response.send_message("Invalid file type - try again", ephemeral=True)

@tTimeTable.slash_command(guild_ids=[518573248968130570], name="addtutorial",
                          description="Add a tutorial to your timetable")
async def addtutorial(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True),
                      semester: str = SlashOption(name="semester", choices={"F": "F", "S": "S", "Y": "Y"}),
                      tutorial_section: Optional[str] = SlashOption(required=True)):
    """
    Command which adds a lecture to a user's profile, and creates a user profile if one does not exist
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    :param tutorial_section: Tutorial section of the course to be added
    """
    db = mongo.tTimeTableUniEdition
    # These are checks to make sure the inputted info is valid
    # Step One: Check if the course code is valid - check if it is in the json file
    course_code = coursecode.upper()
    tutorial_section = tutorial_section.upper()
    try:
        course_code, tutorial_section = validate_course(course_code, semester, tutorial_section, "TUT", "tutorial")
    except CourseNotFoundException:
        await interaction.response.send_message("Invalid course code, check your spelling and try again",
                                                ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message(
            "Looks like this course isn't offered in your selected semester, "
            "try again. If you think this is an error, please contact my owner",
            ephemeral=True)
        return
    except ActivityNotFoundException:
        await interaction.response.send_message("Invalid tutorial section, check your spelling and try again",
                                                ephemeral=True)
        return
    except ActivityNotValidForCourseException:
        await interaction.response.send_message("This course does not have a tutorial", ephemeral=True)
        return
    init_database(interaction, course_code, semester, tutorial_section)
    if "tutorialSection" not in db.users.find_one({"_id": interaction.user.id})[semester][course_code]:
        # Add the tutorial section to the user's profile
        db.users.update_one({"_id": interaction.user.id},
                            {"$set": {semester + "." + course_code + "." + "tutorialSection": tutorial_section}},
                            upsert=True)
        db.courses.update_one({"_id": course_code}, {"$push": {semester + "." + tutorial_section: interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[course_code]['courseTitle']} Added!")
        return
    await interaction.response.send_message(
        "You already have this course in your timetable. Use /remove to remove this course from your timetable",
        ephemeral=True)


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="addpractical",
                          description="Add a practical to your timetable")
async def addpractical(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True),
                       semester: str = SlashOption(name="semester", choices={"F": "F", "S": "S", "Y": "Y"}),
                       practicalsection: Optional[str] = SlashOption(required=True)):
    """
    Command which adds a lecture to a user's profile, and creates a user profile if one does not exist
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    :param practicalsection: Practical section of the course to be added
    """
    db = mongo.tTimeTableUniEdition
    # These are checks to make sure the inputted info is valid
    # Step One: Check if the course code is valid - check if it is in the json file
    course_code = coursecode.upper()
    practical_section = practicalsection.upper()
    try:
        course_code, practical_section = validate_course(course_code, semester, practical_section, "PRA", "practical")
    except CourseNotFoundException:
        await interaction.response.send_message("Invalid course code, check your spelling and try again",
                                                ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message(
            "Looks like this course isn't offered in your selected semester, "
            "try again. If you think this is an error, please contact my owner",
            ephemeral=True)
        return
    except ActivityNotFoundException:
        await interaction.response.send_message("Invalid practical section, check your spelling and try again",
                                                ephemeral=True)
        return
    except ActivityNotValidForCourseException:
        await interaction.response.send_message("This course does not have a practical", ephemeral=True)
        return
    init_database(interaction, course_code, semester, practical_section)
    if "practicalSection" not in db.users.find_one({"_id": interaction.user.id})[semester][course_code]:
        # Add the practical to the user's profile
        db.users.update_one({"_id": interaction.user.id},
                            {"$set": {semester + "." + course_code + "." + "practicalSection": practical_section}},
                            upsert=True)
        db.courses.update_one({"_id": course_code},
                              {"$push": {semester + "." + practical_section: interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[course_code]['courseTitle']} Added!")
        return
    await interaction.response.send_message(
        "You already have this course in your timetable. Use /remove to remove this course from your timetable",
        ephemeral=True)


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="addlecture",
                          description="Add a lecture to your timetable")
async def addlecture(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True),
                     semester: str = SlashOption(name="semester", choices={"F": "F", "S": "S", "Y": "Y"}),
                     lecturesection: Optional[str] = SlashOption(required=True)):
    """
    Command which adds a lecture to the user's timetable
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    :param lecturesection: Lecture section of the course to be added
    """
    db = mongo.tTimeTableUniEdition
    # These are checks to make sure the inputted info is valid
    # Step One: Check if the course code is valid - check if it is in the json file
    course_code = coursecode.upper()
    lecture_section = lecturesection.upper()
    try:
        course_code, lecture_section = validate_course(course_code, semester, lecture_section, "LEC", "lecture")
    except CourseNotFoundException:
        await interaction.response.send_message("Invalid course code, check your spelling and try again",
                                                ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message(
            "Looks like this course isn't offered in your selected semester, "
            "try again. If you think this is an error, please contact my owner",
            ephemeral=True)
        return
    except ActivityNotFoundException:
        await interaction.response.send_message("Invalid lecture section, check your spelling and try again",
                                                ephemeral=True)
        return
    except ActivityNotValidForCourseException:
        await interaction.response.send_message(
            "This course does not have a lecture? This is probably a mistake - Please contact my owner", ephemeral=True)
        return
    init_database(interaction, course_code, semester, lecture_section)
    if "lectureSection" not in db.users.find_one({"_id": interaction.user.id})[semester][course_code]:
        # Add the lecture to the user's profile
        db.users.update_one({"_id": interaction.user.id},
                            {"$set": {semester + "." + course_code + "." + "lectureSection": lecture_section}},
                            upsert=True)
        db.courses.update_one({"_id": course_code}, {"$push": {semester + "." + lecture_section: interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[course_code]['courseTitle']} Added!")
        return
    await interaction.response.send_message(
        "You already have this course in your timetable. Use /remove to remove this course from your timetable",
        ephemeral=True)


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="viewclassmates",
                          description="See who else is in your class!")
async def viewclassmates(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True,
                                                                                           description="Course you'd"
                                                                                                       "like to view "
                                                                                                       "classmates in",
                                                                                           name="coursecode"),
                         semester: str = SlashOption(name="semester",
                                                     choices={"F": "F", "S": "S", "Y": "Y"},
                                                     description="The semester you'd like to view classmates in.",
                                                     required=True)):
    """
    Command which allows the user to view the classmates in a course
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    """
    # Step One: Check if user has a profile
    if not mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id}):
        await interaction.response.send_message(
            "You don't have a profile, use /addlecture to add a course to your profile", ephemeral=True)
        return
    # Step Two: Check if the user has the semester in their profile
    if semester not in mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id}):
        await interaction.response.send_message(
            "You don't have any courses in this semester, use /addlecture to add a course to your profile",
            ephemeral=True)
        return
    # Step Three: Validate coursecode
    course_code = coursecode.upper()
    try:
        course_code = validate_course(course_code, semester, "", "", "lecture", True)
    except CourseNotFoundException:
        await interaction.response.send_message("Invalid course code, check your spelling and try again",
                                                ephemeral=True)
        return
    except SemesterNotValidForCourseException:
        await interaction.response.send_message(
            "Looks like this course isn't offered in your selected semester, "
            "try again. If you think this is an error, please contact my owner",
            ephemeral=True)
    # check if user has course in their profile
    if course_code not in mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id})[semester]:
        await interaction.response.send_message(
            "You don't have this course in your profile, use /addlecture to add a course to your profile",
            ephemeral=True)
        return
    # If we're here, we know the course code is valid, and the user has the course in their profile
    embed = nextcord.embeds.Embed(title=f"Classmates in {UTMCourses[course_code]['courseTitle']}",
                                  description="Here are the people in your class", color=0x00ff00)
    embed_phrase = ["Lecture: ", "Tutorial: ", "Practical: "]
    loop_phrase = ["lectureSection", "tutorialSection", "practicalSection"]
    for i in loop_phrase:  # Loop through lecture, tutorial, practical
        if (i in mongo.tTimeTableUniEdition.users.find_one(
                {"_id": interaction.user.id})[semester][course_code]):
            # If the user has that activity in their profile, get their classmates and add it to the embed
            section = mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id})[semester][course_code][i]
            classmates = ""
            for user in mongo.tTimeTableUniEdition.courses.find_one({"_id": course_code})[semester][section]:
                user = await tTimeTable.fetch_user(user)
                # if the user is the person who ran the command, don't add them to the list
                if user.id == interaction.user.id:
                    continue
                # if the user is in this server
                if user in interaction.guild.members:
                    classmates = classmates + user.mention + "\n"
                    continue
                # Otherwise add their name
                classmates = f"{classmates} {user.name}#{user.discriminator}\n"
            section = mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id})[semester][course_code][i]
            if classmates == "":
                continue
            embed.add_field(name=f"{embed_phrase[loop_phrase.index(i)]} {section}", value=classmates, inline=False)
    # check if embed is empty - how many fields does it have?
    if len(embed.fields) == 0:
        await interaction.response.send_message("You don't have any classmates in this course :(", ephemeral=True)
        return
    await interaction.response.send_message(embed=embed)


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="remove",
                          description="Remove a course from your profile")
async def remove(interaction: Interaction, course_code: Optional[str] = SlashOption(required=True, name="coursecode"),
                 semester: Optional[str] = SlashOption(required=True, name="semester",
                                                       choices={"F": "F", "S": "S", "Y": "Y"}),
                 objecttoremove: Optional[str] = SlashOption(required=True, name="objecttoremove",
                                                             choices={"Lecture": "lec", "Tutorial": "tut",
                                                                      "Practical": "prac", "All": "lec_prac_tut"})):
    """
    Command to remove a course from a user's profile
    :param interaction: The interaction object
    :param course_code: The course code of the course to remove
    :param semester: The semester of the course to remove
    :param objecttoremove: The object to remove
    :return: None
    """
    db = mongo.tTimeTableUniEdition
    # check if user has courses setup
    if not mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id}):
        await interaction.response.send_message(
            "You don't have any courses in your profile, use /addlecture to add a course to your profile",
            ephemeral=True)
        return
    # check if courseCode is valid
    course_code = course_code.upper()
    if course_code not in UTMCourses and not course_code + "H5" in UTMCourses and not course_code + "Y5" in UTMCourses:
        await interaction.response.send_message("Invalid course code, check your spelling and try again",
                                                ephemeral=True)
        return
    # If we're here, we know the course code is at least half valid,
    # we don't know if it has the proper ending. We need to check
    # if it has the proper ending, and if not we need to add the correct ending
    if course_code[-2:] != "H5" and course_code[-2:] != "Y5":
        course_code = course_code + "H5"
        if course_code not in UTMCourses:
            course_code = course_code[:-2] + "Y5"
    # Check is semester is valid for course
    if semester not in UTMCourses[course_code]["validSemesters"]:
        await interaction.response.send_message("This course is not offered in the semester you specified",
                                                ephemeral=True)
        return
    # check if semester is in userprofile
    if semester not in mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id}):
        await interaction.response.send_message(
            "You don't have any courses in this semester, use /addlecture to add a course to your profile",
            ephemeral=True)
        return
    # Now we know both the course and the semester are valid, we need to check
    # if the user has the course in their profile

    if course_code not in mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id})[semester]:
        await interaction.response.send_message(
            "You don't have this course in your profile, use /addlecture to add a course to your profile",
            ephemeral=True)
        return
    # If we're here we know the course is valid, and the user has the
    # course in their profile. We also know the semester is valid for the course

    # Now we need to actually remove the course from the user's profile - Check if the requested removal is valid
    confirm_button = ConfirmDialogue()
    await interaction.response.send_message(
        f"Are you sure you want to remove this course from your profile? "
        f"({course_code} - {UTMCourses[course_code]['courseTitle']})",
        view=confirm_button)
    await confirm_button.wait()
    if not confirm_button.value:
        await interaction.followup.send("Cancelled", ephemeral=True)
        return
    # If we're here, we know the user confirmed the removal - Get the course info from the user's profile
    # get tutorial, practical, and lecture sections
    removed = False  # This will tell us if we actually removed anything
    if ("lec" in objecttoremove and "lectureSection" in db.users.find_one(
            {"_id": interaction.user.id})[semester][course_code]):
        lec = db.users.find_one({"_id": interaction.user.id})[semester][course_code]["lectureSection"]
        db.users.update_one({"_id": interaction.user.id}, {"$unset": {f"{semester}.{course_code}.lectureSection": lec}})
        db.courses.update_one({"_id": course_code}, {"$pull": {f"{semester}.{lec}": interaction.user.id}})
        removed = True
        # remove the user from the lecture section
        db.courses.update_one({"_id": course_code},
                              {"$pull": {semester + ".lectureSections." + lec: interaction.user.id}})
        # remove the lecture section from the user's profile
        db.users.update_one({"_id": interaction.user.id},
                            {"$unset": {semester + "." + course_code + ".lectureSection": ""}})
    if ("tutorialSection" in db.users.find_one(
            {"_id": interaction.user.id})[semester][course_code] and "tut" in objecttoremove):
        removed = True
        tut = db.users.find_one({"_id": interaction.user.id})[semester][course_code]["tutorialSection"]
        db.courses.update_one({"_id": course_code}, {"$pull": {semester + "." + tut: interaction.user.id}})
        db.users.update_one({"_id": interaction.user.id},
                            {"$unset": {semester + "." + course_code + ".tutorialSection": ""}})
    if ("practicalSection" in db.users.find_one({"_id": interaction.user.id})
    [semester][course_code] and "prac" in objecttoremove):
        removed = True
        pra = db.users.find_one({"_id": interaction.user.id})[semester][course_code]["practicalSection"]
        db.courses.update_one({"_id": course_code}, {"$pull": {semester + "." + pra: interaction.user.id}})
        db.users.update_one({"_id": interaction.user.id},
                            {"$unset": {semester + "." + course_code + ".practicalSection": ""}})
    if (objecttoremove == "lec_prac_tut" or (
            not "tutorialSection" in db.users.find_one({"_id": interaction.user.id})[semester][
                course_code] and not "practicalSection" in db.users.find_one({"_id": interaction.user.id})[semester][
        course_code]) and not "lectureSection" in db.users.find_one({"_id": interaction.user.id})[semester][
        course_code]):
        # remove the course from the user's profile
        db.users.update_one({"_id": interaction.user.id}, {"$unset": {semester + "." + course_code: ""}})
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