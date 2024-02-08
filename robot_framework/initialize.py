"""This module defines any initial processes to run when the robot starts."""

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection


def initialize(orchestrator_connection: OrchestratorConnection) -> list:
    """Do all custom startup initializations of the robot."""
    orchestrator_connection.log_trace("Initializing.")
    email_list = []
    return email_list
