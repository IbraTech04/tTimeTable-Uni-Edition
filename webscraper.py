from bs4 import BeautifulSoup
import requests
import json
url = 'https://utm.calendar.utoronto.ca/print/view/pdf/search_courses/print_page/debug/'

# Get the page
page = requests.get(url)
bs4 = BeautifulSoup(page.content, 'html.parser')
# get all elements with class 'views-field views-field-title'
courses = bs4.find_all('div', class_='no-break views-row') #all divs with course info; we will extract the course code from this
jsonFile = {} #initialize the json file
#write the JSON file
for i in range (0, len(courses)):
  #get course title
  try:
    courseTitle = courses[i].find('div', class_='views-field views-field-title').text
    instructionalHours = courses[i].find('span', class_='views-field views-field-field-hours').text.split(":")[1].lstrip()
    jsonFile[courseTitle.split("•")[0].rstrip()] = {
      "courseTitle": courseTitle.split("•")[1].lstrip(),
      "courseCode": courseTitle.split("•")[0].rstrip(),
      "lecture": ("L" in instructionalHours or "S" in instructionalHours),
      "tutorial": ("T" in instructionalHours),
      "practical": ("P" in instructionalHours),    
  }
  except:
    pass

#save JSON to UTMCourses.json
with open("UTMCourses.json", "w") as write_file:
    json.dump(jsonFile, write_file)