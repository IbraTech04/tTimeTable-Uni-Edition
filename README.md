# tTimeTable-Uni-Edition
Versatile Discord Bot used to keep track of student timetables and classmates at UofT

tTimeTable - Uni Edition is a new spin on the concept of tTimeTable. The bot works by communicating with a MongoDB database which keeps track of users and their courses. The main function of this bot is to allow users in a Discord server to easily view their classmates in their lectures, tutorials, and practicals. 

## How it works
The bot works by having users register their courses and their respecitve activities (lectures, practicals, tutorials). This info is then stored in a database somewhere in Toronto. When a user wants to see who is in their class, they can use the respective command, and the bot will traverse the database and find the users who are in the same class.

You'll notice that there are several python files within this repo - That's because of the required webscraping that is required to get the course information. When creating this bot, I needed to implement some form of check to ensure all course codes, activity sessions, etc, were in the same format and were all valid - Otherwise the concept would not work. It is for this reason that webscraper.py exists

My initial concept was to create a JSON file with every course offered at UofT (Well techniaclly UTM cause that's where I go :smile:) and all its relevent info (required activities, course code, course title, etc). My first idea was to scrape https://utm.calendar.utoronto.ca/course-search - It had a printer-friendly page which I was easily able to scrape using beautifulsoup. After consulting DevTools and Inspect Element for class/element names, I wrote the script. The bot worked with the created JSON, but something was missing. The bot could not check the validity of the entered sections as that information was not availible through the website I used. 

From here, I started thinking about different options. I researched ACORN APIs, but found nothing useful (I'm not sure if they even have one). Then it hit me....

https://ttb.utoronto.ca 

The golden key to this puzzle. This website houses all the relevent course information for every course offered on campus. I immediately knew this was going to be my point of entry. I considered scraping like the previous site, but since this site was more interactive that idea was going to be more of a chore. I didn't want to learn Selenium, so I decided to use the skills I built during picoCTF. I consulted DevTools. 

From there, I was able to find the API endpoint that I needed. I copied the cURL data and converted it into a Python request. From there, I played with the header, and was able to make a request to get all 1667 courses offered at UTM. I created, what I consider, by far the most overkill JSON file ever (lectureSections.json if you're curious). Weighing in at over 50 megabytes, this file contains every. single. aspect. of every course offered at UTM.

From there, I wrote a simple script to parse the new JSON file, extract the necissary data out of it, and insert it into the existing JSON. Then it was as simple as updating the code and bam! The bot was working with the new JSON file.
  
## Commands
tTimeTable uses slash commands exclusively. The commands are as follows:

### /addlecture {courseCode} {semester} {lectureSection}
Adds a lecture to a user's profile
### /addtutorial {courseCode} {semester} {tutorialSection}
Adds a tutorial to a user's profile
### /addpractical {courseCode} {semester} {practicalSection}
Adds a practical to a user's profile

### /remove {courseCode} {semester} {activity}
Removes an activity from a user's profile

### viewClassmates {courseCode} {semester} 
Replies with an embed containing the classmates in the specified course