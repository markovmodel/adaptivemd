from adaptivemd.rp.client import Client

from time import sleep

if __name__ == '__main__':

    c = Client(dburl='mongodb://user:user@two.radical-project.org:32769/', project='rp_testing_3')
    c.start()
    sleep(30)
    c.stop()