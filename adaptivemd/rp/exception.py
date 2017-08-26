__author__    = "Vivek Balasubramanian <vivek.balasubramanian@rutgers.edu>"
__copyright__ = "Copyright 2017, http://radical.rutgers.edu"
__license__   = "MIT"

class RPError(Exception):
    """RPError is the base exception raised by Ensemble Toolkit"""
    def __init__ (self, msg):
        super(RPError, self).__init__ (msg)


class TypeError(RPError):
    """TypeError is raised if value of a wrong type is passed to a function or 
    assigned as an attribute of an object"""

    def __init__ (self, expected_type, actual_type, entity=None):
        
        if entity:
            msg = "Entity: %s, Expected (base) type(s) %s, but got %s."%(
                str(entity),
                str(expected_type), 
                str(actual_type)
                )
        else:
            msg = "Expected (base) type(s) %s, but got %s."%(
                str(expected_type), 
                str(actual_type)
                )
        super(TypeError, self).__init__ (msg)


class ValueError(RPError):

    """
    ValueError is raised if a value that is unacceptable is passed to a 
    function or assigned as an attribute of an object"""

    def __init__(self, obj, attribute, expected_value, actual_value):
        if type(expected_value) != list:
            msg = "Value for attribute %s of object %s incorrect. Expected value %s, but got %s."%(
                str(obj),
                str(attribute),
                str(expected_value), 
                str(actual_value)
                )
        else:
            msg=''
            for item in expected_value:
                msg += str(item)

            msg = "Value for attribute %s of object %s incorrect. Expected values %s, but got %s."%(
                str(obj),
                str(attribute),
                str(msg), 
                str(actual_value)
                )

        super(ValueError, self).__init__ (msg)


class MissingError(RPError):

    """
    MissingError is raised when an attribute that is mandatory is left
    unassigned by the user
    """

    def __init__(self, obj, missing_attribute):

        msg = 'Attribute %s in %s undefined'%(str(missing_attribute), str(obj))
        super(MissingError, self).__init__(msg)

class ExistsError(RPError):
    """ExistsError is raised when there is an attempt to add or assign an 
    object with a particular uid to another parent object which already 
    contains an object with the same uid"""

    def __init__ (self, item, parent):
        msg = "Object %s already exists in %s."%(
            str(item), 
            str(parent)
            )
        super(ExistsError, self).__init__ (msg)


class MatchError(RPError):
    """MatchError is thrown if two parameters are not equal."""

    def __init__ (self, par1, par2):
        msg = "%s does not match %s."%(
            str(par1), 
            str(par2)
            )
        super(MatchError, self).__init__ (msg)

class Error(RPError):
    """Error is raised for all other exceptions that cannot be categorized.
    The 'msg' describes the actual error"""

    def __init__(self, msg):
        msg = 'Error: %s'%msg
        super(Error, self).__init__(msg)