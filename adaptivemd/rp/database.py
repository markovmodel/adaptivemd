from pymongo import MongoClient
from pprint import pprint
# Task Status: created, running, fail, halted, success, cancelled


class Database():
    """Mongo database access object

    Current list of collections in the database:
    [
        'files',
        'stores',
        'generators',
        'posts',
        'resources',
        'fs.files',
        'fs.chunks',
        'tasks'
    ]
    """

    def __init__(self, mongo_url='mongodb://localhost:27017/', project='test'):
        """Initialize a new Database interaction class
        :Parameters:
            - `mongo_url`: full mongo url, e.g. mongodb://localhost:27017/
            - `project`: project string for this database
        """
        self.url = mongo_url
        self.project = project
        self.store_prefix = 'storage'
        self.store_name = "{}-{}".format(self.store_prefix, self.project)
        self.tasks_collection = 'tasks'
        self.resource_collection = 'resources'
        self.configuration_collection = 'configurations'
        self.file_collection = 'files'
        self.generator_collection = 'generators'
        self.client = MongoClient(self.url)
        self.db = self.client[self.store_name]

    def get_task_descriptions(self):
        """Returns a list of task definitions from Mongo.
        Returns an empty list if none is found"""
        task_descriptions = list()
        col = self.db[self.tasks_collection]
        for task in col.find({"state": "created"}):
            # Update the current task, should be 'find_and_update'
            # but since we are the only one getting these tasks,
            # we are getting them in bulk
            # col.update_one({'_id': task['_id']}, {"state": "running"})
            # Append task description
            task_descriptions.append(task)
        return task_descriptions

    def get_resource_requirements(self):
        """Get a list resources
        """
        resource_descriptions = list()
        col = self.db[self.resource_collection]
        for resource in col.find():
            resource_descriptions.append(resource)
        return resource_descriptions

    def get_configurations(self):
        """Get a list of configuration descriptions
        """
        configuration_descriptions = list()
        db = self.client[self.store_name]
        col = db[self.configuration_collection]
        for configuration_description in col.find():
            configuration_descriptions.append(configuration_description)
        return configuration_descriptions

    def get_file_destination(self, id=None):
        """Get the location information of a specific file
        :Parameters:
            - `id`: file object 'id' to lookup
        """
        location = None
        if id:
            col = self.db[self.file_collection]
            result = col.find_one({'_id': id})
            if result:
                location = result['_dict']['location']
        return location

    def get_source_files(self, id=None):
        """Get the generator file locations for all types
        :Parameters:
            - `id`: generator object 'id' to lookup
        """
        generator_files = list()
        col = self.db[self.generator_collection]
        generator = col.find_one({'_id': id})
        if generator:
            for key, val in generator['_dict']['types'].iteritems():
                generator_files.append(val['_dict']['filename'])
        return generator_files

    def update_task_description_status(self, id=None, state='success'):
        """Update a single task with specific id
        :Parameters:
            - `id`: task description 'id' to be updated
            - `state`: state desired
        """
        if id:
            col = self.db[self.tasks_collection]
            # Updates both places where the 'state' value is on
            result = col.update_one({'_id': id},
                                    {'$set': {
                                        '_dict.state': state,
                                        'state': state,
                                    }})
            if result.modified_count == 1:
                return True
            else:
                return False
        else:
            return False
