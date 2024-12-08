from abstract_classes_refactor import AbstractCustomerClient, AbstractMerchantClient, AbstractSingleTransfer, \
    AbstractRecurringTransfer, AbstractSinglePayment, AbstractRecurringPayment


class HelcimCustomerClient(AbstractCustomerClient):
    def __init__(self):
        super().__init__()

    @classmethod
    def create_customer(cls, *args, **kwargs):
        # Implementation for creating a Helcim customer
        print("Creating Helcim customer with data:", args, kwargs)

    @classmethod
    def retrieve_customer(cls, *args, **kwargs):
        # Implementation for retrieving a Helcim customer
        print("Retrieving Helcim customer with ID:", args, kwargs)

    @classmethod
    def update_customer(cls, *args, **kwargs):
        # Implementation for updating a Helcim customer
        print("Updating Helcim customer with ID:", args, kwargs)

    @classmethod
    def delete_customer(cls, *args, **kwargs):
        # Implementation for deleting a Helcim customer
        print("Deleting Helcim customer with ID:", args, kwargs)


class HelcimMerchantClient(AbstractMerchantClient):
    def __init__(self):
        super().__init__()

    @classmethod
    def create_merchant(cls, *args, **kwargs):
        # Implementation for creating a Helcim merchant
        print("Creating Helcim merchant with data:", args, kwargs)

    @classmethod
    def retrieve_merchant(cls, *args, **kwargs):
        # Implementation for retrieving a Helcim merchant
        print("Retrieving Helcim merchant with ID:", args, kwargs)

    @classmethod
    def update_merchant(cls, *args, **kwargs):
        # Implementation for updating a Helcim merchant
        print("Updating Helcim merchant with ID:", args, kwargs)

    @classmethod
    def delete_merchant(cls, *args, **kwargs):
        # Implementation for deleting a Helcim merchant
        print("Deleting Helcim merchant with ID:", args, kwargs)


class HelcimSinglePaymentStrategy(AbstractSinglePayment):
    def __init__(self):
        super().__init__()

    def initiate_payment(self, *args, **kwargs):
        # Implementation for initiating a single Helcim payment
        print("Initiating single Helcim payment with data:", args, kwargs)

    def retrieve_payment(self, *args, **kwargs):
        # Implementation for retrieving a single Helcim payment
        print("Retrieving single Helcim payment with ID:", args, kwargs)

    def update_payment(self, *args, **kwargs):
        # Implementation for updating a single Helcim payment
        print("Updating single Helcim payment with ID:", args, kwargs)


class HelcimRecurringPaymentStrategy(AbstractRecurringPayment):
    def __init__(self):
        super().__init__()

    def initiate_payment(self, *args, **kwargs):
        # Implementation for initiating a recurring Helcim payment
        print("Initiating recurring Helcim payment with data:", args, kwargs)

    def retrieve_payment(self, *args, **kwargs):
        # Implementation for retrieving a recurring Helcim payment
        print("Retrieving recurring Helcim payment with ID:", args, kwargs)

    def update_payment(self, *args, **kwargs):
        # Implementation for updating a recurring Helcim payment
        print("Updating recurring Helcim payment with ID:", args, kwargs)


class HelcimSingleTransferStrategy(AbstractSingleTransfer):
    def __init__(self):
        super().__init__()

    def initiate_transfer(self, *args, **kwargs):
        # Implementation for initiating a single Helcim transfer
        print("Initiating single Helcim transfer with data:", args, kwargs)

    def retrieve_transfer(self, *args, **kwargs):
        # Implementation for retrieving a single Helcim transfer
        print("Retrieving single Helcim transfer with ID:", args, kwargs)

    def cancel_transfer(self, *args, **kwargs):
        # Implementation for cancelling a single Helcim transfer
        print("Cancelling single Helcim transfer with ID:", args, kwargs)


class HelcimRecurringTransferStrategy(AbstractRecurringTransfer):
    def __init__(self):
        super().__init__()

    def initiate_transfer(self, *args, **kwargs):
        # Implementation for initiating a recurring Helcim transfer
        print("Initiating recurring Helcim transfer with data:", args, kwargs)

    def retrieve_transfer(self, *args, **kwargs):
        # Implementation for retrieving a recurring Helcim transfer
        print("Retrieving recurring Helcim transfer with ID:", args, kwargs)

    def cancel_transfer(self, *args, **kwargs):
        # Implementation for cancelling a recurring Helcim transfer
        print("Cancelling recurring Helcim transfer with ID:", args, kwargs)

