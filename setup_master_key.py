#!/usr/bin/env python3
"""
Master Encryption Key Setup Tool

Interactive tool for generating and configuring the master encryption key
used to encrypt remote storage credentials in the database.

This tool implements tasks T010-T014 from the implementation plan:
- T010: Interactive key generation using Fernet.generate_key()
- T011: Platform-specific environment variable instructions
- T012: Key validation function (Fernet format)
- T013: Option to save key to ~/.photo_admin_master_key.txt with chmod 600
- T014: Warnings about key loss consequences

Usage:
    python3 setup_master_key.py              # Generate new key
    python3 setup_master_key.py --validate   # Validate existing key
    python3 setup_master_key.py --rotate     # Rotate existing key
"""

import argparse
import os
import platform
import sys
from pathlib import Path

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:
    print("Error: cryptography library not installed")
    print("Install with: pip install cryptography")
    sys.exit(1)


class MasterKeyManager:
    """Manages master encryption key generation and configuration"""

    ENV_VAR_NAME = "PHOTO_ADMIN_MASTER_KEY"
    DEFAULT_KEY_FILE = Path.home() / ".photo_admin_master_key.txt"

    def __init__(self):
        self.platform_name = platform.system()

    def generate_key(self) -> bytes:
        """
        Generate a new Fernet encryption key.

        Returns:
            bytes: A cryptographically secure Fernet key

        Task: T010 - Interactive key generation using Fernet.generate_key()
        """
        return Fernet.generate_key()

    def validate_key(self, key: str) -> tuple[bool, str]:
        """
        Validate that a key string is a valid Fernet key.

        Args:
            key: Key string to validate

        Returns:
            tuple: (is_valid, error_message)

        Task: T012 - Key validation function to check Fernet format
        """
        if not key:
            return False, "Key is empty"

        try:
            # Try to create a Fernet cipher with the key
            Fernet(key.encode() if isinstance(key, str) else key)
            return True, ""
        except Exception as e:
            return False, f"Invalid Fernet key format: {str(e)}"

    def get_platform_instructions(self, key: str) -> str:
        """
        Get platform-specific instructions for setting environment variable.

        Args:
            key: The encryption key to configure

        Returns:
            str: Platform-specific setup instructions

        Task: T011 - Platform-specific environment variable instructions
        """
        instructions = []

        instructions.append(f"\n{'='*70}")
        instructions.append("PLATFORM-SPECIFIC SETUP INSTRUCTIONS")
        instructions.append(f"{'='*70}\n")

        if self.platform_name == "Darwin":  # macOS
            instructions.append("macOS Setup:")
            instructions.append("-" * 70)
            instructions.append(f"\n1. Add to ~/.zshrc (or ~/.bash_profile for bash):")
            instructions.append(f'   export {self.ENV_VAR_NAME}="{key}"')
            instructions.append(f"\n2. Reload your shell configuration:")
            instructions.append(f"   source ~/.zshrc")
            instructions.append(f"\n3. Verify the key is set:")
            instructions.append(f"   echo ${self.ENV_VAR_NAME}")

        elif self.platform_name == "Linux":
            instructions.append("Linux Setup:")
            instructions.append("-" * 70)
            instructions.append(f"\n1. Add to ~/.bashrc (or ~/.zshrc for zsh):")
            instructions.append(f'   export {self.ENV_VAR_NAME}="{key}"')
            instructions.append(f"\n2. Reload your shell configuration:")
            instructions.append(f"   source ~/.bashrc")
            instructions.append(f"\n3. Verify the key is set:")
            instructions.append(f"   echo ${self.ENV_VAR_NAME}")
            instructions.append(f"\n4. Optional: Add to /etc/environment for system-wide access:")
            instructions.append(f'   {self.ENV_VAR_NAME}="{key}"')

        elif self.platform_name == "Windows":
            instructions.append("Windows Setup:")
            instructions.append("-" * 70)
            instructions.append(f"\n1. Set user environment variable (recommended):")
            instructions.append(f"   setx {self.ENV_VAR_NAME} \"{key}\"")
            instructions.append(f"\n2. Or set system-wide (requires admin):")
            instructions.append(f"   setx {self.ENV_VAR_NAME} \"{key}\" /M")
            instructions.append(f"\n3. Restart your terminal/command prompt")
            instructions.append(f"\n4. Verify the key is set:")
            instructions.append(f"   echo %{self.ENV_VAR_NAME}%")
            instructions.append(f"\nAlternatively, use System Properties > Environment Variables GUI")

        else:
            instructions.append(f"Unknown Platform: {self.platform_name}")
            instructions.append("-" * 70)
            instructions.append(f"\nSet environment variable manually:")
            instructions.append(f'{self.ENV_VAR_NAME}="{key}"')

        instructions.append(f"\n{'='*70}\n")
        return "\n".join(instructions)

    def save_key_to_file(self, key: str, filepath: Path = None) -> tuple[bool, str]:
        """
        Save encryption key to a secure file with restricted permissions.

        Args:
            key: Encryption key to save
            filepath: Path to save key (default: ~/.photo_admin_master_key.txt)

        Returns:
            tuple: (success, message)

        Task: T013 - Option to save key to ~/.photo_admin_master_key.txt with chmod 600
        """
        if filepath is None:
            filepath = self.DEFAULT_KEY_FILE

        try:
            # Write key to file
            filepath.write_text(key + "\n", encoding="utf-8")

            # Set file permissions to 600 (owner read/write only)
            if self.platform_name != "Windows":
                os.chmod(filepath, 0o600)
                perm_msg = "Permissions set to 600 (owner read/write only)"
            else:
                perm_msg = "Note: Set file permissions manually on Windows"

            return True, f"Key saved to: {filepath}\n{perm_msg}"

        except Exception as e:
            return False, f"Failed to save key: {str(e)}"

    def get_key_loss_warnings(self) -> str:
        """
        Get warnings about key loss consequences.

        Returns:
            str: Warning messages about key loss

        Task: T014 - Warnings about key loss consequences
        """
        warnings = []

        warnings.append(f"\n{'!'*70}")
        warnings.append("⚠️  CRITICAL: MASTER KEY SECURITY WARNINGS")
        warnings.append(f"{'!'*70}\n")

        warnings.append("CONSEQUENCES OF KEY LOSS:")
        warnings.append("-" * 70)
        warnings.append("❌ ALL encrypted credentials will become PERMANENTLY UNRECOVERABLE")
        warnings.append("❌ Remote collections (S3, GCS, SMB) will become INACCESSIBLE")
        warnings.append("❌ You will need to RECREATE ALL CONNECTORS with new credentials")
        warnings.append("❌ Historical analysis results may become UNUSABLE")
        warnings.append("")

        warnings.append("SECURITY BEST PRACTICES:")
        warnings.append("-" * 70)
        warnings.append("✓ NEVER commit this key to version control")
        warnings.append("✓ STORE a backup copy in a secure password manager")
        warnings.append("✓ DO NOT share this key via email or chat")
        warnings.append("✓ PROTECT the key file with strict permissions (chmod 600)")
        warnings.append("✓ ROTATE the key periodically (use --rotate flag)")
        warnings.append("")

        warnings.append("KEY ROTATION:")
        warnings.append("-" * 70)
        warnings.append("If you need to rotate the key in the future:")
        warnings.append("1. Run: python3 setup_master_key.py --rotate")
        warnings.append("2. The tool will decrypt existing credentials with the old key")
        warnings.append("3. Re-encrypt them with the new key")
        warnings.append("4. Update the environment variable with the new key")
        warnings.append("")

        warnings.append(f"{'!'*70}\n")
        return "\n".join(warnings)

    def check_existing_key(self) -> tuple[bool, str, str]:
        """
        Check if a master key already exists in environment.

        Returns:
            tuple: (exists, key_value, source)
        """
        # Check environment variable
        env_key = os.environ.get(self.ENV_VAR_NAME)
        if env_key:
            return True, env_key, "environment variable"

        # Check default key file
        if self.DEFAULT_KEY_FILE.exists():
            try:
                file_key = self.DEFAULT_KEY_FILE.read_text(encoding="utf-8").strip()
                if file_key:
                    return True, file_key, f"file: {self.DEFAULT_KEY_FILE}"
            except Exception:
                pass

        return False, "", ""

    def interactive_setup(self):
        """
        Run interactive master key setup workflow.

        This is the main entry point that combines all tasks T010-T014.
        """
        print("\n" + "="*70)
        print("Photo Admin - Master Encryption Key Setup")
        print("="*70 + "\n")

        # Check for existing key
        exists, existing_key, source = self.check_existing_key()
        if exists:
            print(f"⚠️  Existing key detected in {source}")
            print("\nOptions:")
            print("  1. Keep existing key and show setup instructions")
            print("  2. Generate a new key (will invalidate existing credentials)")
            print("  3. Exit")

            while True:
                choice = input("\nYour choice (1/2/3): ").strip()
                if choice == "1":
                    # Validate and show instructions for existing key
                    is_valid, error = self.validate_key(existing_key)
                    if not is_valid:
                        print(f"\n❌ Existing key is invalid: {error}")
                        print("Generating new key...\n")
                        break
                    print("\n✓ Existing key is valid")
                    print(self.get_platform_instructions(existing_key))
                    return
                elif choice == "2":
                    print("\n⚠️  WARNING: Generating a new key will make existing encrypted")
                    print("credentials unrecoverable. Continue? (yes/no): ", end="")
                    confirm = input().strip().lower()
                    if confirm not in ("yes", "y"):
                        print("Cancelled.")
                        return
                    break
                elif choice == "3":
                    print("Exiting.")
                    return
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")

        # Generate new key (T010)
        print("Generating new master encryption key...")
        key_bytes = self.generate_key()
        key_str = key_bytes.decode('utf-8')

        # Validate key (T012)
        is_valid, error = self.validate_key(key_str)
        if not is_valid:
            print(f"\n❌ Generated key validation failed: {error}")
            print("This should not happen. Please report this issue.")
            sys.exit(1)

        print("✓ Key generated successfully\n")

        # Display the key
        print("="*70)
        print("YOUR MASTER ENCRYPTION KEY:")
        print("="*70)
        print(f"\n{key_str}\n")
        print("="*70)

        # Show warnings (T014)
        print(self.get_key_loss_warnings())

        # Ask to save to file (T013)
        print("Would you like to save this key to a secure file?")
        print(f"Location: {self.DEFAULT_KEY_FILE}")
        save_choice = input("Save to file? (yes/no): ").strip().lower()

        if save_choice in ("yes", "y"):
            success, message = self.save_key_to_file(key_str)
            if success:
                print(f"\n✓ {message}\n")
            else:
                print(f"\n❌ {message}\n")

        # Show platform instructions (T011)
        print(self.get_platform_instructions(key_str))

        print("\n✓ Setup complete!")
        print("\nNext steps:")
        print("1. Set the environment variable as shown above")
        print("2. Verify with: python3 web_server.py (will check for the key)")
        print("3. Start using the photo-admin web application\n")

    def validate_existing_key(self):
        """Validate an existing key from environment or file."""
        print("\n" + "="*70)
        print("Validating Existing Master Key")
        print("="*70 + "\n")

        exists, key_value, source = self.check_existing_key()

        if not exists:
            print(f"❌ No master key found in:")
            print(f"   - Environment variable: {self.ENV_VAR_NAME}")
            print(f"   - Key file: {self.DEFAULT_KEY_FILE}")
            print("\nRun without --validate flag to generate a new key.")
            sys.exit(1)

        print(f"Found key in: {source}")

        is_valid, error = self.validate_key(key_value)

        if is_valid:
            print("✓ Key is valid and properly formatted")
            print(f"\nKey preview: {key_value[:20]}...{key_value[-20:]}")
        else:
            print(f"❌ Key validation failed: {error}")
            print("\nGenerate a new key with: python3 setup_master_key.py")
            sys.exit(1)


def main():
    """Main entry point for the master key setup tool."""
    parser = argparse.ArgumentParser(
        description="Photo Admin Master Encryption Key Setup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 setup_master_key.py              # Interactive setup (generate new key)
  python3 setup_master_key.py --validate   # Validate existing key
  python3 setup_master_key.py --rotate     # Rotate existing key (future feature)

The master key is used to encrypt remote storage credentials (S3, GCS, SMB)
stored in the database. Keep this key secure and never commit it to version control.
        """
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing master key instead of generating new one"
    )

    parser.add_argument(
        "--rotate",
        action="store_true",
        help="Rotate existing master key (re-encrypt all credentials)"
    )

    args = parser.parse_args()

    manager = MasterKeyManager()

    if args.validate:
        manager.validate_existing_key()
    elif args.rotate:
        print("Key rotation feature coming soon (Phase 2 - Connector service)")
        print("This will decrypt credentials with old key and re-encrypt with new key")
        sys.exit(1)
    else:
        manager.interactive_setup()


if __name__ == "__main__":
    main()
