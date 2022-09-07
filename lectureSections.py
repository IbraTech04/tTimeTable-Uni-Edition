import json
import requests

headers = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    # Already added when you pass json=
    # 'Content-Type': 'application/json',
    'Origin': 'https://ttb.utoronto.ca',
    'Prefer': 'safe',
    'Referer': 'https://ttb.utoronto.ca/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.102 Safari/537.36 Edg/104.0.1293.70',
    'sec-ch-ua': '"Chromium";v="104", " Not A;Brand";v="99", "Microsoft Edge";v="104"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

json_data = {
    'courseCodeAndTitleProps': {
        'courseCode': '',
        'courseTitle': '',
        'courseSectionCode': '',
    },
    'departmentProps': [],
    'campuses': [],
    'sessions': [
        '20229',
        '20231',
        '20229-20231',
    ],
    'requirementProps': [],
    'instructor': '',
    'courseLevels': [],
    'deliveryModes': [],
    'dayPreferences': [],
    'timePreferences': [],
    'divisions': [
        'ERIN',
    ],
    'creditWeights': [],
    'page': 1,
    'pageSize': 2000,
    'direction': 'asc',
}
"""response = requests.post('https://api.easi.utoronto.ca/ttb/getPageableCourses', headers=headers, json=json_data)
#save to json
response = response.json()
with open('response.json', 'w') as f:
    json.dump(response, f, indent=4)"""


response = json.load(open('lectureSections.json'))

courses = response['payload']['pageableCourse']
UTMCourses = json.load(open('UTMCourses.json', 'r'))
failedcourses = []
runs = 0
for course in courses['courses']: 
    runs += 1
    if (not course['code'] in UTMCourses):
        #search for if theres a practical and tutorial
        tutorial = False
        practical = False
        for section in course['sections']:
            if ("PRA" in section['name']):
                practical = True
            if ("TUT" in section['name']):
                tutorial = True
        UTMCourses[course['code']] = {
            "courseTitle": course['name'],
            "courseCode": course['code'],
            "lecture": True,
            "tutorial": tutorial,
            "practical": practical
        }
    utmcourse = UTMCourses[course['code']]
    #Now we'll add the relavent information to the course
    if (not 'sections' in utmcourse):
        utmcourse['sections'] = []
    for section in course['sections']: #Adding valid lecture/practical/tutorial sections
        if (section['name'] not in utmcourse['sections']):
            utmcourse['sections'].append(section['name'])
    #Now we'll add valid semesters
    if (not "validSemesters" in utmcourse):
        utmcourse['validSemesters'] = []
    if (course['sectionCode'] not in utmcourse['validSemesters']):
        utmcourse['validSemesters'].append(course['sectionCode'])
    continue
#Now we need to deal with the failedcourses. These are custom courses made by students so we need to manually scrape their info from the big JSON


#save new json
with open('UTMCourses.json', 'w') as f:
    json.dump(UTMCourses, f, indent=2)
    
