import uuid
from pprint import pprint
import radical.pilot as rp
import os
from exceptions import *
import traceback
import json


def resolve_location(path):
    tripleslash = '///'
    doubleslash = '//'
    singleslash = '/'
    loc = os.path.expandvars(path)

    if loc.count(tripleslash) > 0:
        nvalid = loc.count(':///')
        loc = singleslash.join(loc.rsplit(
                tripleslash, loc.count(tripleslash) - nvalid
                ))

    loc = loc.rsplit(doubleslash, loc.count(doubleslash)-1 )
    location = singleslash.join(loc)

    return location


def resolve_pathholders(path, shared_path, project):

    if '///' not in path:
        resolved_path = os.path.expandvars(path)

    else:
        schema, relative_path = path.split(':///')

        if schema == 'staging':
            resolved_path = 'pilot:///' + os.path.basename(relative_path)

        elif schema == 'sandbox':
            resolved_path = path.replace(schema + '://', shared_path + '/')

        elif schema == 'file':
            resolved_path = path.replace(schema + '://', '')

        elif schema == 'project':
            resolved_path = path.replace(schema + '://', shared_path + '/projects/' + project + '/')

        resolved_path = resolve_location(resolved_path)

    return resolved_path


def get_input_staging(task_details, db, shared_path, project, break_after_non_dict=True):

    staging_directives = list()

    for entity in task_details:

        if not isinstance(entity, dict):
            if break_after_non_dict:
                break
            else:
                continue

        staging_type = entity['_cls']

        if staging_type in ['Link', 'Copy']:

            src,_ = get_file_location(entity['_dict']['source'], db, shared_path, project)
            dest,_ = get_file_location(entity['_dict']['target'], db, shared_path, project)

            if staging_type == 'Link':
                rp_staging_type = rp.LINK

            elif staging_type == 'Copy':
                rp_staging_type = rp.COPY

            temp_directive = {
                'source': str(src),
                'action': rp_staging_type,
                'target': str('unit:///' + dest)
            }

            if temp_directive not in staging_directives:
                staging_directives.append(temp_directive)

    # print staging_directives

    return staging_directives


def get_output_staging(task_desc, task_details, db, shared_path, project, continue_before_non_dict=True):

    # List containing all staging directives...
    staging_directives = list()

    for entity in reversed(task_details):
        
        if not isinstance(entity, dict):
            if continue_before_non_dict:
                break
            else:
                continue

        staging_type = entity['_cls']

        if staging_type in ['Move', 'Copy', 'Link']:
            
            # Get source files
            src_location, is_traj = get_file_location(entity['_dict']['source'], db, shared_path, project)
            if is_traj: # is a trajectory, we need to do something extra
                hex_id_input = hex_to_id(hex_uuid=task_desc['_dict']['generator']['_hex_uuid'])
                traj_files = db.get_source_files(hex_id_input)
                traj_files.append('restart.npz') # hard-code that we also need restart.npz
            
            # Get output/target files
            output_loc, _ = get_file_location(entity['_dict']['target'], db, shared_path, project)

            # Build the directives (for traj files, we need multiple directives...)

            # get propert action type
            if staging_type == 'Move':
               rp_staging_type = rp.MOVE
            
            elif staging_type == 'Link':
                rp_staging_type = rp.LINK
            
            else:
                rp_staging_type = rp.COPY


            if is_traj:
                # For each source file, create a staging directive...
                for file in traj_files:
                    temp = {
                        'source': str(src_location + '/' + file),
                        'action': rp_staging_type,
                        'target': str(output_loc + '/' + file)
                    }
                    staging_directives.append(temp)
            else:
                temp = {
                        'source': str(src_location),
                        'action': rp_staging_type,
                        'target': str(output_loc)
                    }
                staging_directives.append(temp)

    return staging_directives


def get_file_location(file_entity, db, shared_path, project):

    output_loc = None
    trajectory = False

    # it is NOT an entity with '_cls' assume it is something we need to get
    # from the files
    if file_entity.get('_cls', None) is None:
        hex_id_output = hex_to_id(hex_uuid = file_entity['_hex_uuid'])
        output_loc = db.get_file_destination(hex_id_output)
        output_loc = resolve_pathholders(output_loc, shared_path, project)

    # it *is* an entity with "_cls", treat it as such
    elif file_entity.get('_cls') == 'File':
        output_loc = resolve_pathholders(file_entity['_dict']['location'], shared_path, project)
    elif file_entity.get('_cls') == 'Trajectory':
        output_loc = os.path.basename(os.path.abspath(file_entity['_dict']['location']))
        trajectory = True

    return output_loc, trajectory


def get_commands(task_steps_list):

    commands = []

    for step in task_steps_list:
        if isinstance(step, unicode) or isinstance(step, str):
            # Get the command, normalize the command, by removing the `worker://` reference
            commands.append(str(step).replace('worker://', ''))

    return commands


def get_executable_arguments(task_steps_list):

    raw_exec = None
    proc_exec = None

    raw_exec = get_commands(task_steps_list)

    proc_exec = raw_exec[0][107:]
    proc_exec = proc_exec[:-31]

    if ';' in raw_exec[0]:
        # for the regular trajectory tasks (TrajectoryGenerationTasks)
        proc_exec = raw_exec[0].split(';')[2].replace('then', '').replace(
            'worker://', '').replace('=', ' ').replace('"', '').strip()
    else:
        # for all other "standard" tasks
        # Standard == <executable> <args>
        proc_exec = raw_exec[0].strip()
    # print proc_exec

    exe = proc_exec.split(' ')[0]
    args = proc_exec.split(' ')[1:]

    # print exe, args

    return exe, args

def create_cud_from_task_def(task_descs, db, shared_path, project):

    try:

        cuds = list()

        for task_desc in task_descs:

            # TODO: the only difference between the two is the input.json
            #       if we learn how to pull/push it then we can handle it
            #       using the staging directives, which mean we don't need to
            #       differentiate between tasks...

            if task_desc['_cls'] == 'PythonTask':
                cud = generate_pythontask_cud(task_desc, db, shared_path, project)
                cuds.append(cud)

            elif task_desc['_cls'] == 'TrajectoryGenerationTask':
                cud = generate_trajectorygenerationtask_cud(task_desc, db, shared_path, project)
                cuds.append(cud)
            else:
                continue

            db.update_task_description_status(task_desc['_id'], 'running')

        return cuds

    except Exception as ex:

        print traceback.format_exc()
        raise Error(msg=ex)


def generate_pythontask_cud(task_desc, db, shared_path, project):
    # Compute Unit Description
    cud = rp.ComputeUnitDescription()
    cud.name = task_desc['_id']

    # Get each component of the task
    pre_task_details = task_desc['_dict'].get('pre', list())
    main_task_details = task_desc['_dict']['_main']
    post_task_details = task_desc['_dict'].get('post', list())
    resource_requirements = task_desc['_dict']['resource_requirements']

    
    # First, extract environment variables
    cud.environment = get_environment_from_task(task_desc)

    
    # Next, extract things we need to add to the PATH
    # TODO: finish adding path directive
    paths = get_paths_from_task(task_desc)

    
    # Next, get input staging
    # We get "ALL" COPY/LINK/MOVE directives from the pre_exec
    staging_directives = get_input_staging(pre_task_details, db, shared_path, project, break_after_non_dict=False)
    # We get "ALL" COPY/LINK/MOVE directives from the main *before* the first non-dictionary entry
    staging_directives.extend(get_input_staging(main_task_details, db, shared_path, project))
    cud.input_staging = staging_directives


    # Next, get pre execution steps
    d = generate_pythontask_input(db, shared_path, task_desc, project)
    pre_exec = list()
    pre_exec = [
    'mkdir -p traj',
    'echo \'{}\' > \'{}\''.format(json.dumps(d['contents']), d['target']) # stage input.json
    ]
    pre_exec.extend(get_commands(pre_task_details))
    cud.pre_exec = pre_exec


    # Now, do main executable
    exe, args = get_executable_arguments(main_task_details)
    cud.executable = str(exe)
    cud.arguments = args


    # Now, get output staging steps
    # We get "ALL" COPY/LINK directives from the post_exec
    staging_directives = get_output_staging(task_desc, post_task_details, db, shared_path, project, continue_before_non_dict=False)
    # We get "ALL" COPY/LINK directives from the main *after* the first non-dictionary entry
    staging_directives.extend(get_output_staging(task_desc, main_task_details, db, shared_path, project))
    cud.output_staging = staging_directives

    # Get all post-execution steps
    post_exec = list()
    post_exec.extend(get_commands(post_task_details))
    cud.post_exec = post_exec
    
    # Get core count, support MPI
    if is_mpi(task_desc):
        cud.mpi = True
        cud.cores = resource_requirements.get('mpi_rank', 1) * resource_requirements.get('cpu_threads', 1)
    else :
        cud.mpi = False
        cud.cores = resource_requirements.get('cpu_threads', 1)

    # TODO: cud.gpus...

    return cud

def generate_trajectorygenerationtask_cud(task_desc, db, shared_path, project):
    # Compute Unit Description
    cud = rp.ComputeUnitDescription()
    cud.name = task_desc['_id']

    # Get each component of the task
    pre_task_details = task_desc['_dict'].get('pre', list())
    main_task_details = task_desc['_dict']['_main']
    post_task_details = task_desc['_dict'].get('post', list())
    resource_requirements = task_desc['_dict']['resource_requirements']

    
    # First, extract environment variables
    cud.environment = get_environment_from_task(task_desc)

    
    # Next, extract things we need to add to the PATH
    # TODO: finish adding path directive
    paths = get_paths_from_task(task_desc)

    
    # Next, get input staging
    # We get "ALL" COPY/LINK directives from the pre_exec
    staging_directives = get_input_staging(pre_task_details, db, shared_path, project, break_after_non_dict=False)
    # We get "ALL" COPY/LINK directives from the main *before* the first non-dictionary entry
    staging_directives.extend(get_input_staging(main_task_details, db, shared_path, project))
    cud.input_staging = staging_directives


    # Next, get pre execution steps
    pre_exec = list()
    pre_exec = ['mkdir -p traj']
    pre_exec.extend(get_commands(pre_task_details))
    cud.pre_exec = pre_exec


    # Now, do main executable
    exe, args = get_executable_arguments(main_task_details)
    cud.executable = str(exe)
    cud.arguments = args


    # Now, get output staging steps
    # We get "ALL" COPY/LINK directives from the post_exec
    staging_directives = get_output_staging(task_desc, post_task_details, db, shared_path, project, continue_before_non_dict=False)
    # We get "ALL" COPY/LINK directives from the main *after* the first non-dictionary entry
    staging_directives.extend(get_output_staging(task_desc, main_task_details, db, shared_path, project))
    cud.output_staging = staging_directives

    # Get all post-execution steps
    post_exec = list()
    post_exec.extend(get_commands(post_task_details))
    cud.post_exec = post_exec
    

    # Get core count, support MPI
    if is_mpi(task_desc):
        cud.mpi = True
        cud.cores = resource_requirements.get('mpi_rank', 1) * resource_requirements.get('cpu_threads', 1)
    else :
        cud.mpi = False
        cud.cores = resource_requirements.get('cpu_threads', 1)

    # TODO: cud.gpus...

    return cud


def process_resource_requirements(raw_res_descs):

    resources = list()
    for res_desc in raw_res_descs:

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

        if not conf['_dict']['queues']:

            temp_desc = dict()
            temp_desc['resource'] = conf['_dict']['resource_name']
            temp_desc['project'] = conf['_dict']['allocation']
            temp_desc['shared_path'] = conf['_dict']['shared_path']
            temp_desc['queue'] = ''

            configurations.append(temp_desc)

        else:

            for queue in conf['_dict']['queues']:

                temp_desc = dict()
                temp_desc['resource'] = conf['_dict']['resource_name']
                temp_desc['project'] = conf['_dict']['allocation']
                temp_desc['shared_path'] = conf['_dict']['shared_path']
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

    if not value:
        return the_list

    matching = list()
    if the_list:
        for item in the_list:
            matching_value = item[key]
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
        key='resource',
        value=resource_name
    )


def hex_to_id(hex_uuid=None):
    """Convert a hexadecimal string to an ID
    :Parameters:
    - `hex_uuid`: hex_uuid value as string
    """
    the_id = None
    if hex_uuid:
        if hex_uuid.endswith('L'):
            hex_uuid = hex_uuid[:-1]
        temp = uuid.UUID(int=int(hex_uuid, 16))
        the_id = str(temp)
    return the_id


def get_environment_from_task(task):
    environment = dict()
    task_environment = task['_dict'].get('_environment', dict())
    for key in task_environment:
        environment[str(key)] = str(task_environment[key])
    return environment


def get_paths_from_task(task):
    paths = list()
    for path in task['_dict'].get('_add_paths', list()):
        paths.append(str(path))
    return paths

def is_mpi(task):
    task_dict = task.get('_dict', dict())
    task_reqs = task_dict.get('resource_requirements', dict())
    mpi_rank = task_reqs.get('mpi_rank', 0)
    return (mpi_rank > 0)



def generate_pythontask_input(db, shared_path, task, project):
    """Parse a 'PythonTask' task object and generate the
    contents of its input file

    :Parameters:
    - `db`: database instance to poll file locations
    - `shared_path`: shared_path string to flatten file
    - `task`: task object to parse
    """
    input_file = None
    temp_file_contents = None
    temp_src = None
    temp_target = None
    if (task is not None) and (task['_cls'] == 'PythonTask'):
        # Source & Target
        for cmd in task['_dict']['pre']:
            if not isinstance(cmd, dict):
                continue
            if cmd['_cls'] == 'Transfer':
                location = db.get_file_destination(
                    id=hex_to_id(cmd['_dict']['source']['_hex_uuid']))
                if location:
                    temp_src = resolve_pathholders(location, shared_path, project)
                temp_target = cmd['_dict']['target']['_dict']['location']

        # File Contents
        temp = dict()
        # {'import': None, 'function': None, 'kwargs': None}
        temp['import'] = task['_dict']['_python_import']
        temp['function'] = task['_dict']['_python_function_name']
        for key, val in task['_dict']['_python_kwargs'].iteritems():
            if key == 'topfile':
                temp.setdefault('kwargs', dict())[
                    key] = val['_dict']['location']
            elif key == 'trajectories':
                for traj in val:
                    location = db.get_file_destination(
                        id=hex_to_id(traj['_hex_uuid']))
                    if location:
                        temp.setdefault(
                            'kwargs', dict()).setdefault(
                            key, list()).append(resolve_pathholders(
                                location, shared_path, project))
            else:
                temp.setdefault('kwargs', dict())[key] = val
        temp_file_contents = temp

        if temp_file_contents and temp_src and temp_target:
            input_file = {
                'source': temp_src,
                'target': temp_target,
                'contents': temp_file_contents
            }

    return input_file
