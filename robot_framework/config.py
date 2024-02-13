"""This module contains configuration constants used across the framework"""

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
CASE_WORKER_UUID = 'c38ccf61-c879-46e5-92c6-c0abf737d076'
MAIL_SOURCE_FOLDER = "Refusioner"
MAIL_DESTINATION_FOLDER = "Refusioner/Journaliserede ansøgninger"
STATUS_SENDER = "itk-rpa@mkb.aarhus.dk"
