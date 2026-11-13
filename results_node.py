import udi_interface


class ResultsNode(udi_interface.Node):
    """Read-only child node showing the outcome of the last profile size test."""
    id = 'results'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25, 'name': 'Result'},
        {'driver': 'MIN_FAIL_KB', 'value': 0, 'uom': 56, 'name': 'Smallest Failure (KB)'},
        {'driver': 'MAX_PASS_KB', 'value': 0, 'uom': 56, 'name': 'Largest Pass (KB)'},
        {'driver': 'TIME', 'value': 0, 'uom': 151, 'name': 'Last Run'},
    ]
    commands = {}

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
