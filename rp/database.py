from pymongo import MongoClient

# Task Status: created, running, fail, halted, success, cancelled


class Database():
    """Mongo database access object
    """

    def __init__(self, db_url='mongodb://localhost:27017/', project='test'):
        self.url = db_url
        self.project = project
        self.tasks_collection = 'tasks'
        self.resource_collection = 'resource'

    def get_tasks_definitions(self):
        """Returns a list of task definitions from Mongo.
        Returns an empty list if none is found"""
        task_definitions = list()
        client = MongoClient(self.url)
        db = client[self.project]
        col = db[self.tasks_collection]
        for task in col.find({"state": "created"}):
            # Update the current task, should be 'find_and_update'
            # but since we are the only one getting these tasks,
            # we are getting them in bulk
            col.update_one({'_id': task._id}, {"state": "running"})
            task_definitions.append(task)
        return task_definitions

    def get_resource(self, name='test'):
        """Get the resource document
        """
        client = MongoClient(self.url)
        db = client[self.project]
        col = db[self.resource_collection]
        return col.find_one({'': ''}) # TODO: check what to return

    def update_task(self, _id=None, state='success'):
        """Update a single task with id: _id
        """
        if _id:
            client = MongoClient(self.url)
            db = client[self.project]
            col = db[self.tasks_collection]
            col.update_one({'_id': _id}, {"state": state})

