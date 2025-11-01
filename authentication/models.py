# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# -------------------------------------------------------
#            ACCOUNT MANAGER (OWNER + ORG)
# -------------------------------------------------------
class AccountManager(BaseUserManager):

    def create_user(
        self,
        email,
        password=None,
        blockchain_address=None,
        private_key=None,
        role="ORGANIZATION"
    ):
        if not email:
            raise ValueError("Email is required")

        if not blockchain_address:
            raise ValueError("Blockchain address required")

        if not private_key:
            raise ValueError("Private key required")

        user = self.model(
            email=self.normalize_email(email),
            role=role,
            blockchain_address=blockchain_address,
            private_key=private_key,
        )

        user.set_password(password)

        # OWNER is automatically authorized (same as smart contract constructor)
        if role == "OWNER":
            user.is_authorized = True
        else:
            user.is_authorized = False  # ORGANIZATION must be authorized on-chain first

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        """Superuser is automatically the OWNER"""
        user = self.create_user(
            email=email,
            password=password,
            role="OWNER",
            blockchain_address="OWNER_SUPERUSER",
            private_key="OWNER_SUPERUSER_KEY"
        )
        user.is_staff = True
        user.is_superuser = True
        user.is_authorized = True
        user.save(using=self._db)
        return user


# -------------------------------------------------------
#                   ACCOUNT MODEL
# -------------------------------------------------------
class Account(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = (
        ('OWNER', 'Owner'),             # Only 1 — must match the smart contract owner
        ('ORGANIZATION', 'Organization') # Authorized issuer
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ORGANIZATION')

    # Blockchain identity fields
    blockchain_address = models.CharField(max_length=200, unique=True)
    private_key = models.TextField()

    # Django-side record of authorization (reflects smart contract authorizedIssuers)
    is_authorized = models.BooleanField(default=False)

    # Django required fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Only email + password

    objects = AccountManager()

    def __str__(self):
        return f"{self.email} [{self.role}]"


# -------------------------------------------------------
#                CERTIFICATE MODEL
# -------------------------------------------------------
class Certificate(models.Model):
    """
    Mirrors on-chain certificate logic (CertificateRecord struct)
    """

    certificate_id = models.CharField(max_length=100, unique=True)

    # Real-world metadata (stored in DB, NOT on-chain)
    recipient_name = models.CharField(max_length=200)
    course_name = models.CharField(max_length=200)
    issued_date = models.DateField(auto_now_add=True)

    # Issuer = ORGANIZATION account
    issued_by = models.ForeignKey(Account, on_delete=models.CASCADE)

    # Blockchain metadata
    blockchain_hash = models.CharField(max_length=256)        # dataHash
    transaction_hash = models.CharField(max_length=256, blank=True, null=True)

    # Retrieved from contract:
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.certificate_id} - {self.recipient_name}"
