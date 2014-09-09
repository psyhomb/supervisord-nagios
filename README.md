# Introduction

`supervisord-nagios` is a plugin for supervisorctl to allow one to perform nagios-style checks against supervisord-managed services.

It responds with nagios-style exit codes and allows you to specify rules regarding what states are acceptable, unacceptable, etc.
All without having to parse command line output (which is super fragile, of course)

# Installation

Using pip:

    pip install supervisord-nagios

Then, in your main `supervisord.conf` file, put the following:

    [ctlplugin:nagios]
    supervisor.ctl_factory = supervisord_nagios.controllerplugin:make_nagios_plugin

This needs to be in the *main* `supervisord.conf` file, sadly, and not brought in using `[include]` or something (limitation in supervisord, as of this writing).

# Usage

## supervisorctl nagios\_status

This simply checks `supervisor.getState()` and returns success if the server is in state 'RUNNING'.

* `-w, --warn STATE1[,STATE2[...]]`
* `-c, --crit STATE1[,STATE2[...]]`

By default, any status not 'RUNNING' will result in a critical state. You can specify otherwise here.
If you specify only warnstates, then any state not RUNNING or $WARN will result in a critical.
If you specify both warnstates and critstates, then any state not RUNNING, $WARN, or $CRIT will return UNKNOWN.

If the server can't be contacted, it will return a CRITICAL state, always.

The list of states which can be returned by supervisord can be found [here](http://supervisord.org/api.html#supervisor.rpcinterface.SupervisorNamespaceRPCInterface.getState).
Note that the `statename` attribute is used, rather than the `statecode` attribute.

## process and group arguments

* `-w, --warn STATE1[,STATE2[...]]`
* `-c, --crit STATE1[,STATE2[...]]`

By default, any status not 'RUNNING' is considered a critical state. You can specify otherwise here.
If you specify only warnstates, then any state not RUNNING or $WARN will result in a critical.
If you specify both warnstates and critstates, then any state not RUNNING, $WARN, or $CRIT will return UNKNOWN.

The list of states which can be returned by supervisord can be found [here](http://supervisord.org/subprocess.html#process-states)
Note that the `statename` attribute is used, rather than the `state` attribute.

## supervisorctl nagios\_checkprocess

This checks processes running under supervisord.

* `PROC1 [PROC2 [...]]` -- the processes to check the statuses of.

This will always return the "worst" status code of the list of processes.

## supervisorctl nagios\_checkgroup

Reports on the number of processes in the specified group(s) in each state and can warn or critical based on information.

* `GROUP1 [GROUP2 [...]]` -- the group(s) to check the statuses of.

* `-W, --warncritcount INTEGER` -- the warning threshold for the number of processes in a warning state. Defaults to 0 (disabled).
* `-C, --critcritcount INTEGER` -- the critical threshold for the number of processes in a critical state. Defaults to 0 (disabled).

* `-V, --warnwarncount INTEGER` -- the warning threshold for the number of processes in a warning state. Defaults to 0 (disabled).
* `-B, --critwarncount INTEGER` -- the critical threshold for the number of processes in a warning state. Defaults to 0 (disabled).

* `-X, --warnbadcount INTEGER` -- the warning threshold for the number of processes in a not good state. Defaults to 0 (disabled).
* `-D, --critbadcount INTEGER` -- the critical threshold for the number of processes in a not good state. Defaults to 1.

* `-n, --warnprocs INTEGER` -- warning state if the number of total processes in this group drops below this value. Defaults to 0.
* `-N, --critprocs INTEGER` -- critical state if the number of total processes in this group drops below this value. Defaults to 1.

Any process resulting in an UNKNOWN state will result in an UNKNOWN state being reported back to nagios.

The counts are all per group. If you want different counts for different groups, use multiple checks.
