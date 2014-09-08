from supervisor.options import split_namespec
from supervisor.supervisorctl import ControllerPluginBase
from supervisor import xmlrpc
import xmlrpclib
import sys
import argparse

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
        try:
            exit_codes, output = method(arg)
        except Exception, e:
            self._exit(self.UNKNOWN, ["uncaught exception in check function: %s" % e])

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
        parser.add_argument('-w', '--warn', nargs='+', action='append')

        return parser

    # this would appear to need some more work, as things get really weird when state != 'RUNNING'
    def _do_nagios_status(self, arg):
        options = self._get_nagios_status_parser().parse_args(arg.split())

        state = self.supervisor.getState()['statename']
        pid = self.supervisor.getPID()

        if state == 'RUNNING':
            return [self.OK], ['supervisord (pid: %i) is up and running' % pid]

        if options.warn or options.crit:
            if state in options.crit:
                return [self.CRITICAL],['supervisord (pid: %i) is in a critical state: %s' % ( pid, state )]
            elif state in options.warn:
                return [self.WARNING],['supervisord (pid: %i) is in a warning state: %s' % ( pid, state )]
            else:
                return [self.UNKNOWN],['supervisord (pid: %i) is in an unknown state: %s' % ( pid, state )]

    def help_nagios_status(self):
        self._help(self._get_nagios_status_parser)

    # nagios_status end

def make_nagios_plugin(controller, **config):
    return NagiosControllerPlugin(controller)

