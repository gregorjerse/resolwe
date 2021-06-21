"""Resolwe billing model."""
import logging

from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.utils.timezone import now

from resolwe.flow.models import Collection, Data
from resolwe.storage.connectors import DEFAULT_CONNECTOR_PRIORITY, connectors
from resolwe.storage.connectors.baseconnector import BaseStorageConnector
from resolwe.storage.connectors.transfer import Transfer
from resolwe.storage.connectors.utils import paralelize
from resolwe.storage.settings import STORAGE_CONNECTORS

logger = logging.getLogger(__name__)


class ActiveBillingAccountManager(models.Manager):
    """Return only active BillingAccount objects."""

    def get_queryset(self) -> models.QuerySet:
        """Override default queryset."""
        return super().get_queryset().filter(active=True)


class AllBillingAccountsManager(models.Manager):
    """Return all (even inactive) BillingAccount objects."""


class BillingAccount(models.Model):
    """The costs are computed per BillingAccount."""

    def delete(self, *args, **kwargs):
        """Set the active flag to false.

        To preserve the history BillingAccount should never be deleted.
        """
        self.active = False
        self.save()

    # access all objects through all_objects storage manager.
    all_objects = AllBillingAccountsManager()

    # by default return only active BillingAccounts
    objects = ActiveBillingAccountManager()

    #: the user for this billing account
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    #: when deleting BillingAccount active is set to False
    active = models.BooleanField(default=True)


class DefaultUserBillingAccount(models.Model):
    """Default BillingAccount for the user."""

    #: reference to the User model
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    #: reference to the BillingAccount object
    billing_account = models.OneToOneField(BillingAccount, on_delete=models.CASCADE)


class BillingCollection(models.Model):
    """Connects Collection with the BillingAccount."""

    #: reference to a Collection
    collection = models.OneToOneField(Collection, on_delete=models.CASCADE)

    #: reference to a BillingAccount
    billing_account = models.ForeignKey(BillingAccount)


class DataHistory(models.Model):
    """Keeps track of Data instance resource usage even after it is deleted."""

    #: reference to a Data instance
    data = models.OneToOneField(Data, on_delete=models.PROTECT, null=True)

    #: creation date and time
    created = models.DateTimeField(db_index=True, null=False)

    #: deletion date and time
    deleted = models.DateTimeField(db_index=True, null=True, blank=True)

    #: reference to a Collection instance
    collection = models.ForeignKey(Collection, null=True, on_delete=models.PROTECT)

    #: how many cpu cores were requested during computation
    cpu = models.models.PositiveSmallIntegerField(blank=False, null=False)

    #: how many gigabytes of memory were requested during computation
    memory = models.models.PositiveSmallIntegerField(blank=False, null=False)

    #: the amount of seconds used for the computation
    processing_time = models.models.PositiveIntegerField(null=False, default=0)

    #: id of the referenced Data instance
    data_id = models.PositiveIntegerField(blank=False, null=False)

    #: relavant storage pricing entries
    storage_pricing = models.ManyToManyField("StoragePrice", through="StorageHistory")

    #: relavant computation pricing entries
    computational_pricing = models.ManyToManyField("ComputePrice")


class StoragePrice(models.Model):
    """Price of the given storage."""

    #: price in gigabytes per month
    price = models.DecimalField(max_digits=10, decimal_places=8)

    #: datetime interval when price is valid (can be unbounded from above)
    valid = DateTimeRangeField(blank=False, null=False)

    #: name of the storage type
    storage_type = models.CharFiels(max_length=64, null=False, blank=False)


class StorageHistory(models.Model):
    """Storage prices associated with the given DataHistory instance.

    This relation has to be updated periodically.
    """

    #: the interval when Data was stored with the given price
    interval = DateTimeRangeField(blank=False, null=False)

    #: reference to StoragePrice instance
    storage_price = models.ForeignKey(StoragePrice)


class ComputePrice(models.Model):
    """Price of the computaiton."""

    #: number of CPUs available on the node.
    cpu = models.models.PositiveSmallIntegerField(blank=False, null=False)

    #: ammount of RAM available on the node.
    memory = models.models.PositiveIntegerField(blank=False, null=False)

    #: datetime interval when price is valid (can be unbounded from above)
    valid = DateTimeRangeField(blank=False, null=False)

    #: price for one hour of computation
    price = models.DecimalField(max_digits=10, decimal_places=8)
