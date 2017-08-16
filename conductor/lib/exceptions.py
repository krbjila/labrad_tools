class ParameterError(Exception):
    def __init__(self, device_name, parameter_name):
        self.device_name = device_name
        self.parameter_name = parameter_name


class ParameterAlreadyRegistered(ParameterError):
    def __str__(self):
        return "parameter ({} {}) is already registered".format(
                self.device_name, self.parameter_name)

class ParameterNotRegistered(ParameterError):
    def __str__(self):
        return "parameter ({} {}) is not registered".format(
                self.device_name, self.parameter_name)

class ParameterNotImported(ParameterError):
    def __str__(self):
        return "parameter ({} {}) import failed".format(
                self.device_name, self.parameter_name)
