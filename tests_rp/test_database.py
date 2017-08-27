from adaptivemd.rp.database import Database

def test_task_descriptions():

    db = Database(mongo_url='mongodb://user:user@two.radical-project.org:32769/', project='rp_testing_3')

    assert type(db.get_task_descriptions()) == list


def test_resource_requirements():

    db = Database(mongo_url='mongodb://user:user@two.radical-project.org:32769/', project='rp_testing_3')

    assert type(db.get_resource_requirements()) == list


def test_configurations():

    db = Database(mongo_url='mongodb://user:user@two.radical-project.org:32769/', project='rp_testing_3')

    assert type(db.get_configurations()) == list


    