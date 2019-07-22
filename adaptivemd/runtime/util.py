
def print_last_model(project):
    try:
        logger.info("Hopefully model prints below!")
        mdat = project.models.last.data
        logger.info("Model created using modeller:".format(project.models.last.name))
        logger.info("Attempted to use n_microstates: {}".format(mdat['clustering']['k']))
        logger.info("Length of MSM populations row (ie # connected states): {}".format(len(mdat['msm']['C'][0])))
        logger.debug(pformat(mdat['msm']))

    except:
        logger.info("Seems there was an error or could not print the last model")


class counter(object):
    def __init__(self, maxcount=0):
        self.n = maxcount
        self.i = 0

    @property
    def done(self):
        return not self.i < self.n

    def increment(self):
        self.i += 1
