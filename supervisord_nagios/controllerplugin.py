from supervisor.options import split_namespec
from supervisor.supervisorctl import ControllerPluginBase
from supervisor import xmlrpc
import xmlrpclib
import sys
import argparse
import traceback

class NagiosControllerPlugin(ControllerPluginBase):
    OK = 0
    WARNING = 1
    CRITICAL = 2
    UNKNOWN = 3
    TEXTS = ['OK','WARNING','CRITICAL','UNKNOWN']

    def __init__(self, controller):
        self.ctl = controller
        self.supervisor = controller.get_server_proxy('supervisor')

    def _exit_wrapper(self, method, arg):
        #try:
        exit_codes, output = method(arg)
        #except Exception, e:
            #self._exit(self.UNKNOWN, ["uncaught exception in check function: %s" % e])

        self._exit(max(exit_codes), output)

    def _exit(self, status, text):
        self.ctl.output("%s: %s" % (self.TEXTS[status], ", ".join(text)))
        sys.exit(status)

    def _help(self, get_parser):
        self.ctl.output(get_parser().format_help())
        sys.exit(self.UNKNOWN)

    def _exit_state(self, state, warn, crit):
        # RUNNING is *always* ok
        if state == 'RUNNING':
            return self.OK

        if warn or crit:
            if warn and state in warn:
                return self.WARNING
            elif not crit or (crit and state in crit):
                return self.CRITICAL
            else:
                return self.UNKNOWN
        else:
            return self.CRITICAL

    # because --warn FOO,BAR --warn BAZ,BAT comes back to us as [['FOO,BAR'],['BAZ,BAT'], and I want it as ['FOO','BAR','BAZ','BAT']
    # I would love a better way to do this
    def _flatten_comma_separated(self, values):
        if not values:
            return None

        final = []
        for x in values:
            for y in x:
                for value in y.split(','):
                    final.append(value)

        return final

    def _check_process(self, process, warn, crit):
        procname = "%s:%s" % (process['group'], process['name']) if process['group'] and process['group'] != '' else process['name']
        return self._exit_state(process['statename'], warn, crit), "%s pid=%i state=%s" % ( procname, process['pid'], process['statename'] )

    # nagios_status start
    def do_nagios_status(self, arg):
        self._exit_wrapper(self._do_nagios_status, arg)

    def _get_nagios_status_parser(self):
        parser = argparse.ArgumentParser('supervisorctl nagios_status', description = 'check supervisord status in a nagios-like fashion', add_help=False)
        parser.add_argument('-w', '--warn', nargs=1, action='append')
        parser.add_argument('-c', '--crit', nargs=1, action='append')

        return parser

    # this would appear to need some more work, as things get really weird when state != 'RUNNING'
    def _do_nagios_status(self, arg):
        options = self._get_nagios_status_parser().parse_args(arg.split())
        options.warn = self._flatten_comma_separated(options.warn)
        options.crit = self._flatten_comma_separated(options.crit)

        state = self.supervisor.getState()['statename']
        pid = self.supervisor.getPID()

        return [self._exit_state(state, options.warn, options.crit)], ["supevisord (pid: %i) state: %s" % (pid, state)]

    def help_nagios_status(self):
        self._help(self._get_nagios_status_parser)

    # nagios_status end

    # nagios_checkprocess start
    def do_nagios_checkprocess(self, arg):
        self._exit_wrapper(self._do_nagios_checkprocess, arg)

    def _get_nagios_checkprocess_parser(self):
        parser = argparse.ArgumentParser('supervisorctl nagios_checkprocess', description = 'check the status of supervised process in a nagios-like fashion', add_help=False)
        parser.add_argument('-w', '--warn', nargs=1, action='append')
        parser.add_argument('-c', '--crit', nargs=1, action='append')
        parser.add_argument('process', nargs=argparse.REMAINDER)
        return parser

    def _do_nagios_checkprocess(self, arg):
        options = self._get_nagios_checkprocess_parser().parse_args(arg.split())
        options.warn = self._flatten_comma_separated(options.warn)
        options.crit = self._flatten_comma_separated(options.crit)

        if len(options.process) == 0:
            return [self.UNKNOWN], ['must pass process name(s) to script']

        exit_codes = []
        statuses = []
        for process in [self.supervisor.getProcessInfo(process) for process in options.process]:
            exit_code, status = self._check_process(process, options.warn, options.crit)
            exit_codes.append(exit_code)
            statuses.append(status)

        return [max(exit_codes)], statuses

    def help_nagios_checkprocess(self):
        self._help(self._get_nagios_checkprocess_parser)

    # nagios_checkprocess end

    # nagios_checkgroup start
    def do_nagios_checkgroup(self, arg):
        self._exit_wrapper(self._do_nagios_checkgroup, arg)

    def _get_nagios_checkgroup_parser(self):
        parser = argparse.ArgumentParser('supervisorctl nagios_checkgroup', description = 'check the status of supervised processes in a group in a nagios-like fashion', add_help=False)
        parser.add_argument('-w', '--warn', nargs=1, action='append')
        parser.add_argument('-c', '--crit', nargs=1, action='append')
        parser.add_argument('-W', '--warncritcount', type=int, default=0)
        parser.add_argument('-C', '--critcritcount', type=int, default=0)
        parser.add_argument('-V', '--warnwarncount', type=int, default=0)
        parser.add_argument('-B', '--critwarncount', type=int, default=0)
        parser.add_argument('-X', '--warnbadcount', type=int, default=0)
        parser.add_argument('-D', '--critbadcount', type=int, default=1)
        parser.add_argument('-n', '--warnprocs', type=int, default=0)
        parser.add_argument('-N', '--critprocs', type=int, default=1)
        parser.add_argument('group', nargs=argparse.REMAINDER)
        return parser

    def _do_nagios_checkgroup(self, arg):
        options = self._get_nagios_checkgroup_parser().parse_args(arg.split())
        options.warn = self._flatten_comma_separated(options.warn)
        options.crit = self._flatten_comma_separated(options.crit)

        if len(options.group) == 0:
            return [self.UNKNOWN],['must pass group name(s) to script']

        all_processes = self.supervisor.getAllProcessInfo()

        exit_codes = []
        statuses = []
        for group in options.group:
            exit_code, text = self._check_group(group, options, all_processes)
            exit_codes.append(exit_code)
            statuses.append(text)

        return [max(exit_codes)], statuses

    # this implements all of the crazy counting and such, it's probably totally wrong, and definitely ugly
    def _check_group(self, group, options, all_processes):
        process_codes = []
        statuses = []
        exit_codes = [self.OK]

        group_processes = [process for process in all_processes if process['group'] == group]

        totalcount = len(group_processes)
        if options.warnprocs or options.critprocs:
            statuses.append("group %s numprocs: %i" % (group, totalcount))
            if options.critprocs and totalcount < options.critprocs:
                exit_codes.append(self.CRITICAL)
            elif options.warnprocs and totalcount < options.warnprocs:
                exit_codes.append(self.WARNING)


        for process in group_processes:
            process_code, status= self._check_process(process, options.warn, options.crit)
            process_codes.append(process_code)
            statuses.append(status)

        warncount = len([process_code for process_code in process_codes if process_code == self.WARNING])
        critcount = len([process_code for process_code in process_codes if process_code == self.CRITICAL])
        unknowncount = len([process_code for process_code in process_codes if process_code == self.UNKNOWN])


        if options.warncritcount or options.critcritcount:
            if options.critcritcount and critcount >= options.critcritcount:
                exit_codes.append(self.CRITICAL)
            elif options.warncritcount and critcount >= options.warncritcount:
                exit_codes.append(self.WARNING)

        if options.warnwarncount or options.critwarncount:
            if options.critwarncount and warncount >= options.critwarncount:
                exit_codes.append(self.CRITICAL)
            elif options.warnwarncount and worncount >= options.warnwarncount:
                exit_codes.append(self.WARNING)

        if options.warnbadcount or options.critbadcount:
            badcount = warncount + critcount + unknowncount
            if options.critbadcount and badcount >= options.critbadcount:
                exit_codes.append(self.CRITICAL)
            elif options.warnbadcount and badcount >= options.warnbadcount:
                exit_codes.append(self.WARNING)


        if unknowncount:
            exit_codes.append(self.UNKNOWN)

        return max(exit_codes), ",".join(statuses)

    def help_nagios_checkgroup(self):
        self._help(self._get_nagios_checkgroup_parser)

    # nagios_checkgroup end

def make_nagios_plugin(controller, **config):
    return NagiosControllerPlugin(controller)

