from pprint import pprint
import radical.pilot as rp


def resolve_pathholders(path, shared_path):

    if '///' not in path:
        return path

    # schema, relative_path = path.split('///')

    if schema == 'staging':
        path.replace(schema + ':///', '%s/workers/staging_area/' % shared_path)

    return path


def get_input_staging(task_details, shared_path):

    staging_directives = []

    for entity in task_details:

        if not isinstance(entity, dict):
            break

        staging_type = entity['_cls']

        if staging_type in ['Link', 'Copy']:

            src = resolve_pathholders(
                entity['_dict']['source']['_dict']['location'])
            dest = resolve_pathholders(
                entity['_dict']['target']['_dict']['location'])

        temp_directive = {
            'source': src,
            'action': staging_type,
            'target': dest
        }

        staging_directives.append(temp_directive)

    return staging_directive


def get_executable(task_details):

    for entity in task_details:
        if not isinstance(entity, dict):
            return [str(entity)]

    return None


def get_output_staging(task_details, shared_path):

    # TODO
    pass


def create_cud_from_task_def(task_def, shared_path):

    task_details = task_def['_dict']['_main']

    cud = rp.ComputeUnitDescription()
    cud.name = task_def['_id']
    cud.executable = get_executable(task_details)
    cud.input_staging = get_input_staging(task_details, shared_path)
    cud.output_staging = get_output_staging(task_details, shared_path)
    cud.cores = 16

    return cud


def process_resource_description(raw_res_descs):

    resources = list()
    for res_desc in raw_res_descs:
        print type(res_desc)
        temp_desc = dict()
        temp_desc['total_cpus'] = res_desc['_dict']['total_cpus']
        temp_desc['total_gpus'] = res_desc['_dict']['total_gpus']
        temp_desc['total_time'] = res_desc['_dict']['total_time']
        temp_desc['resource'] = res_desc['_dict']['destination']
        resources.append(temp_desc)

    return resources


def process_configurations(conf_descs):

    configurations = list()
    for conf in conf_descs:

        for queue in conf['queues']:

            temp_desc = list()
            temp_desc['resource'] = conf['resource_mname']
            temp_desc['project'] = conf['allocation']
            temp_desc['shared_path'] = conf['shared_path']
            temp_desc['queue'] = queue

            configurations.append(temp_desc)

    return configurations


def generic_matcher(the_list=None, key='', value=''):
    """Searches a list and matches all of the ones entries which 'key'
    and 'value' match. The values should be inside of the '_dict' object.
    :Parameters:
    - `the_list`: list to search through
    - `key`: key of the item to match
    - `value`: value of the item to match
    """
    matching = list()
    if the_list:
        for item in the_list:
            matching_value = item['_dict'][key]
            if matching_value.lower() in [value.lower()]:
                matching.append(item)
    return matching


def get_matching_configurations(configurations=None, resource_name=''):
    """Searches for a configuration descriptions list and matches all of the ones
    that match the specific resource_name.
    :Parameters:
    - `configurations`: list of configurations descriptions to search through
    - `resource_name`: resource name to match
    """
    return generic_matcher(
        the_list=configurations,
        key='resource_name',
        value=resource_name
    )
