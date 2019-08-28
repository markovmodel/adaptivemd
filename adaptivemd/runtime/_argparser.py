#!/usr/bin/env/ python



from argparse import ArgumentParser


__all__ = ["get_argparser"]


#sleeptime = lambda arg: arg if arg == 'wait' else int(arg)
# TODO Aren't args always stripped?
stripped  = lambda arg: arg.strip() if arg else None
anyall    = lambda arg: arg if arg in {'any','all'} else 'any'
digit     = lambda arg: int(arg) if arg.isdigit() else ValueError
pos_int   = lambda arg: int(arg) if (int(arg) > 0 and arg.isdigit()) else ValueError


def get_argparser():

    parser = ArgumentParser(description="Create admd jobs")

    parser.add_argument("project_name",
        help="Name of project", type=stripped)

    parser.add_argument("system_name", nargs="?",
        help="Name of system", type=stripped)

    parser.add_argument("--init_only",
        help="Only initialize project",
        action="store_true")

    parser.add_argument("-N","--n_traj", dest="n_traj",
        help="Number of trajectories to create",
        type=int, default=16)

    parser.add_argument("-M","--modeller",
        help="Create a model on each round", type=stripped)

    parser.add_argument("--rp", action="store_true",
        help="Use RP" )

    parser.add_argument("-C","--config",
        help="Path to config file",
        default="admd.yaml")
        # TODO FIXME none and path from above
        #default=None)

    parser.add_argument("-l","--length",
        help="Length of trajectory segments in frames",
        type=int, default=100)

    parser.add_argument("-b","--n_rounds",
        help="Number of workloads inside a single PBS job",
        type=int, default=1)

    parser.add_argument("-c","--batchsize",
        help="Number of tasks to queue simultaneously",
        type=int, default=999999)

    parser.add_argument("-u","--batchwait",
        help="How to wait on queued task batches of inside workload, \"any\" or \"all\" if given",
        default=False, type=anyall)

    parser.add_argument("--progression",
        help="Workflow task-completion progression criteria",
        default="any", type=anyall)

    parser.add_argument("-s","--batchsleep",
        help="Time to sleep between task batches",
        type=int, default=5)

    parser.add_argument("-R","--round_n",
        help="Round number used to select analysis at runtime",
        type=int, default=1)

    # TODO activate command with full path to bins or shell source
    #      activate of rc file with full activate command
    parser.add_argument("-r","--rc",
        help="Location of AdaptiveMD profile, ie an rc file", type=stripped)

    # Default file lives in the runtime config folder
    parser.add_argument("-F","--features_cfg",
        help="Configuration file specifying features for analysis",
        default="cfg/features.yaml")

    # Default file lives in the runtime config folder
    parser.add_argument("-A","--analysis_cfg",
        help="Configuration file for PyEMMA analysis",
        default="cfg/analysis.yaml")

    parser.add_argument("-a","--after_n_trajs",
        help="Extension of trajs N onward", type=digit)

    parser.add_argument("-k","--minlength",
        help="Minimum trajectory total length in frames",
        type=int, default=100)

    # TODO the default behavior doesn't carry through, and should
    #      be set to fixed and changed to false. investigate this...
    parser.add_argument("-f","--fixedlength",
        help="Default randomizes traj length, flag to fix to n_steps",
        action='store_true')

    # TODO the actual client application should persist, not just the
    #      database. TODO requires further testing of runtime function
    parser.add_argument("--persist",
        help="Flag for adaptivemd client to persist (only persistent DB implemented for now)",
        action='store_true')

    parser.add_argument("-p","--protein-stride", dest="prot",
        help="Stride between saved protein structure frames",
        type=int, default=2)

    parser.add_argument("-m","--master-stride", dest="all",
        help="Stride between saved frames with all atoms",
        type=int, default=10)

    parser.add_argument("-P","--platform",
        help="Simulation Platform: Reference, CPU, CUDA, or OpenCL",
        default="CPU", type=stripped)

    # TODO priority of this vs environment ADMD_DBURL
    parser.add_argument("--dburl",
        help="Full URL of the MongoDB",
        default="mongodb://localhost:27017/", type=stripped)

    parser.add_argument("--threads",
        help="Number of threads for each task",
        default=1, type=int)

    parser.add_argument("-S","--sampling_method",
        help="Name of sampling function saved in sampling_functions.py",
        default="explore_macrostates", type=stripped)

    parser.add_argument("--min_model_trajlength",
        help="Minimum length for trajectories to analyze",
        default=0, type=digit)

    parser.add_argument("--minutes",
        help="Number of minutes to request for LRMS job",
        type=pos_int, default=0)

    parser.add_argument("--submit_only",
        help="Submit a workload and immediately quit AdaptiveMD Application",
        action="store_true")

    parser.add_argument("--rescue_tasks",
        help="Skip workload if failed or incomplete tasks detected",
        action="store_true",)

    # TODO is this needed?
    parser.add_argument("--rescue_only",
        help="Quit runtime after rescue check",
        action="store_true")

    return parser
