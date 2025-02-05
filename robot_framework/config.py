"""This module contains configuration constants used across the framework"""

from itk_dev_shared_components.kmd_nova.nova_objects import Caseworker, Department

# The number of times the robot retries on an error before terminating.
MAX_RETRY_COUNT = 3

# Whether the robot should be marked as failed if MAX_RETRY_COUNT is reached.
FAIL_ROBOT_ON_TOO_MANY_ERRORS = True

# Error screenshot config
SMTP_SERVER = "smtp.aarhuskommune.local"
SMTP_PORT = 25
SCREENSHOT_SENDER = "robot@friend.dk"

# Constant/Credential names
ERROR_EMAIL = "Error Email"
GRAPH_API = "Graph API"
NOVA_API = "Nova API"

QUEUE_NAME = "Journalisering af indkomne anmodninger om refusion gruppe 2"

# Other
MAIL_SOURCE_FOLDER = "Refusioner"
MAIL_DESTINATION_FOLDER = "Refusioner/Journaliserede ansøgninger"
STATUS_SENDER = "itk-rpa@mkb.aarhus.dk"


# Nova constants
CASEWORKER = Caseworker(
    uuid="144d7ab7-302f-4c62-83d2-dcdefcd92dea",
    ident="819697",
    name="ÅÅÅ_Frontoffice",
    type='group'
)

DEPARTMENT = Department(
    id=70403,
    name="Folkeregister og Sygesikring",
    user_key="4BFOLKEREG"
)

SECURITY_UNIT = Department(
    id=818485,
    name="Borgerservice",
    user_key="4BBORGER"
)