import os
import jinja2


class Mount(object):

    def __init__(self, name, internal, external, read_only='false'):
        self.name = name
        self.internal = internal
        self.external = external
        self.read_only = read_only


class HttpLivenessProbe(object):

    def __init__(self, path, delay, timeout, port=8000):
        self.path = path
        self.delay = delay
        self.timeout = timeout
        self.port = port


class DeploymentManager(object):

    deployments = list()

    def add_deployment(self, deployment):
        self.deployments.append(deployment)


class Deployment(object):

    def __init__(self, service_name, docker_image):
        # self.mounts = []
        self.service_name = service_name
        self.docker_image = docker_image

        # mutable variables
        self.environment = {}
        self.replicas = 1
        self.deployment_key = None
        self.mounts = []
        self.always_pull = False
        self.service_port = None
        self.cpu_limit = None
        self.memory_limit = None
        self.node_port = None
        self.command = None

    def add_mount(self, *args):
        self.mounts.append(Mount(*args))

    @staticmethod
    def render_raw(context, template):
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.dirname(__file__))
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template(template)
        return template.render(context=context)

    def render_service(self):
        return self.render_raw(context=self, template='service.template')

    def render_rc(self):
        return self.render_raw(context=self, template='rc.template')

    def write_yaml(self):
        with open(os.path.join('generated', "%s-rc.yaml" % self.service_name), "w") as text_file:
            text_file.write(self.render_rc())
        if self.service_port is not None:
            with open(os.path.join('generated', "%s-service.yaml" % self.service_name), "w") as text_file:
                text_file.write(self.render_service())


class WebApp(Deployment):

    def __init__(self, service_name, host_names, docker_image, service_port=8000, add_www=True, http_check=None):
        self.host_names = host_names
        self.service_port = service_port
        self.add_www = add_www
        self.http_check = http_check
        super(self.__class__, self).__init__(service_name, docker_image)

    @property
    def get_host_names(self):
        host_names = [x.strip() for x in self.host_names.split(' ')]
        if self.add_www:
            host_names += [('www.%s' % h) for h in host_names]
        return host_names

    def set_http_check(self, *args, **kwargs):
        self.http_check = HttpLivenessProbe(*args, **kwargs)

    def render_ingress(self):
        return self.render_raw(self, template='ingress.template')

    def write_yaml(self):
        super(self.__class__, self).write_yaml()
        with open(os.path.join('generated', "%s-ingress.yaml" % self.service_name), "w") as text_file:
            text_file.write(self.render_ingress())


class NetworkService(Deployment):

    def __init__(self, service_name, docker_image, service_port, external_port=None):
        self.service_port = service_port

        if external_port is not None:
            self.node_port = external_port

        super(self.__class__, self).__init__(service_name, docker_image)