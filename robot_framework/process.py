"""This module contains the main process of the robot."""

import os
import json
import re
import uuid
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage

from OpenOrchestrator.orchestrator_connection.connection import OrchestratorConnection
from OpenOrchestrator.database.queues import QueueStatus
from itk_dev_shared_components.graph import authentication as graph_authentication
from itk_dev_shared_components.graph.authentication import GraphAccess
from itk_dev_shared_components.graph import mail as graph_mail
from itk_dev_shared_components.graph.mail import Email
from itk_dev_shared_components.kmd_nova.authentication import NovaAccess
from itk_dev_shared_components.kmd_nova.nova_objects import NovaCase, Document, CaseParty, Task, Caseworker, Department
from itk_dev_shared_components.kmd_nova import nova_cases, nova_documents, nova_tasks
from itk_dev_shared_components.kmd_nova import cpr as nova_cpr

from robot_framework import config


def process(journalized_emails: list[Email], orchestrator_connection: OrchestratorConnection) -> None:
    """Do the primary process of the robot.

    Args:
        journalized_emails: The list of emails that has been journalized so far.
    """
    orchestrator_connection.log_trace("Running process.")

    caseworker, department, receivers = unpack_arguments(orchestrator_connection)

    graph_creds = orchestrator_connection.get_credential(config.GRAPH_API)
    graph_access = graph_authentication.authorize_by_username_password(graph_creds.username, **json.loads(graph_creds.password))

    nova_creds = orchestrator_connection.get_credential(config.NOVA_API)
    nova_access = NovaAccess(nova_creds.username, nova_creds.password)

    email_list = get_emails(graph_access)

    for email in email_list:
        cpr, faktura_numbers = get_info_from_email(email)

        queue_element = orchestrator_connection.create_queue_element(config.QUEUE_NAME, reference=f"{cpr}", data=f"{faktura_numbers}", created_by="Robot")

        case = find_or_create_case(cpr, nova_access, caseworker, department)

        document_name = f"Ansøgning om refusion [{', '.join(faktura_numbers)}]"

        attach_email_to_case(document_name, email, case, caseworker, graph_access, nova_access)

        update_or_create_task(case, nova_access)

        graph_mail.move_email(email, config.MAIL_DESTINATION_FOLDER, graph_access)

        journalized_emails.append(email)

        orchestrator_connection.set_queue_element_status(queue_element.id, QueueStatus.DONE)

    send_status_mail(len(journalized_emails), receivers, orchestrator_connection)


def unpack_arguments(orchestrator_connection: OrchestratorConnection) -> tuple[Caseworker, Department, list[str]]:
    """Unpack the caseworker, department and email receivers given in the OpenOrchestrator arguments.

    Args:
        orchestrator_connection: The connection to OpenOrchestrator.

    Returns:
        A caseworker and department objects and a list of email receivers to be used in the process.
    """
    obj = json.loads(orchestrator_connection.process_arguments)
    caseworker = Caseworker(**obj["caseworker"])
    department = Department(**obj["department"])
    receivers = obj["receivers"]

    return caseworker, department, receivers


def get_emails(graph_access: GraphAccess) -> list[Email]:
    """Get all emails to be handled by the robot.

    Args:
        graph_access: The GraphAccess object used to authenticate against Graph.

    Returns:
        A filtered list of email objects to be handled.
    """
    # Get all emails from the 'Refusioner' folder.
    mails = graph_mail.get_emails_from_folder("folkeregister@aarhus.dk", config.MAIL_SOURCE_FOLDER, graph_access)

    # Filter the emails on sender and subject
    mails = [mail for mail in mails if mail.sender == "noreply@aarhus.dk" and mail.subject == 'Refusion sikringsgruppe 2 (fra Selvbetjening.aarhuskommune.dk)']

    return mails


def get_info_from_email(email: Email) -> tuple[str, list[str]]:
    """Get the relevant cpr number and faktura numbers from the email body.

    Args:
        email: The email object.

    Returns:
        The cpr and a list of faktura numbers.
    """
    text = email.get_text()

    # Determine whether to use the applicant's or their child's cpr.
    is_child = "Omhandler ansøgningen dit barn?Ja" in text

    if is_child:
        cpr_index = text.find("Vælg barn") + 9
    else:
        cpr_index = text.find("CPR-nummer") + 10

    cpr = text[cpr_index:cpr_index+10]

    # Get all faktura numbers
    faktura_numbers = re.findall(r"Fakturanummer: (.+?)Dato for behandling", text)

    return cpr, faktura_numbers


def find_or_create_case(cpr: str, nova_access: NovaAccess, caseworker: Caseworker, department: Department) -> NovaCase:
    """Find a case with the correct title and kle number on the given cpr.
    If no case exists a new one is created instead.

    Args:
        cpr: The cpr of the person to get the case from.
        nova_access: The nova access object used to authenticate.

    Returns:
        The relevant nova case.
    """
    cases = nova_cases.get_cases(nova_access, cpr=cpr)

    # If a case already exists reuse it
    for case in cases:
        if case.title == "Sygesikring i almindelighed" and case.active_code == 'Active' and case.kle_number == '29.03.00':
            return case

    # Find the name of the person in one of the cases
    name = None
    for case in cases:
        for case_party in case.case_parties:
            if case_party.identification == cpr and case_party.name:
                name = case_party.name
                break
        if name:
            break

    # If the name wasn't found in a case look it up in cpr
    if not name:
        name = nova_cpr.get_address_by_cpr(cpr, nova_access)['name']

    case_party = CaseParty(
        role="Primær",
        identification_type="CprNummer",
        identification=cpr,
        name=name,
        uuid=None
    )

    # Create a new case
    case = NovaCase(
        uuid=str(uuid.uuid4()),
        title="Sygesikring i almindelighed",
        case_date=datetime.now(),
        progress_state='Opstaaet',
        case_parties=[case_party],
        kle_number="29.03.00",
        proceeding_facet="G01",
        sensitivity="Følsomme",
        caseworker=caseworker,
        responsible_department=department,
        security_unit=department
    )
    nova_cases.add_case(case, nova_access)
    return case


def attach_email_to_case(document_name: str, email: Email, case: NovaCase, caseworker: Caseworker, graph_access: GraphAccess, nova_access: NovaAccess):
    """Upload the email file to Nova as a document.

    Args:
        document_name: The name of the new document.
        email: The email object to upload.
        case: The nova case to attach to.
        graph_access: The graph access object used to authenticate against Graph.
        nova_access: The nova access object used to authenticate against Nova.
    """
    mime = graph_mail.get_email_as_mime(email, graph_access)
    doc_uuid = nova_documents.upload_document(mime, f"{document_name}.eml", nova_access)

    doc = Document(
        uuid=doc_uuid,
        title=document_name,
        sensitivity="Følsomme",
        document_type="Indgående",
        document_date=email.received_time,
        approved=True,
        description="Automatisk journaliseret af robot.",
        caseworker=caseworker
    )

    nova_documents.attach_document_to_case(case.uuid, doc, nova_access)


def update_or_create_task(case: NovaCase, nova_access: NovaAccess):
    """If a task on the case already exists the deadline is moved if necessary.
    If no task exists a new one is created.

    Args:
        case: The case to update the task on.
        nova_access: The nova access object used to authenticate.
    """
    deadline = datetime.now() + timedelta(days=7)

    # Check if any tasks already exists on the case
    tasks = nova_tasks.get_tasks(case.uuid, nova_access)

    # Find a non-finished task
    task = None
    for t in tasks:
        if t.status_code != 'F':
            task = t
            break

    if task:
        # If a task already exists and its deadline is later than
        # the new deadline, update it
        if task.deadline.date() > deadline.date():
            task.deadline = deadline
            nova_tasks.update_task(task, case.uuid, nova_access)
    else:
        # If no task is found create a new one.
        # When creating tasks we don't need to provide the name and ident.
        caseworker = Caseworker(uuid=config.CASE_WORKER_UUID, name=None, ident=None)

        task = Task(
            uuid=str(uuid.uuid4()),
            title="Ny ansøgning",
            caseworker=caseworker,
            status_code='N',
            deadline=deadline
        )
        nova_tasks.attach_task_to_case(case.uuid, task, nova_access)


def send_status_mail(journal_count: int, receivers: list[str], orchestrator_connection: OrchestratorConnection) -> None:
    """Send an email to the case workers with the total number of emails journalized performed.
    The receivers is defined as a json list in the robot arguments.

    Args:
        journal_count: The number of emails journalized.
        orchestrator_connection: The connection to OpenOrchestrator.
    """
    orchestrator_connection.log_info(f"Sending status to: {receivers}")

    # Create message
    msg = EmailMessage()
    msg['to'] = receivers
    msg['from'] = config.STATUS_SENDER
    msg['subject'] = f"Status på Journalisering af refusionsanmodninger {datetime.now().date()}"

    msg.set_content(f"Antal anmodninger journaliseret i dagens kørsel: {journal_count}\n\nVenlig hilsen\nRobotten")

    # Send message
    with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.send_message(msg)


if __name__ == '__main__':
    conn_string = os.getenv("OpenOrchestratorConnString")
    crypto_key = os.getenv("OpenOrchestratorKey")
    oc = OrchestratorConnection("Journalisering test", conn_string, crypto_key, '')
    process([], oc)
