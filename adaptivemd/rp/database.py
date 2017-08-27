from pymongo import MongoClient
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
        self.store_name = "{}-{}".format('storage', self.project)
        self.tasks_collection = 'tasks'
        self.resource_collection = 'resources'
        self.configuration_collection = 'configurations'
        self.client = MongoClient(self.url)

    def get_task_descriptions(self):
        """Returns a list of task definitions from Mongo.
        Returns an empty list if none is found"""
        task_descriptions = list()
        db = self.client[self.store_name]
        col = db[self.tasks_collection]
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
        db = self.client[self.store_name]
        col = db[self.resource_collection]
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

    def update_task_description_status(self, id=None, state='success'):
        """Update a single task with specific id
        :Parameters:
            - `id`: task description 'id' to be updated
            - `state`: state desired
        """
        if id:
            db = self.client[self.store_name]
            col = db[self.tasks_collection]
            # Updates both places where the 'state' value is on
            col.update_one({'_id': id},
                           {'$set': {
                            '_dict.state': state,
                            'state': state,
                            }})


            # @MM: Add method to check if update was successful and return a boolean?