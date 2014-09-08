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
            exit_codes.append(self._exit_state(process['statename'],options.warn, options.crit))
            statuses.append("%s; pid=%i, status=%s" % (process['name'], process['pid'], process['statename']))

        return [max(exit_codes)], statuses

    def help_nagios_status(self):
        self._help(self._get_nagios_checkprocess_parser(self))

    # nagios_checkprocess end

    # nagios_checkgroup start
    def do_nagios_checkgroup(self, arg):
        self._eit_wrapper(self._do_nagios_checkgroup, arg)

    def _get_nagios_checkgroup_parser(self):
        parser = argparse.ArgumentParser('supervisorctl nagios_checkgroup', description = 'check the status of supervised processes in a group in a nagios-like fashion', add_help=False)
        parser.add_argument('-w', '--warn', nargs=1, action='append')
        parser.add_argument('-c', '--crit', nargs=1, action='append')

        parser.add_argument('group', nargs=argparse.REMAINDER)
        return parser

    def _do_nagios_checkgroup(self, arg):
        options = self._get_nagios_checkgroup_parser().parse_args(arg.split())
        options.warn = self._flatten_comma_separated(options.warn)
        options.crit = self._flatten_comma_separated(options.crit)



    # nagios_checkgroup end

def make_nagios_plugin(controller, **config):
    return NagiosControllerPlugin(controller)

