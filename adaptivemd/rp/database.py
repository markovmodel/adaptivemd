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

    def get_tasks_descriptions(self):
        """Returns a list of task definitions from Mongo.
        Returns an empty list if none is found"""
        task_descriptions = list()
        client = MongoClient(self.url)
        try:
            db = client[self.store_name]
            col = db[self.tasks_collection]
            for task in col.find({"state": "created"}):
                # Update the current task, should be 'find_and_update'
                # but since we are the only one getting these tasks,
                # we are getting them in bulk
                # col.update_one({'_id': task['_id']}, {"state": "running"})
                # Append task description
                task_descriptions.append(task)
        finally:
            client.close()
        return task_descriptions

    def get_resource_descriptions(self):
        """Get a list resources
        """
        resource_descriptions = list()
        client = MongoClient(self.url)
        try:
            db = client[self.store_name]
            col = db[self.resource_collection]
            for resource in col.find():
                resource_description = resource
                # Get configuration for this resource
                config = self.get_configuration_description(
                    name=resource['_dict']['config_name'])
                # If found, put all configuration in the resource,
                # except for the 'wrapper'
                if config:
                    for key, val in config['_dict']:
                        if key != 'wrapper':
                            resource_description['_dict'][key] = val
                resource_descriptions.append(resource_description)
        finally:
            client.close()
        return resource_descriptions

    def update_task_description_status(self, id=None, state='success'):
        """Update a single task with specific id
        :Parameters:
            - `id`: task description 'id' to be updated
            - `state`: state desired
        """
        if id:
            client = MongoClient(self.url)
            try:
                db = client[self.store_name]
                col = db[self.tasks_collection]
                # Updates both places where the 'state' value is on
                col.update_one({'_id': id},
                               {
                    '$set': {'state': state},
                    '$set': {'_dict.state': state}
                })
            finally:
                client.close()

    def get_configuration_description(self, name=None):
        """Get a specific configuration description
        :Parameters:
            - `name`: configuration description 'name'
        """
        configuration_description = None
        client = MongoClient(self.url)
        try:
            db = client[self.store_name]
            col = db[self.configuration_collection]
            result = col.find_one({'name': name})
            # Convert document into value dictionary,
            # we only really care about what is on '_dict'
            # so we will expand it
            if result:
                configuration_description = result
        finally:
            client.close()
        return configuration_description
