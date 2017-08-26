from pprint import pprint
import radical.pilot as rp


def resolve_pathholders(path, shared_path):

    if '///' not in path:
        return path

    #schema, relative_path = path.split('///')

    if schema == 'staging':
        path.replace(schema+':///', '%s/workers/staging_area/'%shared_path)

    return path


def get_input_staging(task_details, shared_path):

    staging_directives = []

    for entity in task_details:

        if not isinstance(entity, dict):
            break

        staging_type = entity['_cls']

        if staging_type in ['Link', 'Copy']:

            src = resolve_pathholders(entity['_dict']['source']['_dict']['location'])
            dest = resolve_pathholders(entity['_dict']['target']['_dict']['location'])

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

    #TODO
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


def process_resource_description(raw_res_desc):

    pass
    
