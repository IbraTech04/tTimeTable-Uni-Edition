class CourseNotFoundException(Exception):
    pass

class SemesterNotValidForCourseException(Exception):
    pass
class ActivityNotValidForCourseException(Exception):
    pass
class ActivityNotFoundException(Exception):
    pass