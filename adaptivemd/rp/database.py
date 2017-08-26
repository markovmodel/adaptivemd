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
        self.store_name = "{}-{}".format('storage', self.project)
        self.tasks_collection = 'tasks'
        self.resource_collection = 'resources'
        self.configuration_collection = 'configurations'

    def get_tasks_descriptions(self):
        """Returns a list of task definitions from Mongo.
        Returns an empty list if none is found"""
        task_descriptions = list()
        client = MongoClient(self.url)
        db = client[self.store_name]
        col = db[self.tasks_collection]

        for task in col.find({"state": "created"}):
            # Update the current task, should be 'find_and_update'
            # but since we are the only one getting these tasks,
            # we are getting them in bulk
            # pprint(task)
            # col.update_one({'_id': task['_id']}, {"state": "running"})

            # Bring '_dict' to higher level
            task_description = task['_dict']
            # Add a few nice-sounding fields
            task_description['name'] = task['_cls']
            task_description['id'] = task['_id']
            # Pass the rest of the root fields
            task_description['_id'] = task['_id']
            task_description['_time'] = task['_time']
            task_description['_cls'] = task['_cls']
            task_description['_obj_uuid'] = task['_obj_uuid']
            # Append task description
            task_descriptions.append(task_description)
            
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
                # pprint(resource)
                resource_description = resource
                # TODO: convert resource_description into nice representation
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
                col.update_one({'_id': id}, {"state": state})
            finally:
                client.close()

    def get_configuration_description(self, id=None):
        """Get a specific configuration description
        :Parameters:
            - `id`: configuration description 'id'
        """
        configuration_description = None
        client = MongoClient(self.url)
        try:
            db = client[self.store_name]
            col = db[self.configuration_collection]
            result = col.find_one({'_id': id})
            # Convert document into value dictionary,
            # we only really care about what is on '_dict'
            # so we will expand it
            config = result['_dict']
            config['id'] = result['_id'],
            config['config_class_name'] = result['_cls'],
            config['_id'] = result['_id'],
            config['_cls'] = result['_cls'],
            config['_obj_uuid'] = result['_obj_uuid'],
            config['_time'] = result['_time'],
            configuration_description = config
        finally:
            client.close()
        return configuration_description
