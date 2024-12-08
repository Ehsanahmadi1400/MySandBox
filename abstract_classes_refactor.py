from abc import ABC, abstractmethod


class ListMixin:
    def list_items(self, *args, **kwargs):
        raise NotImplementedError("list functionality has not been implemented")


class AbstractCustomerClient(ABC):
    """
    Abstract class for customers

    *** Clients could be either customer or merchant
    *** this abstract class serves as a blueprint for
    *** client management systems providing methods for CRUD operations.

    """
    def __init__(self):
        pass


    @classmethod
    @abstractmethod
    def create_customer(cls,  *args, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def retrieve_customer(cls,  *args, **kwargs):
        pass

    @classmethod
    def list_items(cls, *args, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def update_customer(cls,  *args, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def delete_customer(cls,  *args, **kwargs):
        pass


class AbstractMerchantClient(ABC):
    """
    Abstract class for merchants

    *** Clients could be either customer or merchant
    *** this abstract class serves as a blueprint for
    *** merchants management systems providing methods for CRUD operations.

    """

    def __init__(self):
        pass

    @classmethod
    @abstractmethod
    def create_merchant(cls,  *args, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def retrieve_merchant(cls,  *args, **kwargs):
        pass


    @classmethod
    def list_items(cls,  *args, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def update_merchant(cls,  *args, **kwargs):
        pass

    @classmethod
    @abstractmethod
    def delete_merchant(cls,  *args, **kwargs):
        pass


class AbstractTransfer(ABC, ListMixin):
    """
    Abstract class for transfer operations:

    *** This class has three abstract methods that are mandatory
    *** to be implemented in subclasses, and it inherits a method
    *** named list_items from ListMixin that is optional.

    """
    def __init__(self):
        pass

    @abstractmethod
    def initiate_transfer(self,  *args, **kwargs):
        pass

    @abstractmethod
    def retrieve_transfer(self,  *args, **kwargs):
        pass

    @abstractmethod
    def cancel_transfer(self,  *args, **kwargs):
        pass


class AbstractRecurringTransfer(ABC, ListMixin):
    """
    Abstract class for Recurring transfer operations:

    *** Similar to Transfer class, this class also has three abstract
    *** methods that are mandatory to be implemented in subclasses
    *** and it inherits list_items from ListMixin that is optional.

    """
    def __init__(self):
        pass

    @abstractmethod
    def initiate_transfer(self,  *args, **kwargs):
        pass

    @abstractmethod
    def retrieve_transfer(self,  *args, **kwargs):
        pass

    @abstractmethod
    def cancel_transfer(self,  *args, **kwargs):
        pass


class AbstractPayment(ABC, ListMixin):
    """
    Abstract class for payment operations:

    *** This class handles initiation, retrieval, and update functionalities
    *** for payments.

    """
    def __init__(self):
        pass

    @abstractmethod
    def initiate_payment(self,  *args, **kwargs):
        pass

    @abstractmethod
    def retrieve_payment(self,  *args, **kwargs):
        pass

    @abstractmethod
    def update_payment(self,  *args, **kwargs):
        pass


class AbstractRecurringPayment(ABC, ListMixin):
    """
    Abstract class for payment operations:

    *** This class handles initiation, retrieval, and update functionalities
    *** for recurring payments.

    """
    def __init__(self):
        pass

    @abstractmethod
    def initiate_payment(self,  *args, **kwargs):
        pass

    @abstractmethod
    def retrieve_payment(self,  *args, **kwargs):
        pass

    @abstractmethod
    def update_payment(self,  *args, **kwargs):
        pass


class AbstractFundingSource(ABC, ListMixin):
    """
    Abstract class for determining funding source

    *** explanations will be added

    """
    def __init__(self):
        pass

    @abstractmethod
    def create_funding_source(self,  *args, **kwargs):
        pass

    @abstractmethod
    def create_funding_source_manually(self,  *args, **kwargs):
        pass

    @abstractmethod
    def update_funding_source(self,  *args, **kwargs):
        pass

    @abstractmethod
    def retrieve_funding_source(self,  *args, **kwargs):
        pass

    @abstractmethod
    def get_funding_source_balance(self,  *args, **kwargs):
        pass

    @abstractmethod
    def verify_micro_deposit(self,  *args, **kwargs):
        pass


class AbstractWebhook(ABC, ListMixin):
    """
    Abstract class for handling webhook tasks

    *** explanations will be added

    """
    def __init__(self):
        pass

    @abstractmethod
    def create_webhook(self,  *args, **kwargs):
        pass

    @abstractmethod
    def retrieve_webhook(self,  *args, **kwargs):
        pass

    @abstractmethod
    def update_webhook(self,  *args, **kwargs):
        pass

    @abstractmethod
    def delete_webhook(self,  *args, **kwargs):
        pass
