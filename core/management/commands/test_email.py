"""
Django management command to test email configuration.

Usage:
    python manage.py test_email recipient@example.com
    python manage.py test_email recipient@example.com --subject "Custom Subject"
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = 'Send a test email to verify SMTP configuration is working'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            type=str,
            help='Email address to send test email to'
        )
        parser.add_argument(
            '--subject',
            type=str,
            default='Kurutracker - Test Email',
            help='Email subject line (default: "Kurutracker - Test Email")'
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        subject = options['subject']

        self.stdout.write(self.style.WARNING('Testing email configuration...'))
        self.stdout.write(f'Recipient: {recipient}')
        self.stdout.write(f'Subject: {subject}')
        self.stdout.write(f'SMTP Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'SMTP Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'SMTP Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'From Email: {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write('')

        # Create HTML email content
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Poppins', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #3185FC; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #F5EFE7; padding: 30px; border: 1px solid #e5e7eb; }}
                .footer {{ text-align: center; margin-top: 30px; padding: 20px; color: #7A6652; font-size: 12px; }}
                .success-box {{ background: #10b981; color: white; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-weight: 700;">Test Email</h1>
                </div>
                <div class="content">
                    <div class="success-box">
                        <strong>✅ Success!</strong> Your SMTP configuration is working correctly.
                    </div>

                    <h2>Email Configuration Details:</h2>
                    <ul>
                        <li><strong>Backend:</strong> {settings.EMAIL_BACKEND}</li>
                        <li><strong>Host:</strong> {settings.EMAIL_HOST}:{settings.EMAIL_PORT}</li>
                        <li><strong>From Address:</strong> {settings.DEFAULT_FROM_EMAIL}</li>
                        <li><strong>TLS Enabled:</strong> {settings.EMAIL_USE_TLS}</li>
                    </ul>

                    <p>If you received this email, it means:</p>
                    <ul>
                        <li>✅ Your SMTP credentials are correct</li>
                        <li>✅ Your email backend is properly configured</li>
                        <li>✅ Django can send emails successfully</li>
                        <li>✅ Notifications will be delivered to users</li>
                    </ul>

                    <p style="margin-top: 30px; font-size: 14px; color: #7A6652; background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #F9DC5C;">
                        <strong>Note:</strong> This is a test email sent from the Kurutracker management command.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; 2025 Kuru Tracker - Asset Management System</p>
                    <p>This is a test email. You can safely ignore or delete it.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        plain_message = f"""
        TEST EMAIL - SMTP Configuration Verification

        ✅ Success! Your SMTP configuration is working correctly.

        Email Configuration Details:
        - Backend: {settings.EMAIL_BACKEND}
        - Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}
        - From Address: {settings.DEFAULT_FROM_EMAIL}
        - TLS Enabled: {settings.EMAIL_USE_TLS}

        If you received this email, it means:
        ✅ Your SMTP credentials are correct
        ✅ Your email backend is properly configured
        ✅ Django can send emails successfully
        ✅ Notifications will be delivered to users

        ---
        Kuru Tracker - Asset Management System
        This is a test email. You can safely ignore or delete it.
        """

        try:
            # Send the email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,
            )

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('✅ Email sent successfully!'))
            self.stdout.write('')
            self.stdout.write('Please check the recipient inbox:')
            self.stdout.write(f'  📧 {recipient}')
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Note: Gmail may take a few seconds to deliver the email.'))
            self.stdout.write('If you don\'t see it, check the spam folder.')

        except Exception as e:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('❌ Failed to send email!'))
            self.stdout.write('')
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            self.stdout.write('')
            self.stdout.write('Common issues:')
            self.stdout.write('  1. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env')
            self.stdout.write('  2. Ensure Gmail App Password is correct (16 characters, no spaces)')
            self.stdout.write('  3. Verify 2-Factor Authentication is enabled on Gmail account')
            self.stdout.write('  4. Check if "Less secure app access" is disabled (use App Passwords instead)')
            self.stdout.write('  5. Verify SMTP host and port are correct')
            self.stdout.write('')
            raise CommandError(f'Email sending failed: {str(e)}')
