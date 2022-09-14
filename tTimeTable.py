from typing import Optional
import nextcord
import requests
from nextcord.ext import commands
import json
from pymongo import MongoClient
import os
from nextcord import Interaction, SlashOption, slash_command
# from nextcord.abc import GuildChannel  # Tentative import - going be used later
from nextcord import Attachment  # Tentative import - going be used later (ACORN HTML parsing)
from dotenv import load_dotenv
from Buttons import ConfirmDialogue
from Errors import *
from bs4 import BeautifulSoup
import ics
import datetime
import pytz

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
    arr = [x.strip() for x in arr if x.strip() != '']
    # Remove any entry in the array with a bracket
    arr = [x for x in arr if not x.startswith('(')]
    # Replace spaces in each entry with a dash
    arr = [x.replace(' ', '') for x in arr]
    return arr


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="importtimetable",
                          description="Import all your courses at once using an Acorn HTML/ics file")
async def import_timetable(interaction: Interaction, html_file: Optional[Attachment] = SlashOption(required=True, description="The file you exported from Acorn - ICS and HTML files accepted", name="acorn_file")):
    # Check if the file is an HTML file
    database_names = {"TUT": "tutorialSection", "LEC": "lectureSection", "PRA": "practicalSection"}
    if html_file.filename.endswith(".html"):
        # Save file to disk
        await html_file.save(str(interaction.user.id) + ".html")
        # Check if the file is an Acorn HTML file
        site = BeautifulSoup(open(str(interaction.user.id) + ".html", 'r'), 'html.parser')
        try:
            db = mongo.tTimeTableUniEdition
            div = site.find('div', class_='program-course-info')
            # get the table with the class called course-meeting
            table = div.find('table', class_='course-meeting')
            # get all the rows in the table
            rows = table.find_all('tr')
            # Consider using this to reduce variable usage
            # rows = site.find('div', class_='program-course-info').find('table', class_='course-meeting').find_all('tr')
            # iterate through the rows
            for row in rows:
                # get all the columns in the row
                cols = row.find_all('td')
                # iterate through the columns
                for i in range(0, len(cols)):
                    if i % 2 != 0:
                        continue
                    course_info = (cols[i].get_text()).lstrip().rstrip()
                    course_code = course_info.split(" ")[0]
                    course_semester = course_info.split(" ")[1]
                    course_activities = cols[i + 1].get_text().split("\n")
                    course_codes = fix_array(course_activities)
                    for code in course_codes:
                        init_database(interaction, course_code, course_semester, code)
                        if database_names[code[:3]] not in db.users.find_one({"_id": interaction.user.id})[course_semester][course_code]:
                            # Add the code's section to the user's profile
                            db.users.update_one({"_id": interaction.user.id},
                                                {"$set": {course_semester + "." + course_code + "." + database_names[code[:3]]: code}},
                                                upsert=True)
                            db.courses.update_one({"_id": course_code},
                                                  {"$push": {course_semester + "." + code: interaction.user.id}})
            await interaction.response.send_message("Successfully added courses to your profile!", ephemeral=True)
        except AttributeError:
            await interaction.response.send_message("Invalid HTML file - try again", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Something went wrong - try again. This bug has automatically "
                                                    "been reported to my owner", ephemeral=True)
            file = nextcord.File(str(interaction.user.id) + ".html")
            channel = tTimeTable.get_channel(1017951473629401088)
            await channel.send("Ibra! I encountered an error with tihs file. Please investigate", file=file)
        finally:
            # Delete the file
            os.remove(str(interaction.user.id) + ".html")
        return
    if html_file.filename.endswith(".ics"):
        try:
            db = mongo.tTimeTableUniEdition
            await html_file.save(str(interaction.user.id) + ".ics")
            # delay interaction response
            await interaction.response.defer()
            utc = pytz.UTC

            c = ics.Calendar(open(str(interaction.user.id) + ".ics", 'r').read())

            for event in c.events:
                course_code = event.name.split(" ")[0]
                activity_code = event.name.split(" ")[1]
                if event.begin > datetime.datetime(2023, 1, 9, 0, 0, 0, 0, utc):
                    course_semester = "S"
                else:
                    course_semester = "F"
                init_database(interaction, course_code, course_semester, activity_code)

                print(event.name)
                if database_names[activity_code[:3]] not in db.users.find_one({"_id": interaction.user.id})[course_semester][course_code]:
                    # Add the code's section to the user's profile
                    db.users.update_one({"_id": interaction.user.id},
                                        {"$set": {course_semester + "." + course_code + "." + database_names[activity_code[:3]]: activity_code}},
                                        upsert=True)
                    db.courses.update_one({"_id": course_code},
                                          {"$push": {course_semester + "." + activity_code: interaction.user.id}})
            await interaction.followup.send("Successfully added courses to your profile!", ephemeral=True)
        except Exception:
            await interaction.followup.send("Something went wrong. This is likely due to an invalid file")
        finally:
            os.remove(str(interaction.user.id) + ".ics")
            return
    await interaction.response.send_message("Invalid file type - try again", ephemeral=True)


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="addactivity",
                          description="Add an activity to your timetable")
async def add_activity(interaction: Interaction, coursecode: str = SlashOption(required=True, description="The course code of the activity you want to add", name="course_code"),
                       semester: str = SlashOption(name="semester", choices={"F": "F", "S": "S", "Y": "Y"}, description="The semester of the activity you want to add", required=True),
                       activity_type: str = SlashOption(name="activity_type", choices={"LEC": "lecture", "TUT": "tutorial", "PRA": "practical"}, description="The type of activity you want to add", required=True),
                       activity_section: str = SlashOption(required=True, description="The section of the activity you want to add", name="activity_section"),
                       campus_code: str = SlashOption(required=True, description="The campus which the activity is held at", name="campus_code", choices={"UTSG": "1", "UTSC": "3", "UTM": "5"})):

    """
    Command which adds an activity (lecture, tutorial, practical) to a user's profile, and creates a user profile if one
    does not exist
    :param interaction: Interaction object
    :param coursecode: Course code of the course to be added
    :param semester: Semester of the course to be added
    :param activity_type: Type of activity to be added
    :param activity_section: Tutorial section of the course to be added
    """
    activities = {"lecture": "LEC", "tutorial": "TUT", "practical": "PRA"}
    db = mongo.tTimeTableUniEdition
    # These are checks to make sure the inputted info is valid
    # Step One: Check if the course code is valid - check if it is in the json file
    course_code = coursecode.upper()
    activity_section = activity_section.upper()
    try:
        course_code, activity_section = validate_course(course_code, semester, activity_section,
                                                        activities[activity_type], activity_type)
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
        await interaction.response.send_message("Invalid activity section, check your spelling and try again",
                                                ephemeral=True)
        return
    except ActivityNotValidForCourseException:
        await interaction.response.send_message(f"This course does not have a {activity_type} section"
                                                , ephemeral=True)
        return
    init_database(interaction, course_code, semester, activity_section)
    if f"{activity_type}Section" not in db.users.find_one(
            {"_id": interaction.user.id})[semester][course_code]:
        # Add the tutorial section to the user's profile
        db.users.update_one({"_id": interaction.user.id},
                            {"$set": {semester + "." + course_code + "." + f"{activity_type}Section":
                                      activity_section}}, upsert=True)
        db.courses.update_one({"_id": course_code}, {"$push": {semester + "." + activity_section: interaction.user.id}})
        await interaction.response.send_message(f"{UTMCourses[course_code]['courseTitle']} Added!")
        return
    await interaction.response.send_message(
        "You already have this course in your timetable. Use /remove to remove this course from your timetable",
        ephemeral=True)

#help command
@tTimeTable.slash_command(guild_ids=[518573248968130570], name="help", description="Get help with the bot")
async def help_command(interaction: Interaction, command: Optional[str] = SlashOption(name="command", description="The command you need help with", required=False,
                                                                                      choices={"addactivity": "1",
                                                                                               "importtimetable": "2",
                                                                                               "importacorn": "3",
                                                                                               "remove": "4"})):

    """
    Command which sends a help embed to the user
    :param interaction: Interaction object
    :param command: The command the user needs help with
    """
    if (command is None):
        embed = nextcord.embeds.Embed(title="Help", description="Need help with tTimeTable? You're in the right place!", color=0x4287f5)
        embed.add_field(name="/addactivity", value="Add an activity to your timetable (LEC, TUT, PRAC)", inline=False)
        embed.add_field(name="/importtimetable", value="Import your timetable from an Acorn .ics file", inline=False)
        embed.add_field(name="/importacorn", value="Import your timetable directly from Acorn using your weblogin idpz tokens", inline=False)
        embed.add_field(name="/viewclassmates", value="View the classmates in your activity", inline=False)
        embed.add_field(name="/remove", value="Remove a course from your timetable", inline=False)

        embed.add_field(name="/help", value="Get help with the bot", inline=False)
    elif command == "1":
        embed = nextcord.embeds.Embed(title="About /addactivity", description="/addactivity is one of the main commands used with tTimeTable")
        embed.add_field(name = "Description", value="Used to add courses and activites to your timetable")
        embed.add_field(name = "Usage", value="/addactivity <courseCode> <semester> <activityType> <activitySection>")
        embed.add_field(name="Example:", value="`/addActivity CSC108 F LEC 0102`", inline=False)
        embed.add_field(name="Example:", value="`/addActivity CSC108H5 F LEC LEC0102`", inline=False)
        embed.set_footer(text="All arguments are handled through Discords slash command interface")
    elif command == "2":
        embed = nextcord.embeds.Embed(title="About /importtimetable", description="/importtimetable is one of the main commands used with tTimeTable")
        embed.add_field(name = "Description", value="Used to import your timetable from an Acorn .ics file")
        embed.add_field(name = "Usage", value="/importtimetable <file>")
        embed.add_field(name="Supported Files", value="tTimeTabls supports .ics and .html files from Acorn")
        embed.add_field(name="Example:", value="`/importtimetable` with a file attached", inline=False)
        embed.add_field(name="Where can I find my .ics file?", value="From Acorn, navigate to the 'TimeTables and Exams tab. Click 'Download Calendar Export' and upload the file Acorn provides '")
        embed.add_field(name="Where can I find my .html file?", value="Pressing Ctrl/Cmd + S on your Acorn timetable page and uploading the saved html file will suffice for tTimeTable")
        embed.set_footer(text="All arguments are handled through Discords slash command interface")
    elif command == "3":
        embed = nextcord.embeds.Embed(title="About /importacorn", description="/importacorn is one of the main commands used with tTimeTable")
        embed.add_field(name = "Description", value="Used to import your timetable directly from Acorn using your weblogin idpz tokens")
        embed.add_field(name = "Usage", value="/importacorn <idpzToken>")
        embed.add_field(name="Is this safe?" , value="Yes, tTimeTable does not store your idpz token in any way. It is only used to access your timetable and is discarded after the import is complete")
        embed.add_field(name="How do I get my idpz token?", value="This process differs depending on your browser. On chromium browsers (Chrome, Edge, Brave, etc): \n1. Login to Acorn \n2. In a new tab, navigate to `<your browser>://settings/cookies/detail?site=acorn.utoronto.ca` \nExample: If you're using Edge, type in `edge://settings/cookies/detail?site=acorn.utoronto.ca`\n3. Expand each entry in the list \n4. Copy each cookie's content and paste it into its respective field in the command \n5. Run the command")
        embed.set_footer(text="All arguments are handled through Discords slash command interface")

    else:
        embed = nextcord.embeds.Embed(title="About /remove", description="/remove is one of the main commands used with tTimeTable")
        embed.add_field(name = "Description", value="Used to remove courses and activites from your timetable")
        embed.add_field(name = "Usage", value="/remove <courseCode> <semester> <activityToRemove>")
        embed.add_field(name="Example:", value="`/remove CSC108 F LEC`", inline=False)
        embed.set_footer(text="All arguments are handled through Discords slash command interface")

    await interaction.response.send_message(embed=embed)

# Legacy Commands - Merged into /addactivity

# @tTimeTable.slash_command(guild_ids=[518573248968130570], name="addtutorial",
#                           description="Add a tutorial to your timetable")
# async def addtutorial(interaction: Interaction, coursecode: str = SlashOption(required=True),
#                       semester: str = SlashOption(name="semester", choices={"F": "F", "S": "S", "Y": "Y"}, required=True),
#                       tutorial_section: str = SlashOption(required=True)):
#     """
#     Command which adds a lecture to a user's profile, and creates a user profile if one does not exist
#     :param interaction: Interaction object
#     :param coursecode: Course code of the course to be added
#     :param semester: Semester of the course to be added
#     :param tutorial_section: Tutorial section of the course to be added
#     """
#     db = mongo.tTimeTableUniEdition
#     # These are checks to make sure the inputted info is valid
#     # Step One: Check if the course code is valid - check if it is in the json file
#     course_code = coursecode.upper()
#     tutorial_section = tutorial_section.upper()
#     try:
#         course_code, tutorial_section = validate_course(course_code, semester, tutorial_section, "TUT", "tutorial")
#     except CourseNotFoundException:
#         await interaction.response.send_message("Invalid course code, check your spelling and try again",
#                                                 ephemeral=True)
#         return
#     except SemesterNotValidForCourseException:
#         await interaction.response.send_message(
#             "Looks like this course isn't offered in your selected semester, "
#             "try again. If you think this is an error, please contact my owner",
#             ephemeral=True)
#         return
#     except ActivityNotFoundException:
#         await interaction.response.send_message("Invalid tutorial section, check your spelling and try again",
#                                                 ephemeral=True)
#         return
#     except ActivityNotValidForCourseException:
#         await interaction.response.send_message("This course does not have a tutorial", ephemeral=True)
#         return
#     init_database(interaction, course_code, semester, tutorial_section)
#     if "tutorialSection" not in db.users.find_one({"_id": interaction.user.id})[semester][course_code]:
#         # Add the tutorial section to the user's profile
#         db.users.update_one({"_id": interaction.user.id},
#                             {"$set": {semester + "." + course_code + "." + "tutorialSection": tutorial_section}},
#                             upsert=True)
#         db.courses.update_one({"_id": course_code}, {"$push": {semester + "." + tutorial_section: interaction.user.id}})
#         await interaction.response.send_message(f"{UTMCourses[course_code]['courseTitle']} Added!")
#         return
#     await interaction.response.send_message(
#         "You already have this course in your timetable. Use /remove to remove this course from your timetable",
#         ephemeral=True)
#
#
# @tTimeTable.slash_command(guild_ids=[518573248968130570], name="addpractical",
#                           description="Add a practical to your timetable")
# async def addpractical(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True),
#                        semester: str = SlashOption(name="semester", choices={"F": "F", "S": "S", "Y": "Y"}),
#                        practicalsection: Optional[str] = SlashOption(required=True)):
#     """
#     Command which adds a lecture to a user's profile, and creates a user profile if one does not exist
#     :param interaction: Interaction object
#     :param coursecode: Course code of the course to be added
#     :param semester: Semester of the course to be added
#     :param practicalsection: Practical section of the course to be added
#     """
#     db = mongo.tTimeTableUniEdition
#     # These are checks to make sure the inputted info is valid
#     # Step One: Check if the course code is valid - check if it is in the json file
#     course_code = coursecode.upper()
#     practical_section = practicalsection.upper()
#     try:
#         course_code, practical_section = validate_course(course_code, semester, practical_section, "PRA", "practical")
#     except CourseNotFoundException:
#         await interaction.response.send_message("Invalid course code, check your spelling and try again",
#                                                 ephemeral=True)
#         return
#     except SemesterNotValidForCourseException:
#         await interaction.response.send_message(
#             "Looks like this course isn't offered in your selected semester, "
#             "try again. If you think this is an error, please contact my owner",
#             ephemeral=True)
#         return
#     except ActivityNotFoundException:
#         await interaction.response.send_message("Invalid practical section, check your spelling and try again",
#                                                 ephemeral=True)
#         return
#     except ActivityNotValidForCourseException:
#         await interaction.response.send_message("This course does not have a practical", ephemeral=True)
#         return
#     init_database(interaction, course_code, semester, practical_section)
#     if "practicalSection" not in db.users.find_one({"_id": interaction.user.id})[semester][course_code]:
#         # Add the practical to the user's profile
#         db.users.update_one({"_id": interaction.user.id},
#                             {"$set": {semester + "." + course_code + "." + "practicalSection": practical_section}},
#                             upsert=True)
#         db.courses.update_one({"_id": course_code},
#                               {"$push": {semester + "." + practical_section: interaction.user.id}})
#         await interaction.response.send_message(f"{UTMCourses[course_code]['courseTitle']} Added!")
#         return
#     await interaction.response.send_message(
#         "You already have this course in your timetable. Use /remove to remove this course from your timetable",
#         ephemeral=True)
#
#
# @tTimeTable.slash_command(guild_ids=[518573248968130570], name="addlecture",
#                           description="Add a lecture to your timetable")
# async def addlecture(interaction: Interaction, coursecode: Optional[str] = SlashOption(required=True),
#                      semester: str = SlashOption(name="semester", choices={"F": "F", "S": "S", "Y": "Y"}),
#                      lecturesection: Optional[str] = SlashOption(required=True)):
#     """
#     Command which adds a lecture to the user's timetable
#     :param interaction: Interaction object
#     :param coursecode: Course code of the course to be added
#     :param semester: Semester of the course to be added
#     :param lecturesection: Lecture section of the course to be added
#     """
#     db = mongo.tTimeTableUniEdition
#     # These are checks to make sure the inputted info is valid
#     # Step One: Check if the course code is valid - check if it is in the json file
#     course_code = coursecode.upper()
#     lecture_section = lecturesection.upper()
#     try:
#         course_code, lecture_section = validate_course(course_code, semester, lecture_section, "LEC", "lecture")
#     except CourseNotFoundException:
#         await interaction.response.send_message("Invalid course code, check your spelling and try again",
#                                                 ephemeral=True)
#         return
#     except SemesterNotValidForCourseException:
#         await interaction.response.send_message(
#             "Looks like this course isn't offered in your selected semester, "
#             "try again. If you think this is an error, please contact my owner",
#             ephemeral=True)
#         return
#     except ActivityNotFoundException:
#         await interaction.response.send_message("Invalid lecture section, check your spelling and try again",
#                                                 ephemeral=True)
#         return
#     except ActivityNotValidForCourseException:
#         await interaction.response.send_message(
#             "This course does not have a lecture? This is probably a mistake - Please contact my owner", ephemeral=True)
#         return
#     init_database(interaction, course_code, semester, lecture_section)
#     if "lectureSection" not in db.users.find_one({"_id": interaction.user.id})[semester][course_code]:
#         # Add the lecture to the user's profile
#         db.users.update_one({"_id": interaction.user.id},
#                             {"$set": {semester + "." + course_code + "." + "lectureSection": lecture_section}},
#                             upsert=True)
#         db.courses.update_one({"_id": course_code}, {"$push": {semester + "." + lecture_section: interaction.user.id}})
#         await interaction.response.send_message(f"{UTMCourses[course_code]['courseTitle']} Added!")
#         return
#     await interaction.response.send_message(
#         "You already have this course in your timetable. Use /remove to remove this course from your timetable",
#         ephemeral=True)


@tTimeTable.slash_command(guild_ids=[518573248968130570], name="importacorn", description="Import your timetable directly from Acorn")
async def importacorn(interaction: Interaction, jsessionID: str = SlashOption(required=True, name="jsessionid", description="Your JSESSIONID cookie from Acorn"),
                            ltpatoken2: str = SlashOption(required=True, name="ltpatoken2", description="Your LTPATOKEN2 cookie from Acorn"),
    wsjessionid = SlashOption(required=True, name="wsjessionid", description="Your WSJSESSIONID cookie from Acorn"),
    xsrf_token = SlashOption(required=True, name="xsrf_token", description="Your XSRF-TOKEN cookie from Acorn")):
    """
    Command which imports a user's timetable from Acorn
    :param interaction: Interaction object
    :param jsessionID: JSESSIONID cookie from Acorn
    :param ltpatoken2: LTPATOKEN2 cookie from Acorn
    :param wsjessionid: WSJSESSIONID cookie from Acorn
    :param xsrf_token: XSRF-TOKEN cookie from Acorn
    :return:
    """
    cookies = {
        'LtpaToken2': f"{ltpatoken2}",
        'JSESSIONID': f"{jsessionID}",
        'XSRF-TOKEN': f"{xsrf_token}",
        'WSJSESSIONID': f"{wsjessionid}",
    }

    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'If-Modified-Since': '1',
        'Pragma': 'no-cache',
        'Prefer': 'safe',
        'Referer': 'https://acorn.utoronto.ca/sws/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36 Edg/104.0.1293.70',
        'X-XSRF-TOKEN': '74bmRIHJX0vKGYnRN1F4na8o007dpgSF+xZ1j2ZZFU8=',
        'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Microsoft Edge";v="104"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    response = requests.get(
        'https://acorn.utoronto.ca/sws/rest/enrolment/course/enrolled-courses?acpDuration=2&adminOrgCode=ERIN&assocOrgCode=ERIN&coSecondaryOrgCode=&collaborativeOrgCode=&designationCode1=PGM&levelOfInstruction=U&postAcpDuration=2&postCode=ER+++CMS1&postDescription=UTM+Intro+to+CSC,+MATH+%26+STATS&primaryOrgCode=ERIN&secondaryOrgCode=&sessionCode=20229&sessionDescription=2022-2023+Fall%2FWinter&status=REG&subjectCode1=SCN&typeOfProgram=OTH&useSws=Y&yearOfStudy=1',
        cookies=cookies, headers=headers)
    try:
        await interaction.response.defer()
        choices = {"LEC": "lecture", "TUT": "tutorial", "PRA": "practical"}
        db = mongo.tTimeTableUniEdition
        response = response.json()
        response = response['APP']
        for course in response:
            course_code = course['code']
            for meetings in course['meetings']:
                semester = course['sectionCode']
                activity_section = meetings['teachMethod'] + meetings['sectionNo']
                activity_type = choices[meetings['teachMethod']]
                init_database(interaction, course_code, semester, activity_section)
                if f"{activity_type}Section" not in db.users.find_one(
                        {"_id": interaction.user.id})[semester][course_code]:
                    # Add the tutorial section to the user's profile
                    db.users.update_one({"_id": interaction.user.id},
                                        {"$set": {semester + "." + course_code + "." + f"{activity_type}Section":
                                                      activity_section}}, upsert=True)
                    db.courses.update_one({"_id": course_code},
                                          {"$push": {semester + "." + activity_section: interaction.user.id}})
        await interaction.followup.send("Your timetable has been imported!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send("Invalid cookies, please try again. To find your cookies, navigate to `edge://settings/cookies/detail?site=acorn.utoronto.ca` on edge or `chrome://settings/cookies/detail?site=acorn.utoronto.ca` on Chrome. Make sure you're signed into Acorn before you do this", ephemeral=True)
        print(e)
@tTimeTable.slash_command(guild_ids=[518573248968130570], name="viewclassmates",
                          description="See who else is in your class!")
async def viewclassmates(interaction: Interaction, course_code: Optional[str] = SlashOption(required=True,
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
            "You don't have a profile, use /addactivity to add a course to your profile", ephemeral=True)
        return
    # Step Two: Check if the user has the semester in their profile
    if semester not in mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id}):
        await interaction.response.send_message(
            "You don't have any courses in this semester, use /addactivity to add a course to your profile",
            ephemeral=True)
        return
    # Step Three: Validate coursecode
    try:
        course_code = validate_course(course_code.upper(), semester, "", "", "lecture", True)
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
            "You don't have this course in your profile, use /addactivity to add a course to your profile",
            ephemeral=True)
        return
    # If we're here, we know the course code is valid, and the user has the course in their profile
    embed = nextcord.embeds.Embed(title=f"Classmates in {UTMCourses[course_code]['courseTitle']}",
                                  description="Here are the people in your class", color=0x4287f5)
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
            "You don't have any courses in your profile, use /addactivity to add a course to your profile",
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
            "You don't have any courses in this semester, use /addactivity to add a course to your profile",
            ephemeral=True)
        return
    # Now we know both the course and the semester are valid, we need to check
    # if the user has the course in their profile

    if course_code not in mongo.tTimeTableUniEdition.users.find_one({"_id": interaction.user.id})[semester]:
        await interaction.response.send_message(
            "You don't have this course in your profile, use /addactivity to add a course to your profile",
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
    if not removed: #If we didn't remove anything, then the user didn't have it in their timetable
        await interaction.followup.send("You don't have this sections in this course", ephemeral=True)
        return
    await interaction.followup.send(f"Removed {course_code} - {UTMCourses[course_code]['courseTitle']} from your profile", ephemeral=True)
#on ready
@tTimeTable.event
async def on_ready():
    print(f"Logged in as {tTimeTable.user.name}#{tTimeTable.user.discriminator}")
    print("Ready to go!")

tTimeTable.run(os.getenv('DISCORD_TOKEN')) #token for the botfrom typing import Optional