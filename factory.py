from abc import ABC, abstractmethod

from helcim_provide_refactor import HelcimSinglePaymentStrategy, HelcimRecurringPaymentStrategy, \
    HelcimSingleTransferStrategy, HelcimRecurringTransferStrategy
from helcim_provider_refactor import HelcimCustomerClient, HelcimMerchantClient


class FinancialProviderFactory(ABC):
    """
     *** This interface provides the structure for concrete factory classes.
     *** Consequently each concrete factory will have to create specific implementations for
     *** customer clients, merchant clients, payment strategies, and transfer strategies.

    """
    @abstractmethod
    def create_customer_client(self, *args, **kwargs):
        pass

    @abstractmethod
    def create_merchant_client(self, *args, **kwargs):
        pass

    @abstractmethod
    def create_single_payment_strategy(self, *args, **kwargs):
        pass

    @abstractmethod
    def create_recurring_payment_strategy(self, *args, **kwargs):
        pass

    @abstractmethod
    def create_single_transfer_strategy(self, *args, **kwargs):
        pass

    @abstractmethod
    def create_recurring_transfer_strategy(self, *args, **kwargs):
        pass


class HelcimFactory(FinancialProviderFactory):
    def create_customer_client(self, *args, **kwargs):
        return HelcimCustomerClient()

    def create_merchant_client(self, *args, **kwargs):
        return HelcimMerchantClient()

    def create_single_payment_strategy(self, *args, **kwargs):
        return HelcimSinglePaymentStrategy()

    def create_recurring_payment_strategy(self, *args, **kwargs):
        return HelcimRecurringPaymentStrategy()

    def create_single_transfer_strategy(self, *args, **kwargs):
        return HelcimSingleTransferStrategy()

    def create_recurring_transfer_strategy(self, *args, **kwargs):
        return HelcimRecurringTransferStrategy()
