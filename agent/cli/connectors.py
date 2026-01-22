"""
Connectors CLI commands for managing connector credentials.

Provides commands to:
- List connectors available for credential configuration
- Configure credentials for a connector
- Remove credentials for a connector

Issue #90 - Distributed Agent Architecture (Phase 8)
Tasks: T140, T141
"""

import click
import json
from typing import Optional

from src.api_client import AgentApiClient
from src.config import AgentConfig
from src.credential_store import CredentialStore


def _get_api_client() -> Optional[AgentApiClient]:
    """Get configured API client or None if not registered."""
    config = AgentConfig()
    if not config.api_key:
        return None
    return AgentApiClient(
        server_url=config.server_url,
        api_key=config.api_key,
    )


def _test_credentials(connector_type: str, credentials: dict) -> tuple[bool, str]:
    """
    Test credentials by attempting to connect.

    Args:
        connector_type: Connector type (s3, gcs, smb)
        credentials: Credentials dictionary

    Returns:
        Tuple of (success, message)
    """
    try:
        if connector_type == "s3":
            return _test_s3_credentials(credentials)
        elif connector_type == "gcs":
            return _test_gcs_credentials(credentials)
        elif connector_type == "smb":
            return _test_smb_credentials(credentials)
        else:
            return False, f"Unknown connector type: {connector_type}"
    except Exception as e:
        return False, f"Test failed: {str(e)}"


def _test_s3_credentials(credentials: dict) -> tuple[bool, str]:
    """Test S3 credentials."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        session = boto3.Session(
            aws_access_key_id=credentials.get("aws_access_key_id"),
            aws_secret_access_key=credentials.get("aws_secret_access_key"),
            region_name=credentials.get("region"),
        )
        s3 = session.client("s3")

        # Try to list buckets (minimal permission test)
        s3.list_buckets()
        return True, "Successfully connected to AWS S3"

    except NoCredentialsError:
        return False, "Invalid AWS credentials"
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "InvalidAccessKeyId":
            return False, "Invalid AWS Access Key ID"
        elif error_code == "SignatureDoesNotMatch":
            return False, "Invalid AWS Secret Access Key"
        else:
            return False, f"AWS error: {error_code}"
    except ImportError:
        return False, "boto3 library not installed"
    except Exception as e:
        return False, f"S3 test failed: {str(e)}"


def _test_gcs_credentials(credentials: dict) -> tuple[bool, str]:
    """Test GCS credentials."""
    try:
        from google.cloud import storage
        from google.oauth2 import service_account

        # Parse service account JSON
        service_account_info = json.loads(credentials.get("service_account_json", "{}"))
        creds = service_account.Credentials.from_service_account_info(service_account_info)

        # Create client and try to list buckets
        client = storage.Client(credentials=creds, project=service_account_info.get("project_id"))
        list(client.list_buckets(max_results=1))

        return True, "Successfully connected to Google Cloud Storage"

    except json.JSONDecodeError:
        return False, "Invalid service account JSON format"
    except ImportError:
        return False, "google-cloud-storage library not installed"
    except Exception as e:
        return False, f"GCS test failed: {str(e)}"


def _test_smb_credentials(credentials: dict) -> tuple[bool, str]:
    """Test SMB credentials."""
    try:
        import smbclient

        server = credentials.get("server")
        share = credentials.get("share")
        username = credentials.get("username")
        password = credentials.get("password")
        domain = credentials.get("domain", "")

        # Build SMB path
        smb_path = f"\\\\{server}\\{share}"

        # Register session and try to list directory
        smbclient.register_session(
            server,
            username=username,
            password=password,
            domain=domain if domain else None,
        )
        smbclient.listdir(smb_path)

        return True, f"Successfully connected to SMB share: {smb_path}"

    except ImportError:
        return False, "smbprotocol library not installed"
    except Exception as e:
        return False, f"SMB test failed: {str(e)}"


@click.group()
def connectors():
    """
    Manage connector credentials.

    Configure credentials for connectors that use agent-side credential storage.
    Credentials are encrypted and stored locally on this machine.

    Examples:
        # List connectors pending configuration
        shuttersense-agent connectors list --pending

        # Configure credentials for a connector
        shuttersense-agent connectors configure con_01abc123...

        # Test existing credentials and report to server
        shuttersense-agent connectors test con_01abc123...

        # Remove credentials
        shuttersense-agent connectors remove con_01abc123...
    """
    pass


@connectors.command("list")
@click.option(
    "--pending",
    is_flag=True,
    help="Only show connectors pending credential configuration",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON",
)
def list_connectors(pending: bool, as_json: bool):
    """
    List connectors available for credential configuration.

    Shows connectors with credential_location set to 'pending' or 'agent'.
    Use --pending to filter to only those needing initial configuration.
    """
    client = _get_api_client()
    if not client:
        click.echo("Error: Agent not registered. Run 'shuttersense-agent register' first.", err=True)
        raise SystemExit(1)

    try:
        response = client.get(f"/connectors?pending_only={str(pending).lower()}")
        data = response.json()

        if as_json:
            click.echo(json.dumps(data, indent=2))
            return

        connectors_list = data.get("connectors", [])

        if not connectors_list:
            if pending:
                click.echo("No connectors pending configuration.")
            else:
                click.echo("No connectors available for credential configuration.")
            return

        # Table header
        click.echo()
        click.echo(f"{'GUID':<30} {'NAME':<25} {'TYPE':<6} {'STATUS':<15} {'LOCAL CREDS':<12}")
        click.echo("-" * 90)

        for conn in connectors_list:
            status = "Pending" if conn["credential_location"] == "pending" else "Agent"
            local_creds = "Yes" if conn.get("has_local_credentials") else "No"

            click.echo(
                f"{conn['guid']:<30} "
                f"{conn['name'][:24]:<25} "
                f"{conn['type'].upper():<6} "
                f"{status:<15} "
                f"{local_creds:<12}"
            )

        click.echo()
        click.echo(f"Total: {data.get('total', len(connectors_list))} connector(s)")

    except Exception as e:
        click.echo(f"Error listing connectors: {str(e)}", err=True)
        raise SystemExit(1)


@connectors.command("configure")
@click.argument("guid")
@click.option(
    "--test/--no-test",
    default=True,
    help="Test credentials before storing (default: test)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing credentials without prompting",
)
def configure_connector(guid: str, test: bool, force: bool):
    """
    Configure credentials for a connector.

    Prompts for connector-specific credentials, optionally tests them,
    then stores them encrypted locally. After successful configuration,
    reports the capability to the server.

    GUID is the connector identifier (e.g., con_01abc123...).
    """
    client = _get_api_client()
    if not client:
        click.echo("Error: Agent not registered. Run 'shuttersense-agent register' first.", err=True)
        raise SystemExit(1)

    store = CredentialStore()

    # Check if credentials already exist
    if store.has_credentials(guid) and not force:
        if not click.confirm(f"Credentials already exist for {guid}. Overwrite?"):
            click.echo("Aborted.")
            return

    try:
        # Get connector metadata
        response = client.get(f"/connectors/{guid}/metadata")
        metadata = response.json()

        click.echo()
        click.echo(f"Configuring credentials for: {metadata['name']}")
        click.echo(f"Type: {metadata['type'].upper()}")
        click.echo()

        # Collect credentials based on field definitions
        credentials = {}
        for field in metadata.get("credential_fields", []):
            field_name = field["name"]
            field_type = field.get("type", "string")
            required = field.get("required", True)
            description = field.get("description", field_name)

            # Build prompt
            prompt = f"{description}"
            if not required:
                prompt += " (optional)"

            # Get input based on field type
            if field_type == "password":
                value = click.prompt(prompt, hide_input=True, default="" if not required else None)
            elif field_type == "json":
                click.echo(f"{prompt}:")
                click.echo("  (Enter JSON, then press Enter twice to finish)")
                lines = []
                while True:
                    line = click.prompt("", default="", show_default=False)
                    if not line:
                        break
                    lines.append(line)
                value = "\n".join(lines)
            else:
                value = click.prompt(prompt, default="" if not required else None)

            if value:
                credentials[field_name] = value

        click.echo()

        # Test credentials if requested
        if test:
            click.echo("Testing credentials...")
            success, message = _test_credentials(metadata["type"], credentials)

            if success:
                click.echo(click.style(f"✓ {message}", fg="green"))
            else:
                click.echo(click.style(f"✗ {message}", fg="red"))
                if not click.confirm("Credentials test failed. Store anyway?"):
                    click.echo("Aborted.")
                    return

        # Store credentials
        click.echo("Storing credentials...")
        store.store_credentials(
            connector_guid=guid,
            credentials=credentials,
            metadata={"connector_name": metadata["name"], "connector_type": metadata["type"]},
        )
        click.echo(click.style("✓ Credentials stored successfully", fg="green"))

        # Report capability to server
        click.echo("Reporting capability to server...")
        try:
            response = client.post(
                f"/connectors/{guid}/report-capability",
                json={"has_credentials": True},
            )
            result = response.json()

            if result.get("credential_location_updated"):
                click.echo(click.style("✓ Connector status updated (changed from pending to agent)", fg="green"))
                click.echo("  Note: Activate the connector in the WebUI to use it for jobs.")
            else:
                click.echo(click.style("✓ Capability reported to server", fg="green"))

        except Exception as e:
            click.echo(click.style(f"Warning: Failed to report capability: {str(e)}", fg="yellow"))
            click.echo("  Credentials are stored locally but server may not know about them.")
            click.echo("  The next heartbeat will update the server.")

    except Exception as e:
        click.echo(f"Error configuring connector: {str(e)}", err=True)
        raise SystemExit(1)


@connectors.command("remove")
@click.argument("guid")
@click.option(
    "--force",
    is_flag=True,
    help="Remove without confirmation",
)
def remove_credentials(guid: str, force: bool):
    """
    Remove stored credentials for a connector.

    GUID is the connector identifier (e.g., con_01abc123...).
    """
    store = CredentialStore()

    if not store.has_credentials(guid):
        click.echo(f"No credentials found for {guid}")
        return

    if not force:
        if not click.confirm(f"Remove credentials for {guid}?"):
            click.echo("Aborted.")
            return

    store.delete_credentials(guid)
    click.echo(click.style(f"✓ Credentials removed for {guid}", fg="green"))

    # Report removal to server
    client = _get_api_client()
    if client:
        try:
            client.post(
                f"/connectors/{guid}/report-capability",
                json={"has_credentials": False},
            )
            click.echo("✓ Server notified of credential removal")
        except Exception as e:
            click.echo(click.style(f"Warning: Failed to notify server: {str(e)}", fg="yellow"))


@connectors.command("show")
@click.argument("guid")
def show_credentials(guid: str):
    """
    Show stored credentials for a connector (masked).

    GUID is the connector identifier (e.g., con_01abc123...).
    """
    store = CredentialStore()

    creds = store.get_credentials(guid)
    if not creds:
        click.echo(f"No credentials found for {guid}")
        return

    click.echo()
    click.echo(f"Credentials for {guid}:")
    click.echo("-" * 40)

    for key, value in creds.items():
        if "password" in key.lower() or "secret" in key.lower() or "key" in key.lower():
            # Mask sensitive values
            masked = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
            click.echo(f"  {key}: {masked}")
        elif "json" in key.lower():
            # Show truncated JSON
            if len(value) > 50:
                click.echo(f"  {key}: {value[:47]}...")
            else:
                click.echo(f"  {key}: {value}")
        else:
            click.echo(f"  {key}: {value}")

    click.echo()


@connectors.command("test")
@click.argument("guid")
@click.option(
    "--report/--no-report",
    default=True,
    help="Report capability to server after successful test (default: report)",
)
def test_credentials(guid: str, report: bool):
    """
    Test existing credentials for a connector.

    Tests stored credentials without modifying them. If the test succeeds
    and --report is enabled (default), reports the capability to the server.

    This is useful for:
    - Verifying credentials still work
    - Re-reporting capability after server issues
    - Initial sync when credentials were configured offline

    GUID is the connector identifier (e.g., con_01abc123...).

    Examples:
        # Test and report capability
        shuttersense-agent connectors test con_01abc123...

        # Test only, don't report to server
        shuttersense-agent connectors test con_01abc123... --no-report
    """
    store = CredentialStore()

    # Get stored credentials
    creds = store.get_credentials(guid)
    if not creds:
        click.echo(f"No credentials found for {guid}", err=True)
        click.echo("Use 'shuttersense-agent connectors configure' to set up credentials first.")
        raise SystemExit(1)

    # Get metadata to determine connector type
    metadata = store.get_metadata(guid)
    if not metadata or "connector_type" not in metadata:
        click.echo(f"Missing metadata for {guid}. Please reconfigure credentials.", err=True)
        raise SystemExit(1)

    connector_type = metadata["connector_type"]
    connector_name = metadata.get("connector_name", guid)

    click.echo()
    click.echo(f"Testing credentials for: {connector_name}")
    click.echo(f"Type: {connector_type.upper()}")
    click.echo()

    # Test credentials
    click.echo("Testing connection...")
    success, message = _test_credentials(connector_type, creds)

    if success:
        click.echo(click.style(f"✓ {message}", fg="green"))
    else:
        click.echo(click.style(f"✗ {message}", fg="red"))
        raise SystemExit(1)

    # Report capability if requested
    if report:
        client = _get_api_client()
        if not client:
            click.echo()
            click.echo(click.style("Warning: Agent not registered. Cannot report to server.", fg="yellow"))
            click.echo("Run 'shuttersense-agent register' to connect to the server.")
            return

        click.echo()
        click.echo("Reporting capability to server...")
        try:
            response = client.post(
                f"/connectors/{guid}/report-capability",
                json={"has_credentials": True},
            )
            result = response.json()

            if result.get("credential_location_updated"):
                click.echo(click.style("✓ Connector status updated (changed from pending to agent)", fg="green"))
            else:
                click.echo(click.style("✓ Capability reported to server", fg="green"))

        except Exception as e:
            click.echo(click.style(f"Warning: Failed to report capability: {str(e)}", fg="yellow"))
            click.echo("  Credentials are valid but server was not notified.")
            click.echo("  The next heartbeat will update the server.")

    click.echo()
